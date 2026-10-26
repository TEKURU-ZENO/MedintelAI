"""
Fits the PP-OCR vs TrOCR recogniser ensemble for a TrOCR checkpoint and reports it on held-out data.

Fitted jointly on validation candidates (scripts/collect_ensemble_candidates.py):
  - printed_conf_threshold  lines PP-OCR reads at >= this confidence skip the ensemble (printed path)
  - params                  selection rule weights (see app/ai/ocr/htr_ensemble.py)
  - calibration             raw confidence -> expected character accuracy, per engine
--install writes them to <model_dir>/ensemble.json, which the OCR engine loads with the checkpoint.

Usage:
    python scripts/fit_ensemble.py --val outputs/ensemble_val.json --test outputs/ensemble_test.json \
        --install app/ai/models/trocr_medical_finetuned
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

PRINTED = {"funsd_word", "printed_synth"}
MAX_ACCURACY_THRESHOLD = 1.01  # every line through the ensemble


def cer(gt, pred):
    return _edit_distance(gt.lower(), pred.lower()) / max(1, len(gt))


def disagreement(r):
    a, b = r["rapid_text"].lower().strip(), r["trocr_text"].lower().strip()
    return _edit_distance(a, b) / max(1, max(len(a), len(b)))


def pick(row, p):
    def score(text, conf, engine, validity):
        if not text.strip():
            return -1.0
        c = min(1.0, conf * p["trocr_conf_scale"]) if engine == "trocr" else conf
        s = p["conf_weight"] * c + p["validity_weight"] * validity
        return s + (p["rapid_bias"] if engine == "rapid" else 0.0)
    rs = score(row["rapid_text"], row["rapid_conf"], "rapid", row["rapid_validity"])
    ts = score(row["trocr_text"], row["trocr_conf"], "trocr", row["trocr_validity"])
    return row["trocr_text"] if ts > rs else row["rapid_text"]


def policy(threshold, p):
    return lambda r: r["rapid_text"] if r["rapid_conf"] >= threshold else pick(r, p)


def macro_cer(rows, chooser):
    per = defaultdict(lambda: [0, 0])
    for r in rows:
        pred = chooser(r)
        per[r["source"]][0] += _edit_distance(r["gt"].lower(), pred.lower())
        per[r["source"]][1] += max(1, len(r["gt"]))
    by_src = {k: round(e / n, 4) for k, (e, n) in per.items()}
    return round(sum(by_src.values()) / max(1, len(by_src)), 4), by_src


def fit_calibration(rows, engine):
    x = np.array([r[f"{engine}_conf"] for r in rows])
    y = np.array([max(0.0, 1 - cer(r["gt"], r[f"{engine}_text"])) for r in rows])
    qs = np.unique(np.quantile(x, np.linspace(0, 1, 11)))
    kx, ky = [], []
    for lo, hi in zip(qs[:-1], qs[1:]):
        m = (x >= lo) & (x <= hi)
        if m.sum() >= 15:
            kx.append(float(x[m].mean()))
            ky.append(float(y[m].mean()))
    ky = list(np.maximum.accumulate(ky))
    return {"x": [round(v, 4) for v in kx], "y": [round(float(v), 4) for v in ky]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--val", required=True)
    parser.add_argument("--test", required=True)
    parser.add_argument("--install", default=None, help="TrOCR checkpoint dir to write ensemble.json into")
    parser.add_argument("--cpu_threshold", type=float, default=0.97,
                        help="routing threshold for the CPU profile (fewer TrOCR calls on printed lines)")
    parser.add_argument("--max_cost", type=float, default=0.004,
                        help="accept a lower routing threshold (faster: fewer TrOCR calls on print) if val "
                             "macro CER is within this of the best")
    args = parser.parse_args()
    val = json.loads(Path(args.val).read_text(encoding="utf-8"))
    test = json.loads(Path(args.test).read_text(encoding="utf-8"))

    grid = {
        "trocr_conf_scale": [1.0, 1.3, 1.6, 2.0, 2.5, 3.0],
        "conf_weight": [0.2, 0.4, 0.6, 0.8, 1.0],
        "validity_weight": [0.0, 0.2, 0.4],
        "rapid_bias": [-0.15, -0.1, -0.05, 0.0, 0.05, 0.1, 0.2],
    }
    fits = []
    for threshold in (0.85, 0.9, 0.93, 0.95, 0.97, 0.99, MAX_ACCURACY_THRESHOLD):
        best, best_score = None, None
        for vals in itertools.product(*grid.values()):
            p = dict(zip(grid.keys(), vals))
            sc, _ = macro_cer(val, policy(threshold, p))
            if best_score is None or sc < best_score:
                best, best_score = p, sc
        fits.append((threshold, best, best_score))
        print(f"threshold {threshold:.2f}: val macro CER {best_score:.4f}  params {best}")

    overall = min(f[2] for f in fits)
    # Prefer the lowest threshold within max_cost of the best (fewer TrOCR calls on printed lines)
    threshold, params, val_score = min((f for f in fits if f[2] <= overall + args.max_cost), key=lambda f: f[0])
    print(f"\nchosen threshold {threshold} params {params} (val {val_score:.4f}, best {overall:.4f})")

    all_params = next(f[1] for f in fits if f[0] == MAX_ACCURACY_THRESHOLD)
    choosers = {
        "rapid_only": lambda r: r["rapid_text"],
        "trocr_only": lambda r: r["trocr_text"],
        "routed_ensemble": policy(threshold, params),
        "ensemble_all": policy(MAX_ACCURACY_THRESHOLD, all_params),
        "oracle": lambda r: min((r["rapid_text"], r["trocr_text"]), key=lambda t: cer(r["gt"], t)),
    }
    report = {}
    for split, rows in (("val", val), ("test", test)):
        for name, ch in choosers.items():
            m, by = macro_cer(rows, ch)
            report[f"{split}:{name}"] = {"macro_cer": m, "by_source": by}
            print(f"{split:4s} {name:16s} macro CER {m:.4f} {by}")

    calibration = {"rapid": fit_calibration(val, "rapid"), "trocr": fit_calibration(val, "trocr")}
    for eng in ("rapid", "trocr"):
        xt = np.array([r[f"{eng}_conf"] for r in test])
        yt = np.array([max(0.0, 1 - cer(r["gt"], r[f"{eng}_text"])) for r in test])
        pt = np.interp(xt, calibration[eng]["x"], calibration[eng]["y"])
        print(f"calibration {eng}: test mean predicted {pt.mean():.3f} vs actual {yt.mean():.3f}")

    cpu_params = next((f[1] for f in fits if abs(f[0] - args.cpu_threshold) < 1e-9), None)
    if cpu_params is None:
        cpu_params, best_sc = None, None
        for vals in itertools.product(*grid.values()):
            p = dict(zip(grid.keys(), vals))
            sc, _ = macro_cer(val, policy(args.cpu_threshold, p))
            if best_sc is None or sc < best_sc:
                cpu_params, best_sc = p, sc
    cpu_test, _ = macro_cer(test, policy(args.cpu_threshold, cpu_params))
    print(f"cpu profile: threshold {args.cpu_threshold} params {cpu_params} test macro CER {cpu_test:.4f}")

    cfg = {
        # GPU profile (most accurate) at the top level; CPU profile trades a little accuracy for speed
        "printed_conf_threshold": threshold, "params": params,
        "cpu": {"printed_conf_threshold": args.cpu_threshold, "params": cpu_params},
        "calibration": calibration, "report": report,
    }
    out = ROOT / "outputs" / "ensemble_fit.json"
    out.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    if args.install:
        target = Path(args.install) / "ensemble.json"
        target.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        print(f"installed {target}")


if __name__ == "__main__":
    main()
