# Medical HTR TrOCR checkpoint

- Base model: `microsoft/trocr-large-handwritten`
- Trained: 2026-10-26 00:48:47
- Epochs: 8 | best epoch: 8
- Training corpora: {"iam_line": {"train": 6482, "val": 976, "test": 2915}, "rxhandbd": {"val": 446, "train": 4017, "test": 1115}, "kaggle_rx_bd": {"test": 780, "train": 3120, "val": 780}, "gnhk_word": {"train": 28442, "val": 2523, "test": 9561}, "gnhk_line": {"train": 5906, "val": 610, "test": 2085}}
- Lexicon terms: 10855

| Test set | CER | CER (case-insens.) | WER | Exact match | ms/crop |
| :--- | ---: | ---: | ---: | ---: | ---: |
| iam_line:test | 0.049 | 0.046 | 0.124 | 0.391 | 621.4 |
| rxhandbd:test | 0.233 | 0.186 | 0.574 | 0.448 | 299.6 |
| kaggle_rx_bd:test | 0.038 | 0.035 | 0.068 | 0.937 | 205.3 |
| gnhk_word:test | 0.135 | 0.117 | 0.315 | 0.710 | 189.4 |
| gnhk_line:test | 0.091 | 0.079 | 0.283 | 0.418 | 446.6 |
| synthetic:test | 0.002 | 0.002 | 0.013 | 0.963 | 504.3 |

Used by `app/ai/ocr/htr_engine.py` (MedicalHTREngine) for handwritten line/word crops routed by the
hybrid OCR engine. `medical_lexicon.json` holds the drug / clinical vocabulary used for
confidence-gated lexicon correction.