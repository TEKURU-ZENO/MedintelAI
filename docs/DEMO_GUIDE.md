# Desktop application smoke demo

This guide covers features present in the current Electron UI. It makes no claim about OCR accuracy beyond a successful request and response.

## Start

Run `setup-windows.cmd` once, then `npm ci`, followed by `run-medintel.cmd`. Confirm the FastAPI process is available at `http://127.0.0.1:8000/health`. The Electron window should open with the OCR Studio workspace.

## Verify a document

1. Upload a non-sensitive test image or PDF.
2. Choose Balanced, High contrast, Grayscale, or No preprocessing.
3. Run OCR and check the returned text and confidence display.
4. For a multi-page PDF, check the extracted text includes page separators and the response page count is correct.
5. For an image, use Select region, draw a crop, and run Region OCR.
6. Use the correction action and verify the current text reflects the submitted correction.
7. Download text or JSON from the UI.

The current UI exports text and JSON locally. The backend also exposes `/ocr/export/txt` and benchmark endpoints, but the UI does not currently call them. Benchmark UI, per-block correction, page-aware review, global toolbar/hotkeys, live screen capture, and HIS integration are not part of the current feature set.

## Safety and evaluation

Use synthetic or appropriately authorized sample files. A health check or successful OCR request only demonstrates service operation; compare output with labeled ground truth before making any quality claims.
