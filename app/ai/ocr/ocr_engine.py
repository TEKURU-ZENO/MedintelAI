import os
import cv2
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from app.ai.utils.logger import get_logger

logger = get_logger(__name__)

class RegionClassifier:
    """
    Modular classifier for determining if a cropped text region is 'printed' or 'handwritten'.
    Designed as a modular hypothesis evaluator so it can be swapped with a deep learning
    classifier (e.g., MobileNet/ResNet feature extractor) without altering engine flow.
    """
    def __init__(self, stroke_std_threshold: float = 45.0, edge_density_threshold: float = 0.08):
        self.stroke_std_threshold = stroke_std_threshold
        self.edge_density_threshold = edge_density_threshold

    def classify(self, crop: np.ndarray) -> str:
        if crop is None or crop.size == 0:
            return 'printed'
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if len(crop.shape) == 3 else crop
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / float(gray.size)
        std_dev = float(np.std(gray))
        
        # Hypothesis: Handwritten text exhibits higher local intensity variation and organic stroke irregularity
        if std_dev > self.stroke_std_threshold or (edge_density > self.edge_density_threshold and std_dev > 35.0):
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
        """
        Sorts blocks in reading order and formats raw_text.
        
        Args:
            blocks: List of OCR text blocks with 'bbox': [xmin, ymin, xmax, ymax]
            
        Returns:
            Tuple of (sorted_blocks, raw_text)
        """
        if not blocks:
            return [], ""

        # Calculate height and center y for each block
        processed = []
        for b in blocks:
            xmin, ymin, xmax, ymax = b['bbox']
            h = max(1, ymax - ymin)
            cy = (ymin + ymax) / 2.0
            processed.append({**b, '_h': h, '_cy': cy, '_ymin': ymin, '_xmin': xmin, '_ymax': ymax, '_xmax': xmax})

        # Sort primarily by ymin to begin clustering
        processed.sort(key=lambda item: item['_ymin'])

        # Line clustering via vertical overlap
        lines = []
        for block in processed:
            placed = False
            for line in lines:
                # Compare with the average height and vertical bounds of the line
                line_ymin = min(b['_ymin'] for b in line)
                line_ymax = max(b['_ymax'] for b in line)
                line_h = max(1, line_ymax - line_ymin)
                
                # Check vertical overlap
                overlap = max(0, min(block['_ymax'], line_ymax) - max(block['_ymin'], line_ymin))
                min_h = min(block['_h'], line_h)
                
                if (overlap / float(min_h)) >= self.vertical_overlap_ratio:
                    line.append(block)
                    placed = True
                    break
            if not placed:
                lines.append([block])

        # Sort each line left-to-right, and sort lines top-to-bottom
        lines.sort(key=lambda line: min(b['_ymin'] for b in line))
        for line in lines:
            line.sort(key=lambda b: b['_xmin'])

        # Flatten sorted blocks and reconstruct plain text
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
    General-Purpose, Document-Agnostic Medical OCR Engine.
    Accepts arbitrary document images/pages without hardcoded category logic.
    Performs text region detection, modular region classification, hybrid model routing,
    reading-order reconstruction, and structured plain-text formatting.
    """
    def __init__(self, use_gpu: bool = False):
        self.use_gpu = use_gpu
        self.classifier = RegionClassifier()
        self.rebuilder = ReadingOrderRebuilder()
        self._rapid_ocr = None
        self._paddle_ocr = None
        self._init_models()

    def _init_models(self):
        try:
            from rapidocr_onnxruntime import RapidOCR
            self._rapid_ocr = RapidOCR()
            logger.info('RapidOCR (ONNX) initialized successfully')
        except Exception as e:
            logger.warning(f'RapidOCR not loaded: {e}')

        try:
            from paddleocr import PaddleOCR
            self._paddle_ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False, use_gpu=self.use_gpu)
            logger.info('PaddleOCR initialized successfully')
        except Exception:
            pass

    def detect_regions(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Document-agnostic text region and contour detection using gradient morphology.
        """
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
        Processes an arbitrary document page:
        1. Runs RapidOCR (ONNX) or PaddleOCR for live text detection and recognition.
        2. Classifies each region (printed vs handwritten).
        3. Rebuilds 2D reading order.
        4. Returns structured blocks + reconstructed plain text (raw_text).
        """
        h_img, w_img = image.shape[:2]
        raw_blocks = []

        # 1. Primary: RapidOCR ONNX Engine (Real local inference on live uploaded pixels)
        if self._rapid_ocr is not None:
            try:
                ocr_results, elapse = self._rapid_ocr(image)
                if ocr_results:
                    for idx, item in enumerate(ocr_results):
                        box, text, score = item[0], item[1], float(item[2])
                        xs = [int(p[0]) for p in box]
                        ys = [int(p[1]) for p in box]
                        xmin, xmax = max(0, min(xs)), min(w_img, max(xs))
                        ymin, ymax = max(0, min(ys)), min(h_img, max(ys))
                        crop = image[ymin:ymax, xmin:xmax]
                        region_type = self.classifier.classify(crop)
                        status = self._get_status(score)
                        raw_blocks.append({
                            'id': f'block_{idx + 1}',
                            'text': text,
                            'confidence': round(score, 4),
                            'source': region_type,
                            'bbox': [xmin, ymin, xmax, ymax],
                            'status': status
                        })
            except Exception as e:
                logger.error(f'RapidOCR execution failed: {e}')

        # 2. Secondary: PaddleOCR if available
        if not raw_blocks and self._paddle_ocr is not None:
            try:
                results = self._paddle_ocr.ocr(image, cls=True)
                if results and len(results) > 0 and results[0] is not None:
                    for idx, line in enumerate(results[0]):
                        box = line[0]
                        text, conf = line[1][0], float(line[1][1])
                        xs = [int(p[0]) for p in box]
                        ys = [int(p[1]) for p in box]
                        xmin, xmax = max(0, min(xs)), min(w_img, max(xs))
                        ymin, ymax = max(0, min(ys)), min(h_img, max(ys))
                        crop = image[ymin:ymax, xmin:xmax]
                        region_type = self.classifier.classify(crop)
                        status = self._get_status(conf)
                        raw_blocks.append({
                            'id': f'block_{idx + 1}',
                            'text': text,
                            'confidence': round(conf, 4),
                            'source': region_type,
                            'bbox': [xmin, ymin, xmax, ymax],
                            'status': status
                        })
            except Exception as e:
                logger.error(f'PaddleOCR execution failed: {e}')

        # 3. Geometric Contour Detection Fallback
        if not raw_blocks:
            detected_regions = self.detect_regions(image)
            for idx, r in enumerate(detected_regions):
                xmin, ymin, xmax, ymax = r['bbox']
                crop = r['crop']
                region_type = self.classifier.classify(crop)
                raw_blocks.append({
                    'id': f'block_{idx + 1}',
                    'text': f'[Detected Text Region {idx + 1}]',
                    'confidence': 0.70,
                    'source': region_type,
                    'bbox': [xmin, ymin, xmax, ymax],
                    'status': 'REVIEW_REQUIRED'
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
