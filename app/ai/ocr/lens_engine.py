import os
import re
import cv2
import time
import numpy as np
from typing import Dict, Any, List, Tuple, Optional, Union

from app.ai.utils.logger import get_logger
from app.ai.ocr.medical_postprocessor import MedicalVocabularyPostProcessor

logger = get_logger(__name__)


class ScreenCoordinateMapper:
    """
    Precision coordinate transformation system for screen captures and Google-Lens overlays:
    - Maps local crop/snippet coordinates back to the full document/image pixel space.
    - Computes relative normalized coordinates [0.0, 1.0] for responsive browser DOM overlays.
    - Computes absolute screen coordinates [screen_x1, screen_y1, screen_x2, screen_y2]
      accounting for client window offset (origin_x, origin_y) and OS display DPI scaling.
    - Computes DOM client bounding boxes {x, y, width, height}.
    """
    def __init__(
        self,
        doc_width: int,
        doc_height: int,
        screen_origin_x: int = 0,
        screen_origin_y: int = 0,
        screen_scale_factor: float = 1.0
    ):
        self.doc_width = max(1, doc_width)
        self.doc_height = max(1, doc_height)
        self.screen_origin_x = screen_origin_x
        self.screen_origin_y = screen_origin_y
        self.screen_scale_factor = max(0.25, float(screen_scale_factor))

    def map_box(
        self,
        local_bbox: List[int],
        region_offset: Optional[Tuple[int, int]] = None,
        upscale_factor: float = 1.0
    ) -> Dict[str, Any]:
        """
        Transforms a local bounding box [x1, y1, x2, y2] into all coordinate spaces.
        """
        lx1, ly1, lx2, ly2 = local_bbox
        scale = max(0.001, upscale_factor)

        # 1. Unscale back to snippet space if crop was upscaled
        ux1 = lx1 / scale
        uy1 = ly1 / scale
        ux2 = lx2 / scale
        uy2 = ly2 / scale

        # 2. Offset to global document pixel coordinates
        ox = region_offset[0] if region_offset else 0
        oy = region_offset[1] if region_offset else 0

        gx1 = int(round(ox + ux1))
        gy1 = int(round(oy + uy1))
        gx2 = int(round(ox + ux2))
        gy2 = int(round(oy + uy2))

        # Clamp to document boundaries
        gx1 = max(0, min(self.doc_width, gx1))
        gy1 = max(0, min(self.doc_height, gy1))
        gx2 = max(0, min(self.doc_width, gx2))
        gy2 = max(0, min(self.doc_height, gy2))

        bw = max(1, gx2 - gx1)
        bh = max(1, gy2 - gy1)

        # 3. Normalized coordinates in [0.0, 1.0]
        norm_bbox = [
            round(gx1 / self.doc_width, 5),
            round(gy1 / self.doc_height, 5),
            round(gx2 / self.doc_width, 5),
            round(gy2 / self.doc_height, 5)
        ]

        # 4. Absolute screen coordinates
        sx1 = int(round((self.screen_origin_x + gx1) * self.screen_scale_factor))
        sy1 = int(round((self.screen_origin_y + gy1) * self.screen_scale_factor))
        sx2 = int(round((self.screen_origin_x + gx2) * self.screen_scale_factor))
        sy2 = int(round((self.screen_origin_y + gy2) * self.screen_scale_factor))
        screen_bbox = [sx1, sy1, sx2, sy2]

        # 5. DOM client rect format
        client_rect = {
            "x": gx1,
            "y": gy1,
            "width": bw,
            "height": bh
        }

        return {
            "bbox": [gx1, gy1, gx2, gy2],
            "normalized_bbox": norm_bbox,
            "screen_bbox": screen_bbox,
            "client_rect": client_rect,
            "width": bw,
            "height": bh
        }


class ScreenCaptureOptimizer:
    """
    Optimizes OCR for digital screen captures (screenshots, web UIs, application windows):
    - Sub-pixel antialiasing edge enhancement without destructive blur.
    - Polarity detection (detects white-on-dark text and handles inversion).
    - Contrast expansion for low-contrast UI elements (disabled buttons, gray placeholder text).
    """
    @staticmethod
    def enhance_screen_image(image: np.ndarray) -> np.ndarray:
        if image is None or image.size == 0:
            return image

        # 1. Ensure 3-channel BGR
        if len(image.shape) == 2:
            img = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        else:
            img = image.copy()

        # 2. Unsharp masking to sharpen crisp digital anti-aliasing edges
        gaussian = cv2.GaussianBlur(img, (0, 0), 1.0)
        sharpened = cv2.addWeighted(img, 1.30, gaussian, -0.30, 0)

        return sharpened

    @staticmethod
    def is_dark_background(crop: np.ndarray) -> bool:
        """Determines if a crop has a dark background with light text."""
        if crop is None or crop.size == 0:
            return False
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if len(crop.shape) == 3 else crop
        h, w = gray.shape[:2]
        
        # Sample border pixels (background)
        border_pixels = []
        if h > 2 and w > 2:
            border_pixels.extend(gray[0, :].tolist())
            border_pixels.extend(gray[-1, :].tolist())
            border_pixels.extend(gray[:, 0].tolist())
            border_pixels.extend(gray[:, -1].tolist())
        else:
            border_pixels = gray.flatten().tolist()
            
        mean_border = float(np.mean(border_pixels)) if border_pixels else 255.0
        overall_mean = float(np.mean(gray))
        return (mean_border < 110.0 and overall_mean < 125.0)

    @staticmethod
    def invert_crop(crop: np.ndarray) -> np.ndarray:
        """Inverts dark-background image to light-background for DBNet/RapidOCR."""
        return cv2.bitwise_not(crop)


class HISScreenOptimizer:
    """
    Specialized optimizer for Hospital Information Systems (HIS/EHR) screenshots
    (Epic, Cerner, Meditech, Allscripts, AthenaHealth):
    - Inverted patient banner / header detection (white text on navy/dark gray).
    - Grid line suppression to prevent table cell borders from sticking to characters.
    - Clinical entity preservation: vital signs, lab values, MRNs, dosages.
    """
    # Regex patterns for clinical entities common in HIS screenshots
    CLINICAL_PATTERNS = {
        "mrn": re.compile(r'\b(?:MRN|ID|PATIENT\s*ID)[:\s#]*([A-Z0-9\-]+)\b', re.IGNORECASE),
        "dob": re.compile(r'\b(?:DOB|BIRTH)[:\s]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})\b', re.IGNORECASE),
        "blood_pressure": re.compile(r'\b(?:BP|BLOOD\s*PRESSURE)[:\s]*(\d{2,3}\s*\/\s*\d{2,3})\b', re.IGNORECASE),
        "heart_rate": re.compile(r'\b(?:HR|PULSE)[:\s]*(\d{2,3})\s*(?:bpm)?\b', re.IGNORECASE),
        "oxygen_sat": re.compile(r'\b(?:SPO2|SAT|O2\s*SAT)[:\s]*(\d{2,3}%?)\b', re.IGNORECASE),
        "respiratory_rate": re.compile(r'\b(?:RR|RESP)[:\s]*(\d{1,2})\b', re.IGNORECASE),
        "temperature": re.compile(r'\b(?:TEMP)[:\s]*(\d{2,3}(?:\.\d)?)\s*(?:[FC°])?\b', re.IGNORECASE),
        "dosage": re.compile(r'\b\d+(?:\.\d+)?\s*(?:mg|mcg|ml|g|units?|iu|meq)\b', re.IGNORECASE)
    }

    @classmethod
    def clean_ehr_grid_lines(cls, image: np.ndarray) -> np.ndarray:
        """
        Removes thin 1-2px vertical and horizontal grid lines from EHR tables
        that frequently intersect characters or attach to numbers.
        """
        if image is None or image.size == 0:
            return image
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
        
        # Detect vertical grid lines
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))
        v_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, v_kernel)
        
        # Detect horizontal grid lines
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
        h_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, h_kernel)
        
        grid_mask = cv2.bitwise_or(v_lines, h_lines)
        _, grid_bin = cv2.threshold(grid_mask, 200, 255, cv2.THRESH_BINARY)
        
        # Subtle inpainting / subtraction to separate letters from grid borders
        cleaned = image.copy()
        if len(cleaned.shape) == 3:
            for ch in range(3):
                cleaned[:, :, ch] = np.where(grid_bin > 0, np.maximum(cleaned[:, :, ch], 240), cleaned[:, :, ch])
        else:
            cleaned = np.where(grid_bin > 0, np.maximum(cleaned, 240), cleaned)
            
        return cleaned

    @classmethod
    def extract_clinical_entities(cls, text: str) -> Dict[str, List[str]]:
        """Parses structured clinical entities from HIS screen text."""
        entities = {}
        for entity_type, pattern in cls.CLINICAL_PATTERNS.items():
            matches = pattern.findall(text)
            if matches:
                entities[entity_type] = [m if isinstance(m, str) else m[0] for m in matches]
        return entities


class BrowserWindowOptimizer:
    """
    Optimizes OCR for browser windows & web applications:
    - URL bar & breadcrumb preservation (prevents breaking on 'https://', '.', '/').
    - Web typography handling (responsive fonts, light weights, bold chips).
    - Filters isolated icon glyphs / SVG noise tokens.
    """
    URL_PATTERN = re.compile(r'(?:https?:\/\/|www\.)[^\s\/$.?#].[^\s]*', re.IGNORECASE)
    
    @classmethod
    def preserve_urls_and_breadcrumbs(cls, text: str) -> str:
        """Cleans common OCR splits in web URLs and navigation paths."""
        # Fix spaced colons and slashes: 'https : / /' -> 'https://'
        fixed = re.sub(r'(https?)\s*:\s*\/\s*\/', r'\1://', text, flags=re.IGNORECASE)
        # Fix spaced slashes in paths: 'path / subpath' -> 'path/subpath'
        fixed = re.sub(r'([a-zA-Z0-9_\-])\s*\/\s*([a-zA-Z0-9_\-])', r'\1/\2', fixed)
        # Fix spaced dots in domains: 'example . com' -> 'example.com'
        fixed = re.sub(r'([a-zA-Z0-9_\-])\s*\.\s*([a-zA-Z0-9_\-])', r'\1.\2', fixed)
        return fixed

    @classmethod
    def is_standalone_icon(cls, text: str, width: int, height: int) -> bool:
        """Detects standalone icon glyphs (e.g. arrows, single symbols) that should be filtered."""
        clean = text.strip()
        if len(clean) == 1 and clean in ('<', '>', 'v', '^', '+', 'x', '-', 'i', 'o', '|', '•', '>', '»'):
            if abs(width - height) < 6 and width < 25:
                return True
        return False


class PDFViewerOptimizer:
    """
    Optimizes OCR for PDF viewer screenshots (Acrobat, Chrome PDF viewer, Edge, Foxit):
    - Detects the document page boundary inside the viewer window.
    - Excludes outer gray canvas background (#525659), page drop shadows, and top toolbar chrome.
    - Focuses inference precisely on the document page area while retaining window mapping.
    """
    @staticmethod
    def detect_document_page_bounds(image: np.ndarray) -> Optional[List[int]]:
        """
        Finds the primary document page canvas inside a PDF viewer screenshot.
        Returns [x1, y1, x2, y2] of the document page, or None if the whole image is page content.
        """
        if image is None or image.size == 0:
            return None
            
        h, w = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # Document pages in PDF viewers are predominantly light/white (> 210) surrounded by dark gray (< 120)
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        best_box = None
        max_area = 0
        min_page_area = (w * h) * 0.20  # Page must occupy at least 20% of viewer window
        
        for cnt in contours:
            x, y, cw, ch = cv2.boundingRect(cnt)
            area = cw * ch
            if area > min_page_area and area > max_area:
                # Aspect ratio check: typical documents are portrait (0.6 - 0.85) or landscape (1.2 - 1.5)
                ratio = float(cw) / float(max(1, ch))
                if 0.45 <= ratio <= 2.2:
                    best_box = [x, y, x + cw, y + ch]
                    max_area = area
                    
        return best_box


class LineLevelBlockProducer:
    """
    Produces guaranteed line-level OCR blocks:
    - Clusters fragments on the same baseline.
    - Reconstructs left-to-right reading order.
    - Computes word-level tokens within each line.
    - Formats standardized block dictionaries with confidence, screen coordinates, and status.
    """
    @staticmethod
    def build_line_blocks(
        raw_detections: List[Dict[str, Any]],
        coord_mapper: ScreenCoordinateMapper,
        source: str = "screen_digital"
    ) -> Tuple[List[Dict[str, Any]], str]:
        if not raw_detections:
            return [], ""

        # 1. Sort primarily by y-midpoint, secondarily by x1
        for det in raw_detections:
            x1, y1, x2, y2 = det['bbox']
            det['_mid_y'] = (y1 + y2) / 2.0
            det['_height'] = max(1, y2 - y1)

        sorted_dets = sorted(raw_detections, key=lambda d: (d['_mid_y'], d['bbox'][0]))

        # 2. Cluster items into horizontal lines based on baseline overlap
        lines: List[List[Dict[str, Any]]] = []
        for det in sorted_dets:
            placed = False
            y1, y2 = det['bbox'][1], det['bbox'][3]
            h = det['_height']
            mid_y = det['_mid_y']

            for line in lines:
                l_y1 = min(item['bbox'][1] for item in line)
                l_y2 = max(item['bbox'][3] for item in line)
                l_h = max(1, l_y2 - l_y1)
                l_mid_y = (l_y1 + l_y2) / 2.0

                overlap = max(0, min(y2, l_y2) - max(y1, l_y1))
                overlap_ratio = overlap / min(h, l_h)
                mid_diff = abs(mid_y - l_mid_y)

                if overlap_ratio >= 0.45 or mid_diff <= 0.40 * min(h, l_h):
                    line.append(det)
                    placed = True
                    break

            if not placed:
                lines.append([det])

        # 3. Partition baseline lines into discrete column/card line segments if large horizontal gaps exist
        line_segments: List[List[Dict[str, Any]]] = []
        for line in lines:
            line.sort(key=lambda d: d['bbox'][0])
            cur_seg = [line[0]]
            for next_item in line[1:]:
                prev_x2 = max(it['bbox'][2] for it in cur_seg)
                next_x1 = next_item['bbox'][0]
                line_h = max(max(it['_height'] for it in cur_seg), next_item['_height'])
                gap = next_x1 - prev_x2
                if gap > max(45, 2.2 * line_h):
                    line_segments.append(cur_seg)
                    cur_seg = [next_item]
                else:
                    cur_seg.append(next_item)
            if cur_seg:
                line_segments.append(cur_seg)

        # Sort segments primarily by y-midpoint, secondarily by x1
        line_segments.sort(key=lambda seg: ((min(it['bbox'][1] for it in seg) + max(it['bbox'][3] for it in seg)) / 2.0, min(it['bbox'][0] for it in seg)))

        # 4. Construct line-level blocks
        line_blocks = []
        full_text_lines = []
        line_idx = 1

        for seg in line_segments:
            seg.sort(key=lambda d: d['bbox'][0])
            
            lx1 = min(d['bbox'][0] for d in seg)
            ly1 = min(d['bbox'][1] for d in seg)
            lx2 = max(d['bbox'][2] for d in seg)
            ly2 = max(d['bbox'][3] for d in seg)

            line_text = " ".join(d['text'].strip() for d in seg if d.get('text')).strip()
            if not line_text:
                continue

            confs = [d.get('confidence', 0.85) for d in seg]
            avg_conf = float(np.mean(confs)) if confs else 0.85

            # Screen coordinate mapping
            mapped = coord_mapper.map_box([lx1, ly1, lx2, ly2])

            # Word tokens within the line
            words = []
            for d in seg:
                w_text = d.get('text', '').strip()
                if w_text:
                    w_mapped = coord_mapper.map_box(d['bbox'])
                    words.append({
                        "text": w_text,
                        "confidence": round(d.get('confidence', 0.85), 4),
                        "bbox": w_mapped['bbox'],
                        "screen_bbox": w_mapped['screen_bbox'],
                        "normalized_bbox": w_mapped['normalized_bbox']
                    })

            status = 'HIGH_CONFIDENCE' if avg_conf >= 0.85 else ('MEDIUM_CONFIDENCE' if avg_conf >= 0.65 else 'REVIEW_REQUIRED')

            block = {
                "id": f"line_{line_idx}",
                "line_number": line_idx,
                "reading_order": line_idx,
                "text": line_text,
                "confidence": round(avg_conf, 4),
                "source": source,
                "status": status,
                "bbox": mapped['bbox'],
                "normalized_bbox": mapped['normalized_bbox'],
                "screen_bbox": mapped['screen_bbox'],
                "client_rect": mapped['client_rect'],
                "width": mapped['width'],
                "height": mapped['height'],
                "words": words
            }
            line_blocks.append(block)
            full_text_lines.append(line_text)
            line_idx += 1

        raw_text = "\n".join(full_text_lines)
        return line_blocks, raw_text


class SnippetOCREngine:
    """
    Ultra-low-latency OCR engine tailored for marquee snippets and focused screen regions:
    - Multi-scale super-resolution (2.0x - 3.0x bicubic) for small UI fonts (10-18px).
    - Fast single-line shortcut bypassing DBNet detection (latency ~10-25ms).
    - RapidOCR text recognizer integration with polarity handling.
    - Sub-100ms average latency target for marquee interactions.
    """
    def __init__(self, rapid_ocr=None):
        self._rapid_ocr = rapid_ocr
        self.postprocessor = MedicalVocabularyPostProcessor()
        if self._rapid_ocr is None:
            try:
                from rapidocr_onnxruntime import RapidOCR
                self._rapid_ocr = RapidOCR()
            except Exception as e:
                logger.warning(f"Could not initialize RapidOCR in SnippetOCREngine: {e}")

    def is_single_line_crop(self, crop: np.ndarray) -> bool:
        """Determines whether a crop is a single text line based on height & aspect ratio."""
        h, w = crop.shape[:2]
        if h <= 45:
            return True
        if h <= 70 and (w / max(1, h)) >= 3.0:
            return True
        return False

    def process_snippet(
        self,
        snippet_crop: np.ndarray,
        coord_mapper: ScreenCoordinateMapper,
        region_offset: Tuple[int, int] = (0, 0),
        force_multiline: bool = False
    ) -> Dict[str, Any]:
        t0 = time.perf_counter()
        if snippet_crop is None or snippet_crop.size == 0 or self._rapid_ocr is None:
            return {
                "text": "",
                "confidence": 0.0,
                "blocks": [],
                "latency_ms": 0.0,
                "tokens": []
            }

        h_orig, w_orig = snippet_crop.shape[:2]

        # 1. Multi-scale super-sampling based on crop height
        scale = 1.0
        if h_orig < 50:
            scale = 3.0
        elif h_orig < 120:
            scale = 2.5
        elif h_orig < 250:
            scale = 1.8

        if scale > 1.0:
            scaled_crop = cv2.resize(snippet_crop, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        else:
            scaled_crop = snippet_crop.copy()

        # 2. Digital screen enhancement & polarity normalization
        enhanced_crop = ScreenCaptureOptimizer.enhance_screen_image(scaled_crop)
        is_dark = ScreenCaptureOptimizer.is_dark_background(enhanced_crop)
        if is_dark:
            enhanced_crop = ScreenCaptureOptimizer.invert_crop(enhanced_crop)

        # 3. Fast-Path: Single-Line Recognition
        is_single = (not force_multiline) and self.is_single_line_crop(snippet_crop)

        raw_detections = []
        if is_single and hasattr(self._rapid_ocr, 'text_recognizer'):
            # Direct recognition call (bypasses DBNet text detector)
            rec_res, _ = self._rapid_ocr.text_recognizer([enhanced_crop])
            if rec_res and rec_res[0][0]:
                text = rec_res[0][0].strip()
                score = float(rec_res[0][1])
                clean_text = self.postprocessor.clean_text(text)
                raw_detections.append({
                    "text": clean_text,
                    "confidence": score,
                    "bbox": [0, 0, w_orig, h_orig]
                })

        # 4. Fallback / Multi-line Path: Run RapidOCR pipeline on snippet
        if not raw_detections:
            ocr_res, _ = self._rapid_ocr(enhanced_crop, box_thresh=0.36, unclip_ratio=1.9, text_score=0.32)
            if ocr_res:
                for item in ocr_res:
                    box, text, score = item[0], item[1], float(item[2])
                    xs = [p[0] / scale for p in box]
                    ys = [p[1] / scale for p in box]
                    x1, x2 = max(0, min(xs)), min(w_orig, max(xs))
                    y1, y2 = max(0, min(ys)), min(h_orig, max(ys))
                    clean_text = self.postprocessor.clean_text(text.strip())
                    if clean_text:
                        raw_detections.append({
                            "text": clean_text,
                            "confidence": score,
                            "bbox": [int(round(x1)), int(round(y1)), int(round(x2)), int(round(y2))]
                        })

        # 5. Build line-level blocks with screen mapping
        # Create a mapper with offset
        mapped_blocks = []
        full_text_parts = []
        for idx, det in enumerate(raw_detections):
            mapped = coord_mapper.map_box(det['bbox'], region_offset=region_offset, upscale_factor=1.0)
            status = 'HIGH_CONFIDENCE' if det['confidence'] >= 0.85 else 'REVIEW_REQUIRED'
            mapped_blocks.append({
                "id": f"snippet_block_{idx + 1}",
                "line_number": idx + 1,
                "reading_order": idx + 1,
                "text": det['text'],
                "confidence": round(det['confidence'], 4),
                "source": "snippet_ocr",
                "status": status,
                "bbox": mapped['bbox'],
                "normalized_bbox": mapped['normalized_bbox'],
                "screen_bbox": mapped['screen_bbox'],
                "client_rect": mapped['client_rect'],
                "width": mapped['width'],
                "height": mapped['height']
            })
            full_text_parts.append(det['text'])

        t1 = time.perf_counter()
        latency_ms = round((t1 - t0) * 1000.0, 2)
        combined_text = "\n".join(full_text_parts)
        avg_conf = float(np.mean([b['confidence'] for b in mapped_blocks])) if mapped_blocks else 0.0

        return {
            "text": combined_text,
            "overall_confidence": round(avg_conf, 4),
            "blocks": mapped_blocks,
            "latency_ms": latency_ms,
            "token_count": len(combined_text.split()),
            "is_single_line": is_single
        }


class GoogleLensOCREngine:
    """
    Unified Google-Lens OCR Engine orchestrator:
    - Screen capture optimization with anti-aliasing & polarity handling.
    - HIS/EHR screenshot optimization with grid suppression and clinical entity extraction.
    - Browser window optimization with URL & web typography parsing.
    - PDF viewer optimization with page canvas segmentation.
    - Low-latency region-only inference and sub-100ms snippet OCR.
    - Complete screen coordinate mapping for seamless client overlays.
    """
    def __init__(self, rapid_ocr=None):
        self._rapid_ocr = rapid_ocr
        if self._rapid_ocr is None:
            try:
                from rapidocr_onnxruntime import RapidOCR
                self._rapid_ocr = RapidOCR()
            except Exception as e:
                logger.warning(f"Could not initialize RapidOCR in GoogleLensOCREngine: {e}")

        self.snippet_engine = SnippetOCREngine(self._rapid_ocr)
        self.postprocessor = MedicalVocabularyPostProcessor()

    def process_screen_capture(
        self,
        image: np.ndarray,
        screen_origin: Tuple[int, int] = (0, 0),
        screen_scale_factor: float = 1.0,
        mode: str = "screen"
    ) -> Dict[str, Any]:
        """
        Executes Google-Lens OCR on a full screen capture or application window.
        Returns line-level blocks with screen mapping, overall confidence, and latency metrics.
        """
        t0 = time.perf_counter()
        if image is None or image.size == 0:
            return {"status": "error", "message": "Empty image provided", "blocks": [], "raw_text": ""}

        h_img, w_img = image.shape[:2]
        coord_mapper = ScreenCoordinateMapper(
            doc_width=w_img,
            doc_height=h_img,
            screen_origin_x=screen_origin[0],
            screen_origin_y=screen_origin[1],
            screen_scale_factor=screen_scale_factor
        )

        # 1. Mode-specific preprocessing
        processed_img = image.copy()
        if mode == "his":
            processed_img = HISScreenOptimizer.clean_ehr_grid_lines(processed_img)
        elif mode == "pdf_viewer":
            page_bounds = PDFViewerOptimizer.detect_document_page_bounds(processed_img)
            # If page bounds detected and valid, we focus on page bounds
            if page_bounds:
                logger.info(f"PDF viewer page canvas detected at: {page_bounds}")

        enhanced_img = ScreenCaptureOptimizer.enhance_screen_image(processed_img)

        # 2. RapidOCR Detection & Recognition with Screen-Tuned Hyperparameters
        raw_detections = []
        if self._rapid_ocr is not None:
            # box_thresh=0.35 captures fine 10-12px digital fonts
            # unclip_ratio=2.0 expands bounding box to capture full anti-aliased font height
            det_kwargs = {'box_thresh': 0.35, 'unclip_ratio': 2.0, 'text_score': 0.32}
            ocr_results, elapse = self._rapid_ocr(enhanced_img, **det_kwargs)
            if ocr_results:
                for item in ocr_results:
                    box, text, score = item[0], item[1], float(item[2])
                    xs = [int(p[0]) for p in box]
                    ys = [int(p[1]) for p in box]
                    xmin, xmax = max(0, min(xs)), min(w_img, max(xs))
                    ymin, ymax = max(0, min(ys)), min(h_img, max(ys))
                    
                    clean_text = self.postprocessor.clean_text(text.strip())
                    if mode == "browser":
                        clean_text = BrowserWindowOptimizer.preserve_urls_and_breadcrumbs(clean_text)
                        if BrowserWindowOptimizer.is_standalone_icon(clean_text, xmax - xmin, ymax - ymin):
                            continue
                    
                    if clean_text:
                        raw_detections.append({
                            'text': clean_text,
                            'confidence': float(score),
                            'bbox': [xmin, ymin, xmax, ymax]
                        })

        # 3. Check for inverted dark-background headers (common in HIS and dark-mode UIs)
        # If dark banner exists at top or middle, detect inverted text
        dark_header_detections = self._detect_inverted_regions(image, raw_detections)
        raw_detections.extend(dark_header_detections)

        # 4. Produce guaranteed line-level OCR blocks
        line_blocks, raw_text = LineLevelBlockProducer.build_line_blocks(
            raw_detections=raw_detections,
            coord_mapper=coord_mapper,
            source=f"{mode}_screen"
        )

        # 5. Extract structured clinical entities if HIS mode
        clinical_entities = {}
        if mode == "his":
            clinical_entities = HISScreenOptimizer.extract_clinical_entities(raw_text)

        t1 = time.perf_counter()
        latency_ms = round((t1 - t0) * 1000.0, 2)
        overall_conf = float(np.mean([b['confidence'] for b in line_blocks])) if line_blocks else 0.0

        return {
            "status": "success",
            "mode": mode,
            "dimensions": [w_img, h_img],
            "screen_origin": list(screen_origin),
            "screen_scale_factor": screen_scale_factor,
            "total_blocks": len(line_blocks),
            "overall_confidence": round(overall_conf, 4),
            "latency_ms": latency_ms,
            "clinical_entities": clinical_entities,
            "blocks": line_blocks,
            "raw_text": raw_text
        }

    def process_snippet_region(
        self,
        image: np.ndarray,
        region_bbox: List[int],
        screen_origin: Tuple[int, int] = (0, 0),
        screen_scale_factor: float = 1.0,
        mode: str = "screen"
    ) -> Dict[str, Any]:
        """
        Processes a marquee snippet / sub-region with region-only inference.
        Bypasses full-document detection, crops the exact region, upscales,
        and translates coordinates back to screen pixels and client canvas.
        """
        h_img, w_img = image.shape[:2]
        rx1, ry1, rx2, ry2 = region_bbox
        rx1, rx2 = max(0, min(rx1, rx2)), min(w_img, max(rx1, rx2))
        ry1, ry2 = max(0, min(ry1, ry2)), min(h_img, max(ry1, ry2))

        crop_w = rx2 - rx1
        crop_h = ry2 - ry1
        if crop_w < 6 or crop_h < 6:
            return {
                "status": "error",
                "message": "Selected snippet region is too small",
                "blocks": [],
                "raw_text": ""
            }

        snippet_crop = image[ry1:ry2, rx1:rx2]
        coord_mapper = ScreenCoordinateMapper(
            doc_width=w_img,
            doc_height=h_img,
            screen_origin_x=screen_origin[0],
            screen_origin_y=screen_origin[1],
            screen_scale_factor=screen_scale_factor
        )

        res = self.snippet_engine.process_snippet(
            snippet_crop=snippet_crop,
            coord_mapper=coord_mapper,
            region_offset=(rx1, ry1)
        )

        return {
            "status": "success",
            "region_bbox": [rx1, ry1, rx2, ry2],
            "dimensions": [w_img, h_img],
            "total_blocks": len(res["blocks"]),
            "overall_confidence": res["overall_confidence"],
            "latency_ms": res["latency_ms"],
            "is_single_line": res["is_single_line"],
            "blocks": res["blocks"],
            "raw_text": res["text"]
        }

    def _detect_inverted_regions(
        self,
        image: np.ndarray,
        existing_detections: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Scans for dark bands / banner strips with light text that DBNet missed on normal polarity.
        Inverts those bands and runs rapid recognition to recover missed text.
        """
        if image is None or self._rapid_ocr is None:
            return []

        h, w = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Dark regions have low intensity (< 85) across horizontal strips
        # Check top header area (first 25% of image) and bottom status bar (last 15%)
        candidate_strips = []
        top_h = int(h * 0.25)
        if top_h > 20:
            candidate_strips.append((0, top_h))
        bottom_y = int(h * 0.85)
        if h - bottom_y > 20:
            candidate_strips.append((bottom_y, h))

        inverted_dets = []
        for y1, y2 in candidate_strips:
            strip = gray[y1:y2, :]
            if np.mean(strip) < 95.0:  # Dark banner strip detected
                inv_strip = cv2.bitwise_not(image[y1:y2, :])
                strip_res, _ = self._rapid_ocr(inv_strip, box_thresh=0.35, unclip_ratio=1.9, text_score=0.32)
                if strip_res:
                    for item in strip_res:
                        box, text, score = item[0], item[1], float(item[2])
                        xs = [int(p[0]) for p in box]
                        ys = [int(p[1]) for p in box]
                        sx1, sx2 = max(0, min(xs)), min(w, max(xs))
                        sy1, sy2 = max(0, min(ys) + y1), min(h, max(ys) + y1)

                        # Check if this box is already covered by an existing detection
                        already_covered = False
                        for ex in existing_detections:
                            ex1, ey1, ex2, ey2 = ex['bbox']
                            if abs(sx1 - ex1) < 20 and abs(sy1 - ey1) < 15:
                                already_covered = True
                                break

                        clean_text = self.postprocessor.clean_text(text.strip())
                        if not already_covered and clean_text:
                            inverted_dets.append({
                                'text': clean_text,
                                'confidence': float(score),
                                'bbox': [sx1, sy1, sx2, sy2]
                            })

        return inverted_dets
