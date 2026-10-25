# Desktop integration verification plan

This plan covers integration behavior for the Electron UI and primary FastAPI backend. Passing connectivity and contract checks does not validate clinical OCR accuracy.

## Automated checks

From the repository root in PowerShell:

```powershell
Push-Location backend
python -m pytest tests
Pop-Location
npm run build
```

Backend tests cover API contracts, preprocessing modes, and model checkpoint path selection. The frontend build verifies the Vite production bundle used by Electron.

## Runtime checks

Start the backend from `backend/` with the project's Python environment:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Verify `/health`, `/openapi.json`, and the UI's actual requests. Exercise image OCR, a multi-page PDF with page count, region OCR, correction, export, invalid file/mode responses, CORS from the Electron origin, and the API base URL. Record actual server responses and do not substitute mock responses for integration evidence.

For TrOCR selection, test a valid local fine-tuned checkpoint if one exists; otherwise verify and report which base model loaded. A path-selection unit test does not prove weights are present or that the checkpoint initializes.

## Quality evaluation

Use representative, consented documents with labeled ground truth and compute OCR metrics separately. Historical benchmark figures in older materials are not acceptance evidence for this branch unless their inputs, environment, and outputs are reproducible and available.

## Out of scope

Benchmark UI, per-block correction UI, page-aware multi-page review UI, floating global toolbar, global hotkeys, HIS integration, installer generation, and SDK distribution are separate product decisions.
