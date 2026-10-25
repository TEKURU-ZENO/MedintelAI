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

Runtime knobs: `HTR_NUM_BEAMS` (default 4 on GPU, 2 on CPU; beam 2 keeps almost all of beam 4's
accuracy) and `HTR_INT8=0` to disable int8 CPU quantisation (~3x faster on CPU, accuracy within noise).

Training on a laptop GPU: close games / 3D apps and keep the charger connected. A competing renderer
slowed training ~30x in practice; an 8 GB card needs `--gradient_checkpointing` for the base model.

## Current checkpoint (run of 2026-10-25)

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
