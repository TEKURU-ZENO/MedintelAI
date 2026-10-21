import io
import math
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, Union

import numpy as np
from PIL import Image, UnidentifiedImageError
from fastapi import HTTPException

from app.core.config import settings
from app.core.document_errors import DocumentProcessingError
from app.core.logging import logger
from app.core.validation import safe_filename
from app.schemas.document import (DocumentMetadata, DocumentPage, OCRProvenance,
                                 PageMetadata, ProcessedDocument, SourceType)
from app.services.crop_service import CropService


class DocumentProcessingService:
    """Normalize raster and PDF inputs into ordered page images plus source metadata.

    This layer decodes and renders documents only. It does not preprocess text or run OCR.
    Page arrays are OpenCV BGR images; page coordinates are rendered pixels, top-left origin.
    """
    def process(self, data: Union[str, bytes, bytearray, np.ndarray], filename: str,
                source_type: Optional[SourceType] = None, render_scale: Optional[float] = None) -> ProcessedDocument:
        name = safe_filename(filename)
        if isinstance(data, str):
            try:
                with open(data, "rb") as handle:
                    data = handle.read(settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024 + 1)
            except OSError as exc:
                raise DocumentProcessingError("DOCUMENT_NOT_FOUND", "Document source could not be read.", 404) from exc
        if not isinstance(data, np.ndarray) and len(data) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise DocumentProcessingError("DOCUMENT_TOO_LARGE", "Document exceeds the configured size limit.", 413)
        is_array = isinstance(data, np.ndarray)
        is_pdf = not is_array and (bytes(data).startswith(b"%PDF-") or name.lower().endswith(".pdf"))
        actual_source = source_type or (SourceType.PDF if is_pdf else SourceType.IMAGE)
        if actual_source == SourceType.PDF and not is_pdf:
            raise DocumentProcessingError("INVALID_PDF", "Source type is PDF but content is not a PDF.")
        if actual_source != SourceType.PDF and is_pdf:
            raise DocumentProcessingError("INVALID_SOURCE_TYPE", "PDF content requires source_type='pdf'.")
        if is_pdf:
            return self._process_pdf(bytes(data), name, actual_source, render_scale)
        if is_array:
            array = CropService.normalize_color(data)
            self._check_dimensions(array.shape[1], array.shape[0])
            page = self._image_page(array, 1, name, actual_source, None, None, None)
            return self._document(name, actual_source, 0, [page], {"original_format": "numpy.ndarray"})
        return self._process_raster(bytes(data), name, actual_source)

    def _check_dimensions(self, width: int, height: int):
        if width <= 0 or height <= 0:
            raise DocumentProcessingError("CORRUPTED_IMAGE", "Image has invalid dimensions.")
        if width > settings.MAX_IMAGE_DIMENSION or height > settings.MAX_IMAGE_DIMENSION or width * height > settings.MAX_IMAGE_PIXELS:
            raise DocumentProcessingError("IMAGE_TOO_LARGE", "Image dimensions exceed configured processing limits.", 413)

    def _process_raster(self, data: bytes, filename: str, source_type: SourceType) -> ProcessedDocument:
        total_pixels = 0
        pages = []
        source_metadata = {}
        try:
            with Image.open(io.BytesIO(data)) as image:
                image_format = image.format
                supported_formats = {"PNG": {".png"}, "JPEG": {".jpg", ".jpeg"},
                                     "WEBP": {".webp"}, "TIFF": {".tif", ".tiff"}, "BMP": {".bmp"}}
                if image_format not in supported_formats or os.path.splitext(filename)[1].lower() not in supported_formats[image_format]:
                    raise DocumentProcessingError("UNSUPPORTED_IMAGE", "Image format is unsupported or does not match its filename.", 415)
                frames = int(getattr(image, "n_frames", 1))
                if frames > settings.MAX_PDF_PAGES:
                    raise DocumentProcessingError("PAGE_LIMIT_EXCEEDED", "Raster document exceeds the configured page limit.", 413)
                dpi = image.info.get("dpi")
                exif_orientation = image.getexif().get(274)
                rotation_by_orientation = {1: 0, 3: 180, 6: 90, 8: 270}
                rotation = rotation_by_orientation.get(exif_orientation)
                source_metadata = {"format": image_format, "frame_count": frames,
                                   "animated": bool(getattr(image, "is_animated", False)),
                                   "exif_orientation": exif_orientation}
                for index in range(frames):
                    image.seek(index)
                    source_width, source_height = image.size
                    self._check_dimensions(source_width, source_height)
                    total_pixels += source_width * source_height
                    if total_pixels > settings.MAX_DOCUMENT_PROCESSING_PIXELS:
                        raise DocumentProcessingError("DOCUMENT_TOO_LARGE", "Decoded document exceeds the configured pixel budget.", 413)
                    mode = image.mode
                    rgb = image.convert("RGB")
                    import cv2
                    bgr = cv2.cvtColor(np.asarray(rgb), cv2.COLOR_RGB2BGR)
                    page = self._image_page(bgr, index + 1, filename, source_type,
                                            image_format, mode, dpi,
                                            source_width=source_width, source_height=source_height,
                                            rotation=rotation)
                    pages.append(page)
        except DocumentProcessingError:
            raise
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
            raise DocumentProcessingError("CORRUPTED_IMAGE", "Image could not be decoded safely.") from exc
        if not pages:
            raise DocumentProcessingError("CORRUPTED_IMAGE", "Image contains no processable pages.")
        return self._document(filename, source_type, len(data), pages, source_metadata)

    def _image_page(self, bgr, number, filename, source_type, image_format, color_mode, dpi,
                    source_width=None, source_height=None, scale_x=1.0, scale_y=1.0,
                    rotation=None, error=None):
        height, width = bgr.shape[:2] if bgr is not None else (0, 0)
        orientation = "landscape" if width > height else "portrait" if height > width else "square" if width else None
        metadata = PageMetadata(
            page_number=number, width=width, height=height,
            source_width=source_width if source_width is not None else width,
            source_height=source_height if source_height is not None else height,
            format=image_format, color_mode=color_mode, dpi_x=float(dpi[0]) if dpi else None,
            dpi_y=float(dpi[1]) if dpi else None, source_type=source_type,
            document_type="application/pdf" if source_type == SourceType.PDF else "image",
            render_scale_x=scale_x, render_scale_y=scale_y, rotation=rotation,
            orientation=orientation, status="failed" if error else "ready", error_code=error)
        return DocumentPage(metadata=metadata, image=bgr)

    def _process_pdf(self, data: bytes, filename: str, source_type: SourceType,
                     requested_scale: Optional[float] = None) -> ProcessedDocument:
        try:
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(data)
        except Exception as exc:
            message = str(exc).lower()
            encrypted_hint = b"/Encrypt" in data
            code = "ENCRYPTED_PDF" if encrypted_hint or any(word in message for word in ("password", "encrypt", "security")) else "INVALID_PDF"
            raise DocumentProcessingError(code, "PDF is encrypted or could not be opened safely.") from exc
        count = len(pdf)
        if count < 1:
            raise DocumentProcessingError("INVALID_PDF", "PDF does not contain any pages.")
        if count > settings.MAX_PDF_PAGES:
            raise DocumentProcessingError("PDF_PAGE_LIMIT", f"PDF exceeds the configured {settings.MAX_PDF_PAGES}-page limit.", 413)
        base_scale = requested_scale if requested_scale is not None else settings.PDF_RENDER_SCALE
        if base_scale <= 0:
            raise DocumentProcessingError("INVALID_RENDER_SCALE", "PDF render scale must be positive.")
        try:
            pdf_metadata = pdf.get_metadata_dict() or {}
        except Exception:
            pdf_metadata = {}
        pages, failed_pages, total_pixels = [], [], 0
        for index in range(count):
            page_number = index + 1
            source_width = source_height = None
            error_code = "PDF_PAGE_RENDER_FAILED"
            try:
                pdf_page = pdf.get_page(index)
                source_width, source_height = pdf_page.get_size()
                rotation = int(pdf_page.get_rotation()) * 90
                if source_width <= 0 or source_height <= 0:
                    raise ValueError("invalid source page size")
                scale = min(base_scale,
                            settings.MAX_RENDERED_PAGE_DIMENSION / max(source_width, source_height),
                            math.sqrt(settings.MAX_IMAGE_PIXELS / (source_width * source_height)))
                expected_pixels = source_width * source_height * scale * scale
                if scale <= 0 or total_pixels + expected_pixels > settings.MAX_DOCUMENT_PROCESSING_PIXELS:
                    raise OverflowError("document rendering pixel budget exceeded")
                bitmap = pdf_page.render(scale=scale)
                pil_image = bitmap.to_pil()
                import cv2
                rgb = np.asarray(pil_image.convert("RGB"))
                bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
                rendered_height, rendered_width = bgr.shape[:2]
                if max(rendered_width, rendered_height) > settings.MAX_RENDERED_PAGE_DIMENSION:
                    raise OverflowError("rendered page exceeds the configured dimension limit")
                if total_pixels + rendered_width * rendered_height > settings.MAX_DOCUMENT_PROCESSING_PIXELS:
                    raise OverflowError("document rendering pixel budget exceeded")
                self._check_dimensions(rendered_width, rendered_height)
                total_pixels += rendered_width * rendered_height
                dpi = scale * 72.0
                pages.append(self._image_page(bgr, page_number, filename, source_type, "PDF", "RGB",
                    (dpi, dpi), source_width=source_width, source_height=source_height,
                    scale_x=rendered_width / source_width, scale_y=rendered_height / source_height,
                    rotation=rotation))
            except DocumentProcessingError as exc:
                error_code = exc.code
                logger.warning("Could not normalize PDF page %s: %s", page_number, exc.message)
                failed_pages.append(page_number)
                pages.append(self._image_page(None, page_number, filename, source_type, "PDF", None, None,
                    source_width=source_width, source_height=source_height, error=error_code))
            except OverflowError:
                error_code = "PDF_RENDER_LIMIT_EXCEEDED"
                logger.warning("PDF page %s exceeded a render resource limit", page_number)
                failed_pages.append(page_number)
                pages.append(self._image_page(None, page_number, filename, source_type, "PDF", None, None,
                    source_width=source_width, source_height=source_height, error=error_code))
            except Exception as exc:
                logger.warning("Could not render PDF page %s", page_number, exc_info=True)
                failed_pages.append(page_number)
                pages.append(self._image_page(None, page_number, filename, source_type, "PDF", None, None,
                    source_width=source_width, source_height=source_height, error=error_code))
        try:
            pdf.close()
        except Exception:
            pass
        metadata = {key.lower(): value for key, value in pdf_metadata.items() if value is not None}
        metadata["original_format"] = "PDF"
        return self._document(filename, source_type, len(data), pages, metadata,
                              declared_page_count=count, failed_pages=failed_pages)

    def _document(self, filename, source_type, file_size, pages, source_metadata,
                  declared_page_count=None, failed_pages=None):
        failed_pages = failed_pages or [p.metadata.page_number for p in pages if p.metadata.status != "ready"]
        count = declared_page_count if declared_page_count is not None else len(pages)
        status = "failed" if failed_pages and len(failed_pages) == count else "partial" if failed_pages else "ready"
        document_id = uuid.uuid4()
        processed_at = datetime.now(timezone.utc)
        metadata = DocumentMetadata(document_id=document_id, filename=filename, source_type=source_type,
            document_type="application/pdf" if source_type == SourceType.PDF else "image",
            file_size=file_size, page_count=count, processed_at=processed_at,
            original_format=source_metadata.get("original_format", source_metadata.get("format")),
            status=status, failed_pages=failed_pages, source_metadata=source_metadata)
        provenance = [OCRProvenance(source_type=source_type, document_id=document_id,
            page_number=page.metadata.page_number, pipeline_version=settings.VERSION, processed_at=processed_at)
            for page in pages]
        return ProcessedDocument(metadata=metadata, pages=pages, provenance=provenance)
