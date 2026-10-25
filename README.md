# MedIntelAI OCR Studio

MedIntelAI OCR Studio is an Electron desktop application backed by a local FastAPI OCR service. The desktop runtime uses RapidOCR for printed text and TrOCR for handwriting, followed by medical vocabulary post-processing and structured results. Training and evaluation scripts are maintained separately under `scripts/`; the desktop uses fine-tuned TrOCR weights only when a valid checkpoint is present.

## Requirements

- Windows 10/11 (the supplied launch scripts are Windows command files)
- Python 3.10–3.12, 64-bit; Python 3.11 is recommended
- Node.js 20+ and npm
- Runtime dependencies from `backend/requirements-original.txt` and `backend/requirements.txt`
- TrOCR weights: the base model is downloaded from Hugging Face on first use unless cached. Fine-tuned medical weights are not included in Git.

## Setup and run

From PowerShell at the repository root:

```powershell
cmd /c setup-windows.cmd
cmd /c run-medintel.cmd
```

The setup script creates the local Python environment, installs the repository's declared OCR dependencies, and installs Node packages with `npm ci` from the tracked lockfile. `run-medintel.cmd` starts the primary backend from `backend/` using `app.main:app` and launches the Electron desktop application. The API is served on `http://127.0.0.1:8000`; health and OpenAPI are available at `/health` and `/openapi.json`.

For manual backend startup, activate the environment created by `setup-windows.cmd`, then run from the `backend` directory:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## TrOCR checkpoint selection

The training script writes to `app/ai/models/trocr_medical_finetuned`. The desktop backend checks that path first, then its legacy backend-local checkpoint directory. Set `TROCR_FINETUNED_MODEL_PATH` to select another checkpoint directory. It must contain a Transformers-compatible processor and model. `TROCR_MODEL_NAME` selects the base model (default `microsoft/trocr-base-handwritten`); if unavailable, the existing `microsoft/trocr-small-handwritten` fallback is attempted. Without a successfully loaded checkpoint, the application uses the base model. Training dependencies include PyTorch and Transformers as listed in `backend/requirements-original.txt`.

## Development checks

```powershell
Push-Location backend
python -m pytest tests
Pop-Location
npm run build
```

The backend test suite does not establish clinical OCR accuracy. Validate OCR quality with representative, consented documents and labeled ground truth before relying on extracted text.

## Project map

- `src/`, `electron-main.cjs` — desktop UI and Electron shell
- `backend/` — primary desktop FastAPI API, document pipeline, preprocessing, and OCR engines
- `app/` — retained root AI/OCR modules and checkpoint output location used by training/evaluation resources
- `scripts/` — model training and evaluation utilities
- `docs/` — architecture, setup, and verification notes

Website frontend and its web deployment configuration have been removed from this desktop-focused branch. Installer packaging, SDK distribution, and HIS integration are outside the current scope.

## License

See [LICENSE](LICENSE).
