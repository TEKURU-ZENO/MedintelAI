# MedIntel OCR backend

## Primary engine (preserves original MedIntel pipeline)
The original backend is `app.main:app`. It includes image/PDF ingestion, multi-page processing, OCR provenance, normalized bounding boxes, crop processing, correction, and benchmark endpoints. `main.py` also mounts the expiring share-link router from `sharing.py`.

From this directory, run on Windows:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Dependencies for the original hybrid engine are listed in `requirements-original.txt`. RapidOCR/TrOCR dependencies and their model weights can be large and may download on first use. Configure `CORS_ORIGINS` and a unique `SECRET_KEY` in `.env` before deployment.

## Lightweight fallback
`tesseract_api.py` is a separate fallback API using Tesseract, Pillow and PyMuPDF. Run it on port 8001 if the original engine is already on 8000. It is not the original hybrid engine. Install `requirements.txt`, install the Tesseract executable separately, then run:

```powershell
.venv\Scripts\python.exe -m uvicorn tesseract_api:app --host 127.0.0.1 --port 8000
```

## Share links
`sharing.py` creates expiring TXT/JSON download links and stores only token hashes. A separate revocation secret is returned once. Bearer URLs must be protected. Authentication/authorization, audit logs, HTTPS, rate limits, encryption, and retention controls are required before use with real patient data.

## Tests
Fallback API smoke tests:

```powershell
.venv\Scripts\python.exe -m pip install pytest httpx
.venv\Scripts\python.exe -m pytest -q
```
