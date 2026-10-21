import cv2
import numpy as np
from app.core.config import settings
from app.core.document_errors import DocumentProcessingError
from app.schemas.document import CropRegion


class CropService:
    """Strict page cropper in top-left-origin rendered pixel coordinates."""
    def crop(self, image: np.ndarray, region: CropRegion) -> np.ndarray:
        if image is None or image.size == 0:
            raise DocumentProcessingError("PAGE_IMAGE_UNAVAILABLE", "Page image is unavailable.")
        height, width = image.shape[:2]
        if region.width > settings.MAX_CROP_DIMENSION or region.height > settings.MAX_CROP_DIMENSION:
            raise DocumentProcessingError("CROP_TOO_LARGE", "Crop exceeds the configured maximum dimensions.", 413)
        if region.x + region.width > width or region.y + region.height > height:
            raise DocumentProcessingError("OUT_OF_BOUNDS_CROP", "Crop region is outside page bounds.")
        crop = image[region.y:region.y + region.height, region.x:region.x + region.width]
        if crop.size == 0:
            raise DocumentProcessingError("INVALID_CROP", "Crop region is empty.")
        return crop.copy()

    @staticmethod
    def normalize_color(image: np.ndarray) -> np.ndarray:
        if image.ndim == 2:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        if image.shape[2] == 4:
            return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        return image
