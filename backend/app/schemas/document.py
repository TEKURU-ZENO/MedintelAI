from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourceType(str, Enum):
    IMAGE = "image"
    PDF = "pdf"
    SCREEN_CAPTURE = "screen_capture"


class PreprocessingMode(str, Enum):
    """Explicit OCR preprocessing preset; omitted values preserve input-mode behavior."""
    BALANCED = "balanced"
    HIGH_CONTRAST = "high-contrast"
    GRAYSCALE = "grayscale"
    NONE = "none"


class Coordinate(BaseModel):
    """Pixel coordinate: origin top-left, x rightward, y downward."""
    x: int = Field(ge=0)
    y: int = Field(ge=0)


class BoundingBox(BaseModel):
    """Pixel box in top-left origin coordinates."""
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class NormalizedBoundingBox(BaseModel):
    """Page-relative box; all values are fractions in [0, 1]."""
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(ge=0, le=1)
    height: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def within_page(self):
        if self.x + self.width > 1.0000001 or self.y + self.height > 1.0000001:
            raise ValueError("Normalized bounding box must fit within the page.")
        return self


class CropRegion(BoundingBox):
    """Crop box in page pixel coordinates; it is never clipped automatically."""


class PageMetadata(BaseModel):
    page_number: int = Field(ge=1)
    width: int = Field(ge=0, description="Rendered page width in pixels")
    height: int = Field(ge=0, description="Rendered page height in pixels")
    source_width: Optional[float] = Field(default=None, ge=0, description="Source dimensions (pixels for raster, PDF points for PDF)")
    source_height: Optional[float] = Field(default=None, ge=0)
    format: Optional[str] = None
    color_mode: Optional[str] = None
    dpi_x: Optional[float] = Field(default=None, gt=0)
    dpi_y: Optional[float] = Field(default=None, gt=0)
    source_type: SourceType
    document_type: Optional[str] = None
    render_scale_x: Optional[float] = Field(default=None, gt=0)
    render_scale_y: Optional[float] = Field(default=None, gt=0)
    rotation: Optional[int] = None
    orientation: Optional[str] = None
    status: str = "ready"
    error_code: Optional[str] = None


class DocumentMetadata(BaseModel):
    document_id: UUID
    filename: str
    source_type: SourceType
    document_type: Optional[str] = None
    file_size: int = Field(ge=0)
    page_count: int = Field(ge=0)
    processed_at: datetime
    original_format: Optional[str] = None
    status: str = "ready"
    failed_pages: List[int] = Field(default_factory=list)
    source_metadata: Dict[str, Any] = Field(default_factory=dict)


class OCRProvenance(BaseModel):
    source_type: SourceType
    document_id: UUID
    page_number: int = Field(ge=1)
    ocr_engine: Optional[str] = None
    ocr_engine_version: Optional[str] = None
    pipeline_version: str
    processed_at: datetime


class DocumentPage(BaseModel):
    """Internal normalized page. Image data is an OpenCV BGR array, excluded from JSON."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    metadata: PageMetadata
    image: Any = Field(exclude=True, repr=False)


class ProcessedDocument(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    metadata: DocumentMetadata
    pages: List[DocumentPage]
    provenance: List[OCRProvenance] = Field(default_factory=list)
