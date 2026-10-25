"""
Medical HTR fine-tuning for the OCR engine's TrOCR handwriting recogniser.

Data (see scripts/download_htr_datasets.py):
  iam_line      general English cursive lines        -> keeps line-level reading ability
  rxhandbd      physician prescription word crops    -> drug brands, generics, dosages
  kaggle_rx_bd  78-class prescription medicine words -> optional, used when present
  synthetic     rendered prescription / clinical lines from the medical lexicon + medication corpus

Pipeline:
  weighted multi-source sampling -> shared prepare_htr_image() -> augmentation -> TrOCR fine-tune
  (bf16 autocast, discriminative LR for encoder/decoder, warmup + cosine decay, label smoothing)
  -> per-source CER/WER validation every epoch -> best checkpoint -> held-out test report
  -> promotion into app/ai/models/trocr_medical_finetuned ONLY if it beats the installed model.

Usage:
  python scripts/train_trocr_medical.py --epochs 10 --promote
  python scripts/train_trocr_medical.py --eval_only --model_dir app/ai/models/trocr_medical_finetuned
"""
import argparse
import gc
import json
import math
import os
import random
import shutil
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

# Variable label lengths fragment the CUDA cache; on Windows an oversized cache spills into shared
# memory and slows training ~10x. Must be set before torch initialises CUDA.
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from datasets.htr_sources import (  # noqa: E402
    DEFAULT_CORPORA_DIR, GENERAL_SOURCES, HTRSample, build_medical_lexicon, load_all_image_corpora,
    load_kaggle_generic_names, load_medication_text_corpus, load_rxnorm_names, summarize,
)
from datasets.htr_augment import HTRAugmenter, SyntheticMedicalLines, discover_handwriting_fonts  # noqa: E402
from app.ai.ocr.htr_engine import LEXICON_FILENAME, MedicalHTREngine, prepare_htr_image  # noqa: E402
from app.ai.ocr.medical_postprocessor import MedicalVocabularyPostProcessor  # noqa: E402

INSTALLED_MODEL_DIR = ROOT / "app" / "ai" / "models" / "trocr_medical_finetuned"
MEDICAL_SOURCES = ("rxhandbd", "kaggle_rx_bd", "synthetic")
DEFAULT_MIX = (
    "iam_line=0.18,gnhk_line=0.17,gnhk_word=0.07,rxhandbd=0.25,kaggle_rx_bd=0.13,synthetic=0.20"
)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def _edit_distance(a: Sequence, b: Sequence) -> int:
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def score_predictions(gts: List[str], preds: List[str]) -> Dict[str, float]:
    ce = ce_ci = cn = we = wn = exact = exact_ci = 0
    for gt, pr in zip(gts, preds):
        ce += _edit_distance(gt, pr)
        ce_ci += _edit_distance(gt.lower(), pr.lower())
        cn += max(1, len(gt))
        gw, pw = gt.split(), pr.split()
        we += _edit_distance(gw, pw)
        wn += max(1, len(gw))
        exact += int(gt == pr)
        exact_ci += int(gt.lower() == pr.lower())
    n = max(1, len(gts))
    return {
        "cer": round(ce / max(1, cn), 4),
        "cer_case_insensitive": round(ce_ci / max(1, cn), 4),
        "wer": round(we / max(1, wn), 4),
        "exact_match": round(exact / n, 4),
        "exact_match_case_insensitive": round(exact_ci / n, 4),
        "samples": len(gts),
    }


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------
class MixedHTRDataset(Dataset):
    """
    Map-style dataset over real samples plus `synthetic_slots` virtual indices that render a fresh
    synthetic medical line on every access. Sampling weights are handled by WeightedRandomSampler.
    """

    AUG_PROB = {"iam_line": 0.6, "rxhandbd": 0.8, "kaggle_rx_bd": 0.8, "synthetic": 1.0}

    def __init__(
        self,
        samples: List[HTRSample],
        processor,
        decoder_start_token_id: int,
        max_label_len: int,
        synthetic: Optional[SyntheticMedicalLines] = None,
        synthetic_slots: int = 0,
        augment: bool = True
    ):
        self.samples = samples
        self.image_processor = processor.image_processor
        self.tokenizer = processor.tokenizer
        self.decoder_start_token_id = decoder_start_token_id
        self.max_label_len = max_label_len
        self.synthetic = synthetic
        self.synthetic_slots = synthetic_slots if synthetic is not None else 0
        self.augment = augment
        self.augmenter = HTRAugmenter()
        self._pid = None

    def __len__(self):
        return len(self.samples) + self.synthetic_slots

    def source_of(self, idx: int) -> str:
        return self.samples[idx].source if idx < len(self.samples) else "synthetic"

    def _reseed_if_new_worker(self):
        # DataLoader workers inherit identical RNG state; reseed once per process
        if self._pid != os.getpid():
            self._pid = os.getpid()
            seed = (int(time.time() * 1e6) ^ (os.getpid() << 16)) & 0xFFFFFFFF
            self.augmenter.rng.seed(seed)
            np.random.seed(seed)
            if self.synthetic is not None:
                self.synthetic.rng.seed(seed + 1)

    def encode_label(self, text: str) -> List[int]:
        ids = self.tokenizer(text, add_special_tokens=True, truncation=True, max_length=self.max_label_len).input_ids
        # fairseq-style TrOCR target: tokens + </s>; the decoder start token is prepended by the model
        if ids and ids[0] == self.tokenizer.bos_token_id and self.decoder_start_token_id != self.tokenizer.bos_token_id:
            ids = ids[1:]
        return ids

    def __getitem__(self, idx: int):
        self._reseed_if_new_worker()
        source = self.source_of(idx)
        if source == "synthetic":
            img, text = self.synthetic.sample()
        else:
            s = self.samples[idx]
            img, text = s.load_bgr(), s.text

        if self.augment and self.augmenter.rng.random() < self.AUG_PROB.get(source, 0.7):
            img = self.augmenter(img)

        pil = prepare_htr_image(img)
        pixel_values = self.image_processor(pil, return_tensors="pt").pixel_values.squeeze(0)
        return {"pixel_values": pixel_values, "labels": torch.tensor(self.encode_label(text), dtype=torch.long)}


def collate(batch):
    pixel_values = torch.stack([b["pixel_values"] for b in batch])
    max_len = max(len(b["labels"]) for b in batch)
    labels = torch.full((len(batch), max_len), -100, dtype=torch.long)
    for i, b in enumerate(batch):
        labels[i, : len(b["labels"])] = b["labels"]
    return {"pixel_values": pixel_values, "labels": labels}


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------
def evaluate_engine(
    engine: MedicalHTREngine,
    eval_sets: Dict[str, List[Tuple[np.ndarray, str]]],
    batch_size: int = 32,
    with_postprocessor: bool = False
) -> Dict[str, Dict]:
    post = MedicalVocabularyPostProcessor() if with_postprocessor else None
    report: Dict[str, Dict] = {}
    for name, items in eval_sets.items():
        gts, raw_preds, lex_preds = [], [], []
        t0 = time.time()
        for i in range(0, len(items), batch_size):
            chunk = items[i: i + batch_size]
            results = engine.recognize_batch([img for img, _ in chunk])
            for (_, gt), res in zip(chunk, results):
                gts.append(gt)
                raw_preds.append(res["raw_text"])
                text = res["text"]
                lex_preds.append(post.clean_text(text) if post else text)
        elapsed = time.time() - t0
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        report[name] = {
            "decoder_only": score_predictions(gts, raw_preds),
            "with_lexicon": score_predictions(gts, lex_preds),
            "ms_per_crop": round(1000.0 * elapsed / max(1, len(items)), 1),
            "examples": [
                {"gt": g, "pred": p} for g, p in list(zip(gts, lex_preds))[:8]
            ],
        }
    return report


def selection_score(report: Dict[str, Dict]) -> float:
    """Lower is better: 70% medical CER + 30% general-handwriting CER (case-insensitive, with lexicon)."""
    med = [report[k]["with_lexicon"]["cer_case_insensitive"] for k in report if k.split(":")[0] in MEDICAL_SOURCES]
    gen = [report[k]["with_lexicon"]["cer_case_insensitive"] for k in report
           if k.split(":")[0] in GENERAL_SOURCES and k.split(":")[0] != "gnhk_word"]
    med_cer = float(np.mean(med)) if med else 0.0
    gen_cer = float(np.mean(gen)) if gen else med_cer
    return 0.7 * med_cer + 0.3 * gen_cer if med else gen_cer


def build_eval_sets(
    corpora: Dict[str, List[HTRSample]],
    split: str,
    max_per_source: int,
    synthetic: Optional[SyntheticMedicalLines],
    synthetic_count: int,
    seed: int
) -> Dict[str, List[Tuple[np.ndarray, str]]]:
    rng = random.Random(seed)
    sets: Dict[str, List[Tuple[np.ndarray, str]]] = {}
    for name, items in corpora.items():
        pool = [s for s in items if s.split == split]
        if not pool:
            continue
        rng.shuffle(pool)
        if max_per_source > 0:
            pool = pool[:max_per_source]
        sets[f"{name}:{split}"] = [(s.load_bgr(), s.text) for s in pool]
    if synthetic is not None and synthetic_count > 0:
        state = synthetic.rng.getstate()
        synthetic.rng.seed(seed)
        sets[f"synthetic:{split}"] = [synthetic.sample() for _ in range(synthetic_count)]
        synthetic.rng.setstate(state)
    return sets


def tune_decoding(
    engine: MedicalHTREngine,
    eval_sets: Dict[str, List[Tuple[np.ndarray, str]]],
    weights: Sequence[float] = (0.0, 0.05, 0.1, 0.2, 0.35, 0.5, 0.8),
    gates: Sequence[float] = (0.0, 0.5, 0.7, 0.85),
    batch_size: int = 16
) -> Tuple[Dict[str, float], List[Dict]]:
    """
    Decodes each validation set once (n-best = beam width) and grid-searches the n-best rescoring
    weight and lexicon-correction confidence gate on the selection score.
    """
    cands: Dict[str, List[List[Dict]]] = {}
    for name, items in eval_sets.items():
        cands[name] = []
        for i in range(0, len(items), batch_size):
            cands[name].extend(engine.decode_nbest([img for img, _ in items[i: i + batch_size]], n_best=engine.num_beams))
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    grid = []
    for w in weights:
        for g in gates:
            engine.rescore_weight, engine.lexicon_conf_gate = w, g
            report = {
                name: {"with_lexicon": score_predictions([t for _, t in items], [engine.select(c)["text"] for c in cands[name]])}
                for name, items in eval_sets.items()
            }
            grid.append({"rescore_weight": w, "lexicon_conf_gate": g, "score": round(selection_score(report), 5),
                         "cer_ci": {k: v["with_lexicon"]["cer_case_insensitive"] for k, v in report.items()}})
    best = min(grid, key=lambda r: r["score"])
    engine.rescore_weight, engine.lexicon_conf_gate = best["rescore_weight"], best["lexicon_conf_gate"]
    return {"rescore_weight": best["rescore_weight"], "lexicon_conf_gate": best["lexicon_conf_gate"]}, grid


def build_common_words(corpora: Dict[str, List[HTRSample]], min_count: int = 1) -> List[str]:
    """General English vocabulary from the training transcriptions of the general handwriting corpora."""
    counts: Dict[str, int] = {}
    for name, items in corpora.items():
        if name not in GENERAL_SOURCES:
            continue
        for s in items:
            if s.split != "train":
                continue
            for tok in s.text.split():
                w = tok.strip(".,;:!?()\"'").lower()
                if w.isalpha() and len(w) >= 2:
                    counts[w] = counts.get(w, 0) + 1
    return sorted(w for w, c in counts.items() if c >= min_count)


# ---------------------------------------------------------------------------
# Model helpers
# ---------------------------------------------------------------------------
def load_model_and_processor(model_id: str):
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel

    processor = TrOCRProcessor.from_pretrained(model_id)
    model = VisionEncoderDecoderModel.from_pretrained(model_id)
    tok = processor.tokenizer

    start_id = getattr(model.generation_config, "decoder_start_token_id", None)
    if start_id is None:
        start_id = model.config.decoder.decoder_start_token_id
    if start_id is None:
        start_id = tok.eos_token_id

    model.config.decoder_start_token_id = start_id
    model.config.pad_token_id = tok.pad_token_id
    model.config.eos_token_id = tok.eos_token_id
    model.config.vocab_size = model.config.decoder.vocab_size
    model.generation_config.decoder_start_token_id = start_id
    model.generation_config.pad_token_id = tok.pad_token_id
    model.generation_config.eos_token_id = tok.eos_token_id
    return processor, model


def write_vocabularies(out_dir: Path, lexicon: List[str], common_words: List[str], decoding: Optional[Dict] = None):
    with open(out_dir / LEXICON_FILENAME, "w", encoding="utf-8") as f:
        json.dump({"terms": lexicon, "count": len(lexicon), "common_words": common_words,
                   "decoding": decoding or {}}, f, indent=1)


def save_checkpoint(model, processor, out_dir: Path, lexicon: List[str], meta: Dict,
                    common_words: Optional[List[str]] = None):
    out_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out_dir)
    processor.save_pretrained(out_dir)
    write_vocabularies(out_dir, lexicon, common_words or [])
    with open(out_dir / "training_report.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


def write_model_card(out_dir: Path, meta: Dict):
    test = meta.get("test_report", {})
    lines = [
        "# Medical HTR TrOCR checkpoint",
        "",
        f"- Base model: `{meta.get('base_model')}`",
        f"- Trained: {meta.get('finished_at')}",
        f"- Epochs: {meta.get('epochs')} | best epoch: {meta.get('best_epoch')}",
        f"- Training corpora: {json.dumps(meta.get('corpora_summary', {}))}",
        f"- Lexicon terms: {meta.get('lexicon_terms')}",
        "",
        "| Test set | CER | CER (case-insens.) | WER | Exact match | ms/crop |",
        "| :--- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, r in test.items():
        m = r["with_lexicon"]
        lines.append(
            f"| {name} | {m['cer']:.3f} | {m['cer_case_insensitive']:.3f} | {m['wer']:.3f} | "
            f"{m['exact_match']:.3f} | {r['ms_per_crop']} |"
        )
    lines += [
        "",
        "Used by `app/ai/ocr/htr_engine.py` (MedicalHTREngine) for handwritten line/word crops routed by the",
        "hybrid OCR engine. `medical_lexicon.json` holds the drug / clinical vocabulary used for",
        "confidence-gated lexicon correction.",
    ]
    (out_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------
def build_resources(corpora_dir: str, seed: int):
    """Corpora, lexicon, common words and the synthetic generator, built identically for training and eval."""
    corpora = load_all_image_corpora(corpora_dir)
    med_lines = load_medication_text_corpus(corpora_dir)
    rxnorm_names = load_rxnorm_names(corpora_dir)
    generic_names = load_kaggle_generic_names(corpora_dir)
    lexicon = build_medical_lexicon(
        corpora,
        extra_terms=MedicalVocabularyPostProcessor.KNOWN_MEDICINES + [l.split(" ")[0] for l in med_lines]
        + rxnorm_names + generic_names,
    )
    common_words = build_common_words(corpora)
    # Synthetic drug names: the real prescription corpora + RxNorm whole names (single-word, title-cased)
    corpus_drugs = build_medical_lexicon(corpora, extra_terms=MedicalVocabularyPostProcessor.KNOWN_MEDICINES + generic_names)
    rx_single = [n.title() for n in rxnorm_names if n.replace("-", "").isalpha() and len(n) >= 4]
    drug_names = [t for t in corpus_drugs if t[0].isupper()] + rx_single
    synthetic = SyntheticMedicalLines(drug_names, med_lines, fonts=discover_handwriting_fonts(), seed=seed)
    info = {"med_lines": len(med_lines), "rxnorm": len(rxnorm_names), "drug_names": len(drug_names)}
    return corpora, lexicon, common_words, synthetic, info


def parse_mix(spec: str) -> Dict[str, float]:
    out = {}
    for part in spec.split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = float(v)
    return out


def train_trocr(
    epochs: int = 10,
    batch_size: int = 16,
    lr: float = 5e-5,
    model_id: str = "microsoft/trocr-small-handwritten",
    corpora_dir: str = str(DEFAULT_CORPORA_DIR),
    mix: str = DEFAULT_MIX,
    samples_per_epoch: int = 12000,
    encoder_lr_scale: float = 0.5,
    warmup_ratio: float = 0.06,
    weight_decay: float = 0.01,
    label_smoothing: float = 0.1,
    grad_accum: int = 1,
    max_label_len: int = 96,
    num_workers: int = 4,
    val_max_per_source: int = 400,
    test_max_per_source: int = 1500,
    synthetic_eval: int = 300,
    gradient_checkpointing: bool = False,
    resume: bool = False,
    output_dir: Optional[str] = None,
    promote: bool = False,
    force_promote: bool = False,
    seed: int = 42,
):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    run_dir = Path(output_dir) if output_dir else ROOT / "outputs" / "htr_runs" / time.strftime("%Y%m%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_bf16 = device.type == "cuda" and torch.cuda.is_bf16_supported()

    print("=" * 80)
    print(f"MEDICAL HTR FINE-TUNING  base={model_id}  device={device}  bf16={use_bf16}")
    print("=" * 80)

    # 1. Data
    corpora, lexicon, common_words, synthetic, info = build_resources(corpora_dir, seed)
    if not corpora:
        raise SystemExit("No HTR corpora found. Run scripts/download_htr_datasets.py first.")
    print(f"Corpora: {json.dumps(summarize(corpora))}")
    print(f"Medication text lines: {info['med_lines']} | lexicon terms: {len(lexicon)} (RxNorm {info['rxnorm']}) | "
          f"common words: {len(common_words)} | synthetic drug names: {info['drug_names']} | fonts: {len(synthetic.fonts)}")

    processor, model = load_model_and_processor(model_id)
    start_id = model.config.decoder_start_token_id

    train_samples = [s for items in corpora.values() for s in items if s.split == "train"]
    mix_w = parse_mix(mix)
    synthetic_slots = 1 if mix_w.get("synthetic", 0) > 0 else 0
    train_ds = MixedHTRDataset(
        train_samples, processor, start_id, max_label_len,
        synthetic=synthetic, synthetic_slots=synthetic_slots, augment=True
    )

    # Per-index weights so each source contributes its mix share regardless of corpus size
    counts: Dict[str, int] = {}
    for i in range(len(train_ds)):
        counts[train_ds.source_of(i)] = counts.get(train_ds.source_of(i), 0) + 1
    present = {k: mix_w.get(k, 0.0) for k in counts if mix_w.get(k, 0.0) > 0}
    total_w = sum(present.values())
    weights = [present.get(train_ds.source_of(i), 0.0) / total_w / counts[train_ds.source_of(i)] for i in range(len(train_ds))]
    print(f"Effective mix: { {k: round(v / total_w, 3) for k, v in present.items()} }")

    sampler = WeightedRandomSampler(weights, num_samples=samples_per_epoch, replacement=True)
    loader = DataLoader(
        train_ds, batch_size=batch_size, sampler=sampler, collate_fn=collate,
        num_workers=num_workers, pin_memory=False, persistent_workers=num_workers > 0,
        drop_last=True,
    )

    val_sets = build_eval_sets(corpora, "val", val_max_per_source, synthetic, synthetic_eval, seed + 7)
    print(f"Validation sets: { {k: len(v) for k, v in val_sets.items()} }")

    # 2. Optimiser: discriminative learning rates, no decay on norms/biases
    if gradient_checkpointing:
        model.gradient_checkpointing_enable()
    model.to(device)
    enc_decay, enc_nodecay, dec_decay, dec_nodecay = [], [], [], []
    for n, p in model.named_parameters():
        if not p.requires_grad:
            continue
        nodecay = p.ndim < 2 or "norm" in n.lower() or n.endswith(".bias")
        if n.startswith("encoder."):
            (enc_nodecay if nodecay else enc_decay).append(p)
        else:
            (dec_nodecay if nodecay else dec_decay).append(p)
    optimizer = torch.optim.AdamW([
        {"params": enc_decay, "lr": lr * encoder_lr_scale, "weight_decay": weight_decay},
        {"params": enc_nodecay, "lr": lr * encoder_lr_scale, "weight_decay": 0.0},
        {"params": dec_decay, "lr": lr, "weight_decay": weight_decay},
        {"params": dec_nodecay, "lr": lr, "weight_decay": 0.0},
    ])
    steps_per_epoch = max(1, len(loader) // grad_accum)
    total_steps = steps_per_epoch * epochs
    warmup = max(1, int(total_steps * warmup_ratio))

    def lr_lambda(step):
        if step < warmup:
            return (step + 1) / warmup
        progress = (step - warmup) / max(1, total_steps - warmup)
        return 0.05 + 0.95 * 0.5 * (1 + math.cos(math.pi * progress))

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

    engine = MedicalHTREngine(processor, model, lexicon=lexicon, common_words=common_words, device=str(device),
                              num_beams=1, quantize_cpu=False)
    best_dir = run_dir / "best"
    last_state = run_dir / "last_state.pt"
    start_epoch, global_step = 1, 0

    if resume and last_state.exists():
        # Resume an interrupted run (laptop sleep, power loss) from the last completed epoch
        state = torch.load(last_state, map_location=device, weights_only=False)
        model.load_state_dict(state["model"])
        optimizer.load_state_dict(state["optimizer"])
        scheduler.load_state_dict(state["scheduler"])
        start_epoch, global_step = state["epoch"] + 1, state["global_step"]
        best_score, best_epoch, history = state["best_score"], state["best_epoch"], state["history"]
        print(f"Resumed from epoch {state['epoch']} (best {best_score:.4f} @ epoch {best_epoch})", flush=True)
    else:
        # Baseline validation before any update
        base_val = evaluate_engine(engine, val_sets)
        best_score = selection_score(base_val)
        print(f"Baseline val score: {best_score:.4f}")
        history = [{"epoch": 0, "val": {k: v['with_lexicon'] for k, v in base_val.items()}, "score": best_score}]
        best_epoch = 0
        save_checkpoint(model, processor, best_dir, lexicon, {"base_model": model_id, "epoch": 0}, common_words)

    # 3. Train
    for epoch in range(start_epoch, epochs + 1):
        model.train()
        t0 = time.time()
        running, seen = 0.0, 0
        optimizer.zero_grad(set_to_none=True)
        for step, batch in enumerate(loader, 1):
            pixel_values = batch["pixel_values"].to(device, non_blocking=True)
            labels = batch["labels"].to(device, non_blocking=True)
            with torch.autocast(device_type=device.type, dtype=torch.bfloat16, enabled=use_bf16):
                logits = model(pixel_values=pixel_values, labels=labels).logits
            loss = F.cross_entropy(
                logits.float().reshape(-1, logits.size(-1)), labels.reshape(-1),
                ignore_index=-100, label_smoothing=label_smoothing,
            )
            (loss / grad_accum).backward()
            if step % grad_accum == 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)
                global_step += 1
            running += loss.item()
            seen += 1
            if step % 100 == 0:
                print(f"  epoch {epoch} step {step}/{len(loader)} loss {running / seen:.4f} "
                      f"lr {scheduler.get_last_lr()[2]:.2e} {(time.time() - t0) / step:.2f}s/it", flush=True)

        model.eval()
        val = evaluate_engine(engine, val_sets)
        score = selection_score(val)
        summary = {k: (v["with_lexicon"]["cer_case_insensitive"], v["with_lexicon"]["exact_match_case_insensitive"]) for k, v in val.items()}
        print(f"Epoch {epoch}/{epochs} loss {running / max(1, seen):.4f} val_score {score:.4f} "
              f"(cer_ci, exact_ci) {summary} [{time.time() - t0:.0f}s]", flush=True)
        history.append({"epoch": epoch, "train_loss": running / max(1, seen),
                        "val": {k: v["with_lexicon"] for k, v in val.items()}, "score": score})
        if score < best_score:
            best_score, best_epoch = score, epoch
            save_checkpoint(model, processor, best_dir, lexicon, {"base_model": model_id, "epoch": epoch}, common_words)
            print(f"  -> new best checkpoint (epoch {epoch})")
        tmp = last_state.with_suffix(".tmp")
        torch.save({
            "model": model.state_dict(), "optimizer": optimizer.state_dict(), "scheduler": scheduler.state_dict(),
            "epoch": epoch, "global_step": global_step, "best_score": best_score, "best_epoch": best_epoch,
            "history": history,
        }, tmp)
        os.replace(tmp, last_state)

    # 4. Held-out test with production decoding settings (beam search). Release training state first so
    #    beam search has the whole GPU.
    del loader, engine, optimizer, scheduler
    model.cpu()
    del model
    gc.collect()
    if device.type == "cuda":
        torch.cuda.empty_cache()

    if last_state.exists():
        last_state.unlink()  # multi-GB optimiser state is only needed while training

    # 4a. Tune n-best rescoring weight + lexicon gate on validation, persist them with the checkpoint
    best_engine = MedicalHTREngine.from_pretrained(str(best_dir), device=str(device), num_beams=4)
    decoding, grid = tune_decoding(best_engine, val_sets)
    write_vocabularies(best_dir, lexicon, common_words, decoding)
    print(f"Tuned decoding on validation: {decoding} "
          f"(untuned score {next(g['score'] for g in grid if g['rescore_weight'] == 0 and g['lexicon_conf_gate'] == 0.0)}, "
          f"tuned {min(g['score'] for g in grid)})", flush=True)

    del best_engine
    gc.collect()
    if device.type == "cuda":
        torch.cuda.empty_cache()

    meta = {
        "base_model": model_id,
        "epochs": epochs,
        "best_epoch": best_epoch,
        "hyperparameters": {
            "batch_size": batch_size, "lr": lr, "encoder_lr_scale": encoder_lr_scale, "warmup_ratio": warmup_ratio,
            "label_smoothing": label_smoothing, "samples_per_epoch": samples_per_epoch, "mix": mix, "seed": seed,
        },
        "corpora_summary": summarize(corpora),
        "lexicon_terms": len(lexicon),
        "common_words": len(common_words),
        "decoding": decoding,
        "decoding_grid": grid,
        "history": history,
    }
    with open(run_dir / "train_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    return finalize_candidate(
        best_dir, run_dir, corpora, synthetic, meta, test_max_per_source, synthetic_eval, seed, promote, force_promote
    )


def _evaluate_model_dir(model_dir: Path, test_sets, device) -> Dict[str, Dict]:
    engine = MedicalHTREngine.from_pretrained(str(model_dir), device=str(device), num_beams=4)
    try:
        return evaluate_engine(engine, test_sets, batch_size=8)
    finally:
        del engine
        gc.collect()
        if device.type == "cuda":
            torch.cuda.empty_cache()


def finalize_candidate(
    best_dir: Path,
    run_dir: Path,
    corpora: Dict[str, List[HTRSample]],
    synthetic: SyntheticMedicalLines,
    meta: Dict,
    test_max_per_source: int,
    synthetic_eval: int,
    seed: int,
    promote: bool,
    force_promote: bool,
) -> Dict:
    """
    Held-out test of the candidate and the installed checkpoint on identical test sets (beam 4, tuned
    decoding from each checkpoint's medical_lexicon.json), model card, and gated promotion.
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    test_sets = build_eval_sets(corpora, "test", test_max_per_source, synthetic, synthetic_eval, seed + 11)
    print(f"Test sets: { {k: len(v) for k, v in test_sets.items()} }", flush=True)

    test_report = _evaluate_model_dir(best_dir, test_sets, device)
    new_score = selection_score(test_report)
    print(f"Candidate test score: {new_score:.4f}", flush=True)

    installed_report, installed_score = None, None
    if INSTALLED_MODEL_DIR.exists() and INSTALLED_MODEL_DIR.resolve() != best_dir.resolve():
        try:
            installed_report = _evaluate_model_dir(INSTALLED_MODEL_DIR, test_sets, device)
            installed_score = selection_score(installed_report)
        except Exception:
            import traceback
            print("Could not evaluate installed model:", flush=True)
            traceback.print_exc()

    meta = dict(meta)
    meta.update({
        "finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "test_report": test_report,
        "test_selection_score": new_score,
        "installed_model_test_report": installed_report,
        "installed_model_selection_score": installed_score,
    })
    with open(best_dir / "training_report.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    write_model_card(best_dir, meta)
    with open(run_dir / "report.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print("\nTEST (beam=4, tuned decoding):")
    for name, r in test_report.items():
        m = r["with_lexicon"]
        old = installed_report[name]["with_lexicon"]["cer_case_insensitive"] if installed_report and name in installed_report else None
        print(f"  {name:22s} CER {m['cer']:.3f}  CER(ci) {m['cer_case_insensitive']:.3f}  WER {m['wer']:.3f}  "
              f"exact(ci) {m['exact_match_case_insensitive']:.3f}  {r['ms_per_crop']} ms/crop"
              + (f"   [installed CER(ci) {old:.3f}]" if old is not None else ""), flush=True)
    print(f"Selection score new={new_score:.4f} installed={installed_score}", flush=True)

    improved = installed_score is None or new_score < installed_score
    if promote and (improved or force_promote):
        if INSTALLED_MODEL_DIR.exists():
            backup = INSTALLED_MODEL_DIR.with_name(f"{INSTALLED_MODEL_DIR.name}.bak-{time.strftime('%Y%m%d_%H%M%S')}")
            shutil.move(str(INSTALLED_MODEL_DIR), str(backup))
            print(f"Backed up previous checkpoint to {backup}")
        shutil.copytree(best_dir, INSTALLED_MODEL_DIR)
        print(f"Promoted new checkpoint to {INSTALLED_MODEL_DIR}")
    elif promote:
        print("New checkpoint did not beat the installed model; installed model left unchanged.")
    print(f"Run artefacts: {run_dir}", flush=True)
    return meta


def eval_only(model_dir: str, corpora_dir: str, max_per_source: int, num_beams: int, seed: int = 42,
              report_json: Optional[str] = None):
    corpora, _, _, synthetic, _ = build_resources(corpora_dir, seed)
    test_sets = build_eval_sets(corpora, "test", max_per_source, synthetic, 300, seed + 11)
    engine = MedicalHTREngine.from_pretrained(model_dir, num_beams=num_beams)
    report = evaluate_engine(engine, test_sets, batch_size=8)
    for name, r in report.items():
        d, m = r["decoder_only"], r["with_lexicon"]
        print(f"{name:22s} CER {d['cer']:.3f} -> tuned {m['cer']:.3f} | CER(ci) {m['cer_case_insensitive']:.3f} | "
              f"WER {m['wer']:.3f} | exact(ci) {m['exact_match_case_insensitive']:.3f} | {r['ms_per_crop']} ms/crop")
    print(f"Selection score: {selection_score(report):.4f}")
    if report_json:
        with open(report_json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
    return report


def retune(model_dir: str, corpora_dir: str, val_max_per_source: int, seed: int,
           medical_gate: Optional[float] = None):
    """
    Rebuilds a checkpoint's lexicon / common-word vocabularies with the current code and re-tunes the
    n-best rescoring weight and lexicon gate on validation. `medical_gate` pins the gate instead of
    tuning it (validation only contains in-distribution words, so it under-rewards the lexicon).
    """
    model_path = Path(model_dir)
    corpora, lexicon, common_words, synthetic, _ = build_resources(corpora_dir, seed)
    write_vocabularies(model_path, lexicon, common_words, {})
    val_sets = build_eval_sets(corpora, "val", val_max_per_source, synthetic, 300, seed + 7)
    engine = MedicalHTREngine.from_pretrained(str(model_path), num_beams=4)
    gates = (medical_gate,) if medical_gate is not None else (0.0, 0.5, 0.7, 0.85)
    decoding, grid = tune_decoding(engine, val_sets, gates=gates)
    write_vocabularies(model_path, lexicon, common_words, decoding)
    for g in grid:
        print(g["rescore_weight"], g["lexicon_conf_gate"], g["score"],
              {k.split(":")[0]: v for k, v in g["cer_ci"].items()})
    print(f"Wrote vocabularies ({len(lexicon)} terms, {len(common_words)} common words) and decoding {decoding}")
    return decoding, grid


def promote_from(candidate_dir: str, corpora_dir: str, max_per_source: int, seed: int, force: bool):
    """Re-runs the held-out comparison for an existing run's best/ checkpoint and promotes it if better."""
    best_dir = Path(candidate_dir)
    run_dir = best_dir.parent
    corpora, _, _, synthetic, _ = build_resources(corpora_dir, seed)
    meta_path = run_dir / "train_meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    if not meta:
        lex = json.loads((best_dir / LEXICON_FILENAME).read_text(encoding="utf-8"))
        meta = {"decoding": lex.get("decoding", {}), "lexicon_terms": lex.get("count"),
                "corpora_summary": summarize(corpora)}
    return finalize_candidate(best_dir, run_dir, corpora, synthetic, meta, max_per_source, 300, seed, True, force)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune / evaluate the medical TrOCR handwriting recogniser")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=5e-5)
    parser.add_argument("--model_id", type=str, default="microsoft/trocr-small-handwritten")
    parser.add_argument("--corpora_dir", type=str, default=str(DEFAULT_CORPORA_DIR))
    parser.add_argument("--mix", type=str, default=DEFAULT_MIX)
    parser.add_argument("--samples_per_epoch", type=int, default=12000)
    parser.add_argument("--encoder_lr_scale", type=float, default=0.5)
    parser.add_argument("--label_smoothing", type=float, default=0.1)
    parser.add_argument("--grad_accum", type=int, default=1)
    parser.add_argument("--num_workers", type=int, default=4)
    parser.add_argument("--val_max_per_source", type=int, default=400)
    parser.add_argument("--test_max_per_source", type=int, default=1500, help="0 = full test split")
    parser.add_argument("--gradient_checkpointing", action="store_true", help="trade compute for memory (base/large models)")
    parser.add_argument("--resume", action="store_true", help="continue an interrupted run in --output_dir")
    parser.add_argument("--output_dir", type=str, default=None)
    parser.add_argument("--promote", action="store_true", help="install the best checkpoint if it beats the current one")
    parser.add_argument("--force_promote", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--eval_only", action="store_true")
    parser.add_argument("--model_dir", type=str, default=str(INSTALLED_MODEL_DIR))
    parser.add_argument("--num_beams", type=int, default=4)
    parser.add_argument("--report_json", type=str, default=None, help="--eval_only: write the report here")
    parser.add_argument("--retune", type=str, default=None,
                        help="rebuild vocabularies and re-tune decoding for this checkpoint dir")
    parser.add_argument("--medical_gate", type=float, default=None, help="--retune: pin the lexicon gate")
    parser.add_argument("--promote_from", type=str, default=None,
                        help="evaluate an existing run's best/ dir against the installed model and promote if better")
    args = parser.parse_args()

    if args.retune:
        retune(args.retune, args.corpora_dir, args.val_max_per_source, args.seed, args.medical_gate)
    elif args.promote_from:
        promote_from(args.promote_from, args.corpora_dir, args.test_max_per_source, args.seed, args.force_promote)
    elif args.eval_only:
        eval_only(args.model_dir, args.corpora_dir, args.test_max_per_source, args.num_beams, args.seed, args.report_json)
    else:
        train_trocr(
            epochs=args.epochs, batch_size=args.batch_size, lr=args.lr, model_id=args.model_id,
            corpora_dir=args.corpora_dir, mix=args.mix, samples_per_epoch=args.samples_per_epoch,
            encoder_lr_scale=args.encoder_lr_scale, label_smoothing=args.label_smoothing,
            grad_accum=args.grad_accum, num_workers=args.num_workers,
            val_max_per_source=args.val_max_per_source, test_max_per_source=args.test_max_per_source,
            output_dir=args.output_dir, promote=args.promote, force_promote=args.force_promote, seed=args.seed,
            gradient_checkpointing=args.gradient_checkpointing, resume=args.resume,
        )
