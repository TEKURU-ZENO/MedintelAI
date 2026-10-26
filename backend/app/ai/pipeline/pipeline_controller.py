import os
import json
import tempfile
from typing import Dict, Any, List, Union, Optional
import numpy as np

from app.ai.utils.logger import get_logger
from app.ai.preprocessing.preprocessing_pipeline import run_preprocessing_pipeline
from app.ai.ocr.ocr_engine import MedIntelOCREngine
from app.schemas.document import ProcessedDocument, SourceType
from app.services.document_processing_service import DocumentProcessingService
from app.services.crop_service import CropService
from app.schemas.document import CropRegion

logger = get_logger(__name__)

class PipelineController:
    """
    General-Purpose Medical Document Pipeline Controller.
    Accepts arbitrary documents (Image files, image bytes, or multi-page PDFs),
    runs OpenCV preprocessing, hybrid OCR extraction, reading-order reconstruction,
    and structured JSON + .txt export.
    """
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.preprocess_config = self.config.get("preprocessing", {})
        self.ocr_engine = MedIntelOCREngine()
        self.document_processor = DocumentProcessingService()
        self.crop_service = CropService()
        self.output_dir = os.path.join(tempfile.gettempdir(), "medintel_json")
        self.txt_output_dir = os.path.join(tempfile.gettempdir(), "medintel_txt")

    def process_document(
        self,
        document_input: Union[str, bytes, np.ndarray, ProcessedDocument],
        doc_name: str = "document",
        output_json_path: Optional[str] = None,
        output_txt_path: Optional[str] = None,
        input_mode: str = "auto",
        source_type: Optional[SourceType] = None,
        preprocessing_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processes an uploaded medical document (image or multi-page PDF).
        Executes preprocessing, hybrid OCR routing, 2D reading order reconstruction,
        and saves JSON + .txt artifacts.
        """
        logger.info(f"Ingesting document: {doc_name} (mode: {input_mode})")
        if input_mode == 'auto' and ('screen' in doc_name.lower() or doc_name.lower().endswith('.pdf')):
            input_mode = 'screen' if 'screen' in doc_name.lower() else 'digital'

        document = document_input if isinstance(document_input, ProcessedDocument) else self.document_processor.process(document_input, doc_name, source_type)
        pages = [page for page in document.pages if page.image is not None]
        if not pages:
            from app.core.document_errors import DocumentProcessingError
            failed_code = document.pages[0].metadata.error_code if document.pages else None
            status_code = 413 if failed_code in {"PDF_RENDER_LIMIT_EXCEEDED", "IMAGE_TOO_LARGE", "DOCUMENT_TOO_LARGE"} else 422
            raise DocumentProcessingError(failed_code or "PDF_RENDER_ERROR", "No document pages could be rendered.", status_code)

        all_blocks = []
        page_texts = []
        confidences = []

        for page in pages:
            page_num = page.metadata.page_number
            page_img = page.image
            # 1. Appropriate Preprocessing (Screen / Digital vs Scanned Paper)
            clean_page = run_preprocessing_pipeline(
                page_img, self.preprocess_config, input_mode=input_mode,
                preprocessing_mode=preprocessing_mode
            )
            
            # 2. General-Purpose OCR Engine Execution
            page_result = self.ocr_engine.process_document(
                clean_page, doc_name=doc_name, page_num=page_num, input_mode=input_mode, original_image=page_img
            )
            
            # Tag blocks with page number
            for b in page_result.get('blocks', []):
                b['page'] = page_num
                all_blocks.append(b)
                confidences.append(b['confidence'])
                
            p_text = page_result.get('raw_text', '').strip()
            if p_text:
                if document.metadata.page_count > 1:
                    page_texts.append(f"--- Page {page_num} ---\n{p_text}")
                else:
                    page_texts.append(p_text)

        overall_conf = float(np.mean(confidences)) if confidences else 0.0
        combined_raw_text = "\n\n".join(page_texts)

        # Generate image preview (base64) of the first page for frontend visualization
        image_preview = None
        image_dimensions = [800, 600]
        if pages:
            try:
                import cv2
                import base64
                h_p, w_p = pages[0].image.shape[:2]
                image_dimensions = [w_p, h_p]
                _, buf = cv2.imencode('.jpg', pages[0].image)
                image_preview = f"data:image/jpeg;base64,{base64.b64encode(buf).decode('utf-8')}"
            except Exception as e:
                logger.warning(f"Failed to generate image preview base64: {e}")

        final_result = {
            'status': 'success',
            'document': doc_name,
            'pages': document.metadata.page_count,
            'image_preview': image_preview,
            'image_dimensions': image_dimensions,
            'total_blocks': len(all_blocks),
            'overall_confidence': round(overall_conf, 4),
            'blocks': all_blocks,
            'raw_text': combined_raw_text,
            'document_metadata': document.metadata.model_dump(mode='json'),
            'page_metadata': [page.metadata.model_dump(mode='json') for page in document.pages],
            'provenance': [item.model_dump(mode='json') for item in document.provenance]
        }

        # 3. Export JSON and .txt files safely
        base_name = os.path.splitext(doc_name)[0]
        if output_json_path is None:
            output_json_path = os.path.join(self.output_dir, f"{base_name}.json")
        if output_txt_path is None:
            output_txt_path = os.path.join(self.txt_output_dir, f"{base_name}.txt")

        try:
            os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
            with open(output_json_path, 'w', encoding='utf-8') as f:
                json.dump(final_result, f, indent=2)
            logger.info(f"Saved OCR JSON to {output_json_path}")
        except Exception as e:
            logger.warning(f"Could not persist JSON file ({e}), continuing in-memory.")

        try:
            os.makedirs(os.path.dirname(output_txt_path), exist_ok=True)
            with open(output_txt_path, 'w', encoding='utf-8') as f:
                f.write(combined_raw_text)
            logger.info(f"Saved plain text .txt to {output_txt_path}")
        except Exception as e:
            logger.warning(f"Could not persist .txt file ({e}), continuing in-memory.")

        return final_result

    def process_image(self, image_path: str, output_path: str = None) -> Dict[str, Any]:
        """Backward-compatible alias for process_document."""
        doc_name = os.path.basename(image_path) if isinstance(image_path, str) else "document"
        return self.process_document(image_path, doc_name=doc_name, output_json_path=output_path)

    def process_region(
        self,
        document_input: Union[str, bytes, np.ndarray],
        region_bbox: List[int],
        doc_name: str = "snippet",
        input_mode: str = "screen",
        source_type: Optional[SourceType] = None,
        preprocessing_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processes a focused region using the shared strict crop and coordinate utilities.
        """
        document = self.document_processor.process(document_input, doc_name, source_type)
        if not document.pages or document.pages[0].image is None:
            from app.core.document_errors import DocumentProcessingError
            failed_code = document.pages[0].metadata.error_code if document.pages else None
            status_code = 413 if failed_code in {"PDF_RENDER_LIMIT_EXCEEDED", "IMAGE_TOO_LARGE", "DOCUMENT_TOO_LARGE"} else 422
            raise DocumentProcessingError(failed_code or "PDF_RENDER_ERROR", "The first page could not be rendered.", status_code)
        page = document.pages[0]
        x1, y1, x2, y2 = region_bbox
        crop = self.crop_service.crop(page.image, CropRegion(x=x1, y=y1, width=x2 - x1, height=y2 - y1))
        result = self.process_document(
            crop, doc_name=doc_name, input_mode=input_mode,
            preprocessing_mode=preprocessing_mode
        )
        for block in result.get('blocks', []):
            bx1, by1, bx2, by2 = block['bbox']
            bx1, by1, bx2, by2 = bx1 + x1, by1 + y1, bx2 + x1, by2 + y1
            block['bbox'] = [bx1, by1, bx2, by2]
            block['normalized_bbox'] = [round(bx1 / page.metadata.width, 5), round(by1 / page.metadata.height, 5),
                                        round(bx2 / page.metadata.width, 5), round(by2 / page.metadata.height, 5)]
        result['image_dimensions'] = [page.metadata.width, page.metadata.height]
        result['region_bbox'] = [x1, y1, x2, y2]
        result['document'] = doc_name
        result['pages'] = 1
        result['document_metadata'] = document.metadata.model_dump(mode='json')
        result['page_metadata'] = [page.metadata.model_dump(mode='json')]
        result['provenance'] = [item.model_dump(mode='json') for item in document.provenance[:1]]
        return result
