# OCR Document Reading System — Product Requirements Document (PRD)

> **Version:** 2.0.0 | **Status:** Production-Ready, Pipeline Hardened

---

## 1. Product Vision & Executive Summary

The **OCR Document Reading System** is an intelligent, document-agnostic optical character recognition and reading-order reconstruction platform. It allows users and clinicians to extract high-accuracy text from arbitrary documents—including multi-page PDFs, hospital admissions, lab tests, prescriptions, and live digital screen captures—and overlay the recognized text directly onto the visual document in a **Google Lens-style** interactive canvas.

### The Core Problem Solved
Traditional OCR pipelines fail upstream of recognition:
1. **Destructive Downscaling & Hard Binarization**: Downscaling documents to arbitrary low-resolution canvases (e.g. 800px) and applying aggressive global binarization shreds antialiased digital fonts into binary noise, dropping recognition confidence to $<60\%$ and creating fragmented garbage characters (e.g. `Doy ela`).
2. **Micro-Fragmentation**: Detectors split words and buttons into fragments (`Su`, `bm`, `it`), which recognition models cannot interpret out of context.
3. **Lack of In-Situ Visual Feedback**: Standard OCR returns disjointed text without spatial provenance, preventing users from validating recognized text against the original visual document.

The **OCR Document Reading System** eliminates these failure modes via resolution preservation, dual-path preprocessing, spatial line grouping before recognition, and an interactive Google Lens visual interface.

---

## 2. Target Users & Use Cases

| User Group | Core Workflow | Primary Pain Point Addressed |
| :--- | :--- | :--- |
| **Clinicians & Doctors** | Instant capture of open hospital EHRs, lab reports, and handwritten prescriptions. | Eliminates manual transcription errors and interprets mixed handwriting. |
| **Medical Records Staff** | Ingestion of multi-page PDF discharge summaries and referral forms. | Reconstructs natural columnar reading order with single-click `.txt` export. |
| **Enterprise Users** | Screen snippet capture from digital documents, resumes, or administrative web tools. | 2.5× upscale preserves digital font edges with zero micro-fragmentation. |

---

## 3. Functional Requirements

### 3.1 Ingestion & Preprocessing Subsystem
- **FR-1.1 (Multi-Format Intake)**: The system must ingest PDFs, PNGs, JPEGs, TIFFs, WEBP images, and live browser window video frames.
- **FR-1.2 (Resolution Preservation)**: Original document resolutions must be preserved up to 4096px. Downscaling to arbitrary 800px canvases is strictly prohibited.
- **FR-1.3 (Dual-Path Preprocessing)**:
  - *Screen / Digital Mode*: Continuous grayscale, mild CLAHE (`clipLimit=1.2`), light bilateral denoise (`d=3`), NO binarization.
  - *Scanned Paper Mode*: Deskewing, noise filtering, adaptive Gaussian thresholding.
- **FR-1.4 (Snippet Upscaling)**: For snippet crops under 250px height, the pipeline must apply a 2.5× bicubic upscale before detection.

### 3.2 Detection & Line Grouping Subsystem
- **FR-2.1 (Line-Level Detection)**: The detector must locate all printed and handwritten text regions with pixel coordinates.
- **FR-2.2 (Spatial Line Grouping)**: Adjacent detection boxes on the same baseline (vertical overlap $\ge 0.45$, horizontal gap $-0.3h \le \text{gap} \le 2.2h$) must be unified into single line crops prior to recognition.
- **FR-2.3 (Whole-Line Recognition)**: Recognition models must execute on complete line crops rather than concatenating recognized word fragments.

### 3.3 Hybrid Recognition Engine
- **FR-3.1 (Printed Recognition)**: RapidOCR ONNX inference engine must handle printed Latin text lines with sub-millisecond per-line latency.
- **FR-3.2 (Handwritten Recognition)**: Microsoft TrOCR (`microsoft/trocr-base-handwritten`) must recognize cursive handwriting and clinical notes routed via stroke morphology analysis.
- **FR-3.3 (Confidence Scoring)**: Every line block must be assigned a confidence score and classified into `HIGH_CONFIDENCE`, `REVIEW_REQUIRED`, or `HUMAN_VERIFICATION_NEEDED`.

### 3.4 2D Reading-Order Rebuilder
- **FR-4.1 (Geometric Reordering)**: Lines must be topologically sorted from top to bottom and left to right across multiple columns, preventing cross-column text interleaving.
- **FR-4.2 (Plain Text Generation)**: The engine must assemble formatted, reading-order text (`raw_text`) ready for export.

### 3.5 Google Lens Visual Studio & Interaction
- **FR-5.1 (Visual Text Overlay)**: Recognized text lines must render directly on top of the document image using normalized percentages (`normalized_bbox`), ensuring zero drift regardless of screen size.
- **FR-5.2 (Click-to-Copy)**: Clicking any recognized block on the document must immediately copy its text to the system clipboard.
- **FR-5.3 (Region-First Screen Capture)**: Capturing a screen frame must immediately activate marquee snippet selection mode, allowing the user to crop the target area.
- **FR-5.4 (Dual Export)**: Users must be able to download plain text (`.txt`) and structured JSON artifacts with a single click.
- **FR-5.5 (Clinician Corrections)**: The interface must provide a review drawer where users can correct transcriptions and submit feedback to `/ocr/correct`.

---

## 4. Non-Functional Requirements

- **Accuracy**:
  - Overall confidence on digital documents $\ge 85\%$.
  - Character Error Rate (CER) on standard printed forms $< 5\%$.
- **Latency**:
  - Focused screen snippet crops: $< 1.0\text{s}$.
  - Full high-resolution single-page document: $< 8.0\text{s}$ on CPU.
- **Agnostic Architecture**:
  - The core OCR engine must remain strictly document-agnostic. No hardcoding of specific resume layouts, prescription templates, or form IDs.
- **Security & Privacy**:
  - All processing occurs locally or within self-hosted private VPCs. No document images are sent to third-party public AI APIs.

---

## 5. Acceptance Benchmark Criteria

The platform is evaluated against four real-world acceptance benchmarks:
1. **Resume PDF** (`DevMehta_Groww_IT.pdf`): Must recognize key identity and technical lines with $\ge 85\%$ confidence and 0 fragmented characters (`Doy ela`).
2. **Printed Medical Report** (`mvd_medical_report.jpg`): Must classify 100% of lines as printed with $\ge 80\%$ confidence.
3. **Prescription** (`prescription.png`): Must preserve dosages and route handwriting to TrOCR.
4. **Web UI Buttons Snippet**: Must recognize complete coherent lines (`Submit another application`, `Cookie Preferences`) within 1.0s.
