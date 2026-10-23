import os
import json
import tempfile
from typing import Dict, Any, List, Union, Optional, Tuple
import numpy as np

from app.ai.utils.logger import get_logger
from app.ai.utils.pdf_handler import load_document_pages
from app.ai.preprocessing.preprocessing_pipeline import run_preprocessing_pipeline
from app.ai.ocr.ocr_engine import OCRDocumentReadingEngine, MedIntelOCREngine
from app.ai.ocr.lens_engine import GoogleLensOCREngine, ScreenCoordinateMapper

logger = get_logger(__name__)

class PipelineController:
    """
    OCR Document Reading System Pipeline Controller.
    Accepts arbitrary documents (Image files, image bytes, or multi-page PDFs),
    runs resolution-preserving preprocessing, hybrid OCR extraction, reading-order reconstruction,
    Google-Lens screen and snippet OCR, and structured JSON + .txt export.
    """
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.preprocess_config = self.config.get("preprocessing", {})
        self.ocr_engine = OCRDocumentReadingEngine()
        self.lens_engine = GoogleLensOCREngine(rapid_ocr=self.ocr_engine._rapid_ocr)
        self.output_dir = os.path.join(tempfile.gettempdir(), "ocr_document_json")
        self.txt_output_dir = os.path.join(tempfile.gettempdir(), "ocr_document_txt")

    def process_document(
        self,
        document_input: Union[str, bytes, np.ndarray],
        doc_name: str = "document",
        output_json_path: Optional[str] = None,
        output_txt_path: Optional[str] = None,
        input_mode: str = "auto",
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

        pages = load_document_pages(document_input, filename=doc_name)
        if not pages:
            logger.error(f"Failed to load pages for document: {doc_name}")
            return {
                'status': 'error',
                'message': 'Failed to decode or parse document file.',
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
        doc_tables = []
        doc_key_values = []
        doc_checkboxes = []

        for idx, page_img in enumerate(pages):
            page_num = idx + 1
            # 1. Appropriate Preprocessing (Screen / Digital vs Scanned Paper)
            clean_page = run_preprocessing_pipeline(page_img, self.preprocess_config, input_mode=input_mode, preprocessing_mode=preprocessing_mode)
            
            # 2. General-Purpose OCR Engine Execution
            page_result = self.ocr_engine.process_document(clean_page, doc_name=doc_name, page_num=page_num, input_mode=input_mode)
            
            # Tag blocks with page number
            for b in page_result.get('blocks', []):
                b['page'] = page_num
                all_blocks.append(b)
                confidences.append(b['confidence'])

            # Collect page-level layout intelligence
            page_layout = page_result.get('layout', {})
            for t in page_layout.get('tables', []):
                t_copy = dict(t)
                t_copy['page'] = page_num
                doc_tables.append(t_copy)
            for kv in page_layout.get('key_value_pairs', []):
                kv_copy = dict(kv)
                kv_copy['page'] = page_num
                doc_key_values.append(kv_copy)
            for cb in page_layout.get('checkboxes', []):
                cb_copy = dict(cb)
                cb_copy['page'] = page_num
                doc_checkboxes.append(cb_copy)
                
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
            'layout_intelligence': {
                'total_tables': len(doc_tables),
                'tables': doc_tables,
                'total_key_values': len(doc_key_values),
                'key_value_pairs': doc_key_values,
                'total_checkboxes': len(doc_checkboxes),
                'checkboxes': doc_checkboxes
            },
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

    def process_region(
        self,
        document_input: Union[str, bytes, np.ndarray],
        region_bbox: List[int],
        doc_name: str = "snippet",
        input_mode: str = "screen",
        preprocessing_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processes a focused sub-region / snippet from the document.
        Passes the original high-resolution page image directly into ocr_engine.process_region
        so the region crop can be upscaled and preprocessed without full-page binarization.
        """
        pages = load_document_pages(document_input, filename=doc_name)
        if not pages:
            return {
                'status': 'error',
                'message': 'Failed to decode document for region processing.',
                'blocks': [],
                'raw_text': ''
            }
        page_img = pages[0]

        # Use GoogleLensOCREngine snippet mode if screen/digital input mode
        if input_mode in ('screen', 'snippet', 'digital', 'his', 'browser'):
            lens_res = self.lens_engine.process_snippet_region(
                image=page_img,
                region_bbox=region_bbox,
                mode=input_mode
            )
            lens_res['document'] = doc_name
            lens_res['pages'] = 1
            lens_res['image_dimensions'] = [page_img.shape[1], page_img.shape[0]]
            return lens_res

        return self.ocr_engine.process_region(page_img, region_bbox, doc_name=doc_name, input_mode=input_mode)

    def process_lens_snippet(
        self,
        document_input: Union[str, bytes, np.ndarray],
        region_bbox: List[int],
        screen_origin: Tuple[int, int] = (0, 0),
        screen_scale_factor: float = 1.0,
        doc_name: str = "snippet"
    ) -> Dict[str, Any]:
        """
        Executes ultra-low-latency marquee snippet OCR with screen coordinate mapping.
        """
        pages = load_document_pages(document_input, filename=doc_name)
        if not pages:
            return {
                'status': 'error',
                'message': 'Failed to decode snippet document.',
                'blocks': [],
                'raw_text': ''
            }
        page_img = pages[0]
        res = self.lens_engine.process_snippet_region(
            image=page_img,
            region_bbox=region_bbox,
            screen_origin=screen_origin,
            screen_scale_factor=screen_scale_factor
        )
        res['document'] = doc_name
        return res

    def process_screen_capture(
        self,
        document_input: Union[str, bytes, np.ndarray],
        screen_origin: Tuple[int, int] = (0, 0),
        screen_scale_factor: float = 1.0,
        mode: str = "screen",
        doc_name: str = "screen_capture"
    ) -> Dict[str, Any]:
        """
        Executes Google-Lens full screen capture OCR with screen coordinate mapping,
        line-level blocks, and specialized HIS/browser/pdf handling.
        """
        pages = load_document_pages(document_input, filename=doc_name)
        if not pages:
            return {
                'status': 'error',
                'message': 'Failed to decode screen capture.',
                'blocks': [],
                'raw_text': ''
            }
        page_img = pages[0]
        res = self.lens_engine.process_screen_capture(
            image=page_img,
            screen_origin=screen_origin,
            screen_scale_factor=screen_scale_factor,
            mode=mode
        )
        res['document'] = doc_name
        return res
