# OCR Document Reading System — Developer Setup Guide

This guide provides step-by-step instructions for engineers to set up a local development environment, install all OCR inference dependencies, run the test suite, and launch the OCR Document Reading System.

---

## 1. Prerequisites

Before starting, ensure your workstation meets the following requirements:
* **Python**: Version 3.10, 3.11, or 3.12 (64-bit recommended)
* **Node.js**: Version 20+ (with `npm`)
* **Git**: Installed and configured
* **System Libraries (Linux only)**:
  ```bash
  sudo apt-get update && sudo apt-get install -y libgl1-mesa-glx libglib2.0-0
  ```

---

## 2. Backend Setup

### A. Clone Repository & Create Virtual Environment
```bash
git clone https://github.com/TEKURU-ZENO/MedintelAI.git
cd MedintelAI

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows PowerShell:
.\venv\Scripts\activate
# Windows Command Prompt:
.\venv\Scripts\activate.bat
# Linux / macOS:
source venv/bin/activate
```

### B. Install Python Dependencies
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Key packages installed:
* `fastapi` & `uvicorn` — REST API framework and ASGI server
* `rapidocr-onnxruntime` — ONNX DBNet text detection and printed line recognizer
* `transformers` & `torch` — HuggingFace VisionEncoderDecoder runtime for TrOCR handwriting recognition
* `pypdfium2` — High-performance PDF renderer
* `opencv-python-headless` & `numpy` — Image manipulation, CLAHE, and deskewing

### C. Environment Configuration
Create a `.env` file in the project root:
```env
ENVIRONMENT=development
PORT=8000
TROCR_MODEL_NAME=microsoft/trocr-base-handwritten
DEBUG_OCR=true
```

### D. Verify Backend Service
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Navigate to `http://localhost:8000/docs` to inspect the Swagger UI.

---

## 3. Frontend Setup

### A. Install Dependencies
In a separate terminal window:
```bash
cd frontend
npm install
```

### B. Start Vite Development Server
```bash
npm run dev -- --host 0.0.0.0 --port 5173
```
Open your browser at `http://localhost:5173` to interact with the **OCR Document Reading System** console.

### C. Verify Production Build
```bash
npm run build
```
Confirms all TypeScript typings and JSX modules bundle cleanly without errors.

---

## 4. Running Benchmarks & Acceptance Tests

Execute the 4-document automated acceptance suite:

```bash
python scripts/run_acceptance_tests.py
```

This suite validates:
1. **Screen / Digital Pipeline**: `DevMehta_Groww_IT.pdf` (Tests resolution preservation, verifies $\ge 85\%$ confidence and 0 fragmented characters).
2. **Scanned Form Pipeline**: `mvd_medical_report.jpg` (Tests adaptive thresholding and 100% printed recognition).
3. **Prescription Form**: `prescription.png` (Tests handwriting classification and dosage preservation).
4. **Digital Screen Crop**: Tests multi-scale 2.5× bicubic upscale and spatial line grouping.
