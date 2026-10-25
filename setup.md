# Desktop developer setup

## Prerequisites

- Windows 10/11
- Python 3.11 64-bit (the setup script creates `backend/.venv` with `py -3.11`)
- Node.js 20+ and npm
- Internet access on first dependency/model download
- For OpenCV on Linux, install the distribution's OpenGL and GLib runtime libraries (commonly `libgl1` and `libglib2.0-0`).

## Install

From the repository root in PowerShell:

```powershell
cmd /c setup-windows.cmd
```

The Python setup installs `backend/requirements-original.txt` (primary RapidOCR/TrOCR engine and test dependencies) and `backend/requirements.txt` (API and currently retained fallback dependencies). The desktop OCR path is the primary RapidOCR/TrOCR backend. Tesseract is not the primary desktop engine.

The setup script checks Node and Python, creates the virtual environment, and uses `npm ci` with the tracked `package-lock.json`.

## Launch

```powershell
cmd /c run-medintel.cmd
```

The script starts `uvicorn app.main:app` from `backend/` on `127.0.0.1:8000` and launches Electron. For backend-only development:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Health: `http://127.0.0.1:8000/health`; OpenAPI: `http://127.0.0.1:8000/openapi.json`.

## Models and configuration

The base TrOCR model defaults to `microsoft/trocr-base-handwritten`, fetched by Transformers on first use and cached locally. Set `TROCR_MODEL_NAME` to another supported base model. Fine-tuning writes to `app/ai/models/trocr_medical_finetuned`; set `TROCR_FINETUNED_MODEL_PATH` to override the checkpoint location for desktop inference. The runtime will report and fall back if the configured checkpoint is missing or cannot load. No fine-tuned weights are committed or generated as part of setup.

PyTorch and Transformers are declared in `backend/requirements-original.txt`. GPU acceleration depends on a compatible PyTorch/CUDA environment; CPU inference is supported but may be slower. No additional OCR system binary is required for the primary RapidOCR/TrOCR path.

## Checks

```powershell
Push-Location backend
python -m pytest tests
Pop-Location
npm run build
```

These checks validate software behavior and buildability, not clinical OCR accuracy. Use representative labeled documents for quality evaluation.
