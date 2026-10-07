# OCR Document Reading System — AI/ML Codebase Map

> **Scope:** Comprehensive architectural reference for all AI, computer vision, OCR, and geometric algorithms.

---

## 1. Directory Structure

```
app/ai/
├── ocr/
│   └── ocr_engine.py             # Hybrid engine, line grouping & recognition router
├── pipeline/
│   └── pipeline_controller.py    # Multi-page orchestration, region crops & persistence
├── preprocessing/
│   ├── normalize.py              # Resolution preservation (up to 4096px)
│   ├── deskew.py                 # Hough-transform angle detection & affine rotation
│   ├── denoise.py                # Bilateral filter & edge-preserving smoothing
│   ├── binarize.py               # Otsu & adaptive Gaussian thresholding
│   ├── clahe.py                  # Contrast-limited adaptive histogram equalization
│   └── preprocessing_pipeline.py # Dual-path screen vs scanned preprocessing
└── utils/
    ├── pdf_handler.py            # High-res PyPDFium2 document loader
    └── logger.py                 # Structured pipeline logger
```

---

## 2. Module Specifications

### 2.1 Preprocessing Pipeline (`app/ai/preprocessing/`)

#### `normalize.py`
- **`normalize_image(image: np.ndarray, target_height: int = None, preserve_aspect: bool = True) -> np.ndarray`**
  - Preserves original input resolution up to 4096px.
  - Downscales only if $\max(w, h) > 4096\text{px}$ using `cv2.INTER_AREA`.
  - Removed old destructive downscaling ($800\text{px}$) and hard thresholding ($127$) to protect antialiased fonts.

#### `preprocessing_pipeline.py`
- **`run_screen_preprocessing(image: np.ndarray) -> np.ndarray`**
  - Purpose: Preprocessing for digital screen captures, PDFs, and UI snippets.
  - Converts RGB to grayscale.
  - Applies mild CLAHE (`clipLimit=1.2, tileGridSize=(8, 8)`) to enhance contrast without introducing thresholding artifacts.
  - Applies light bilateral filter (`d=3, sigmaColor=15, sigmaSpace=15`) to suppress compression noise while maintaining crisp font edges.
  - **Does NOT binarize.**
- **`run_scanned_preprocessing(image: np.ndarray) -> np.ndarray`**
  - Purpose: Preprocessing for physical paper scans, hospital records, and faxes.
  - Executes deskewing (`deskew.py`).
  - Applies bilateral noise reduction (`denoise.py`).
  - Applies adaptive Gaussian thresholding (`binarize.py`) to eliminate uneven lighting and shadows.
- **`run_preprocessing_pipeline(image, config, input_mode='auto') -> np.ndarray`**
  - Master entrypoint routing between screen and scanned pipelines based on document metadata.

---

### 2.2 OCR Engine & Spatial Line Grouping (`app/ai/ocr/ocr_engine.py`)

#### `OCRDocumentReadingEngine` (alias: `MedIntelOCREngine`)
Primary inference class managing models and line grouping:

- **`_init_models()`**:
  - Initializes RapidOCR ONNX runtime for detection and printed recognition.
  - Initializes HuggingFace TrOCR (`VisionEncoderDecoderModel`, `TrOCRProcessor`) on GPU or CPU.

- **`group_and_merge_lines(items: List[Dict], image: np.ndarray) -> List[Dict]`**:
  - Eliminates micro-fragmentation by clustering adjacent detection boxes into complete line crops.
  - Filters out detection noise (confidence $< 0.40$ with length $\le 2$).
  - Baseline clustering based on vertical overlap:
    $$\text{overlap} = \max(0, \min(y_{2,a}, y_{2,b}) - \max(y_{1,a}, y_{1,b})) \ge 0.45 \times \min(h_a, h_b)$$
  - Proximity grouping: joins adjacent boxes if horizontal gap is within $-0.3h \le \text{gap} \le 2.2h$.

- **`_recognize_line_group(group: List[Dict], image: np.ndarray) -> Dict`**:
  - Merges bounding boxes into a unified bounding box $[x_1, y_1, x_2, y_2]$ with 3px safety padding.
  - Crops the full line from the high-resolution image.
  - Classifies crop morphology using `RegionClassifier`.
  - Executes `self._rapid_ocr.text_recognizer` (printed) or `self._trocr_recognize` (handwritten).
  - Normalizes text via `MedicalVocabularyPostProcessor`.
  - Calculates `normalized_bbox = [x1/w, y1/h, x2/w, y2/h]` for frontend alignment.

- **`process_region(image, region_bbox, doc_name, input_mode='screen') -> Dict`**:
  - Crops focused snippet defined by user marquee selection.
  - If snippet height $< 250\text{px}$, applies 2.5× bicubic upscale (`cv2.INTER_CUBIC`).
  - Runs screen preprocessing and line recognition.
  - Re-scales and offsets coordinates back to global document coordinates.

#### `RegionClassifier`
- Evaluates stroke variance and edge density using Sobel filters to distinguish between uniform printed fonts and high-entropy handwriting.

#### `ReadingOrderRebuilder`
- Sorts recognized line blocks into standard 2D human reading order using horizontal overlap banding and left-to-right sorting. Assembles formatted `raw_text`.

#### `MedicalVocabularyPostProcessor`
- Cleans clinical dosage units (`mg`, `ml`, `mcg`, `tabs`, `1-0-1`) and normalizes common clinical abbreviations.

---

### 2.3 Controller & Utilities (`app/ai/pipeline/`, `app/ai/utils/`)

#### `PipelineController` (`pipeline_controller.py`)
- Manages multi-page document loops, persists JSON and `.txt` artifacts, and bridges FastAPI to `OCRDocumentReadingEngine`.

#### `pdf_handler.py`
- Uses `pypdfium2` to render PDF pages into NumPy BGR images at high-resolution 2.0 scale ($1191 \times 1684\text{px}$).
