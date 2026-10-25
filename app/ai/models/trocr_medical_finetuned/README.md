# Medical HTR TrOCR checkpoint

- Base model: `microsoft/trocr-base-handwritten`
- Trained: 2026-10-25 11:38:41
- Epochs: 10 | best epoch: 9
- Training corpora: {"iam_line": {"train": 6482, "val": 976, "test": 2915}, "rxhandbd": {"val": 446, "train": 4017, "test": 1115}, "kaggle_rx_bd": {"test": 780, "train": 3120, "val": 780}, "gnhk_word": {"train": 28442, "val": 2523, "test": 9561}, "gnhk_line": {"train": 5906, "val": 610, "test": 2085}}
- Lexicon terms: 10856

| Test set | CER | CER (case-insens.) | WER | Exact match | ms/crop |
| :--- | ---: | ---: | ---: | ---: | ---: |
| iam_line:test | 0.065 | 0.062 | 0.152 | 0.312 | 429.7 |
| rxhandbd:test | 0.269 | 0.219 | 0.635 | 0.392 | 157.1 |
| kaggle_rx_bd:test | 0.039 | 0.037 | 0.066 | 0.944 | 129.0 |
| gnhk_word:test | 0.150 | 0.131 | 0.337 | 0.686 | 124.2 |
| gnhk_line:test | 0.116 | 0.103 | 0.336 | 0.341 | 356.9 |
| synthetic:test | 0.002 | 0.002 | 0.005 | 0.980 | 370.0 |

Used by `app/ai/ocr/htr_engine.py` (MedicalHTREngine) for handwritten line/word crops routed by the
hybrid OCR engine. `medical_lexicon.json` holds the drug / clinical vocabulary used for
confidence-gated lexicon correction.