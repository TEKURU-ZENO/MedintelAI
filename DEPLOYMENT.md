# Local desktop runtime operations

This repository is currently maintained as a Windows Electron desktop application with a local FastAPI service. Web hosting, Docker Compose, Vercel, and installer delivery are outside this branch's current scope.

## Runtime prerequisites

- Windows 10/11, Python 3.11 64-bit, Node.js 20+
- Python dependencies in `backend/requirements-original.txt` and `backend/requirements.txt`
- Node dependencies in the root `package-lock.json`
- Sufficient local disk for Python packages and downloaded OCR model weights; TrOCR base weights are fetched from Hugging Face if not cached.

## First-time setup and launch

```powershell
cmd /c setup-windows.cmd
cmd /c run-medintel.cmd
```

The launcher runs the desktop API on `127.0.0.1:8000` and opens the Electron UI. Check `http://127.0.0.1:8000/health` for service status and `/openapi.json` for the active API schema.

## Model configuration

- `TROCR_FINETUNED_MODEL_PATH`: optional local Transformers checkpoint directory. The default is the root training output `app/ai/models/trocr_medical_finetuned`, followed by the legacy `backend/app/ai/models/trocr_medical_finetuned` directory.
- `TROCR_MODEL_NAME`: base TrOCR model identifier or local directory; defaults to `microsoft/trocr-base-handwritten`.

The fine-tuned checkpoint is used only when files are present and the Transformers processor and model load successfully. Otherwise the service logs a warning and attempts the configured base model followed by its existing small-model fallback. Keep trained weights local unless separately approved for repository distribution.

## Troubleshooting

- Backend startup failures: run the command from `backend/` so `app.main:app` resolves correctly; check the installed dependencies and model download/cache.
- Port conflict: stop the process already listening on port 8000 before launching.
- Missing model: verify local cache/network access or set `TROCR_MODEL_NAME` to a valid local model directory.
- Linux OpenCV runtime errors: install the platform's OpenGL and GLib runtime libraries.

Do not treat health or API connectivity as evidence of OCR quality. Validate extracted content against labeled examples for each supported document type.
