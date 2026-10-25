# Desktop runtime guide

MedIntelAI is being consolidated as a locally run Electron application with its primary FastAPI OCR backend. Web, Vercel, and Docker deployment instructions were retired along with their web-only resources.

## Startup

See [setup.md](../setup.md) for supported Python/Node versions and dependency installation. On Windows, `setup-windows.cmd` prepares the Python environment and `run-medintel.cmd` starts `backend/app.main:app` on `127.0.0.1:8000` before launching Electron.

Verify the service at `http://127.0.0.1:8000/health` and inspect `http://127.0.0.1:8000/openapi.json`. The frontend's API URL is configured in the Electron application source; local desktop origin access is allowed by the backend CORS configuration.

## Model paths

The fine-tuning script writes its checkpoint under `app/ai/models/trocr_medical_finetuned`. Desktop inference checks that output, then the legacy backend-local checkpoint path. `TROCR_FINETUNED_MODEL_PATH` overrides the candidate path. A directory counts as active only if both its processor and model load; otherwise the service logs a warning and uses the configured base TrOCR model, then the existing small-model fallback.

The base model may be downloaded/cached by Hugging Face Transformers. PyTorch and Transformers are installed from `backend/requirements-original.txt`. Model files are not tracked in Git. GPU use requires a PyTorch build compatible with the installed CUDA runtime.

## Operational boundary

This guide does not describe a packaged installer, SDK, hosted website, or HIS integration. Health checks prove process/API availability only; OCR quality requires labeled input samples and separate evaluation.
