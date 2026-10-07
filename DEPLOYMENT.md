# OCR Document Reading System — Production Deployment Guide

This guide covers deployment procedures for the **OCR Document Reading System** across Docker containers, bare-metal servers, and cloud serverless platforms.

---

## 1. System Requirements

### Minimum Requirements:
- **CPU**: 4 cores (x86_64 or ARM64)
- **RAM**: 8 GB (to accommodate RapidOCR ONNX and PyTorch TrOCR runtime models in memory)
- **Disk**: 10 GB available SSD storage
- **OS**: Linux (Ubuntu 22.04+ recommended), macOS (Apple Silicon supported), or Windows 11 / Server 2022

### Recommended for High-Throughput (GPU Accelerated):
- **GPU**: NVIDIA GPU with 8GB+ VRAM (e.g., RTX 3060, T4, or A10G)
- **CUDA**: 11.8+ or 12.1+
- **RAM**: 16 GB DDR4/DDR5

---

## 2. Docker Compose Deployment (Recommended)

Docker Compose encapsulates the FastAPI backend, the ONNX/PyTorch dependencies, and the Vite production web server.

### Steps:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/TEKURU-ZENO/MedintelAI.git
   cd MedintelAI
   ```

2. **Configure environment:**
   Create a `.env` file in the root directory:
   ```env
   ENVIRONMENT=production
   PORT=8000
   VITE_API_URL=http://localhost:8000
   TROCR_MODEL_NAME=microsoft/trocr-base-handwritten
   ```

3. **Build and launch containers:**
   ```bash
   docker compose up -d --build
   ```

4. **Verify container health:**
   ```bash
   docker compose ps
   curl -f http://localhost:8000/health
   ```

Endpoints:
- **Web Application Studio**: `http://localhost:5173` (or port 80 if reverse proxied)
- **FastAPI Documentation**: `http://localhost:8000/docs`

---

## 3. Manual Server Deployment (Ubuntu / Debian)

### 1. System Dependencies:
```bash
sudo apt-get update && sudo apt-get install -y \
    python3.10 python3.10-venv python3-pip \
    libgl1-mesa-glx libglib2.0-0 tesseract-ocr \
    nodejs npm git
```

### 2. Backend Setup:
```bash
git clone https://github.com/TEKURU-ZENO/MedintelAI.git
cd MedintelAI

python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Run as a systemd service or background daemon
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000
```

### 3. Frontend Production Build & Nginx:
```bash
cd frontend
npm install
npm run build

# Copy dist files to Nginx web root
sudo cp -r dist/* /var/www/ocr-document-system/
```

Configure Nginx reverse proxy block:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    root /var/www/ocr-document-system;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /ocr/ {
        proxy_pass http://127.0.0.1:8000/ocr/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 50M;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }
}
```

---

## 4. Vercel Cloud Deployment

The repository includes configuration for direct deployment to Vercel:
- **`vercel.json`** routes frontend assets and serverless Python API functions.
- **Frontend SPA**: Vite builds into static edge distribution.
- **Serverless API**: Handled through `/api/index.py`.

### Deploy Steps:
1. Import repository `TEKURU-ZENO/MedintelAI` into the Vercel dashboard.
2. In Project Settings, confirm Framework Preset is **Vite**.
3. Deploy.

---

## 5. Health Check & Validation

Run the automated acceptance suite to ensure the deployed environment meets latency and accuracy requirements:

```bash
python scripts/run_acceptance_tests.py
```

Expected output:
```
======================================================================
SUMMARY OF ACCEPTANCE BENCHMARKS
======================================================================
Test 1 (Resume PDF)         : PASS -> {'confidence': 0.8931, 'latency_sec': 7.62}
Test 2 (Printed Report)     : PASS -> {'confidence': 0.8285, 'latency_sec': 2.47}
Test 3 (Prescription)       : PASS -> {'confidence': 0.8470, 'latency_sec': 0.77}
Test 4 (Screen Snippet Crop): PASS -> {'confidence': 0.8970, 'latency_sec': 0.50}

Final Verdict: ALL 4 ACCEPTANCE TESTS PASSED
```
