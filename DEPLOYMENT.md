# MedIntel AI ? Medical Document OCR Production Deployment Guide

This guide covers deploying the **MedIntel AI Medical Document OCR System** locally via Docker, or to cloud providers (AWS, DigitalOcean, Azure, GCP).

---

## 1. Quick Start via Docker Compose (Recommended)

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/macOS) or Docker Engine + Docker Compose (Linux)
- Git

### Deployment Commands

#### Linux / macOS:
```bash
chmod +x deploy.sh
./deploy.sh
```

#### Windows PowerShell:
```powershell
.\deploy.ps1
```

#### Manual Docker Compose:
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Access Ports & Endpoints
- **Frontend Dual-Pane OCR Studio**: [http://localhost](http://localhost) (Port 80)
- **FastAPI Backend Service**: [http://localhost:8000](http://localhost:8000) (Port 8000)
- **Interactive OpenAPI Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check Endpoint**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 2. Cloud Server Deployment (AWS EC2 / DigitalOcean / Azure)

### Step 1: Provision Server Instance
- **Instance Size**: 2 vCPU, 4GB RAM minimum (8GB recommended for heavy PaddleOCR / TrOCR inference).
- **OS**: Ubuntu 22.04 LTS.

### Step 2: Install Docker & Git
```bash
sudo apt update && sudo apt install -y docker.io docker-compose git
sudo systemctl enable --now docker
```

### Step 3: Clone Repository & Deploy
```bash
git clone <repository-url> medintel-ocr
cd medintel-ocr
chmod +x deploy.sh
./deploy.sh
```

---

## 3. Direct System Deployment (Without Docker)

### Backend Service:
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Launch FastAPI backend with Uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Frontend Static Build:
```bash
cd frontend
npm install
npm run build
# Serve static build folder via Nginx or static host
```

---

## 4. Environment Configuration Options

Edit `config/preprocessing.yaml` or set environment variables:
- `ENVIRONMENT`: Set to `production` or `development`.
- `PORT`: Default `8000`.
- Persistent document storage is mapped to `./outputs/` inside the container.
