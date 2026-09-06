import os
import json
import tempfile
from typing import Dict, Any, List, Union
import numpy as np

from app.ai.utils.logger import get_logger
from app.ai.utils.pdf_handler import load_document_pages
from app.ai.preprocessing.preprocessing_pipeline import run_preprocessing_pipeline
from app.ai.ocr.ocr_engine import MedIntelOCREngine

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
        self.output_dir = os.path.join(tempfile.gettempdir(), "medintel_json")
        self.txt_output_dir = os.path.join(tempfile.gettempdir(), "medintel_txt")

    def process_document(
        self,
        document_input: Union[str, bytes, np.ndarray],
        doc_name: str = "document",
        output_json_path: str = None,
        output_txt_path: str = None
    ) -> Dict[str, Any]:
        """
        Processes arbitrary document (Image or PDF):
        - Ingests all pages.
        - Preprocesses each page with CLAHE, Bilateral Denoising, Deskewing, Binarization.
        - Extracts text blocks, routes regions, and rebuilds reading order.
        - Assembles multi-page results into JSON and formatted .txt.
        """
        logger.info(f"Ingesting document: {doc_name}")
        pages = load_document_pages(document_input, filename=doc_name)
        
        if not pages:
            logger.error(f"No valid image pages loaded for {doc_name}")
            return {
                'status': 'error',
                'message': 'Failed to decode or render document.',
                'document': doc_name,
                'pages': 0,
                'total_blocks': 0,
                'overall_confidence': 0.0,
                'blocks': [],
                'raw_text': ''
            }

        all_blocks = []
        page_texts = []
        confidences = []

        for idx, page_img in enumerate(pages):
            page_num = idx + 1
            # 1. OpenCV Preprocessing
            clean_page = run_preprocessing_pipeline(page_img, self.preprocess_config)
            
            # 2. General-Purpose OCR Engine Execution
            page_result = self.ocr_engine.process_document(clean_page, doc_name=doc_name, page_num=page_num)
            
            # Tag blocks with page number
            for b in page_result.get('blocks', []):
                b['page'] = page_num
                all_blocks.append(b)
                confidences.append(b['confidence'])
                
            p_text = page_result.get('raw_text', '').strip()
            if p_text:
                if len(pages) > 1:
                    page_texts.append(f"--- Page {page_num} ---\n{p_text}")
                else:
                    page_texts.append(p_text)

        overall_conf = float(np.mean(confidences)) if confidences else 0.0
        combined_raw_text = "\n\n".join(page_texts)

        # Generate image preview (base64) of the first page for frontend visualization
        image_preview = None
        image_dimensions = [800, 600]
        if pages and len(pages) > 0:
            try:
                import cv2
                import base64
                h_p, w_p = pages[0].shape[:2]
                image_dimensions = [w_p, h_p]
                _, buf = cv2.imencode('.jpg', pages[0])
                image_preview = f"data:image/jpeg;base64,{base64.b64encode(buf).decode('utf-8')}"
            except Exception as e:
                logger.warning(f"Failed to generate image preview base64: {e}")

        final_result = {
            'status': 'success',
            'document': doc_name,
            'pages': len(pages),
            'image_preview': image_preview,
            'image_dimensions': image_dimensions,
            'total_blocks': len(all_blocks),
            'overall_confidence': round(overall_conf, 4),
            'blocks': all_blocks,
            'raw_text': combined_raw_text
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
