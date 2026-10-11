# MedIntel AI OCR Studio — Windows Desktop Project

A Windows-oriented Electron + React OCR workspace connected to the **existing MedIntel OCR pipeline** from `MedintelAI-main.rar`. The original FastAPI OCR service is retained under `backend/app/`; expiring TXT/JSON share-link routes are added to that service. A separately launchable Tesseract API is included as a lightweight fallback for environments where the original ML runtime cannot be installed.

## Included

- Windows desktop shell (Electron) and responsive React OCR Studio.
- Existing MedIntel OCR backend modules, medical post-processing, PDF/image ingestion, multi-page document handling, provenance, block reading order, and crop/region service.
- OCR response adapter for confidence, metadata, and bounding boxes.
- PDF/image preview, image region selection, screen capture, OCR overlays, click-to-copy, editable results, correction submission, local document history, TXT/JSON export.
- FastAPI share links with expiry and a separate revocation token.
- Backend tests, setup scripts, security notes, and the design mockup.

## Prerequisites

- Windows 10/11 x64
- Node.js 20 LTS or newer
- Python 3.11 recommended for compatibility with the ML dependencies
- Internet access for the first dependency install; the original TrOCR/ML runtime may download large packages and model weights on first use.

## Setup and launch

1. Extract the ZIP and open the project folder.
2. Run `setup-windows.cmd`. It creates `backend\\.venv`, installs the original ML requirements plus the lightweight API requirements, and installs frontend packages.
3. Run `run-medintel.cmd`. It starts the existing FastAPI backend on `127.0.0.1:8000` and opens the Windows desktop UI.
4. If needed, open **API configuration** in the UI; the default is `http://localhost:8000`.

You can also launch the original backend manually:

```powershell
cd backend
.venv\\Scripts\\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Interactive API documentation: `http://127.0.0.1:8000/docs`.

`run-medintel.cmd` starts this same primary service and then launches Electron. For API-only development, `backend/start-api.cmd` runs `app.main:app` using the project's `backend/.venv`.

### OCR preprocessing options

The desktop sends `preprocessing_mode` independently of `input_mode` (the latter describes source context such as screen, digital, or scanned paper):

- `balanced`: retain the existing input-mode preprocessing behavior. The desktop selects screen mode for captures, digital mode for PDFs, and automatic mode for other files.
- `high-contrast`: run the existing scanned-paper pipeline (grayscale, normalization, CLAHE contrast enhancement, denoising, thresholding, and deskew).
- `grayscale`: convert to grayscale and back to three-channel image data for the OCR engines, without additional filtering.
- `none`: pass an unchanged image copy to OCR.

Older clients may omit `preprocessing_mode`; the backend then preserves its previous `input_mode` behavior. Unsupported preprocessing values are rejected by FastAPI validation.

## Build a Windows installer

On Windows, after dependencies have installed:

```powershell
npm.cmd run desktop:win
```

The NSIS installer is output to `release/`. The installer currently packages the Electron frontend; the Python API and model runtime remain separate services and must be installed/launched on the target machine. Code signing is not configured.

## Lightweight Tesseract fallback

If the original ML requirements are unavailable, install Tesseract OCR separately and launch the fallback on port 8001:

```powershell
cd backend
.venv\\Scripts\\python.exe -m uvicorn tesseract_api:app --host 127.0.0.1 --port 8001
```

This fallback supports image/PDF OCR, confidence and normalized word boxes, region OCR, TXT/JSON sharing, correction submission, and a basic WER endpoint. In the UI, change API configuration to `http://localhost:8001` while using this fallback. It is not a replacement for the original hybrid RapidOCR/TrOCR engine and does not provide dedicated handwriting recognition.

## Validation

- The fallback API tests cover image OCR, multipage PDF OCR, region coordinates, correction, benchmark, and share-link creation/revocation.
- Primary backend preprocessing contract tests: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_preprocessing_modes.py -q`.
- Full RapidOCR/TrOCR operation also requires the primary dependencies in `backend/requirements-original.txt` and model weights, which may download on first use.
- The Windows installer contains the Electron frontend only. Install and launch the primary Python service separately as described above.

## Production security

The share URL is a bearer credential: anyone possessing it can download the file until expiry or revocation. Before using real patient data, add authenticated user/tenant authorization, HTTPS, access auditing, rate limiting, protected storage and backups, retention/deletion controls, secret management, and a privacy/compliance review. Configure a unique `SECRET_KEY` and exact CORS origins in `backend/.env`. Do not expose this service publicly without those controls. OCR confidence is not a probability of clinical correctness; all clinical details must be reviewed by a qualified human. This software is not a certified medical device or a compliance certification.
