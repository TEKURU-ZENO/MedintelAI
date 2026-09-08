import os
import cv2
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from app.ai.utils.logger import get_logger
from app.ai.ocr.medical_postprocessor import MedicalVocabularyPostProcessor

logger = get_logger(__name__)

class RegionClassifier:
    """
    Modular classifier for determining if a cropped text region is 'printed' or 'handwritten'.
    Analyzes connected component variance, stroke morphology, and recognition confidence.
    """
    def __init__(self, variance_threshold: float = 0.38, score_threshold: float = 0.90):
        self.variance_threshold = variance_threshold
        self.score_threshold = score_threshold

    def classify(self, crop: np.ndarray, base_score: float = 1.0) -> str:
        if crop is None or crop.size == 0:
            return 'printed'
        
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if len(crop.shape) == 3 else crop
        h, w = gray.shape[:2]
        if h < 10 or w < 15:
            return 'printed'

        # 1. Binarize crop to find stroke components
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return 'printed'

        # 2. Analyze component heights
        heights = []
        for c in contours:
            cx, cy, cw, ch = cv2.boundingRect(c)
            if ch > h * 0.25 and cw > 3:
                heights.append(ch)

        h_std = float(np.std(heights)) / (float(np.mean(heights)) + 1e-5) if len(heights) >= 3 else 0.0

        # High component height variance or low base printed score signals organic handwriting
        if h_std > self.variance_threshold or base_score < self.score_threshold:
            return 'handwritten'
        return 'printed'


class ReadingOrderRebuilder:
    """
    2D geometric reading-order reconstruction engine.
    Clusters bounding boxes into lines via vertical overlap and sorts horizontally,
    rebuilding human reading order for forms, multi-column sections, tables, and notes.
    """
    def __init__(self, vertical_overlap_ratio: float = 0.45):
        self.vertical_overlap_ratio = vertical_overlap_ratio

    def rebuild_order(self, blocks: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], str]:
        if not blocks:
            return [], ""

        processed = []
        for b in blocks:
            xmin, ymin, xmax, ymax = b['bbox']
            h = max(1, ymax - ymin)
            cy = (ymin + ymax) / 2.0
            processed.append({**b, '_h': h, '_cy': cy, '_ymin': ymin, '_xmin': xmin, '_ymax': ymax, '_xmax': xmax})

        processed.sort(key=lambda item: item['_ymin'])

        lines = []
        for block in processed:
            placed = False
            for line in lines:
                line_ymin = min(b['_ymin'] for b in line)
                line_ymax = max(b['_ymax'] for b in line)
                line_h = max(1, line_ymax - line_ymin)
                
                overlap = max(0, min(block['_ymax'], line_ymax) - max(block['_ymin'], line_ymin))
                min_h = min(block['_h'], line_h)
                
                if (overlap / float(min_h)) >= self.vertical_overlap_ratio:
                    line.append(block)
                    placed = True
                    break
            if not placed:
                lines.append([block])

        lines.sort(key=lambda line: min(b['_ymin'] for b in line))
        for line in lines:
            line.sort(key=lambda b: b['_xmin'])

        sorted_blocks = []
        text_lines = []
        idx = 1
        for line in lines:
            line_texts = []
            for b in line:
                clean_b = {k: v for k, v in b.items() if not k.startswith('_')}
                clean_b['id'] = f"block_{idx}"
                sorted_blocks.append(clean_b)
                idx += 1
                if b.get('text'):
                    line_texts.append(b['text'].strip())
            if line_texts:
                text_lines.append("  ".join(line_texts))

        raw_text = "\n".join(text_lines)
        return sorted_blocks, raw_text


class MedIntelOCREngine:
    """
    True Hybrid Medical OCR Engine:
    - RapidOCR (ONNX) for detection & printed text recognition
    - TrOCR (VisionEncoderDecoder) for handwritten clinical text recognition
    - MedicalVocabularyPostProcessor for medicine & dosage normalization
    - ReadingOrderRebuilder for 2D layout reading-order recovery
    """
    def __init__(self, use_gpu: bool = False):
        self.use_gpu = use_gpu
        self.classifier = RegionClassifier()
        self.rebuilder = ReadingOrderRebuilder()
        self.postprocessor = MedicalVocabularyPostProcessor()
        self._rapid_ocr = None
        self._trocr_processor = None
        self._trocr_model = None
        self._paddle_ocr = None
        self._init_models()

    def _init_models(self):
        # 1. RapidOCR for printed text and fast text line detection
        try:
            from rapidocr_onnxruntime import RapidOCR
            self._rapid_ocr = RapidOCR()
            logger.info('RapidOCR (ONNX) initialized successfully')
        except Exception as e:
            logger.warning(f'RapidOCR not loaded: {e}')

        # 2. TrOCR for handwritten clinical text
        try:
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel
            model_id = "microsoft/trocr-small-handwritten"
            finetuned_path = os.path.join(os.path.dirname(__file__), "..", "models", "trocr_medical_finetuned")
            
            if os.path.exists(finetuned_path):
                logger.info(f"Loading fine-tuned medical TrOCR model from {finetuned_path}")
                self._trocr_processor = TrOCRProcessor.from_pretrained(finetuned_path)
                self._trocr_model = VisionEncoderDecoderModel.from_pretrained(finetuned_path)
            else:
                logger.info(f"Loading base TrOCR handwriting model: {model_id}")
                self._trocr_processor = TrOCRProcessor.from_pretrained(model_id)
                self._trocr_model = VisionEncoderDecoderModel.from_pretrained(model_id)
            self._trocr_model.eval()
            logger.info("TrOCR model initialized successfully for handwriting recognition")
        except Exception as e:
            logger.warning(f"TrOCR not loaded: {e}")

        # 3. PaddleOCR optional secondary
        try:
            from paddleocr import PaddleOCR
            self._paddle_ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False, use_gpu=self.use_gpu)
            logger.info('PaddleOCR initialized successfully')
        except Exception:
            pass

    def _trocr_recognize(self, crop: np.ndarray) -> Tuple[str, float]:
        """
        Runs TrOCR on a cropped handwritten line image.
        Returns recognized string and model confidence score.
        """
        if self._trocr_processor is None or self._trocr_model is None or crop is None or crop.size == 0:
            return "", 0.0
        try:
            import torch
            import torch.nn.functional as F
            from PIL import Image

            # Ensure proper RGB channels
            if len(crop.shape) == 2:
                rgb = cv2.cvtColor(crop, cv2.COLOR_GRAY2RGB)
            elif len(crop.shape) == 3 and crop.shape[2] == 3:
                rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            else:
                rgb = crop

            # Ensure minimum height for ViT patch embedding
            h, w = rgb.shape[:2]
            if h < 24:
                scale = 24.0 / float(h)
                rgb = cv2.resize(rgb, (int(w * scale), 24), interpolation=cv2.INTER_CUBIC)

            pil_img = Image.fromarray(rgb)
            pixel_values = self._trocr_processor(pil_img, return_tensors='pt').pixel_values

            with torch.no_grad():
                generated_outputs = self._trocr_model.generate(
                    pixel_values,
                    max_new_tokens=32,
                    return_dict_in_generate=True,
                    output_scores=True
                )

            token_ids = generated_outputs.sequences
            raw_text = self._trocr_processor.batch_decode(token_ids, skip_special_tokens=True)[0].strip()

            if hasattr(generated_outputs, 'scores') and generated_outputs.scores:
                probs = [float(F.softmax(score, dim=-1).max().item()) for score in generated_outputs.scores]
                conf = float(np.mean(probs)) if probs else 0.85
            else:
                conf = 0.88

            return raw_text, round(conf, 4)
        except Exception as e:
            logger.error(f"TrOCR recognition error: {e}")
            return "", 0.0

    def detect_regions(self, image: np.ndarray) -> List[Dict[str, Any]]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 5))
        grad = cv2.morphologyEx(gray, cv2.MORPH_GRADIENT, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
        _, thresh = cv2.threshold(grad, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        dilated = cv2.dilate(thresh, kernel, iterations=2)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        h_img, w_img = gray.shape[:2]
        
        regions = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w > 15 and h > 8 and w < w_img * 0.99 and h < h_img * 0.98:
                regions.append({
                    'bbox': [x, y, x + w, y + h],
                    'crop': image[y:y+h, x:x+w]
                })
        return regions

    def process_document(self, image: np.ndarray, doc_name: str = 'document', page_num: int = 1) -> Dict[str, Any]:
        """
        True Hybrid Processing Pipeline:
        1. Detects text bounding boxes.
        2. Classifies each crop as printed or handwritten.
        3. Routes:
           - Printed regions -> RapidOCR
           - Handwritten regions -> TrOCR (VisionEncoderDecoder)
        4. Applies medical lexicon normalization.
        5. Rebuilds 2D reading order.
        """
        h_img, w_img = image.shape[:2]
        raw_blocks = []

        # 1. Primary: RapidOCR Detection & Hybrid Recognition Routing
        if self._rapid_ocr is not None:
            try:
                ocr_results, elapse = self._rapid_ocr(image)
                if ocr_results:
                    for idx, item in enumerate(ocr_results):
                        box, rapid_text, rapid_score = item[0], item[1], float(item[2])
                        xs = [int(p[0]) for p in box]
                        ys = [int(p[1]) for p in box]
                        xmin, xmax = max(0, min(xs)), min(w_img, max(xs))
                        ymin, ymax = max(0, min(ys)), min(h_img, max(ys))
                        crop = image[ymin:ymax, xmin:xmax]
                        region_type = self.classifier.classify(crop, base_score=rapid_score)

                        if region_type == 'handwritten' and self._trocr_model is not None:
                            # ROUTE TO TrOCR FOR HANDWRITING
                            trocr_text, trocr_conf = self._trocr_recognize(crop)
                            if trocr_text:
                                final_text = self.postprocessor.clean_text(trocr_text)
                                model_used = 'trocr-handwritten'
                                final_conf = trocr_conf
                            else:
                                final_text = self.postprocessor.clean_text(rapid_text)
                                model_used = 'rapidocr-fallback'
                                final_conf = rapid_score
                        else:
                            # ROUTE TO RapidOCR FOR PRINTED TEXT
                            final_text = self.postprocessor.clean_text(rapid_text)
                            model_used = 'rapidocr-printed'
                            final_conf = rapid_score

                        status = self._get_status(final_conf)
                        raw_blocks.append({
                            'id': f'block_{idx + 1}',
                            'text': final_text,
                            'confidence': round(final_conf, 4),
                            'source': region_type,
                            'model_used': model_used,
                            'bbox': [xmin, ymin, xmax, ymax],
                            'status': status
                        })
            except Exception as e:
                logger.error(f'RapidOCR execution failed: {e}')

        # 2. Secondary: Contour Detection Fallback
        if not raw_blocks:
            detected_regions = self.detect_regions(image)
            for idx, r in enumerate(detected_regions):
                xmin, ymin, xmax, ymax = r['bbox']
                crop = r['crop']
                region_type = self.classifier.classify(crop)
                
                if self._trocr_model is not None:
                    trocr_text, trocr_conf = self._trocr_recognize(crop)
                    final_text = self.postprocessor.clean_text(trocr_text) if trocr_text else f'[Text Region {idx + 1}]'
                    model_used = 'trocr-handwritten'
                    conf = trocr_conf if trocr_text else 0.70
                else:
                    final_text = f'[Text Region {idx + 1}]'
                    model_used = 'opencv-contour'
                    conf = 0.70

                status = self._get_status(conf)
                raw_blocks.append({
                    'id': f'block_{idx + 1}',
                    'text': final_text,
                    'confidence': round(conf, 4),
                    'source': region_type,
                    'model_used': model_used,
                    'bbox': [xmin, ymin, xmax, ymax],
                    'status': status
                })

        # Reconstruct reading order and produce coherent plain text (raw_text)
        sorted_blocks, raw_text = self.rebuilder.rebuild_order(raw_blocks)
        overall_conf = float(np.mean([b['confidence'] for b in sorted_blocks])) if sorted_blocks else 0.0

        return {
            'status': 'success',
            'document': doc_name,
            'page': page_num,
            'pages': 1,
            'image_dimensions': [w_img, h_img],
            'total_blocks': len(sorted_blocks),
            'overall_confidence': round(overall_conf, 4),
            'blocks': sorted_blocks,
            'raw_text': raw_text
        }

    def _get_status(self, conf: float) -> str:
        if conf >= 0.90:
            return 'HIGH_CONFIDENCE'
        elif conf >= 0.60:
            return 'REVIEW_REQUIRED'
        else:
            return 'HUMAN_VERIFICATION_NEEDED'
