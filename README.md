# OCR Document Reading System

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19.2+-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-8.0+-646CFF.svg?logo=vite&logoColor=white)](https://vitejs.dev)
[![RapidOCR](https://img.shields.io/badge/RapidOCR-ONNX_Runtime-brightgreen.svg)](https://github.com/RapidAI/RapidOCR)
[![TrOCR](https://img.shields.io/badge/TrOCR-VisionEncoderDecoder-yellow.svg)](https://huggingface.co/microsoft/trocr-base-handwritten)
[![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-v4.0-38B2AC.svg?logo=tailwind-css&logoColor=white)](https://tailwindcss.com)

A high-accuracy, production-grade document intelligence platform that ingests arbitrary documents (multi-page PDFs, high-res scans, hospital records, and screen captures), runs **resolution-preserving preprocessing**, executes **hybrid OCR routing** (RapidOCR ONNX for printed layout + fine-tuned TrOCR for handwriting), performs **spatial line grouping before recognition**, rebuilds natural 2D reading order, and renders a **Google Lens-style visual text overlay** with click-to-copy and structured export.

---

## System Architecture

```
                      Arbitrary Document / Screen Capture
                      (PDF, JPEG, PNG, TIFF, Screen Frame)
                                      │
                                      ▼
                        Input Mode Classifier & Router
                                      │
               ┌──────────────────────┴──────────────────────┐
               ▼                                             ▼
       [Screen / Digital Mode]                       [Scanned Paper Mode]
    • NO destructive binarization                 • Deskewing & perspective correction
    • Preserves sub-pixel antialiasing            • Noise reduction & morphological cleanup
    • Mild CLAHE (clipLimit=1.2)                  • Adaptive Gaussian binarization
    • Light bilateral denoise (d=3)               • High-contrast document thresholding
    • 2.5× bicubic upscale for crops              • Preserves document borders
               │                                             │
               └──────────────────────┬──────────────────────┘
                                      │
                                      ▼
                           Text Region Detection
                        (RapidOCR ONNX DBNet Detector)
                                      │
                                      ▼
                         Spatial Line Grouping Engine
                 (Vertical Overlap ≥ 0.45, Proximity Clustering)
                   Constructs Unified Line Crops from High-Res
                                      │
                                      ▼
                        Line Classification & Routing
                                      │
               ┌──────────────────────┴──────────────────────┐
               ▼                                             ▼
       [Printed Text Engine]                         [Handwritten Engine]
         RapidOCR Rec (ONNX)                       TrOCR (VisionEncoderDecoder)
         Fast, sub-millisecond                     Fine-tuned transformer attention
               │                                             │
               └──────────────────────┬──────────────────────┘
                                      │
                                      ▼
                        Medical Vocabulary Normalizer
                       (Dosages, Rx units, medical terms)
                                      │
                                      ▼
                       2D Reading-Order Geometric Rebuilder
                     (Top-to-bottom, multi-column traversal)
                                      │
                                      ▼
                    Interactive Google Lens Visual Canvas
              (Exact normalized bounding box overlays, click-to-copy)
                                      │
                                      ▼
                        Structured JSON & Plain Text (.txt)
```

---

## Key Capabilities

1. **Resolution-Preserving Preprocessing**:
   - Eliminates downscaling degradation by preserving original image resolution (up to 4096px).
   - Separates digital screen captures from physical paper scans, preventing the destructive binarization noise that ruins antialiased fonts.

2. **Spatial Line Grouping Before Recognition**:
   - Replaces fragile character/word micro-fragmentation with intelligent geometric line clustering.
   - Merges adjacent detection boxes horizontally ($-0.3h \le \text{gap} \le 2.2h$) and vertically ($\ge 0.45$ overlap) to crop and recognize complete lines (e.g., `Dev Mehta`, `Submit another application`).

3. **Hybrid OCR Routing**:
   - **Printed Text**: Handled by RapidOCR (ONNX Runtime) for millisecond inference.
   - **Handwritten Text**: Handled by Microsoft TrOCR (`microsoft/trocr-base-handwritten`) fine-tuned on clinical notes and forms.

4. **Google Lens-Style Visual Studio**:
   - Renders text overlays directly on top of the original document canvas with zero visual drift (`normalized_bbox` percentages).
   - Instant click-to-copy for any text line.
   - Marquee snippet crop tool: drag a box over any region to execute a 2.5× upscaled OCR scan.
   - Region-first live screen capture via browser `getDisplayMedia`.

5. **2D Reading-Order Geometric Rebuilder**:
   - Sorts blocks topologically using horizontal overlap bands, handling multi-column layouts, tabular medical forms, and standard reading flow.

6. **Standardized Exports & Human Corrections**:
   - Plain text `.txt` download with preserved paragraph and column flow.
   - Full structured JSON export containing bounding boxes, confidence scores, model provenance, and normalized ratios.
   - Human-in-the-loop clinician review drawer to submit corrections.

---

## Quantitative Benchmarks

Benchmarked across canonical real-world test sets:

| Test Document | Input Mode | Blocks Detected | Confidence | Accuracy Highlights | Latency | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Resume PDF** (`DevMehta_Groww_IT.pdf`) | Screen / Digital | 70 lines | **89.3%** | "Dev Mehta", "Software Engineering", 0 fragmented characters | 7.62s | **PASS** |
| **Printed Medical Report** (`mvd_medical_report.jpg`) | Scanned Form | 36 lines | **82.8%** | 100% printed lines detected, "MEDICAL REPORT", "DRIVER LICENSE" | 2.47s | **PASS** |
| **Prescription Form** (`prescription.png`) | Mixed / Auto | 7 lines | **84.7%** | All header and dosage information intact | 0.77s | **PASS** |
| **Web UI Snippet** (Buttons) | Screen Snippet | 4 lines | **89.7%** | "Submit another application", "Cookie Preferences" | 0.50s | **PASS** |

---

## REST API Specification

The FastAPI backend exposes the following endpoints:

### 1. Document OCR Ingestion
- **`POST /ocr/extract`**
  - **Payload**: `file` (multipart/form-data: PDF, PNG, JPG, TIFF, WEBP), `input_mode` (optional: `auto`, `screen`, `scanned`).
  - **Response**: JSON containing `status`, `document`, `pages`, `total_blocks`, `overall_confidence`, `blocks` (with `id`, `text`, `confidence`, `source`, `model_used`, `bbox`, `normalized_bbox`), and `raw_text`.

### 2. Snippet / Marquee Crop OCR
- **`POST /ocr/extract-region`**
  - **Payload**: `file`, `xmin`, `ymin`, `xmax`, `ymax`, `input_mode` (optional).
  - **Response**: Up-scaled snippet OCR with global coordinates mapped back to the document canvas.

### 3. Plain Text Export
- **`POST /ocr/export/txt`**
  - **Payload**: `file`
  - **Response**: Plain text file attachment (`.txt`) with reading-order preserved text.

### 4. Human Clinician Correction
- **`POST /ocr/correct`**
  - **Payload**: JSON `{ "document": "filename", "block_id": "b1", "original_text": "...", "corrected_text": "...", "clinician_notes": "..." }`
  - **Response**: Status acknowledgement stored in corrections registry.

### 5. Health Check
- **`GET /health`**
  - **Response**: `{"status": "ok", "system": "OCR Document Reading System", "version": "1.0.0"}`

---

## Technology Stack

- **Backend**: Python 3.10+, FastAPI, Uvicorn, OpenCV (`opencv-python-headless`), NumPy, PyPDFium2.
- **Inference Engines**: RapidOCR ONNX Runtime, HuggingFace Transformers (`VisionEncoderDecoderModel`), PyTorch.
- **Frontend**: React 19, TypeScript, Vite 8, Tailwind CSS v4, Axios, React Router.
- **Deployment**: Docker, Docker Compose, Nginx, Vercel Serverless.

---

## Quick Start Guide

### Prerequisites
- Python 3.10+ (64-bit)
- Node.js 20+ & npm

### 1. Backend Setup
```bash
# Clone the repository
git clone https://github.com/TEKURU-ZENO/MedintelAI.git
cd MedintelAI

# Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API documentation available at: `http://localhost:8000/docs`

### 2. Frontend Setup
```bash
cd frontend

# Install packages
npm install

# Start Vite development server
npm run dev -- --host 0.0.0.0 --port 5173
```

Access the UI at: `http://localhost:5173`

---

## Repository Structure

```
├── app/
│   ├── ai/
│   │   ├── ocr/
│   │   │   └── ocr_engine.py             # Hybrid RapidOCR + TrOCR engine & line grouping
│   │   ├── pipeline/
│   │   │   └── pipeline_controller.py    # Multi-page orchestration & region cropping
│   │   ├── preprocessing/
│   │   │   ├── normalize.py              # Resolution preservation (up to 4096px)
│   │   │   └── preprocessing_pipeline.py # Dual-path screen vs scanned preprocessing
│   │   └── utils/
│   │       ├── pdf_handler.py            # High-res PyPDFium2 rasterizer
│   │       └── logger.py                 # Structured logger
│   ├── api/
│   │   └── ocr.py                        # FastAPI /ocr endpoints
│   ├── core/
│   │   └── config.py                     # Environment settings
│   └── main.py                           # Application entry point & router setup
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── MedIntelOCRStudio.tsx     # Google Lens visual canvas & snippet tool
│   │   ├── pages/
│   │   │   ├── LandingPage.tsx           # Feature showcase & benchmark breakdown
│   │   │   └── Home.tsx                  # Root console view
│   │   └── App.tsx                       # Router configuration
│   └── package.json
├── docs/                                 # Architectural specifications & guides
├── scripts/                              # Benchmark & evaluation harnesses
├── requirements.txt                      # Backend dependencies
└── README.md
```

---

## License

This project is licensed under the Apache 2.0 License.
