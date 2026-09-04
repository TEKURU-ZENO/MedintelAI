# MedIntel AI - Medical Document OCR Engine & Verification System

MedIntel AI is a production-grade medical document OCR engine combining OpenCV document image preprocessing, PaddleOCR layout & printed text extraction, TrOCR handwriting recognition, confidence status classification, and an interactive dual-pane clinician verification UI.

---

##  Key Features

* **Medical Document Preprocessing**: CLAHE contrast enhancement, Bilateral denoising, Otsu/Adaptive binarization, and Deskewing for hospital scans, prescriptions, and lab reports.
* **Hybrid OCR Architecture**:
  * Printed text regions ? PaddleOCR Engine.
  * Handwritten notes & clinical observations ? TrOCR / Line Recognition Engine.
* **Confidence Status Classification**:
  * `HIGH_CONFIDENCE` (`? 90%`) ? Accepted ?
  * `REVIEW_REQUIRED` (`60% ? 90%`) ? Flagged for Review ?
  * `HUMAN_VERIFICATION_NEEDED` (`< 60%`) ? Verification Needed ?
* **FastAPI Medical OCR API**:
  * `POST /ocr/extract` ? Upload document and receive structured OCR JSON with bounding boxes `[xmin, ymin, xmax, ymax]`.
  * `POST /ocr/correct` ? Human clinician review correction endpoint.
  * `GET /ocr/benchmark` ? Real-time CER & WER benchmark report.
* **Interactive Dual-Pane OCR Viewer**: React 19 + Tailwind UI rendering original image with interactive SVG bounding boxes overlay and clinician correction form.
* **Quantitative Benchmark Harness**: Automated evaluation calculating Character Error Rate (CER), Word Error Rate (WER), and processing speed.

---

##  Technology Stack

* **Backend**: Python 3.10+, FastAPI, Uvicorn, OpenCV, NumPy, PyYAML, Pillow.
* **OCR Engines**: PaddleOCR, TrOCR (`transformers`).
* **Frontend**: React 19, TypeScript, Vite, Tailwind CSS v4, Axios.
* **Containerization & Web Server**: Docker, Docker Compose, Nginx Alpine.

---

##  Quick Start (Docker Deployment)

```bash
# Clone the repository
git clone https://github.com/TEKURU-ZENO/MedintelAI.git
cd MedintelAI

# Deploy using Docker Compose
docker-compose up -d --build
```

Access endpoints:
* **Frontend Dual-Pane OCR Studio**: [http://localhost](http://localhost)
* **Backend OCR API**: [http://localhost:8000](http://localhost:8000)
* **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

##  Benchmark Evaluation

Run accuracy evaluation on test medical dataset:

```bash
python scripts/benchmark_ocr.py
```

Outputs CER, WER, and latency metrics across Printed, Handwritten, Mixed, and Low-Quality document categories.
