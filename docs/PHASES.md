# OCR Document Reading System — Engineering Phase History & Evolution Log

> **Canonical Record:** Comprehensive chronicle of architectural decisions, root cause analyses, and development milestones.

---

## Phase Summary Overview

| Phase | Milestone Name | Core Breakthrough | Outcome |
| :--- | :--- | :--- | :--- |
| **Phase 1** | Baseline Engine & Pipeline | FastAPI backend, RapidOCR ONNX + TrOCR integration | Functional end-to-end OCR pipeline |
| **Phase 2** | Document-Agnostic Refactor | Decoupled prescription assumptions, built standardized benchmark harness | 8-category evaluation suite |
| **Phase 3** | Google Lens Visual Experience | In-place CSS percentage overlays, click-to-copy, live screen capture | Interactive visual feedback |
| **Phase 4** | Root Cause Diagnosis of Fragmentation | Traced 100-box shredded OCR (`Doy ela`) to 800px downscale and hard threshold 127 | Root cause identified and isolated |
| **Phase 5** | Resolution Preservation & Line Grouping | Dual-path preprocessing, spatial line grouping before recognition | Coherent lines, 89.3% confidence |
| **Phase 6** | Region-First Marquee Snippet Mode | 2.5× multi-scale bicubic upscale, marquee snippet workflow | All 4 acceptance benchmarks passed |
| **Phase 7** | Production Hardening & Documentation Sync | Cleaned legacy names, unified API contracts, updated all 11 doc files | Production-ready release |

---

## Phase 1: Baseline Engine & Pipeline

- **Objective**: Establish a modern, production-grade document OCR system using local, privacy-compliant inference.
- **Key Deliverables**:
  - Implemented `app/api/ocr.py` with `/extract`, `/extract-region`, and `/correct` endpoints.
  - Built `app/ai/ocr/ocr_engine.py` integrating RapidOCR (ONNX DBNet text line detector) and HuggingFace TrOCR (`VisionEncoderDecoderModel`).
  - Implemented 2D geometric reading-order rebuilder.
  - Created initial dual-pane React UI for document preview.

---

## Phase 2: Document-Agnostic Refactor & Benchmark Harness

- **Objective**: Prevent the OCR engine from over-indexing on prescription forms, making it universally applicable across all document types.
- **Key Deliverables**:
  - Separated domain-specific medical dictionary lookups into non-destructive post-processors.
  - Built automated evaluation suite measuring Character Error Rate (CER) and Word Error Rate (WER).
  - Established standardized benchmarks across 8 document categories (Prescriptions, Lab Reports, Discharge Summaries, Clinical Notes, Referral Forms, Admission Records, Consent Forms, Arbitrary Documents).

---

## Phase 3: Google Lens Visual Experience & Screen Ingestion

- **Objective**: Shift the paradigm from a static "upload-and-read-text" tool to an interactive Google Lens visual experience.
- **Key Deliverables**:
  - Replaced disjointed sidebar text with in-place text overlays directly on top of the visual document canvas.
  - Implemented `normalized_bbox` coordinate ratios to ensure zero visual drift across different screen sizes and zoom levels.
  - Added single-click text copying to system clipboard.
  - Added browser window and screen capture via `navigator.mediaDevices.getDisplayMedia`.

---

## Phase 4: Root Cause Diagnosis of Severe Fragmentation

- **Symptom**: Ingesting clean digital documents (such as a 1-page resume PDF) produced 100 broken fragments, low confidence (56.6%), and garbled characters (e.g., `Doy ela`, `I'tyt. tt-`, `--+*`).
- **Root Cause Identified**:
  - In `app/ai/preprocessing/normalize.py`, every document was forcibly downscaled to `height = 800` (reducing a $1191 \times 1684$ PDF to $565 \times 800$).
  - A global hard binarization threshold `cv2.threshold(normalized, 127, 255)` was applied to all documents.
  - This destroyed the sub-pixel antialiasing of digital fonts, turning crisp vector letters into noisy black-and-white pixel clusters that broke the DBNet detector into 100 micro-fragments.
- **Empirical Proof**:
  - Bypassing the downscale and thresholding on the raw $1191 \times 1684$ image immediately boosted average confidence to **89.3%**, reading `Dev Mehta`, `Software Engineering`, and `B.Tech CSE, 2027` cleanly.

---

## Phase 5: Resolution Preservation, Dual-Path Preprocessing & Line Grouping

- **Key Implementations**:
  1. **Resolution Preservation**: Updated `normalize.py` to preserve original dimensions up to 4096px.
  2. **Dual-Path Preprocessing**:
     - `run_screen_preprocessing`: Grayscale + mild CLAHE (`clipLimit=1.2`) + bilateral filter (`d=3`). **NO binarization.**
     - `run_scanned_preprocessing`: Deskewing + bilateral denoise + adaptive Gaussian thresholding.
  3. **Spatial Line Grouping (`group_and_merge_lines`)**:
     - Clustered bounding boxes by vertical overlap ($\ge 0.45$) and horizontal proximity ($-0.3h \le \text{gap} \le 2.2h$).
     - Built `_recognize_line_group` to construct complete line crops from the high-resolution image and recognize whole lines rather than micro-fragments.

---

## Phase 6: Region-First Marquee Snippet Mode & Acceptance Benchmarking

- **Key Implementations**:
  - Implemented a **region-first workflow** for screen captures: capturing a window loads the frame and immediately activates the marquee selection tool.
  - In `process_region`, added a 2.5× multi-scale bicubic upscale for snippets $< 250\text{px}$, allowing small digital fonts (12–18px) to be read with $\ge 89\%$ confidence.
  - Automated acceptance benchmark suite (`scripts/run_acceptance_tests.py`) passed all 4 canonical documents:
    - **Test 1 (Resume PDF)**: PASS (89.3% confidence, 70 clean lines, 0 "Doy ela").
    - **Test 2 (MVD Printed Report)**: PASS (82.8% confidence, 100% printed).
    - **Test 3 (Prescription Form)**: PASS (84.7% confidence, dosage intact).
    - **Test 4 (Screen Action Buttons)**: PASS (89.7% confidence, 4 coherent lines, 0.50s latency).

---

## Phase 7: Production Hardening & Global Documentation Sync

- **Key Deliverables**:
  - Standardized all class and module names to `OCRDocumentReadingEngine` and `OCRDocumentStudio`.
  - Updated temp directories to `ocr_document_temp`, `ocr_document_json`, and `ocr_document_txt`.
  - Re-wrote and synchronized all 11 project documentation files (`README.md`, `DEPLOYMENT.md`, `setup.md`, `frontend/README.md`, and all 7 files in `docs/`).
  - Validated frontend build (`npm run build`) and backend tests.
