# OCR Document Reading System — Technical Architecture

> **Version:** 2.0.0 | **Stack:** Python 3.10+ (FastAPI + RapidOCR + TrOCR + OpenCV) + React 19 (TypeScript + Vite + Tailwind CSS v4)

---

## 1. System Philosophy & Core Design Principles

The **OCR Document Reading System** is engineered to solve the real-world challenges of document ingestion, visual comprehension, and precision text extraction across both digital screen captures and physical scanned forms:

1. **Resolution-Preserving Preprocessing**: The OCR engine must never downscale documents to arbitrary low-resolution canvases (e.g. 800px) that destroy font antialiasing and produce fragmented, garbled characters. Original pixel resolution is preserved up to 4096px.
2. **Dual-Path Preprocessing**: Digital screen captures and scanned physical papers have fundamentally different noise profiles. Digital screen captures must never undergo destructive binarization (which shreds antialiased font edges); scanned physical papers require deskewing, noise filtering, and adaptive Gaussian thresholding.
3. **Spatial Line Grouping Before Recognition**: Rather than detecting tiny character/word fragments, running recognition, and trying to concatenate inaccurate strings, detection bounding boxes must be spatially clustered into coherent line candidates, cropped as full line images, and recognized as unified lines.
4. **Hybrid Recognition Routing**: High-throughput printed text is recognized with millisecond ONNX inference (RapidOCR), while complex cursive and handwriting are recognized with transformer attention (Microsoft TrOCR).
5. **Google Lens Visual Experience**: Extracted text is projected directly onto the visual document canvas with exact coordinate alignment (`normalized_bbox`), providing instant click-to-copy and interactive region marquee cropping.

---

## 2. End-to-End Pipeline Architecture

```
                    Arbitrary Input Document
       (Multi-page PDF, High-Res JPEG, PNG, TIFF, Screen Frame)
                               │
                               ▼
            Document Loader & Rasterizer (PyPDFium2)
           Renders PDF pages at 2.0x scale (e.g. 1191x1684)
                               │
                               ▼
                  Input Mode Classifier & Router
                               │
         ┌─────────────────────┴─────────────────────┐
         ▼                                           ▼
 [Screen / Digital Mode]                     [Scanned Paper Mode]
  • No binarization (RGB/Gray)                • Deskewing & rotation correction
  • Preserves sub-pixel antialiasing          • Bilateral noise filtering
  • Mild CLAHE (clipLimit=1.2)                • Morphological background normalization
  • Light bilateral denoise (d=3)             • Adaptive Gaussian thresholding
  • 2.5× bicubic upscale for crops
         │                                           │
         └─────────────────────┬─────────────────────┘
                               │
                               ▼
                   Text Region Detection
               (RapidOCR ONNX DBNet Detector)
                               │
                               ▼
                  Spatial Line Grouping Engine
           • Vertical overlap ratio ≥ 0.45
           • Horizontal proximity gap: -0.3h ≤ gap ≤ 2.2h
           • Merges adjacent micro-boxes into unified line crops
                               │
                               ▼
                 Region Classification & Routing
                               │
         ┌─────────────────────┴─────────────────────┐
         ▼                                           ▼
 [Printed Text Engine]                       [Handwritten Engine]
  RapidOCR Rec (ONNX)                         TrOCR VisionEncoderDecoder
  Fast, sub-millisecond inference             Deep transformer attention
         │                                           │
         └─────────────────────┬─────────────────────┘
                               │
                               ▼
                 Medical Vocabulary Normalizer
              • Dosage tokens (mg, ml, tabs, 1-0-1)
              • Clinical lexicon verification
                               │
                               ▼
              2D Reading-Order Geometric Rebuilder
          • Horizontal overlap banding
          • Column-aware topological sort
                               │
                               ▼
                     Structured OCR Payload
           • Global pixels: [xmin, ymin, xmax, ymax]
           • Normalized ratios: [x1/w, y1/h, x2/w, y2/h]
           • Confidence statuses & reading-order plain text
                               │
                               ▼
                 Google Lens Visual Studio Canvas
               • In-place text overlay (click-to-copy)
               • Marquee snippet selection (2.5x upscale)
               • Plain text (.txt) & JSON exports
```

---

## 3. Subsystem Breakdown

### 3.1 Preprocessing Subsystem (`app/ai/preprocessing/`)

- **`normalize.py`**:
  - `normalize_image(image, target_height=None, preserve_aspect=True)`: Preserves original document dimensions without artificial downscaling. Downscales with bicubic interpolation only if image dimensions exceed 4096px.
  - Eliminates hard global binarization (`cv2.threshold(..., 127, 255)`) that previously corrupted antialiased font edges.
- **`preprocessing_pipeline.py`**:
  - **`run_screen_preprocessing(image)`**: Designed specifically for screen captures and digital PDFs. Converts to grayscale, applies mild CLAHE (`clipLimit=1.2, tileGridSize=(8, 8)`), and light bilateral filtering (`d=3, sigmaColor=15, sigmaSpace=15`) while keeping the image in continuous grayscale.
  - **`run_scanned_preprocessing(image)`**: Designed for physical paper scans. Executes deskewing via Hough lines, bilateral noise reduction, and adaptive Gaussian thresholding (`cv2.adaptiveThreshold(..., ADAPTIVE_THRESH_GAUSSIAN_C)`).
  - **`run_preprocessing_pipeline(image, config, input_mode='auto')`**: Automatic router based on filename extensions and metadata.

### 3.2 Detection & Line Grouping Subsystem (`app/ai/ocr/ocr_engine.py`)

- **Text Detection**:
  - Employs RapidOCR ONNX DBNet to locate polygonal text boundaries across the high-resolution image.
- **Spatial Line Grouping (`group_and_merge_lines`)**:
  - Clustered lines using vertical overlap:
    $$\text{overlap\_ratio} = \frac{\min(y_{2,a}, y_{2,b}) - \max(y_{1,a}, y_{1,b})}{\min(h_a, h_b)} \ge 0.45$$
  - Adjacent horizontal bounding boxes are joined if their horizontal gap satisfies:
    $$-0.3 \times h \le \text{gap} \le 2.2 \times h$$
  - **Complete Line Crop Recognition (`_recognize_line_group`)**: Bounding boxes within a group are combined into a single unified bounding box, cropped from the original high-resolution image, and submitted as a full line to the recognizer.

### 3.3 Recognition & Model Subsystem

- **RapidOCR Recognizer**:
  - ONNX runtime model for printed Latin text, operating with sub-millisecond per-line latency.
- **TrOCR Handwriting Recognizer**:
  - Microsoft TrOCR (`microsoft/trocr-base-handwritten`) loaded via HuggingFace `VisionEncoderDecoderModel` and `TrOCRProcessor`.
  - Morphological stroke analysis dynamically routes high-variance, cursive regions to TrOCR.
- **Confidence Status Classification**:
  - `HIGH_CONFIDENCE` ($\ge 90\%$)
  - `REVIEW_REQUIRED` ($60\% \le \text{conf} < 90\%$)
  - `HUMAN_VERIFICATION_NEEDED` ($< 60\%$)

### 3.4 2D Reading-Order Geometric Rebuilder (`ReadingOrderRebuilder`)

- Rebuilds natural multi-column human reading flow:
  1. Identifies line bands based on vertical overlap.
  2. Sorts lines top-to-bottom.
  3. Within each band, sorts blocks left-to-right.
  4. Generates formatted plain text output (`raw_text`) with preserved indentation and linebreaks.

---

## 4. API & Controller Subsystem (`app/api/`, `app/ai/pipeline/`)

### 4.1 `PipelineController` (`app/ai/pipeline/pipeline_controller.py`)
- Accepts file paths, raw byte streams, or NumPy arrays.
- Renders multi-page PDFs using `pypdfium2` at high-resolution 2.0 scale.
- Executes `process_region` for focused marquee snippets, applying 2.5× bicubic upscale and translating local bounding boxes back to global image coordinates.

### 4.2 FastAPI Endpoints (`app/api/ocr.py`)
- **`POST /ocr/extract`**: Accepts arbitrary documents (PDF, PNG, JPG, TIFF, WEBP) and returns structured JSON with bounding boxes, confidence metrics, and raw text.
- **`POST /ocr/extract-region`**: Accepts focused snippet coordinates (`xmin`, `ymin`, `xmax`, `ymax`) for 2.5× resolution-preserving snippet extraction.
- **`POST /ocr/export/txt`**: Returns formatted plain text file attachment.
- **`POST /ocr/correct`**: Human clinician review correction endpoint.
- **`GET /health`**: System status endpoint.

---

## 5. Frontend Client Architecture (`frontend/`)

- **React 19 & Tailwind CSS v4**:
  - High-performance reactive UI with dark theme and typography.
- **Google Lens Overlay Canvas**:
  - Overlays recognition tags using CSS percentage styling (`left: normalized_bbox[0]*100%`, etc.), guaranteeing perfect spatial alignment at any viewport zoom level.
  - Interactive click-to-copy for recognized text blocks.
- **Marquee Snippet Crop Tool**:
  - Crosshair mouse selection allowing clinicians or users to draw a box around any snippet on screen or scanned records.
- **Live Screen / Window Capture**:
  - Leverages `navigator.mediaDevices.getDisplayMedia` to capture active hospital EHRs, browser tabs, or PDF viewers into a region-first snippet workflow.

---

## 6. Structured JSON Data Contract

Each recognized block adheres to the following JSON schema:

```json
{
  "id": "line_1",
  "text": "Dev Mehta",
  "confidence": 0.9482,
  "status": "HIGH_CONFIDENCE",
  "source": "printed",
  "model_used": "rapidocr-printed",
  "bbox": [58, 43, 224, 68],
  "normalized_bbox": [0.0487, 0.0255, 0.1881, 0.0404],
  "page": 1
}
```
