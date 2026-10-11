"""MedIntel AI OCR Studio API. Requires Tesseract OCR installed on the host."""
from __future__ import annotations
import io, os, time, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import fitz
import pytesseract
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field

from sharing import router as sharing_router

APP_VERSION = "1.0.0"
MAX_UPLOAD_BYTES = int(os.getenv("MEDINTEL_MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))
ALLOWED_EXTS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
app = FastAPI(title="MedIntel AI OCR Studio API", version=APP_VERSION,
              description="Document OCR, region extraction, correction, export, benchmark, and expiring share links.")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("MEDINTEL_CORS_ORIGINS", "http://localhost:5173,app://medintel").split(","), allow_credentials=False, allow_methods=["GET", "POST", "DELETE", "OPTIONS"], allow_headers=["Content-Type", "X-Share-Revocation-Token"])
app.include_router(sharing_router)

class CorrectionRequest(BaseModel):
    text: str | None = Field(default=None, max_length=5_000_000)
    original_text: str | None = Field(default=None, max_length=5_000_000)
    corrected_text: str = Field(max_length=5_000_000)
    document: str | None = Field(default=None, max_length=255)

class ExportRequest(BaseModel):
    text: str = Field(max_length=5_000_000)
    filename: str = Field(default="medintel-export.txt", max_length=180)

class BenchmarkRequest(BaseModel):
    reference_text: str = Field(min_length=1, max_length=1_000_000)
    extracted_text: str = Field(min_length=1, max_length=1_000_000)

def _validate_file(upload: UploadFile, data: bytes) -> str:
    suffix = Path(upload.filename or "document").suffix.lower()
    if suffix not in ALLOWED_EXTS:
        raise HTTPException(415, f"Unsupported file type: {suffix or 'unknown'}")
    if not data:
        raise HTTPException(400, "Uploaded file is empty")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"File exceeds {MAX_UPLOAD_BYTES // (1024*1024)} MB limit")
    return suffix

def _preprocess(image: Image.Image, mode: str) -> Image.Image:
    image = ImageOps.exif_transpose(image).convert("RGB")
    if mode == "grayscale":
        image = ImageOps.grayscale(image).convert("RGB")
    elif mode == "high-contrast":
        gray = ImageOps.grayscale(image)
        image = ImageOps.autocontrast(gray).convert("RGB")
    elif mode not in {"auto", "balanced", "none"}:
        raise HTTPException(422, "preprocessing_mode must be auto, balanced, grayscale, high-contrast, or none")
    if mode in {"auto", "balanced", "high-contrast"} and max(image.size) < 1400:
        scale = min(2.0, 1400 / max(image.size))
        if scale > 1:
            image = image.resize((int(image.width*scale), int(image.height*scale)))
    return image

def _ocr_image(image: Image.Image, language: str, page_index: int, mode: str):
    image = _preprocess(image, mode)
    try:
        data = pytesseract.image_to_data(image, lang=language, output_type=pytesseract.Output.DICT, config="--psm 3")
    except pytesseract.TesseractNotFoundError as exc:
        raise HTTPException(503, "Tesseract OCR is not installed. Install Tesseract and add it to PATH.") from exc
    except pytesseract.TesseractError as exc:
        raise HTTPException(422, f"OCR engine error: {exc}") from exc
    blocks = []
    words_by_line = {}
    confidences = []
    width, height = image.size
    for i, raw in enumerate(data.get("text", [])):
        word = str(raw).strip()
        try: conf = float(data["conf"][i])
        except (ValueError, TypeError, KeyError): conf = -1
        if not word or conf < 0: continue
        x, y, w, h = (int(data[k][i]) for k in ("left", "top", "width", "height"))
        line_key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        words_by_line.setdefault(line_key, []).append(word)
        confidences.append(conf)
        blocks.append({"text": word, "confidence": round(conf, 2), "bbox": {"x": round(x/width, 6), "y": round(y/height, 6), "width": round(w/width, 6), "height": round(h/height, 6)}, "pixel_bbox": {"x": x, "y": y, "width": w, "height": h}, "page_index": page_index, "block_index": len(blocks), "kind": "printed"})
    lines = [" ".join(words) for words in words_by_line.values()]
    return {"text": "\n".join(lines), "blocks": blocks, "confidence": round(sum(confidences)/len(confidences), 2) if confidences else None, "width": width, "height": height}

def _run_ocr(data: bytes, suffix: str, language: str, mode: str):
    if not language.replace("+", "").replace("_", "").isalnum():
        raise HTTPException(422, "Invalid OCR language code")
    pages = []
    started = time.perf_counter()
    try:
        if suffix == ".pdf":
            try: doc = fitz.open(stream=data, filetype="pdf")
            except Exception as exc: raise HTTPException(422, "The PDF could not be opened") from exc
            if doc.page_count > 100: raise HTTPException(413, "PDF exceeds 100-page limit")
            for page_idx, page in enumerate(doc):
                pix = page.get_pixmap(matrix=fitz.Matrix(1.8, 1.8), alpha=False)
                image = Image.open(io.BytesIO(pix.tobytes("png")))
                result = _ocr_image(image, language, page_idx, mode)
                pages.append({"page_index": page_idx, **result})
            doc.close()
        else:
            try: image = Image.open(io.BytesIO(data)); image.verify(); image = Image.open(io.BytesIO(data))
            except (UnidentifiedImageError, OSError) as exc: raise HTTPException(422, "Image file is invalid or unreadable") from exc
            if getattr(image, "n_frames", 1) > 100: raise HTTPException(413, "Image contains too many frames")
            if getattr(image, "n_frames", 1) > 1:
                for page_idx in range(image.n_frames):
                    image.seek(page_idx); pages.append({"page_index": page_idx, **_ocr_image(image.copy(), language, page_idx, mode)})
            else: pages.append({"page_index": 0, **_ocr_image(image, language, 0, mode)})
    except HTTPException: raise
    except Exception as exc: raise HTTPException(422, f"Document processing failed: {type(exc).__name__}") from exc
    blocks = [block for page in pages for block in page["blocks"]]
    text = "\n\n".join(page["text"] for page in pages if page["text"])
    confidences = [b["confidence"] for b in blocks]
    return {"text": text, "confidence": round(sum(confidences)/len(confidences), 2) if confidences else None,
            "blocks": blocks, "pages": [{"page_index": p["page_index"], "width": p["width"], "height": p["height"], "text": p["text"]} for p in pages],
            "page_count": len(pages), "source": "Tesseract OCR", "model": f"Tesseract {pytesseract.get_tesseract_version()}",
            "language": language, "preprocessing_mode": mode, "duration_ms": round((time.perf_counter()-started)*1000),
            "processed_at": datetime.now(timezone.utc).isoformat(), "request_id": str(uuid.uuid4()), "confidence_semantics": "Mean word-level Tesseract confidence; not a clinical correctness probability."}

@app.get("/health")
def health():
    try: version = str(pytesseract.get_tesseract_version())
    except Exception: version = None
    return {"status": "ok", "version": APP_VERSION, "ocr_engine_available": version is not None, "ocr_engine_version": version}

@app.post("/ocr/extract")
async def extract(file: UploadFile = File(...), preprocessing_mode: str = Form("balanced"), language: str = Form("eng")):
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    suffix = _validate_file(file, data)
    return _run_ocr(data, suffix, language, preprocessing_mode)

@app.post("/ocr/extract-region")
async def extract_region(file: UploadFile = File(...), x: float = Form(...), y: float = Form(...), width: float = Form(...), height: float = Form(...), language: str = Form("eng"), preprocessing_mode: str = Form("balanced"), coordinate_mode: Literal["normalized", "pixel"] = Form("normalized")):
    data = await file.read(MAX_UPLOAD_BYTES + 1); suffix = _validate_file(file, data)
    if suffix == ".pdf": raise HTTPException(422, "Region OCR currently expects a cropped image, not a PDF")
    try: image = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception as exc: raise HTTPException(422, "Invalid region image") from exc
    if coordinate_mode == "pixel":
        if min(x, y, width, height) < 0 or width <= 0 or height <= 0 or x+width > image.width or y+height > image.height:
            raise HTTPException(422, "Pixel region coordinates must stay within the image")
        left, top, right, bottom = int(x), int(y), int(x+width), int(y+height)
        x, y, width, height = left/image.width, top/image.height, (right-left)/image.width, (bottom-top)/image.height
    else:
        if min(x, y, width, height) < 0 or width <= 0 or height <= 0 or x+width > 1 or y+height > 1: raise HTTPException(422, "Region coordinates must be normalized to 0..1 and stay within the image")
        left, top = int(x*image.width), int(y*image.height); right, bottom = int((x+width)*image.width), int((y+height)*image.height)
    crop_w, crop_h = right-left, bottom-top
    result = _ocr_image(image.crop((left, top, right, bottom)), language, 0, preprocessing_mode)
    # Map region-local normalized boxes back into full source-image coordinates for overlays.
    for block in result["blocks"]:
        box = block["bbox"]
        box["x"] = round(x + box["x"] * width, 6)
        box["y"] = round(y + box["y"] * height, 6)
        box["width"] = round(box["width"] * width, 6)
        box["height"] = round(box["height"] * height, 6)
        px = block["pixel_bbox"]
        px["x"] += left; px["y"] += top
    return {**result, "source": "Tesseract OCR region", "model": f"Tesseract {pytesseract.get_tesseract_version()}", "region": {"x": x, "y": y, "width": width, "height": height}, "processed_at": datetime.now(timezone.utc).isoformat()}

@app.post("/ocr/correct")
def correct(payload: CorrectionRequest):
    original = payload.original_text if payload.original_text is not None else (payload.text or "")
    return {"text": payload.corrected_text, "corrected_text": payload.corrected_text, "changed": original != payload.corrected_text, "corrected_at": datetime.now(timezone.utc).isoformat(), "note": "Correction is user-supplied; no clinical fact checking is performed."}

@app.post("/ocr/export/txt", response_class=PlainTextResponse)
def export_txt(payload: ExportRequest):
    filename = Path(payload.filename).name.replace('"', "") or "medintel-extract.txt"
    if not filename.lower().endswith(".txt"): filename += ".txt"
    return PlainTextResponse(payload.text, headers={"Content-Disposition": f'attachment; filename="{filename}"'})

@app.post("/ocr/benchmark")
def benchmark(payload: BenchmarkRequest):
    import re
    norm = lambda s: re.sub(r"\s+", " ", s.casefold()).strip()
    ref, hyp = norm(payload.reference_text), norm(payload.extracted_text)
    a, b = ref.split(), hyp.split(); prev = list(range(len(b)+1))
    for i, wa in enumerate(a, 1):
        cur = [i]
        for j, wb in enumerate(b, 1): cur.append(min(cur[-1]+1, prev[j]+1, prev[j-1]+(wa != wb)))
        prev = cur
    errors = prev[-1]
    return {"word_error_rate": errors/max(1, len(a)), "reference_word_count": len(a), "extracted_word_count": len(b), "edit_distance": errors, "note": "WER is an approximate token-level comparison after whitespace normalization."}
