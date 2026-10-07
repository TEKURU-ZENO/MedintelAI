# OCR Document Reading System — Deployment & Operations Guide

> **Audience:** DevOps Engineers, System Administrators, and Cloud Architects

---

## 1. Production Topology

```
                  Internet / Client Requests
                              │
                              ▼
                       Nginx / Traefik
               (SSL Termination, Rate Limiting)
                              │
               ┌──────────────┴──────────────┐
               ▼                             ▼
       Static Web Assets             FastAPI ASGI Service
     (React 19 / Port 80)           (Uvicorn / Port 8000)
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       ▼                                           ▼
             RapidOCR ONNX Runtime                       TrOCR Transformer Runtime
            (Multi-threaded CPU/GPU)                     (PyTorch / CUDA Inference)
```

---

## 2. Environment Variables Specification

Configure the following variables in `/etc/ocr-system.env` or `.env`:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `production` | Deployment mode (`development`, `staging`, `production`) |
| `PORT` | `8000` | Backend API port |
| `HOST` | `0.0.0.0` | Binding interface |
| `TROCR_MODEL_NAME` | `microsoft/trocr-base-handwritten` | HuggingFace model identifier or local directory |
| `DEBUG_OCR` | `false` | When `true`, saves annotated debug crops to `outputs/debug/` |
| `MAX_UPLOAD_SIZE_MB` | `50` | Maximum file size for multi-page PDFs |
| `CORS_ORIGINS` | `*` | Allowed client origins (comma-separated) |

---

## 3. Docker Compose Production Deployment

### `docker-compose.yml`
```yaml
version: '3.8'

services:
  ocr-backend:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: ocr_document_backend
    restart: always
    environment:
      - ENVIRONMENT=production
      - PORT=8000
      - OMP_NUM_THREADS=4
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    volumes:
      - temp_data:/tmp/ocr_document_temp

  ocr-frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: ocr_document_frontend
    restart: always
    ports:
      - "80:80"
    depends_on:
      - ocr-backend

volumes:
  temp_data:
```

### Deployment Commands:
```bash
docker compose up -d --build
docker compose ps
docker compose logs -f ocr-backend
```

---

## 4. Bare-Metal Linux Service (Systemd)

Create systemd service `/etc/systemd/system/ocr-system.service`:

```ini
[Unit]
Description=OCR Document Reading System Backend Service
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/ocr-document-system
EnvironmentFile=/opt/ocr-document-system/.env
ExecStart=/opt/ocr-document-system/venv/bin/gunicorn \
    -w 4 \
    -k uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    app.main:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ocr-system
sudo systemctl start ocr-system
sudo systemctl status ocr-system
```

---

## 5. Nginx Reverse Proxy Configuration

```nginx
server {
    listen 80;
    server_name ocr.yourdomain.com;

    client_max_body_size 50M;

    location / {
        root /var/www/ocr-document-system;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    location /ocr/ {
        proxy_pass http://127.0.0.1:8000/ocr/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 180s;
        proxy_connect_timeout 60s;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }
}
```

---

## 6. Performance Tuning & Scaling Guidelines

1. **ONNX Runtime Concurrency**:
   Set `OMP_NUM_THREADS` and `ONNX_NUM_THREADS` equal to the number of physical CPU cores (e.g. 4 or 8) to optimize RapidOCR DBNet inference without CPU context switching overhead.
2. **GPU Acceleration**:
   If an NVIDIA GPU is available, install `onnxruntime-gpu` and ensure PyTorch detects CUDA (`torch.cuda.is_available() == True`). TrOCR will automatically execute on the GPU, lowering line inference latency from ~150ms to ~15ms.
3. **Multi-Page PDF Processing**:
   Large PDFs (10+ pages) are rasterized page-by-page via `pypdfium2` generator iteration, ensuring RAM usage remains bounded regardless of document length.
