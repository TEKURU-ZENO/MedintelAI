"""
Fits when (and whether) the local VLM reading replaces the PP-OCR / TrOCR ensemble choice for a line.

Replays the installed ensemble (routing threshold, selection rule, calibration from <checkpoint>/ensemble.json)
on validation candidates that also carry VLM readings (scripts/collect_ensemble_candidates.py --add_vlm), and
grid-searches:
  gate       run the VLM only when the ensemble's calibrated confidence is below this
  mode       plain transcription prompt, or prompt with both engines' readings as hints
  anchor     accept only if the VLM text is within this normalised edit distance of an engine reading
  min_conf   minimum VLM token confidence
--install writes <checkpoint>/vlm.json (used by the engine when HTR_VLM=1).
"""
import argparse
import itertools
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.train_trocr_medical import _edit_distance  # noqa: E402


def load_ensemble(model_dir):
    cfg = json.loads((Path(model_dir) / "ensemble.json").read_text(encoding="utf-8"))
    return cfg["printed_conf_threshold"], cfg["params"], cfg["calibration"]


def ensemble_choice(r, threshold, p, cal):
    """(text, calibrated confidence) the installed ensemble produces for this crop."""
    calib = lambda c, e: float(np.interp(c, cal[e]["x"], cal[e]["y"]))
    if r["rapid_conf"] >= threshold:
        return r["rapid_text"], calib(r["rapid_conf"], "rapid"), False

    def score(text, conf, engine, validity):
        if not text.strip():
            return -1.0
        c = min(1.0, conf * p["trocr_conf_scale"]) if engine == "trocr" else conf
        return p["conf_weight"] * c + p["validity_weight"] * validity + (p["rapid_bias"] if engine == "rapid" else 0)
    rs = score(r["rapid_text"], r["rapid_conf"], "rapid", r["rapid_validity"])
    ts = score(r["trocr_text"], r["trocr_conf"], "trocr", r["trocr_validity"])
    if ts > rs:
        return r["trocr_text"], calib(r["trocr_conf"], "trocr"), True
    return r["rapid_text"], calib(r["rapid_conf"], "rapid"), True


def apply_rule(r, base, rule):
    text, conf, eligible = base
    if not eligible or conf >= rule["gate"]:
        return text
    key = "vlm_hint" if rule["mode"] == "hint" else "vlm"
    vt, vc = r.get(f"{key}_text", ""), r.get(f"{key}_conf", 0.0)
    if not vt or vc < rule["min_conf"]:
        return text
    refs = [x for x in (r["rapid_text"], r["trocr_text"]) if x.strip()]
    if not any(_edit_distance(vt.lower(), x.lower()) / max(1, len(x)) <= rule["anchor"] for x in refs):
        return text
    return vt


def macro_cer(rows, preds):
    agg = defaultdict(lambda: [0, 0])
    for r, p in zip(rows, preds):
        agg[r["source"]][0] += _edit_distance(r["gt"].lower(), p.lower())
        agg[r["source"]][1] += max(1, len(r["gt"]))
    by = {k: round(e / n, 4) for k, (e, n) in agg.items()}
    return round(sum(by.values()) / len(by), 4), by


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--val", required=True)
    parser.add_argument("--test", required=True)
    parser.add_argument("--model_dir", default=str(ROOT / "app" / "ai" / "models" / "trocr_medical_finetuned"))
    parser.add_argument("--vlm_model", default="Qwen/Qwen3-VL-2B-Instruct")
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()
    threshold, params, cal = load_ensemble(args.model_dir)
    val = json.loads(Path(args.val).read_text(encoding="utf-8"))
    test = json.loads(Path(args.test).read_text(encoding="utf-8"))
    base_v = [ensemble_choice(r, threshold, params, cal) for r in val]
    base_t = [ensemble_choice(r, threshold, params, cal) for r in test]

    for name, rows in (("val", val), ("test", test)):
        for key in ("vlm", "vlm_hint"):
            m, by = macro_cer(rows, [r.get(f"{key}_text", "") for r in rows])
            print(f"{name} {key + '_only':14s} macro CER {m} {by}")
    vb, vby = macro_cer(val, [b[0] for b in base_v])
    tb, tby = macro_cer(test, [b[0] for b in base_t])
    print(f"val  ensemble       macro CER {vb} {vby}")

    grid = {"gate": [0.5, 0.7, 0.8, 0.9, 0.95, 1.01], "mode": ["plain", "hint"],
            "anchor": [0.15, 0.25, 0.35, 0.5, 10.0], "min_conf": [0.0, 0.5, 0.7, 0.85]}
    best, best_score = None, vb
    for vals in itertools.product(*grid.values()):
        rule = dict(zip(grid.keys(), vals))
        sc, _ = macro_cer(val, [apply_rule(r, b, rule) for r, b in zip(val, base_v)])
        if sc < best_score - 1e-9:
            best, best_score = rule, sc
    print(f"best rule {best} val macro CER {best_score} (ensemble {vb})")
    print(f"test ensemble       macro CER {tb} {tby}")
    if best:
        ts, tby2 = macro_cer(test, [apply_rule(r, b, best) for r, b in zip(test, base_t)])
        share = np.mean([b[2] and b[1] < best["gate"] for b in base_t])
        print(f"test ensemble+VLM   macro CER {ts} {tby2}  (VLM consulted on {share:.0%} of crops)")
        if args.install and ts < tb:
            out = {**best, "model": args.vlm_model, "val_macro_cer": best_score, "test_macro_cer": ts,
                   "test_ensemble_macro_cer": tb}
            (Path(args.model_dir) / "vlm.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
            print("installed vlm.json")
        elif args.install:
            print("not installed: no held-out improvement")


if __name__ == "__main__":
    main()
