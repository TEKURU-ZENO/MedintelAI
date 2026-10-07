# OCR Document Reading System — Demo & Evaluation Guide

> **Audience:** Product Evaluators, Clinical Stakeholders & Technical Reviewers

---

## 1. Demo Objectives

This guide demonstrates how the **OCR Document Reading System** addresses the real-world shortcomings of document OCR via:
1. **Resolution-Preserving Preprocessing**: Preserving fine font geometry without destructive binarization.
2. **Spatial Line Grouping Before Recognition**: Eliminating character and word fragmentation.
3. **Google Lens Visual Experience**: Presenting recognized text directly on top of the document canvas with single-click copy and marquee snippet selection.
4. **Natural 2D Reading-Order Recovery**: Maintaining multi-column layout coherence for clean plain text export.

---

## 2. Step-by-Step Demonstration Script

### Act 1: Platform Overview & Benchmark Suite
1. Open the application at `http://localhost:5173`.
2. Review the **Landing Page**:
   - Point out the 8 benchmark document categories (Prescriptions, Lab Reports, Discharge Summaries, Clinical Notes, Referral Forms, Admission Records, Consent Forms, Arbitrary Documents).
   - Emphasize the document-agnostic pipeline: the same engine handles clinical forms, financial statements, resumes, and digital screen captures.
3. Click **"Launch OCR Console"** to enter the Document Studio.

### Act 2: High-Resolution Document Ingestion & Google Lens Overlay
1. In the Document Intake area, click on the sample **"MVD Medical Report"** or drag and drop a high-resolution PDF (e.g. `DevMehta_Groww_IT.pdf`).
2. Observe the ingestion speed:
   - RapidOCR ONNX executes detection across the full image.
   - Spatial line grouping consolidates adjacent boxes into coherent lines.
   - 2D reading-order reconstruction rebuilds paragraph hierarchy.
3. Switch between the 3 visualization modes:
   - **Lens Text**: Semitransparent text tags render directly over the original document. Hover over any text block to inspect confidence and engine provenance (RapidOCR vs. TrOCR).
   - **Boxes Mode**: Displays color-coded bounding wireframes based on verification status (`HIGH_CONFIDENCE`, `REVIEW_REQUIRED`, `HUMAN_VERIFICATION_NEEDED`).
   - **Original Document Mode**: View the raw document without overlays.
4. **Interactive Click-to-Copy**: Click on any text block on the document image. Confirm that the full text line is copied to the clipboard with an instant visual notification.

### Act 3: Live Screen Capture & Region-First Snippet Mode
1. In the studio toolbar, click **"Capture Screen or Window"**.
2. Select any open window on your desktop (e.g., a hospital EHR, browser tab, or PDF viewer).
3. Notice the **region-first workflow**:
   - The screen capture is immediately loaded into the canvas.
   - Marquee snippet mode is active with a crosshair cursor.
4. Drag a rectangular box over a target snippet (e.g., an action button, a medication table, or a clinical signature).
5. Click **"⚡ Run OCR on Selected Region"**:
   - The system crops the snippet, applies a 2.5× multi-scale bicubic upscale, and runs non-destructive screen preprocessing.
   - The text is extracted with high precision and mapped back to global coordinates.

### Act 4: Plain Text & Structured JSON Export
1. Switch to the **.txt View** tab to inspect the natural top-to-bottom and columnar text flow.
2. Click **"Download .txt"** to save the formatted plain text file.
3. Click **"JSON"** in the top action bar to inspect the machine-readable output containing pixel coordinates and normalized viewport ratios.

### Act 5: Clinician Review & Human-in-the-Loop Correction
1. In the right-hand panel, find any block flagged for review or click **"Correct"** on a block.
2. A review modal opens displaying the Block ID, original text, and an editable correction box.
3. Enter updated text and clinician notes, then click **"Save Correction"**.
4. The system updates the in-memory transcription and logs the correction to `/ocr/correct`.

---

## 3. Key Talking Points & Differentiators

- **Why Traditional OCR Fails**: Most systems downscale images to 800px and binarize using global thresholds, turning antialiased fonts into binary noise and producing fragmented gibberish (e.g., `Doy ela`).
- **Our Solution**: We preserve resolution up to 4096px, apply dual-path preprocessing (continuous grayscale with mild CLAHE for screens; adaptive thresholding for scans), and group bounding boxes before recognition.
- **Privacy & Security**: The entire stack runs locally or within private VPCs. No patient or enterprise document data is transmitted to public cloud LLMs.
