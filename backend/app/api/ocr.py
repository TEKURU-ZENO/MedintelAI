import base64
import binascii
import json
import os
import tempfile
from typing import Literal, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import ValidationError

from app.ai.ocr.medical_postprocessor import MedicalVocabularyPostProcessor
from app.core.config import settings
from app.core.document_errors import DocumentProcessingError
from app.core.logging import logger
from app.core.validation import safe_filename, validate_upload
from app.schemas.ocr import (BenchmarkReportResponse, BenchmarkRequest, BenchmarkResponse,
                             CorrectionRequest, CorrectionResponse, OCRResponse,
                             TextExportRequest, ErrorResponse, RegionRequest)
from app.schemas.document import PreprocessingMode, SourceType
from app.services.benchmark_service import BenchmarkService
from app.services.ocr_service import OCRService

router = APIRouter()
ocr_service = OCRService()
benchmark_service = BenchmarkService(ocr_service)
correction_engine = MedicalVocabularyPostProcessor()
TEMP_BASE = os.path.join(tempfile.gettempdir(), "medintel_temp")
CORRECTIONS_FILE = os.path.join(TEMP_BASE, "corrections.json")


@router.post("/extract", response_model=OCRResponse, summary="Extract text from an uploaded image or PDF",
             description="Accepts PNG, JPEG, WEBP, TIFF, BMP, or PDF. Raster and PDF pages are normalized in order and the response includes rendered/source dimensions, page metadata, and OCR provenance. Coordinates use a top-left origin with x rightward and y downward. Optionally provide source_type=screen_capture; file type alone never implies a screen capture.",
             responses={400: {"model": ErrorResponse}, 413: {"model": ErrorResponse}, 415: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}})
async def extract_ocr(file: UploadFile = File(..., description="Supported PNG, JPEG, WEBP, TIFF or PDF document"), input_mode: Optional[Literal["auto", "screen", "digital", "scanned_paper"]] = Form(None), source_type: Optional[SourceType] = Form(None, description="Explicitly set to screen_capture for a client-provided screen capture"), preprocessing_mode: Optional[PreprocessingMode] = Form(None)):
    contents, filename = await validate_upload(file)
    return ocr_service.extract(contents, filename, input_mode, source_type, preprocessing_mode)


@router.post("/extract-region", response_model=OCRResponse, summary="Extract text from a selected region",
             description="The crop is in rendered pixel coordinates on the first page, origin at top-left, x rightward and y downward. Use x/y/width/height or legacy xmin/ymin/xmax/ymax. Regions are bounds-checked and never clipped. The response includes page dimensions and provenance.",
             responses={400: {"model": ErrorResponse, "description": "Invalid or out-of-bounds region"}, 413: {"model": ErrorResponse, "description": "Upload too large"}, 415: {"model": ErrorResponse, "description": "Unsupported media type"}, 422: {"model": ErrorResponse}})
async def extract_region_ocr(
    file: UploadFile = File(...),
    x: Optional[int] = Form(None), y: Optional[int] = Form(None),
    width: Optional[int] = Form(None), height: Optional[int] = Form(None),
    xmin: Optional[int] = Form(None), ymin: Optional[int] = Form(None),
    xmax: Optional[int] = Form(None), ymax: Optional[int] = Form(None),
    input_mode: Optional[Literal["auto", "screen", "digital", "scanned_paper"]] = Form(None),
    source_type: Optional[SourceType] = Form(None),
    preprocessing_mode: Optional[PreprocessingMode] = Form(None),
):
    if None not in (x, y, width, height):
        box = [x, y, width, height]
    elif None not in (xmin, ymin, xmax, ymax):
        box = [xmin, ymin, xmax - xmin, ymax - ymin]
    else:
        raise HTTPException(422, "Provide x, y, width, height or xmin, ymin, xmax, ymax.")
    try:
        region = RegionRequest(x=box[0], y=box[1], width=box[2], height=box[3])
    except ValidationError as exc:
        raise DocumentProcessingError("INVALID_CROP", "Region coordinates must be non-negative with positive width and height.") from exc
    contents, filename = await validate_upload(file)
    return ocr_service.extract_region(contents, filename, [region.x, region.y, region.width, region.height], input_mode, source_type, preprocessing_mode)


@router.post("/export/txt", summary="Download OCR text as a UTF-8 text file",
             description="Accepts extracted text and returns it as a downloadable .txt attachment.",
             response_class=Response, responses={200: {"content": {"text/plain": {"schema": {"type": "string"}}}}})
async def export_txt(request: TextExportRequest):
    raw_name = safe_filename(request.filename)
    base_name = os.path.splitext(raw_name)[0] or "ocr-result"
    filename = f"{base_name}.txt"
    disposition_name = filename.replace('"', "")
    return Response(content=request.text.encode("utf-8"), media_type="text/plain; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{disposition_name}"'})


@router.post("/correct", response_model=CorrectionResponse, summary="Correct OCR text or record a clinician edit",
             description="Applies the existing deterministic medical vocabulary correction rules to text, or records a clinician block correction for the OCR studio.")
async def correct_text(request: CorrectionRequest):
    if request.text is not None:
        original = request.text.strip()
        corrected = correction_engine.clean_text(original)
        return CorrectionResponse(original_text=original, corrected_text=corrected,
                                  correction_applied=corrected != original, message="Rule-based medical text normalization completed.")

    original = request.original_text or ""
    corrected = request.corrected_text or ""
    entry = {"document": safe_filename(request.document), "block_id": request.block_id or "",
             "original_text": original, "corrected_text": corrected,
             "clinician_notes": request.clinician_notes, "status": "CORRECTED"}
    try:
        os.makedirs(TEMP_BASE, exist_ok=True)
        entries = []
        if os.path.exists(CORRECTIONS_FILE):
            try:
                with open(CORRECTIONS_FILE, "r", encoding="utf-8") as handle:
                    loaded = json.load(handle)
                    entries = loaded if isinstance(loaded, list) else []
            except (OSError, json.JSONDecodeError):
                logger.warning("Could not read previous clinician corrections")
        entries.append(entry)
        with open(CORRECTIONS_FILE, "w", encoding="utf-8") as handle:
            json.dump(entries, handle, indent=2, ensure_ascii=False)
    except Exception as exc:
        logger.exception("Could not persist clinician correction")
        raise HTTPException(503, "Clinician correction could not be recorded.") from exc
    return CorrectionResponse(original_text=original, corrected_text=corrected, correction_applied=True,
                              message="Clinician correction recorded.", entry=entry)


@router.post("/benchmark", response_model=BenchmarkResponse, summary="Benchmark OCR on a bounded set of images",
             description="Processes 1 to 10 base64-encoded image samples. Accuracy metrics are returned only when ground truth is supplied.")
async def run_benchmark(request: BenchmarkRequest):
    samples = []
    total_bytes = 0
    for sample in request.samples:
        try:
            data = base64.b64decode(sample.image_base64, validate=True)
        except (binascii.Error, ValueError):
            raise HTTPException(400, "Benchmark image_base64 must contain valid base64 data.")
        total_bytes += len(data)
        if total_bytes > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise HTTPException(413, "Combined benchmark image data exceeds the configured upload limit.")
        filename = safe_filename(sample.filename)
        ext = os.path.splitext(filename)[1].lower()
        if ext not in {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"}:
            raise HTTPException(415, "Benchmark samples must use a supported image filename extension.")
        # Reuse the same content decoder validation used for regular uploads.
        import cv2
        import numpy as np
        if not data or cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR) is None:
            raise HTTPException(400, "Benchmark sample contains invalid image data.")
        samples.append({"data": data, "filename": filename, "ground_truth": sample.ground_truth})
    return benchmark_service.run(samples)


@router.get("/benchmark", response_model=BenchmarkReportResponse, summary="Read previously measured OCR benchmark report",
            description="Returns only metrics from a benchmark report generated by the repository benchmark tools. Does not run OCR.")
async def get_benchmark_report():
    for path in ("outputs/benchmark_results.json", os.path.join(TEMP_BASE, "benchmark_results.json")):
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                metrics = data.get("metrics", {}) if isinstance(data, dict) else {}
                return {"status": "success", "system": data.get("system", "OCR Document Reading System Engine"), "metrics": metrics}
            except (OSError, json.JSONDecodeError, AttributeError):
                logger.exception("Could not load OCR benchmark report")
                raise HTTPException(500, "Stored benchmark report is unreadable.")
    return {"status": "unavailable", "system": "OCR Document Reading System Engine", "metrics": {}}
