# MedIntel AI ? Medical Document OCR Production Deployment Guide

This guide covers deploying the **MedIntel AI Medical Document OCR System** on Vercel, Docker, or Cloud Virtual Machines (AWS, DigitalOcean, Azure, GCP).

---

## 1. Vercel Cloud Deployment

MedIntel AI includes pre-configured **`vercel.json`**, **`.python-version` (3.10)**, and **`api/index.py`** serverless entrypoint for instant deployment on Vercel.

### Vercel Setup Steps:
1. Connect your GitHub repository `TEKURU-ZENO/MedintelAI` on [Vercel.com](https://vercel.com).
2. Vercel automatically detects `vercel.json` and builds:
   - **Frontend React SPA**: Built with Vite and served statically at edge locations.
   - **Backend OCR Engine**: Deployed as Vercel Serverless Python Functions (`/api/index.py`).
3. Click **Deploy**.

---

## 2. Docker Compose Deployment (Recommended for Full Performance)

### Prerequisites
- Docker Desktop or Docker Engine + Docker Compose

### Commands
#### Linux / macOS:
```bash
chmod +x deploy.sh
./deploy.sh
```

#### Windows PowerShell:
```powershell
.\deploy.ps1
```

---

## 3. Cloud Server Deployment (AWS EC2 / DigitalOcean / Azure)

```bash
git clone https://github.com/TEKURU-ZENO/MedintelAI.git
cd MedintelAI
chmod +x deploy.sh
./deploy.sh
```
