# Setup & Installation Guide

This guide provides step-by-step instructions for engineers to set up the development environment, download the handwriting datasets, run the AI extraction pipeline, train the ML model, and run the complete application.

---

## 1. Prerequisites

Ensure you have the following installed on your machine:
* **Docker** (v24+) & **Docker Compose** (v2.x+)
* **Python** (v3.10+)
* **Node.js** (v20+) & **npm**

---

## 2. Project Installation

### Local Development Setup

#### Backend Setup
1. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up the environment file:
   * Create a `.env` file in the root directory:
     ```env
     DATABASE_URL=postgresql://akshar_user:akshar_password@localhost:5432/aksharabyasa
     SECRET_KEY=generate-a-secure-secret-key-here
     ENVIRONMENT=development
     ```

#### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install Node modules:
   ```bash
   npm install
   ```

---

## 3. Dataset Setup

The dataset image files are excluded from Git to keep the repository lightweight. To run batch feature extraction pipelines, download and place the datasets manually as described below.

### A. IAM Handwriting Database
1. Go to the [IAM Handwriting Database Download Page](https://fki.tic.heia-fr.ch/databases/download-the-iam-handwriting-database).
2. Register a free account (required by the host institution).
3. Download the **Words** dataset (`words.tgz`).
4. Extract the archive. Create a folder path matching `datasets/archive/iam_words/words` and place the extracted image folders (like `a01`, `a02`, etc.) inside it.
   
   **Expected Directory Structure:**
   ```text
   datasets/
   └── archive/
       └── iam_words/
           └── words/
               ├── a01/
               ├── a02/
               └── ... (other subfolders containing png images)
   ```

### B. CVL Database
1. Go to the [CVL Database Research Page](https://caa.tuwien.ac.at/cvl/research/cvl-database/).
2. Download CVL Database version 1.1 (`cvl-database-1-1.zip`).
3. Extract the archive. Place the `trainset` and `testset` directories under `datasets/cvl-database-1-1/cvl-database-1-1/`.
   
   **Expected Directory Structure:**
   ```text
   datasets/
   └── cvl-database-1-1/
       └── cvl-database-1-1/
           ├── trainset/
           ├── testset/
           └── readme.txt
   ```

---

## 4. Run the AI Pipeline & Train the Model

The pipeline extracts visual features (slant, spacing, baseline variation, stroke quality) from the raw datasets. These features are then used to train the XGBoost grade predictor model.

### Step 1: Run Feature Extraction Pipeline
To run the batch processor on a dataset, use `run_pipeline.py`. You can limit the number of processed files to test the integration.

* **Run on IAM Dataset:**
  ```bash
  python run_pipeline.py --dataset iam --limit 100 --output outputs/iam_features.json
  ```
* **Run on CVL Dataset:**
  ```bash
  python run_pipeline.py --dataset cvl --limit 100 --output outputs/cvl_features.json
  ```
* **Process a Custom Directory / Single Image:**
  ```bash
  python run_pipeline.py --dir /path/to/handwriting/images --output outputs/custom_features.json
  python run_pipeline.py --input /path/to/single_image.png --output outputs/single_feature.json
  ```

### Step 2: Build the Training CSV
Export database features to `dataset.csv`:
```bash
python scripts/build_dataset.py
```
*Note: If the local database is empty or has fewer than 10 logs, this script automatically bootstraps synthetic dataset records to allow offline model training.*

### Step 3: Train the ML Model
Train the XGBoost regressor model and dump the trained model weights to `model.pkl`:
```bash
python scripts/train_model.py
```
This updates the top-level `model.pkl` which the FastAPI backend uses to score student stroke logs in real-time.

---

## 5. Running the Application

### Option A: Using Docker Compose (Recommended)
This runs the PostgreSQL DB, FastAPI backend, and Nginx-proxied Vite frontend in orchestration.

1. Build and run all services:
   ```bash
   docker-compose up --build -d
   ```
2. Verify service health:
   ```bash
   docker-compose ps
   ```
3. Run the database seed script to generate demo/showcase telemetry data:
   ```bash
   docker-compose exec backend python app/scripts/seed_demo.py
   ```
4. Access the apps:
   * **Frontend Web App:** `http://localhost`
   * **FastAPI Swagger API Docs:** `http://localhost:8000/docs`

### Option B: Local Running (Individual Services)

#### 1. Backend Server
Make sure you have a local PostgreSQL server running and configured in `.env`, then run:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Frontend Development Server
```bash
cd frontend
npm run dev
# Starts Vite Server at http://localhost:5173
```

---

## 6. Running Tests

To verify that the ML services, curriculum engines, and analytics aggregates work correctly, run the Pytest suite:

```bash
python -m pytest tests/test_analytics_service.py tests/test_ml_recommendations.py tests/test_phase2_learning_engine.py tests/test_profile_service.py tests/test_stroke_analyzer.py -v
```
*Expected: All tests pass.*
