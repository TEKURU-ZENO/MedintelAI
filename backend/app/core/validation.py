import os
import re
from pathlib import PurePath

import io
from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.core.document_errors import DocumentProcessingError

IMAGE_TYPES = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".webp": "image/webp", ".bmp": "image/bmp", ".tif": "image/tiff",
    ".tiff": "image/tiff", ".pdf": "application/pdf",
}


def safe_filename(filename: str | None) -> str:
    name = PurePath((filename or "").replace("\\", "/")).name
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name).strip("._")
    if not name or name in {".", ".."}:
        raise HTTPException(400, "A valid filename is required.")
    return name[:180]


async def validate_upload(file: UploadFile) -> tuple[bytes, str]:
    if not file or not file.filename:
        raise HTTPException(400, "A file and filename are required.")
    name = safe_filename(file.filename)
    ext = os.path.splitext(name)[1].lower()
    expected_type = IMAGE_TYPES.get(ext)
    if expected_type is None:
        raise HTTPException(415, "Unsupported file extension.")
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    allowed_types = set(settings.SUPPORTED_IMAGE_TYPES) | set(settings.SUPPORTED_DOCUMENT_TYPES)
    if expected_type not in allowed_types or content_type not in allowed_types or content_type != expected_type:
        raise HTTPException(415, "File extension and media type must match a supported format.")
    limit = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    chunks = bytearray()
    while True:
        chunk = await file.read(min(1024 * 1024, limit + 1 - len(chunks)))
        if not chunk:
            break
        chunks.extend(chunk)
        if len(chunks) > limit:
            raise HTTPException(413, f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB upload limit.")
    data = bytes(chunks)
    if not data:
        raise HTTPException(400, "Uploaded file is empty.")
    if ext == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise DocumentProcessingError("INVALID_PDF", "Uploaded content is not a valid PDF.")
    else:
        try:
            with Image.open(io.BytesIO(data)) as image:
                actual_format = (image.format or "").upper()
                expected_formats = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP", ".tif": "TIFF", ".tiff": "TIFF", ".bmp": "BMP"}
                if actual_format != expected_formats.get(ext):
                    raise DocumentProcessingError("UNSUPPORTED_IMAGE", "Image content does not match its file extension.", 415)
                frame_count = int(getattr(image, "n_frames", 1))
                if frame_count > settings.MAX_PDF_PAGES:
                    raise DocumentProcessingError("PAGE_LIMIT_EXCEEDED", "Raster document exceeds the configured page limit.", 413)
                total_pixels = 0
                for frame in range(frame_count):
                    image.seek(frame)
                    width, height = image.size
                    if width <= 0 or height <= 0 or width > settings.MAX_IMAGE_DIMENSION or height > settings.MAX_IMAGE_DIMENSION or width * height > settings.MAX_IMAGE_PIXELS:
                        raise DocumentProcessingError("IMAGE_TOO_LARGE", "Image dimensions exceed configured processing limits.", 413)
                    total_pixels += width * height
                    image.load()
                if total_pixels > settings.MAX_DOCUMENT_PROCESSING_PIXELS:
                    raise DocumentProcessingError("DOCUMENT_TOO_LARGE", "Decoded document exceeds the configured pixel budget.", 413)
        except DocumentProcessingError:
            raise
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
            raise DocumentProcessingError("CORRUPTED_IMAGE", "Uploaded content could not be decoded as an image.") from exc
    return data, name
