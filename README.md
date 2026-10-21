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

## Benchmark Performance Matrix

| Document Category | Target | Resolution | Confidence | Routing | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Digital Vector PDF (Resume)** | Multi-column, modern fonts | $1191 \times 1684$ | **89.3%** | 100% RapidOCR | PASS |
| **Scanned Medical Report (MVD)** | Official hospital form | $1024 \times 1448$ | **82.8%** | 100% RapidOCR | PASS |
| **Clinical Prescription** | Mixed printed + cursive | $800 \times 1000$ | **84.7%** | Hybrid RapidOCR + TrOCR | PASS |
| **Digital Screen Capture Snippet** | UI action buttons / menus | $460 \times 320$ | **89.7%** | RapidOCR + 2.5× Upscale | PASS |

---

## API Routes & Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Engine health check, initialized models & system status |
| `POST` | `/ocr/extract` | Ingests PDF or image, runs resolution preservation & line grouping |
| `POST` | `/ocr/extract-region` | Processes a cropped snippet with 2.5× multi-scale bicubic upscaling |
| `POST` | `/ocr/correct` | Submits human clinician transcription correction |
| `POST` | `/ocr/evaluate` | Evaluates Character Error Rate (CER) and Word Error Rate (WER) against ground truth |
| `GET` | `/ocr/stats` | Pipeline latency and confidence breakdown |

---

## Quickstart

### Prerequisites
- Python 3.10, 3.11, or 3.12 (64-bit)
- Node.js 20+ and npm

### 1. Clone & Set Up Backend
```bash
git clone https://github.com/TEKURU-ZENO/MedintelAI.git
cd MedintelAI

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start backend server (port 8000)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Set Up Web Frontend
```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```
- Open [http://localhost:5173](http://localhost:5173) in your browser.
- Interactive API docs available at [http://localhost:8000/docs](http://localhost:8000/docs).

---

## Windows Desktop Studio & Electron App

In addition to the web studio, a standalone Windows desktop workspace is included:

### Desktop Shell Features
- **Electron Integration**: Native Windows desktop shell (`electron-main.cjs`) running React with direct local backend service pairing.
- **Automated Windows Scripts**:
  - `setup-windows.cmd` — Automates Python virtual environment setup and dependencies.
  - `run-medintel.cmd` — Starts the backend OCR API on `127.0.0.1:8000` and launches the Electron desktop app.
  - `start-desktop.cmd` — Launches the Electron desktop UI directly.
  - `build-windows-installer.cmd` — Compiles a native Windows NSIS installer (`.exe`) via `electron-builder` into `release/`.

To build the Windows desktop installer:
```powershell
npm run desktop:win
```

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
├── backend/                              # Desktop companion tools & fallback APIs
├── design/                               # Desktop UI mockups and specifications
├── docs/                                 # Architectural specifications & deployment guides
├── electron-main.cjs                     # Electron desktop shell entry point
├── electron-builder.yml                  # NSIS Windows installer configuration
├── scripts/                              # Benchmark & evaluation harnesses
├── requirements.txt                      # Primary OCR engine dependencies
└── README.md
```

---

## License

This project is licensed under the Apache 2.0 License.
