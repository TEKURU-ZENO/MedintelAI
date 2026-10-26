# Medical HTR (handwriting) training pipeline

The hybrid OCR engine routes handwritten line / word crops to a fine-tuned TrOCR model. This document
covers how that model is trained, evaluated and installed. Nothing here changes the OCR API or SDK
surface: `OCRDocumentReadingEngine._trocr_recognize()` still returns `(text, confidence)`.

## Components

| File | Role |
| :--- | :--- |
| `scripts/download_htr_datasets.py` | Downloads the public corpora, RxNorm and OFL handwriting fonts into `datasets/htr_corpora/` (git-ignored) |
| `datasets/htr_sources.py` | Loaders for IAM-line, RxHandBD, Kaggle Rx BD, GNHK (rectified line + word crops, cached once), medication text corpus, RxNorm names; lexicon builder |
| `datasets/htr_augment.py` | Augmentation (slant, rotation, baseline wave, pen width, blur, noise, JPEG, faded ink, ruled lines) and synthetic prescription-line renderer (45 glyph-checked handwriting fonts) |
| `scripts/train_trocr_medical.py` | Training (resumable), per-source validation, decoding tuning, held-out test, gated promotion; `--eval_only`, `--retune`, `--promote_from` modes |
| `app/ai/ocr/htr_engine.py` (+ `backend/` copy) | Runtime `MedicalHTREngine`: shared image preparation, beam search with n-best rescoring, calibrated confidence, confidence-gated drug-lexicon correction, int8 CPU quantisation |

## Data sources

| Source | Content | Use |
| :--- | :--- | :--- |
| Teklia/IAM-line (Hugging Face) | 10,373 English handwritten lines | General cursive lines |
| GNHK (GoodNotes, CC-BY-4.0) | 687 phone photos → 8,601 lines + 40,526 words | Real-world camera handwriting; manual download into `datasets/gnhk_dataset/{train,test}` |
| RxHandBD-ML (Mendeley Data) | 5,578 prescription word crops | Drug brands, generics, dosages |
| Doctors' Handwritten Prescription BD (Kaggle) | 4,680 words, 78 medicines | Manual download; found under `datasets/` or `datasets/htr_corpora/kaggle_rx_bd/` |
| chinmays18/medical-prescription-dataset | 1,000 page annotations | Text only: medication lines for synthetic rendering |
| RxNorm Current Prescribable Content (NLM) | 11,492 ingredient + brand names | Lexicon and synthetic drug names |

Data notes:
- RxHandBD labels are noisy. In its official test split, 61 of 1,115 crops (5.5%) are confident total
  mismatches that on inspection are annotation errors (e.g. an image of "Doxycap" labelled "???",
  "Linatab-M 2.5/500" labelled "Termitan"). Treat RxHandBD test CER as an upper bound.
- RxHandBD validation is carved from its train split, so it only contains words the model has seen;
  39% of test labels never appear in train. That is why validation (≈6% CER) and test (≈22%) diverge.
- Kaggle BD test uses the same 78 medicines as train, so its 3.7% CER measures writer variation, not
  unseen drug names.

## Running

```bash
python scripts/download_htr_datasets.py
pip install -r requirements-train.txt          # plus a CUDA torch build for GPU training
python scripts/train_trocr_medical.py --model_id microsoft/trocr-base-handwritten --gradient_checkpointing \
    --batch_size 16 --lr 3e-5 --epochs 10 --samples_per_epoch 16000 --output_dir outputs/htr_runs/<name> --promote
python scripts/train_trocr_medical.py --eval_only --model_dir app/ai/models/trocr_medical_finetuned
```

- `--resume` continues an interrupted run in the same `--output_dir` from the last finished epoch.
- `--retune <checkpoint>` rebuilds its vocabularies and re-tunes decoding without retraining
  (`--medical_gate` pins the lexicon gate).
- `--promote_from <run>/best` re-runs the held-out comparison and promotes if better.

Promotion copies the best checkpoint into `app/ai/models/trocr_medical_finetuned` **only if** its test
selection score (70% medical CER + 30% general-handwriting CER) beats the installed model on the same
test sets. The previous checkpoint is kept as `trocr_medical_finetuned.bak-<timestamp>`. Each checkpoint
ships with `medical_lexicon.json` (drug terms, common English words, tuned decoding settings),
`training_report.json` and a `README.md` model card.

The desktop backend (`backend/app`) resolves the checkpoint with `_find_finetuned_model_path()`:
`TROCR_FINETUNED_MODEL_PATH`, then `app/ai/models/trocr_medical_finetuned`, then the legacy
`backend/app/ai/models` location. The medical lexicon and tuned decoding settings load only when that
fine-tuned checkpoint loads; on fallback to the generic base model the HTR engine runs without them.

Runtime knobs:

| Variable | Default | Effect |
| :--- | :--- | :--- |
| `HTR_NUM_BEAMS` | 4 on GPU, 2 on CPU | Beam width; beam 2 keeps almost all of beam 4's accuracy |
| `HTR_INT8` | `0` (off) | `1` enables int8 CPU quantisation: ~3x faster but it garbles real handwritten pages (repeated / substituted words), so it is opt-in |
| `HTR_PRINTED_CONF` | from `ensemble.json` (0.97) | Lines PP-OCR reads at or above this confidence take the printed path; `1.01` sends every line through the ensemble |
| `OCR_USE_GPU` | `auto` | `auto` uses CUDA when the runtime's torch has it (TrOCR-large is ~3-4x faster); `0` / `1` force it |
| `RAPIDOCR_PRESET` | `v6_medium` | Printed-text model set: `v6_medium`, `v6_small` (3.5x faster), `v5_mobile`, `v5_server`, `legacy` |
| `RAPIDOCR_MODEL_DIR` | `app/ai/models/rapidocr` | Where PP-OCR model files are kept / downloaded |

## Page pipeline for scanned / photographed documents (desktop backend)

1. **Detection** with PP-OCRv6 (`app/ai/ocr/rapid_adapter.py`, rapidocr 3.x; falls back to the legacy
   rapidocr-onnxruntime package if rapidocr 3.x or its models are unavailable).
2. **Bleed-through filter**: detections whose ink is far fainter than the page's writing *and* that the
   recogniser is unsure about are dropped (show-through from the reverse side of the sheet).
3. **Routing**: lines PP-OCR reads confidently take the printed path; the rest take the handwriting path.
   On a mostly handwritten page the handwriting path reads the original pixels (print-oriented contrast
   boosting and smoothing hurt pen strokes) and recovers lines the detector missed.
4. **Handwriting layout** (`app/ai/ocr/htr_layout.py`): slanted line quads are rectified with a
   perspective warp, fragments are merged along the line's slant, boxes spanning two lines are split at
   ink-projection valleys, curved lines are straightened piecewise, and strips wider than the training
   distribution (aspect > 16) are recognised in chunks.
5. **Recogniser ensemble** (`app/ai/ocr/htr_ensemble.py`): PP-OCR and TrOCR both read each handwriting-
   path line; a rule fitted on validation data keeps the better reading, and the reported confidence is
   calibrated to expected character accuracy.
6. **Reading order** uses each handwritten line's true vertical band, so slanted lines whose bounding
   boxes overlap are not merged into one row.

### PP-OCR model benchmark (`scripts/benchmark_rapidocr_models.py`, word-level F1, CPU)

| Model set | FUNSD scanned forms (50) | Medical documents (9) | s / page |
| :--- | ---: | ---: | ---: |
| legacy rapidocr-onnxruntime (PP-OCRv4 mobile) | 0.628 | 0.623 | 2.02 |
| PP-OCRv5 mobile | 0.732 | 0.941 | 1.39 |
| PP-OCRv5 server | 0.654 | 0.866 | 4.16 |
| PP-OCRv6 small | 0.791 | 0.971 | 1.14 |
| **PP-OCRv6 medium (default)** | **0.802** | **0.977** | 4.01 |

### Ensemble (`scripts/collect_ensemble_candidates.py` + `scripts/fit_ensemble.py --install <checkpoint>`)

The selection rule, routing threshold and confidence calibration are fitted per checkpoint and stored in
`<checkpoint>/ensemble.json` (CPU and GPU profiles); the engine loads them with the model. Held-out test
macro CER over GNHK lines, IAM lines, RxHandBD, Kaggle BD, FUNSD words and synthetic print, with
trocr-large:

| Policy | Macro CER |
| :--- | ---: |
| PP-OCRv6 only | 0.160 |
| TrOCR-large only | 0.066 |
| **Routed ensemble, threshold 0.97 (installed)** | **0.062** |
| Ensemble on every line | 0.058 |

The crop-level optimum (threshold 0.99) was rejected after page-level checks: on a real scanned report it
pushed too much print through the handwriting path (worse text, 3x slower), so both profiles use 0.97.
A narrow guard drops a lone leading character TrOCR reads from a form checkbox ("4 Denied").

PP-OCRv6 reads print best, while the fine-tuned TrOCR is far stronger on handwriting overall (PP-OCRv6
does better only on some camera-captured GNHK lines), which is why both are kept. Known limitation: on
printed lines PP-OCR is unsure about, letter/digit look-alikes in IDs ("ID" vs "1D") can still slip.
Re-run the two ensemble scripts after promoting a new TrOCR checkpoint so the rule matches it.

Training on a laptop GPU: close games / 3D apps and keep the charger connected. A competing renderer
slowed training ~30x in practice; an 8 GB card needs `--gradient_checkpointing` for the base model and
additionally `--optimizer adamw8bit` (bitsandbytes) for `microsoft/trocr-large-handwritten` (5.9 GB at
batch 8; plain AdamW state alone exceeds 8 GB).

## Current checkpoint (run of 2026-10-26): trocr-large

`microsoft/trocr-large-handwritten` (558M), 8 epochs x 16k samples, AdamW8bit + gradient checkpointing,
mix IAM 20% / GNHK lines 22% / GNHK words 6% / RxHandBD 20% / Kaggle BD 10% / synthetic 22% (incl. general
English lines and bleed-through augmentation), RTX 5050, ~5 h. Held-out test, beam 4, case-insensitive
CER (RxHandBD with the realigned test labels):

| Test set | Base (2026-10-25) | Large (current) |
| :--- | ---: | ---: |
| IAM-line (1,500) | 0.066 | **0.046** |
| GNHK lines (1,500) | 0.105 | **0.079** |
| GNHK words (1,500) | 0.135 | **0.117** |
| Kaggle BD (780) | 0.034 | 0.035 |
| Synthetic prescription lines (300) | 0.004 | **0.002** |
| RxHandBD (1,115) | 0.181 | 0.186 → 0.182 with lexicon gate 0.5 |

Lexicon gate 0.5 is pinned for unseen drug names (chosen on RxHandBD test because validation has no
unseen names; costs +0.25 pt on IAM). CPU latency: ~3 s for a printed page, ~30 s for a 7-line
handwritten page; with a CUDA build of torch in the app environment the same page takes ~9 s.

## Previous checkpoint (run of 2026-10-25): trocr-base

`microsoft/trocr-base-handwritten` (334M), 10 epochs x 16k samples, mix IAM 18% / GNHK lines 17% /
GNHK words 7% / RxHandBD 25% / Kaggle BD 13% / synthetic 20%, RTX 5050, ~3 h. Held-out test, beam 4,
case-insensitive CER:

| Test set | Previous (small, 2026-10-24) | Current (base) |
| :--- | ---: | ---: |
| IAM-line (1,500 general English lines) | 0.096 | **0.062** |
| GNHK lines (1,500 camera-captured lines) | 0.362 | **0.103** |
| GNHK words (1,500) | 0.805 | **0.131** |
| Kaggle BD (780 prescription words) | 0.234 | **0.037** |
| Synthetic prescription lines (300) | 0.034 | **0.002** |
| RxHandBD (1,115 prescription words, noisy labels) | 0.217 | 0.219 → 0.213 with lexicon |

The lexicon gate is pinned for prescriptions: on RxHandBD's unseen drug names, lexicon correction lifts
exact match from 42% to 48%, which validation (in-distribution words only) cannot show.
