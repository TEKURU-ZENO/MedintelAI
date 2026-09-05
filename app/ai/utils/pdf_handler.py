import io
import os
import cv2
import numpy as np
from typing import List, Union, Optional
from PIL import Image
from app.ai.utils.logger import get_logger

logger = get_logger(__name__)

def is_pdf(file_path_or_bytes: Union[str, bytes], filename: Optional[str] = None) -> bool:
    """
    Determines if input is a PDF by filename extension or magic bytes (%PDF-).
    """
    if filename and filename.lower().endswith('.pdf'):
        return True
    if isinstance(file_path_or_bytes, str) and file_path_or_bytes.lower().endswith('.pdf'):
        return True
    if isinstance(file_path_or_bytes, (bytes, bytearray)) and file_path_or_bytes.startswith(b'%PDF-'):
        return True
    if isinstance(file_path_or_bytes, str) and os.path.exists(file_path_or_bytes):
        try:
            with open(file_path_or_bytes, 'rb') as f:
                header = f.read(5)
                if header.startswith(b'%PDF-'):
                    return True
        except Exception:
            pass
    return False

def render_pdf_to_images(file_path_or_bytes: Union[str, bytes], dpi_scale: float = 2.0) -> List[np.ndarray]:
    """
    Renders each page of a PDF into an OpenCV BGR NumPy array using pypdfium2.
    
    Args:
        file_path_or_bytes: Filepath string or raw PDF bytes.
        dpi_scale: Rendering scale (2.0 gives ~144 DPI, ideal for medical OCR).
        
    Returns:
        List[np.ndarray]: List of page images in OpenCV BGR format.
    """
    pages = []
    try:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(file_path_or_bytes)
        for idx, page in enumerate(pdf):
            bitmap = page.render(scale=dpi_scale)
            pil_image = bitmap.to_pil()
            rgb_arr = np.array(pil_image)
            if len(rgb_arr.shape) == 2:
                bgr_arr = cv2.cvtColor(rgb_arr, cv2.COLOR_GRAY2BGR)
            elif rgb_arr.shape[2] == 4:
                bgr_arr = cv2.cvtColor(rgb_arr, cv2.COLOR_RGBA2BGR)
            else:
                bgr_arr = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)
            pages.append(bgr_arr)
            logger.info(f"Rendered PDF page {idx + 1}/{len(pdf)} ({bgr_arr.shape[1]}x{bgr_arr.shape[0]})")
        return pages
    except Exception as e:
        logger.error(f"Failed to render PDF using pypdfium2: {e}")
        
    # Fallback to pypdf image extraction if rendering failed
    try:
        from pypdf import PdfReader
        stream = io.BytesIO(file_path_or_bytes) if isinstance(file_path_or_bytes, (bytes, bytearray)) else open(file_path_or_bytes, 'rb')
        reader = PdfReader(stream)
        for idx, page in enumerate(reader.pages):
            for count, image_file_object in enumerate(page.images):
                pil_img = Image.open(io.BytesIO(image_file_object.data))
                rgb_arr = np.array(pil_img)
                bgr_arr = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR) if len(rgb_arr.shape) == 3 else cv2.cvtColor(rgb_arr, cv2.COLOR_GRAY2BGR)
                pages.append(bgr_arr)
                break
        if pages:
            return pages
    except Exception as fallback_err:
        logger.warning(f"pypdf fallback extraction also failed: {fallback_err}")

    return pages

def load_document_pages(file_path_or_bytes: Union[str, bytes, np.ndarray], filename: Optional[str] = None) -> List[np.ndarray]:
    """
    General-purpose document loader accepting an Image (filepath, bytes, ndarray) or PDF.
    Always returns a list of OpenCV BGR images (one per page).
    """
    if isinstance(file_path_or_bytes, np.ndarray):
        return [file_path_or_bytes]

    if is_pdf(file_path_or_bytes, filename):
        pages = render_pdf_to_images(file_path_or_bytes)
        if pages:
            return pages
        logger.warning("Could not render PDF pages, falling back to empty list.")
        return []

    # Standard image loading
    if isinstance(file_path_or_bytes, (bytes, bytearray)):
        nparr = np.frombuffer(file_path_or_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is not None:
            return [image]
            
    if isinstance(file_path_or_bytes, str) and os.path.exists(file_path_or_bytes):
        image = cv2.imread(file_path_or_bytes)
        if image is not None:
            return [image]

    logger.error(f"Failed to load document from input: {filename or type(file_path_or_bytes)}")
    return []
