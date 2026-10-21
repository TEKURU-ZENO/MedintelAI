import time
from typing import Any, Dict, List

from fastapi import HTTPException

from app.ai.pipeline.pipeline_controller import PipelineController
from app.core.document_errors import DocumentProcessingError
from app.core.logging import logger
from app.schemas.document import PreprocessingMode, SourceType


class OCRService:
    def __init__(self, controller: PipelineController | None = None):
        self.controller = controller or PipelineController()

    def extract(self, data: bytes, filename: str, input_mode: str | None = None,
                source_type: SourceType | None = None,
                preprocessing_mode: PreprocessingMode | None = None) -> Dict[str, Any]:
        mode = input_mode or ("screen" if filename.lower().startswith("screen_capture_") or filename.lower().endswith(".pdf") else "auto")
        start = time.perf_counter()
        try:
            result = self.controller.process_document(
                data, doc_name=filename, input_mode=mode, source_type=source_type,
                preprocessing_mode=preprocessing_mode.value if preprocessing_mode else None
            )
        except DocumentProcessingError:
            raise
        except Exception as exc:
            logger.exception("OCR processing failed")
            raise HTTPException(503, "OCR processing is currently unavailable.") from exc
        if not result or result.get("status") != "success":
            logger.error("OCR returned a failure status: %s", result.get("message") if isinstance(result, dict) else "invalid result")
            raise HTTPException(503, "OCR could not process this document.")
        elapsed = time.perf_counter() - start
        confidence = float(result.get("overall_confidence", 0.0) or 0.0)
        result.update({"success": True, "confidence": confidence, "processing_time": round(elapsed, 6),
                       "metadata": {"file_type": filename.rsplit(".", 1)[-1].lower(), "page_count": result.get("pages", 0)}})
        return result

    def extract_region(self, data: bytes, filename: str, box: List[int], input_mode: str | None = None,
                       source_type: SourceType | None = None,
                       preprocessing_mode: PreprocessingMode | None = None) -> Dict[str, Any]:
        try:
            x, y, region_width, region_height = box
            start = time.perf_counter()
            result = self.controller.process_region(
                data, [x, y, x + region_width, y + region_height], doc_name=filename,
                input_mode=input_mode or "screen", source_type=source_type,
                preprocessing_mode=preprocessing_mode.value if preprocessing_mode else None
            )
        except DocumentProcessingError:
            raise
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Region OCR processing failed")
            raise HTTPException(503, "OCR region processing is currently unavailable.") from exc
        if result.get("status") != "success":
            raise HTTPException(400, result.get("message", "Selected region could not be processed."))
        confidence = float(result.get("overall_confidence", 0.0) or 0.0)
        result.update({"success": True, "confidence": confidence, "processing_time": round(time.perf_counter() - start, 6),
                       "metadata": {"file_type": filename.rsplit(".", 1)[-1].lower(), "page_count": result.get("pages", 1)}})
        return result
