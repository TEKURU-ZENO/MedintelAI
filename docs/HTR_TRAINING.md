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

## Document intelligence layer (desktop backend)

Added on top of the page pipeline; none of it changes the OCR API shape (new fields are additive).

| Stage | File | What it does |
| :--- | :--- | :--- |
| Orientation | `backend/app/services/document_processing_service.py`, `app/ai/ocr/page_orientation.py` | Phone photos are decoded upright from their EXIF tag. Pages with no tag are checked from content: one downscaled PP-OCR detection tells horizontal from vertical lines, then PP-OCR reads the longest lines at both remaining rotations and the clearly better one wins (104/104 correct on gold pages turned 0/90/180/270) |
| Layout roles | `app/ai/ocr/document_layout.py`, `htr_layout.py` | Braces / vertical rules become separators that lines are never merged across; short notes left of a separator become `role: margin_note` with `applies_to` (the lines the brace spans) and get their own reading row; signatures (labelled, or short low-validity handwriting in the lower page, or a short lower-page line whose two readings share under 40% of their characters, i.e. a scribble whichever reader won) become `role: signature`, text `[signature]`, reading kept in `raw_text`; header / footer roles |
| Spelling correction | `app/ai/ocr/htr_language_model.py`, `scripts/fit_spell_correction.py` | Noisy-channel correction of handwriting lines: SymSpell candidates from the checkpoint's lexicon, a handwriting confusion channel (u/r, a/o, rn/m, cl/d...) and DistilGPT-2 context. Never touches known words, drug names, acronyms, mid-line capitalised words (names) or words next to doses. Weights in `<checkpoint>/spell_correction.json`, fitted with a rule that rejects any medical-source regression. Blocks keep `raw_text` and list `corrections` |
| Reading choice | `app/ai/ocr/htr_language_model.py` (`choose_reading`), `scripts/fit_reading_choice.py` | Before spelling correction each line is checked against the other recogniser's reading of the same crop. An unknown word becomes the formulary drug the other reading spells within two look-alike edits, even when that reader ran it into its dose ("Tab ParID 40mg" / "Tab. PanD40nmg" -> Pan-D). Where the other reading has a different real word in the same place, DistilGPT-2 picks the one that fits the line by `reading_margin` nats, less `clinical_prior` when the other word is in `app/ai/ocr/clinical_terms.txt` and this one is not ("gun paint" / "gum paint", "General Dictionary" / "General Dentistry"). A drug name is never traded for an English word. `reading_margin` 1.0 is fitted on the ensemble crops in both directions with no source allowed to get worse (test CER of PP-OCR-read lines: Kaggle Rx 0.168 -> 0.106, RxHandBD 0.413 -> 0.380, GNHK 0.156 -> 0.147, IAM 0.189 -> 0.179; TrOCR-read lines change by under 0.002). `clinical_prior` 4.0 is set by hand: the crops hold no clinical-term swaps, so the fit cannot see it; it only acts on words in the clinical list and is checked on the gold pages. Changes are listed in `corrections` with `reason: "other reading"` / `"drug in other reading"` |
| Image-checked spelling (off) | `app/ai/ocr/htr_engine.py` (`score_texts`), `scripts/fit_spell_correction.py --image` | TrOCR's teacher-forced likelihood of each candidate line given the crop can join the spelling gain (`image_weight`) or veto a candidate (`image_veto`). It separates the true line from a one-letter misspelling 35/35 times, but it favours TrOCR's own reading, so it adds nothing on TrOCR lines, and on PP-OCR lines the fitted gain (about 0.003 CER on GNHK / IAM) came with a loss on Kaggle Rx. Left at `image_weight` 0 |
| Word review | `app/ai/ocr/text_review.py` | Grammarly-style flags, `block.review` = `[{word, start, end, kind, suggestions, reason}]` with offsets into `block.text`, and `result.review_summary` (`flagged_words`, `lines_to_check`). `ambiguous`: the two recognisers read a word differently and the other reading is made of real words (its garbles are ignored); `spelling`: not a known word, drug, number or abbreviation, with LM-ranked suggestions (drug names only beside a dose); `corrected`: auto-corrected, the original reading is offered to revert. Names and words beside a dose are flagged only on unsure lines; lines under 0.6 confidence get `needs_review`. The text is never edited. Printed-path lines of scans and photos are spell-corrected too (not screen / digital input); a correction of a word broken across lines ("recommenda" / "tion") is undone so the formatter can rejoin it |
| Formatted reading | `app/ai/ocr/document_formatter.py` | `result.formatted_text`, the document as a clinician would retype it: letterhead first; one patient line (`Patient: ... \| Age/Sex: ... \| Date: ...`) where the fields sit; prescriptions as `Rx` plus numbered medicine lines with dose, frequency, duration, timing (margin notes folded in) and instructions; lab tables as `test \| value unit \| ref range \| HIGH/LOW`; wrapped lines rejoined into paragraphs (hyphenated and unhyphenated word breaks); a side column split at a clear gutter is read after the main text as its own paragraph, unless both sides line up row by row (table / form); footer and `[Signature]` last. `raw_text` keeps the as-read order. The studio shows the formatted view by default with an "As read" toggle, and a Review tab whose suggestion chips replace the word in the text |
| Section template | `app/ai/ocr/document_formatter.py`, `app/ai/ocr/format_template.json` | Clinical pages (medicines, lab rows, a written section heading or vitals) come out in a fixed section order whatever order the page is written in: patient, vitals, complaints, examination, diagnosis, Rx, labs, investigations, advice, follow-up, notes. A line goes to the section its heading names (C/O, H/O, O/E, Dx, Imp, Inv, Adv, F/U...), else by content (medicines, lab rows, vitals such as `BP 120/80` / `RR - 22/min`, follow-up phrases), else to the section of the heading above it; text below the medicines goes to advice and text with no section to notes, so nothing is dropped. Clinical sections keep the doctor's lines as items; only notes are reflowed. A side column starts its own context. The hospital's own format is a JSON file (`OCR_FORMAT_TEMPLATE`): section keys, printed titles, order and the headings its doctors write. `result.sections` gives the same sections for an HIS form (`{template, letterhead, sections: [{key, title, lines, medications}], signature}`); notebook and letter pages keep the plain reading and get `sections: null` |
| Structured extraction | `app/ai/ocr/medical_structurer.py` | `result.structured` / `metadata.structured`: document type, patient name / age / sex / weight / date / doctor, medications (form, drug, concentration such as `(250/5)`, preparation as written such as "gum paint" with a wrapped next word ("massage") rejoined, strength, frequency incl. `1-0-1` and `Q6H`, duration, timing incl. margin-note timing via `applies_to`, route), lab results with H/L flags, key-values and issues (incl. "drug matched approximately to X (verify)" when a drug was snapped to the lexicon). Every fact cites its block ids; OCR text is never edited |
| Local VLM (opt-in) | `app/ai/ocr/vlm_reader.py`, `scripts/fit_vlm_rule.py` | `HTR_VLM=1` lets a local vision-language model (default `Qwen/Qwen3-VL-2B-Instruct`, GPU only) re-read handwriting lines the ensemble is unsure about. Only used when `<checkpoint>/vlm.json` exists, which `fit_vlm_rule.py --install` writes only if the gate improved held-out CER. Nothing leaves the machine |
| Feedback loop (opt-in) | `backend/app/services/feedback_service.py` | `OCR_FEEDBACK_DATASET=1` keeps page images + boxes of extractions; corrections saved through `/correct` are aligned line by line and become (page region, corrected text) pairs in `manifest.jsonl`, read by `datasets/htr_sources.load_feedback()` as the `feedback` training source (15% of the mix). Off by default because it stores patient pages |

Extra runtime knobs:

| Variable | Default | Effect |
| :--- | :--- | :--- |
| `OCR_AUTO_ORIENT` | `1` | `0` skips the content orientation check (EXIF is always applied) |
| `HTR_SPELL_CORRECTION` | `1` | `0` disables context spelling correction |
| `OCR_FORMAT_TEMPLATE` | bundled `format_template.json` | The hospital's section template (order, titles, headings) for the formatted reading and `result.sections` |
| `OCR_FORMULARY` | unset | Path of the hospital formulary (one name per line, or a CSV whose first column is the name; a header row is skipped). Its names join the checkpoint's drug terms and the bundled `app/ai/ocr/drug_names_india.txt` (common Indian brands): never spell-corrected to English, matched by the structurer, and offered as drug swaps |
| `HTR_VLM` | `0` | `1` enables the local VLM re-read (needs `vlm.json`, a CUDA GPU and transformers >= 4.57) |
| `HTR_VLM_MODEL` | from `vlm.json` | Hugging Face id or local path of the VLM |
| `OCR_FEEDBACK_DATASET` | `0` | `1` stores extractions and turns corrections into training pairs |
| `OCR_FEEDBACK_DIR` | `datasets/htr_corpora/feedback` | Where the feedback store lives |

### Gold page set and harness (`datasets/gold/`, `backend/scripts/evaluate_gold.py`)

Full-page, end-to-end evaluation, the number a user actually sees (crop-level CER hides detection,
segmentation, orientation and reading-order losses). Each gold page is a JSON with the image path, ordered
lines (optional `role`, `applies_to`) and expected structured `fields`.

| Group | Pages | Source |
| :--- | ---: | :--- |
| `user_pages` | 3 | Hand-transcribed real pages (prescription with margin notes, two notebook pages) |
| `printed` | 8 | Synthetic medical documents from `datasets/*/sample_1` |
| `gnhk` | 20 | GNHK test phone photos (`scripts/build_gold_from_public.py`) |
| `funsd` | 15 | FUNSD test scanned forms |
| `rxsynth` | 20 | chinmays18 prescription test pages with patient / medication fields |

```bash
cd backend
python scripts/evaluate_gold.py --label <name>          # all pages -> outputs/gold_eval/<name>.json
python scripts/evaluate_gold.py --only gnhk_eng_AF_036 --verbose
```

Metrics: row-level line CER / WER (gold lines matched to reading rows), word F1 (order-free), insertion
rate, page CER, Kendall tau of reading order, field F1 on structured facts, seconds per page.

Results (GPU, RTX 5050; line CER / word F1 / page CER):

| Group | Baseline | + EXIF orientation, layout roles, spelling, structuring | + median-band rows | + spelling on printed-path lines of scans, review, formatting (current, v6) |
| :--- | :--- | :--- | :--- | :--- |
| printed (8) | 0.005 / 0.967 / 0.005 | 0.005 / 0.967 / 0.005 | 0.005 / 0.967 / 0.005 | 0.005 / 0.971 / 0.004 |
| rxsynth (20) | 0.101 / 0.865 / 0.111 | 0.096 / 0.870 / 0.105 | 0.096 / 0.870 / 0.105 | 0.096 / 0.876 / 0.104 |
| user_pages (3) | 0.244 / 0.716 / 0.168 | 0.231 / 0.722 / 0.161 | 0.231 / 0.722 / 0.161 | **0.226 / 0.752 / 0.156** |
| gnhk (20) | 0.422 / 0.580 / 0.516 | 0.273 / 0.700 / 0.383 | **0.245** / 0.700 / 0.380 | 0.245 / 0.702 / 0.380 |
| funsd (15) | 0.699 / 0.804 / 0.277 | 0.698 / 0.805 / 0.276 | **0.673** / 0.805 / 0.274 | 0.672 / 0.808 / 0.273 |

Structured field F1: 0.93 on rxsynth, 0.70 on the real prescription page (margin timing written over two
lines, or fused by the detector onto a medicine line, is attached to the medicines it spans; lab rows split
into table cells are read whole). Seconds per page on the GPU with all of the above: printed 2.8, rxsynth
5.2, GNHK 9.9, FUNSD 12.6, real prescription / notebook pages 16 (orientation check about 0.8 s of that
on CPU). Close other GPU apps first: a game launcher overlay sharing the 8 GB card stalled the run.

v8 (full GPU run, `outputs/gold_eval/v8.json`), adding paediatric Rx parsing (concentration, Q6H, weight,
wrapped preparation words), the scribble-signature rule, the bundled Indian brand list and the reading choice
(line CER / word F1 / page CER):

| Group | v6 | v8 |
| :--- | :--- | :--- |
| printed (8) | 0.005 / 0.971 / 0.004 | 0.005 / 0.971 / 0.004 |
| rxsynth (20) | 0.096 / 0.876 / 0.104, field F1 0.927 | 0.095 / 0.877 / 0.104, field F1 0.932 |
| user_pages (3) | 0.226 / 0.752 / 0.156, field F1 0.70 | **0.213 / 0.795 / 0.137**, field F1 0.75 |
| gnhk (20) | 0.245 / 0.702 / 0.380 | 0.244 / 0.706 / 0.379 |
| funsd (15) | 0.672 / 0.808 / 0.273 | 0.672 / 0.810 / 0.271 |

Of 66 pages, 13 improved and two FUNSD forms slipped slightly (word F1 0.626 -> 0.614 on one, line CER
0.429 -> 0.432 on another). The White Tusk prescription's medicine block now reads exactly (Pan-D,
Hexigel gum paint massage, "General Dentistry").

v9 (section template, follow-up and stray-duration fixes in the structurer): every page scores the same as v8.
The harness scores reading rows and structured fields, not section order; the order is covered by the tests in
`backend/tests/test_review_and_format.py` (jumbled pages, shuffled detector order, a hospital template).

VLM fit (Qwen3-VL-2B-Instruct, untuned, 1,200 val + 1,200 test crops): alone it reads at 0.21 macro CER
(0.10 with both engines' readings as hints) against 0.06 for the ensemble. The best gate (calibrated
confidence < 0.9, plain prompt, anchored to an engine reading, VLM confidence >= 0.85) helped GNHK
(0.071 -> 0.067) and IAM (0.053 -> 0.051) but hurt drug names (RxHandBD 0.183 -> 0.186), 0.0621 vs 0.0618
overall, so `vlm.json` was **not** installed and `HTR_VLM=1` currently has no effect. Re-run
`collect_ensemble_candidates.py --add_vlm` + `fit_vlm_rule.py --install` for a larger or fine-tuned VLM.

Findings that drove the changes:
- Phone photos stored sideways with an EXIF tag were read rotated (5 of 20 GNHK pages scored line CER
  1.0, though the words were recognised); decoding upright fixed them. The content orientation check
  covers pages without a tag.
- The row grouper compared new boxes with the union band of a row, so one tall box chained the next line
  into it; comparing with the row's median band fixed that.
- FUNSD line CER stays high while word F1 is 0.80: FUNSD gold "lines" are form entities (a label and its
  value are separate), while the engine reports one reading row, so this is partly a unit mismatch.
  GNHK gold also leaves printed text (packaging, letterheads) unannotated, so reading it counts as insertions.
- The remaining GNHK gap is mostly segmentation on camera pages (adjacent lines and side notes fused).
- Field extraction reads garbled labels ("Pauent:", "Apr: 42" -> Patient / Age; real labels such as
  "Bed:" are never rewritten) and reports SIG instructions ("as directed", "every 8 hours", "as needed for
  pain") as `instructions`. The OCR text itself is not changed.
- Known recogniser bias: the fine-tuned TrOCR appends "mg" after numbers in patient headers ("28/m" ->
  "28 mg", "Age: 42" -> "12 mg") and can read "Patient:" as the drug "Praluent", because its synthetic
  prescription lines are mostly drug lines.
  - Retraining with synthetic patient-header lines (`header_share=0.15` in `datasets/htr_augment.py`; run
    `run4_header_ft`, 3 epochs at lr 1e-5 from the installed checkpoint) learnt the headers (synthetic val CER
    0.31% -> 0.24%) but lost a little on drug names (Kaggle BD 2.5% -> 3.0%): val score 0.0397 against the
    installed 0.0368, so it was not promoted. A retry should use a lower learning rate (about 5e-6) and a
    smaller header share.
  - Fixed at run time instead (`ocr_engine.py`, `_DOSE_ONLY` / `_AGE_SEX_READ`): a bare "<n> mg" line whose
    PP-OCR reading is "<n>/m" with the slash misread ("281m", "28|m") becomes "28/M". Real-page field F1
    0.70 -> 0.75, rxsynth unchanged (0.926).
- `--resume` loaded the saved model and optimiser state onto the GPU and kept that copy, which spilled an
  8 GB card (training slowed to a crawl, or ran out of memory at a smaller batch). It now loads on the CPU.

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
