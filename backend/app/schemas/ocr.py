from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.schemas.document import (CropRegion as RegionRequest, DocumentMetadata,
                                  OCRProvenance, PageMetadata)


class OCRBlock(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    text: str
    confidence: float = Field(ge=0, le=1)
    bbox: List[int]


class OCRResponse(BaseModel):
    """OCR payload with the legacy document layout fields kept for the studio UI."""
    success: bool = True
    status: str = "success"
    document: str
    pages: int = Field(ge=0)
    image_preview: Optional[str] = None
    image_dimensions: Optional[List[int]] = None
    total_blocks: int = Field(ge=0)
    overall_confidence: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    processing_time: float = Field(ge=0)
    blocks: List[OCRBlock]
    raw_text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    region_bbox: Optional[List[int]] = None
    document_metadata: Optional[DocumentMetadata] = None
    page_metadata: List[PageMetadata] = Field(default_factory=list)
    provenance: List[OCRProvenance] = Field(default_factory=list)


class CorrectionRequest(BaseModel):
    # The optional legacy fields preserve the existing studio clinician review flow.
    text: Optional[str] = Field(default=None, min_length=1, max_length=100_000)
    document: Optional[str] = Field(default=None, max_length=255)
    block_id: Optional[str] = Field(default=None, max_length=128)
    original_text: Optional[str] = Field(default=None, max_length=100_000)
    corrected_text: Optional[str] = Field(default=None, max_length=100_000)
    clinician_notes: Optional[str] = Field(default=None, max_length=10_000)

    @model_validator(mode="after")
    def require_correction_content(self):
        if self.text is not None and self.text.strip():
            return self
        if self.original_text is not None and self.original_text.strip() and self.corrected_text is not None:
            return self
        raise ValueError("Provide non-empty text or original_text with corrected_text.")


class CorrectionResponse(BaseModel):
    success: bool = True
    original_text: str
    corrected_text: str
    correction_applied: bool
    message: str
    entry: Optional[Dict[str, Any]] = None


class BenchmarkSample(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    image_base64: str = Field(min_length=1, max_length=10_000_000, description="Base64 encoded image")
    ground_truth: Optional[str] = Field(default=None, max_length=100_000)


class BenchmarkRequest(BaseModel):
    samples: List[BenchmarkSample] = Field(min_length=1, max_length=10)


class BenchmarkResponse(BaseModel):
    success: bool = True
    samples_processed: int = Field(ge=0)
    successful_samples: int = Field(ge=0)
    failed_samples: int = Field(ge=0)
    average_processing_time: Optional[float] = Field(default=None, ge=0)
    average_confidence: Optional[float] = Field(default=None, ge=0, le=1)
    character_accuracy: Optional[float] = Field(default=None, ge=0, le=1)
    word_accuracy: Optional[float] = Field(default=None, ge=0, le=1)
    exact_match_accuracy: Optional[float] = Field(default=None, ge=0, le=1)
    ground_truth_samples: int = Field(ge=0)


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


class TextExportRequest(BaseModel):
    text: str = Field(max_length=1_000_000, description="OCR text to export as UTF-8 plain text")
    filename: str = Field(default="ocr-result.txt", min_length=1, max_length=255)


class BenchmarkReportResponse(BaseModel):
    status: str
    system: str
    metrics: Dict[str, Dict[str, Any]]
