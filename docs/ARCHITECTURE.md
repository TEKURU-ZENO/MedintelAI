# MedIntelAI desktop architecture

## Runtime path

```text
Electron shell (electron-main.cjs)
  └─ Vite-built React UI (src/main.jsx)
      └─ local HTTP requests to FastAPI
          └─ backend/app/main.py
              └─ backend/app/api/ocr.py
                  └─ backend/app/services/ocr_service.py
                      └─ backend/app/ai/pipeline/pipeline_controller.py
                          ├─ document and PDF processing
                          ├─ preprocessing pipeline
                          └─ backend/app/ai/ocr/ocr_engine.py
                              ├─ RapidOCR / ONNX for printed text
                              └─ TrOCR / Transformers for handwriting
```

The desktop UI and backend API contract remain the integration boundary. The root `app/` tree is retained for the existing OCR/AI implementation and training ecosystem; the desktop service does not import the root web API entrypoint.

## Model training and inference

Training and runtime inference remain separate. `scripts/train_trocr_medical.py` writes a Transformers checkpoint to `app/ai/models/trocr_medical_finetuned`; evaluation utilities in `scripts/` read that location. Desktop inference checks `TROCR_FINETUNED_MODEL_PATH` when set, then the root training output and the legacy backend-local checkpoint path. It uses a fine-tuned model only when the checkpoint directory exists and both processor and model load. On failure it logs and tries `TROCR_MODEL_NAME` (default `microsoft/trocr-base-handwritten`), then the existing small handwritten model fallback. Checkpoints are local artifacts and are not included in Git.

## Request processing

The primary FastAPI service accepts images and PDFs through `/ocr/extract`, crops through `/ocr/extract-region`, corrections through `/ocr/correct`, and text exports through `/ocr/export/txt`. The controller renders PDF pages, preprocesses each page according to the selected mode, runs OCR, and normalizes results for the existing desktop UI. See `/openapi.json` from a running service for the current definitive schema.

`backend/app/ai/preprocessing/preprocessing_pipeline.py` implements the explicit `balanced`, `high-contrast`, `grayscale`, and `none` presets. Omitted preprocessing options retain the legacy input-mode dispatch. Unsupported values are rejected.

## Repository boundaries

- `src/`, `electron-main.cjs`, root `package.json`: desktop client and Electron shell
- `backend/`: primary desktop API, OCR runtime, schemas, and tests
- `app/`: retained root AI/OCR implementation and model output path used by training scripts
- `scripts/`: fine-tuning and evaluation tools
- `datasets/`, `config/`: data and configuration resources
- `docs/`: desktop setup, operations, test plan, and this architecture note

Website-only `frontend/` and web deployment adapters/configuration have been retired. Installer packaging, SDK distribution, and HIS integration are not part of this phase.
