import os
import re
import cv2
import time
import json
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from app.ai.utils.logger import get_logger
from app.ai.ocr.medical_postprocessor import MedicalVocabularyPostProcessor
from app.ai.layout.layout_intelligence import LayoutIntelligenceEngine
from app.ai.preprocessing.preprocessing_pipeline import run_screen_preprocessing, run_preprocessing_pipeline
from app.ai.preprocessing.enhance import enhance_small_or_lowres_text

logger = get_logger(__name__)

class RegionClassifier:
    """
    Multi-Feature Printed vs. Handwritten Region Classifier:
    - Baseline drift & vertical variance (h_std, b_std)
    - Stroke curvature & perimeter-to-area ratio
    - Character stroke thickness regularity
    - Primary detector confidence & glyph continuity
    Returns full classification metadata and provenance.
    """
    def __init__(self, variance_threshold: float = 0.40):
        self.variance_threshold = variance_threshold

    def classify_with_provenance(
        self,
        crop: np.ndarray,
        base_score: float = 1.0,
        rapid_text: str = ""
    ) -> Dict[str, Any]:
        if crop is None or crop.size == 0:
            return {
                "region_type": "printed",
                "confidence": 0.5,
                "reasons": ["empty_crop_default"],
                "features": {}
            }

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if len(crop.shape) == 3 else crop
        h, w = gray.shape[:2]
        if h < 10 or w < 15:
            return {
                "region_type": "printed",
                "confidence": 0.6,
                "reasons": ["micro_crop_default"],
                "features": {"height": h, "width": w}
            }

        # 1. Binarize crop to find stroke components
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return {
                "region_type": "printed",
                "confidence": 0.55,
                "reasons": ["no_contours_found"],
                "features": {}
            }

        # 2. Analyze component heights, vertical baselines and stroke curvature
        heights = []
        bottoms = []
        curvatures = []
        for c in contours:
            cx, cy, cw, ch = cv2.boundingRect(c)
            area = cv2.contourArea(c)
            peri = cv2.arcLength(c, True)
            if ch > h * 0.20 and cw > 2:
                heights.append(ch)
                bottoms.append(cy + ch)
                if area > 10 and peri > 0:
                    curvatures.append(float(peri * peri / (4.0 * np.pi * area)))

        if len(heights) < 3:
            h_std = 0.0
            b_std = 0.0
        else:
            h_std = float(np.std(heights)) / (float(np.mean(heights)) + 1e-5)
            b_std = float(np.std(bottoms)) / float(h)

        mean_curvature = float(np.mean(curvatures)) if curvatures else 1.0

        reasons = []
        is_handwritten = False

        if base_score < 0.60 and (h_std > 0.28 or b_std > 0.09):
            is_handwritten = True
            reasons.append("low_detector_conf_with_baseline_drift")
        elif base_score < 0.75 and (h_std > 0.38 or b_std > 0.14):
            is_handwritten = True
            reasons.append("moderate_detector_conf_with_height_variance")
        elif h_std > 0.48 and b_std > 0.18:
            is_handwritten = True
            reasons.append("extreme_morphological_irregularity")
        elif mean_curvature > 4.5 and b_std > 0.12:
            is_handwritten = True
            reasons.append("high_stroke_curvature_and_wandering")

        if not is_handwritten:
            reasons.append("regular_typography_and_stable_baseline")

        conf = 0.85 if is_handwritten else (0.90 if base_score > 0.70 else 0.75)
        return {
            "region_type": "handwritten" if is_handwritten else "printed",
            "confidence": round(conf, 3),
            "reasons": reasons,
            "features": {
                "height_std": round(h_std, 3),
                "baseline_std": round(b_std, 3),
                "mean_curvature": round(mean_curvature, 2),
                "detector_score": round(base_score, 3)
            }
        }

    def classify(self, crop: np.ndarray, base_score: float = 1.0, rapid_text: str = "") -> str:
        return self.classify_with_provenance(crop, base_score, rapid_text)["region_type"]


class AntiHallucinationFilter:
    """
    Guardrail against autoregressive vision-language model hallucinations:
    - Corpus boilerplate (Wikipedia / Wikimedia phrases)
    - Alphabet loop sequences (e.g., 'a b c d e f g h')
    - Cyclical repeating n-grams
    - Severe character count disparity relative to bounding box width
    - Repetitive punctuation / trailing burst artifacts
    """
    BLACKLIST_PHRASES = [
        "what links here", "related changes", "upload file", "special pages",
        "permanent link", "page information", "cite this page", "wikidata item",
        "wikipedia", "wikimedia", "in the united states in the united states",
        "of the united states of the united", "the first time of the first time",
        "management anniversary", "cosmopolitanism formal holidays",
        "washington post", "new york times", "external links", "references categories"
    ]

    @classmethod
    def check_hallucination(cls, text: str, crop_w: int = 0) -> Tuple[bool, str, str]:
        """
        Returns (is_hallucination: bool, sanitized_text: str, trigger_reason: str).
        """
        if not text:
            return False, "", "empty"

        clean = text.strip()
        lower = clean.lower()

        # 1. Corpus blacklist
        for phrase in cls.BLACKLIST_PHRASES:
            if phrase in lower:
                return True, "", f"blacklisted_corpus_phrase: {phrase}"

        # 2. Alphabet sequence loops (e.g. 'a b c d e f g h')
        if re.search(r'(?:[a-z]\s+){4,}[a-z]', lower):
            return True, "", "alphabet_sequence_loop"

        # 3. Repeating 2-gram to 4-gram loops
        words = lower.split()
        if len(words) >= 6:
            for n in range(2, 5):
                for i in range(len(words) - 2 * n + 1):
                    if words[i:i+n] == words[i+n:i+2*n]:
                        clean_words = clean.split()
                        prefix = " ".join(clean_words[:i+n])
                        return True, prefix, f"repeating_{n}gram_loop"

        # 4. Extreme length disparity
        if crop_w > 0 and len(clean) > (crop_w / 4.2) + 12:
            return True, clean[:int(crop_w / 4.5)], "extreme_length_disparity"

        # 5. Sanitize trailing burst artifacts (e.g. ' . " 1 ) : I.m-O...')
        sanitized = re.sub(r'[\s\.\'\"\,\-\_\:\;0-9\(\)\/\\]{5,}$', '', clean).strip()
        if not sanitized and len(clean) > 8:
            return True, "", "symbol_burst_artifact"

        return False, sanitized if sanitized else clean, "passed"


class OCRErrorDetector:
    """
    Automated Diagnostic Engine for OCR Predictions:
    Identifies common OCR failure modes, digit/letter confusions, low-confidence regions,
    and medical domain anomalies.
    """
    def __init__(self, postprocessor: Optional[MedicalVocabularyPostProcessor] = None):
        self.postprocessor = postprocessor or MedicalVocabularyPostProcessor()

    def analyze(
        self,
        text: str,
        confidence: float,
        crop: np.ndarray,
        provenance: Dict[str, Any]
    ) -> Dict[str, Any]:
        flags = []
        disputed_tokens = []
        severity = "none"

        # 1. Low confidence alert
        if confidence < 0.60:
            flags.append("LOW_CONFIDENCE")
            severity = "medium" if confidence >= 0.40 else "high"

        # 2. Fallback occurred
        if provenance.get("fallback_occurred", False):
            flags.append("FALLBACK_TRIGGERED")
            if severity == "none":
                severity = "low"

        # 3. Digit-Letter Confusion Suspicions
        raw_pred = provenance.get("raw_prediction", text)
        if re.search(r'\b[0-9]*[lIOo][0-9]+\b', raw_pred):
            flags.append("DIGIT_LETTER_CONFUSION_SUSPECTED")
            disputed_tokens.extend(re.findall(r'\b[0-9]*[lIOo][0-9]+\b', raw_pred))
            severity = max(severity, "medium", key=lambda x: ["none", "low", "medium", "high"].index(x))

        if re.search(r'\b[Ss]00\s*(?:mg|ml)\b', raw_pred):
            flags.append("DOSAGE_DIGIT_S_FOR_5")
            disputed_tokens.append("S00 -> 500")

        # 4. Unusual Punctuation / Glyph Glitches
        if re.search(r'[\ufffd\u25a1\u53e3\?\*]{2,}', raw_pred):
            flags.append("UNRECOGNIZED_GLYPHS")
            if severity == "none":
                severity = "low"

        # 5. Aspect Ratio & Geometry Warning
        if crop is not None and crop.size > 0:
            h, w = crop.shape[:2]
            if h > w * 1.5 and len(text) > 3:
                flags.append("VERTICAL_ORIENTATION_ANOMALY")
            if h < 12:
                flags.append("EXTREME_LOW_RESOLUTION")

        # 6. Hallucination Mitigation Flag
        if provenance.get("hallucination_mitigated", False):
            flags.append("HALLUCINATION_MITIGATED")
            severity = max(severity, "medium", key=lambda x: ["none", "low", "medium", "high"].index(x))

        return {
            "has_errors": len(flags) > 0,
            "flags": flags,
            "severity": severity,
            "disputed_tokens": disputed_tokens
        }


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
        for line_num, line in enumerate(lines, 1):
            line_texts = []
            for b in line:
                clean_b = {k: v for k, v in b.items() if not k.startswith('_')}
                clean_b['id'] = f"block_{idx}"
                clean_b['reading_order'] = idx
                clean_b['line_number'] = line_num
                sorted_blocks.append(clean_b)
                idx += 1
                if b.get('text'):
                    line_texts.append(b['text'].strip())
            if line_texts:
                text_lines.append("  ".join(line_texts))

        raw_text = "\n".join(text_lines)
        return sorted_blocks, raw_text


class OCRDocumentReadingEngine:
    """
    OCR Document Reading System Hybrid Engine:
    - RapidOCR (ONNX) for detection & printed text recognition
    - TrOCR (VisionEncoderDecoder) for handwritten text recognition
    - Spatial line grouping & line-level crop recognition
    - MedicalVocabularyPostProcessor for medicine & dosage normalization
    - ReadingOrderRebuilder for 2D layout reading-order recovery
    """
    def __init__(self, use_gpu: bool = False):
        self.use_gpu = use_gpu
        self.classifier = RegionClassifier()
        self.rebuilder = ReadingOrderRebuilder()
        self.postprocessor = MedicalVocabularyPostProcessor()
        self.error_detector = OCRErrorDetector(self.postprocessor)
        self.layout_engine = LayoutIntelligenceEngine()
        self._rapid_ocr = None
        self._trocr_processor = None
        self._trocr_model = None
        self._htr = None
        self._paddle_ocr = None
        self._init_models()

    def _init_models(self):
        # 1. RapidOCR for printed text and fast text line detection
        try:
            from app.ai.ocr.rapid_adapter import create_rapid_ocr
            self._rapid_ocr = create_rapid_ocr(logger=logger)
            logger.info('RapidOCR (ONNX) initialized successfully')
        except Exception as e:
            logger.warning(f'RapidOCR not loaded: {e}')

        # 2. TrOCR for handwritten clinical text
        try:
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel
            from app.ai.ocr.htr_engine import MedicalHTREngine, load_vocabularies, resolve_trocr_model_dir
            model_id = os.getenv("TROCR_MODEL_NAME", "microsoft/trocr-base-handwritten")
            finetuned_path = resolve_trocr_model_dir()

            if finetuned_path:
                logger.info(f"Loading fine-tuned medical TrOCR model from {finetuned_path}")
                self._trocr_processor = TrOCRProcessor.from_pretrained(finetuned_path)
                self._trocr_model = VisionEncoderDecoderModel.from_pretrained(finetuned_path)
            else:
                try:
                    logger.info(f"Loading base TrOCR model: {model_id}")
                    self._trocr_processor = TrOCRProcessor.from_pretrained(model_id)
                    self._trocr_model = VisionEncoderDecoderModel.from_pretrained(model_id)
                except Exception as ex:
                    fallback_id = "microsoft/trocr-small-handwritten"
                    logger.warning(f"Could not load {model_id} ({ex}), falling back to {fallback_id}")
                    self._trocr_processor = TrOCRProcessor.from_pretrained(fallback_id)
                    self._trocr_model = VisionEncoderDecoderModel.from_pretrained(fallback_id)
            self._trocr_model.eval()
            logger.info("TrOCR model initialized successfully for handwriting recognition")
            try:
                self._htr = MedicalHTREngine(
                    self._trocr_processor,
                    self._trocr_model,
                    device="cuda" if self.use_gpu else "cpu",
                    **load_vocabularies(finetuned_path)
                )
                logger.info(f"Medical HTR engine ready (lexicon terms: {len(self._htr.corrector or [])})")
            except Exception as ex:
                logger.warning(f"Medical HTR engine unavailable, using legacy TrOCR decoding: {ex}")
        except Exception as e:
            logger.warning(f"TrOCR not loaded: {e}")

        # 3. PaddleOCR optional secondary
        try:
            from paddleocr import PaddleOCR
            self._paddle_ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False, use_gpu=self.use_gpu)
            logger.info('PaddleOCR initialized successfully')
        except Exception:
            pass

    @staticmethod
    def _is_hallucination(text: str, crop_w: int = 0) -> bool:
        """
        Document-agnostic detector for autoregressive language model hallucinations:
        - Wikipedia / internet boilerplate strings
        - Alphabet sequence loops (e.g., 'a b c d e f g h')
        - Cyclical repeating n-grams
        - Character count disproportionate to bounding box width
        """
        if not text:
            return False
        lower = text.lower().strip()

        # 1. Blacklisted corpus boilerplate
        blacklist = [
            "what links here", "related changes", "upload file", "special pages",
            "permanent link", "page information", "cite this page", "wikidata item",
            "wikipedia", "wikimedia", "in the united states in the united states",
            "of the united states of the united", "the first time of the first time",
            "management anniversary", "cosmopolitanism formal holidays"
        ]
        for phrase in blacklist:
            if phrase in lower:
                return True

        # 2. Alphabet sequence loops (e.g. 'a b c d e f g h')
        if re.search(r'(?:[a-z]\s+){4,}[a-z]', lower):
            return True

        # 3. Repeating 2-gram to 4-gram phrase loops
        words = lower.split()
        if len(words) >= 6:
            for n in range(2, 5):
                for i in range(len(words) - 2 * n + 1):
                    if words[i:i+n] == words[i+n:i+2*n]:
                        return True

        # 4. Extreme length disparity (e.g. 50px box generating 100 characters)
        if crop_w > 0 and len(text) > (crop_w / 4.5) + 12:
            return True

        return False

    def _trocr_recognize(self, crop: np.ndarray) -> Tuple[str, float]:
        """
        Runs TrOCR on a cropped handwritten line image with anti-hallucination guardrails.
        Returns recognized string and model confidence score.
        """
        if self._trocr_processor is None or self._trocr_model is None or crop is None or crop.size == 0:
            return "", 0.0
        if self._htr is not None:
            try:
                return self._htr.recognize(crop)
            except Exception as e:
                logger.warning(f"Medical HTR engine failed, falling back to legacy TrOCR decoding: {e}")
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

            # Width-proportional max token constraint prevents runaway generation
            max_tokens = min(32, max(8, int(w / 7)))

            with torch.no_grad():
                generated_outputs = self._trocr_model.generate(
                    pixel_values,
                    max_new_tokens=max_tokens,
                    repetition_penalty=2.0,
                    no_repeat_ngram_size=3,
                    early_stopping=True,
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

    def _recognize_printed_crop(
        self,
        enhanced_crop: np.ndarray,
        default_text: str = "",
        default_conf: float = 0.5
    ) -> Tuple[str, float]:
        """Executes RapidOCR recognizer on a printed line crop with score extraction."""
        if self._rapid_ocr is None or not hasattr(self._rapid_ocr, 'text_recognizer') or enhanced_crop.size == 0:
            return default_text, default_conf
        try:
            rec_res, _ = self._rapid_ocr.text_recognizer([enhanced_crop])
            if rec_res and rec_res[0][0]:
                rec_text = rec_res[0][0].strip()
                rec_score = float(rec_res[0][1])
                return rec_text, rec_score
        except Exception as e:
            logger.warning(f"RapidOCR recognition error: {e}")
        return default_text, default_conf

    def _recognize_line_group(self, group: List[Dict[str, Any]], image: np.ndarray) -> Optional[Dict[str, Any]]:
        """
        Takes a group of horizontally adjacent detection items on the same baseline,
        crops the entire consolidated line from the high-res image, and runs hybrid recognition:
        - Printed regions routed to RapidOCR
        - Handwritten regions routed to TrOCR
        - Bidirectional fallback with reason tracking
        - Anti-hallucination guardrail filtering
        - Medical token normalization
        - Comprehensive model provenance & automated error detection
        """
        if not group:
            return None
        h_img, w_img = image.shape[:2]

        xmin = max(0, min(it['bbox'][0] for it in group))
        ymin = max(0, min(it['bbox'][1] for it in group))
        xmax = min(w_img, max(it['bbox'][2] for it in group))
        ymax = min(h_img, max(it['bbox'][3] for it in group))

        # Add 2px margin to ensure full ascenders/descenders are captured
        c_ymin = max(0, ymin - 2)
        c_ymax = min(h_img, ymax + 2)
        c_xmin = max(0, xmin - 2)
        c_xmax = min(w_img, xmax + 2)

        line_crop = image[c_ymin:c_ymax, c_xmin:c_xmax]
        crop_w = c_xmax - c_xmin

        joined_text = " ".join(it['text'].strip() for it in group if it.get('text')).strip()
        avg_conf = float(np.mean([it['confidence'] for it in group]))

        # 1. Multi-factor region classification with provenance
        class_meta = self.classifier.classify_with_provenance(line_crop, base_score=avg_conf, rapid_text=joined_text)
        region_type = class_meta["region_type"]
        class_conf = class_meta["confidence"]
        class_reasons = class_meta["reasons"]

        raw_prediction = ""
        final_text = ""
        final_conf = avg_conf
        model_used = ""
        fallback_occurred = False
        fallback_reason = None
        hallucination_mitigated = False

        # 2. Bidirectional Hybrid Routing & Fallback
        if region_type == 'handwritten' and self._trocr_model is not None:
            # Primary Route: TrOCR for handwriting
            trocr_raw, trocr_conf = self._trocr_recognize(line_crop)
            is_hallu, sanitized_trocr, hallu_reason = AntiHallucinationFilter.check_hallucination(trocr_raw, crop_w=crop_w)

            if is_hallu:
                hallucination_mitigated = True

            if sanitized_trocr and not is_hallu and trocr_conf >= 0.45:
                raw_prediction = sanitized_trocr
                final_text = sanitized_trocr
                final_conf = trocr_conf
                model_used = 'trocr-handwritten'
            else:
                # Fallback Route: RapidOCR on enhanced crop
                fallback_occurred = True
                fallback_reason = f"trocr_{hallu_reason}" if is_hallu else "trocr_low_conf_or_empty"
                enhanced_crop, _ = enhance_small_or_lowres_text(line_crop, target_min_height=36)
                rapid_fallback_text, rapid_fallback_conf = self._recognize_printed_crop(
                    enhanced_crop, default_text=joined_text, default_conf=avg_conf
                )
                raw_prediction = rapid_fallback_text
                final_text = rapid_fallback_text
                final_conf = rapid_fallback_conf
                model_used = 'rapidocr-fallback'
        else:
            # Primary Route: RapidOCR for printed text
            enhanced_crop, _ = enhance_small_or_lowres_text(line_crop, target_min_height=36)
            rapid_text, rapid_conf = self._recognize_printed_crop(
                enhanced_crop, default_text=joined_text, default_conf=avg_conf
            )

            if rapid_text and rapid_conf >= 0.35:
                raw_prediction = rapid_text
                final_text = rapid_text
                final_conf = rapid_conf
                model_used = 'rapidocr-printed'
            elif self._trocr_model is not None:
                # Fallback Route: TrOCR if RapidOCR was empty or low conf
                trocr_raw, trocr_conf = self._trocr_recognize(line_crop)
                is_hallu, sanitized_trocr, hallu_reason = AntiHallucinationFilter.check_hallucination(trocr_raw, crop_w=crop_w)
                if sanitized_trocr and not is_hallu and trocr_conf >= 0.40:
                    raw_prediction = sanitized_trocr
                    final_text = sanitized_trocr
                    final_conf = trocr_conf
                    model_used = 'trocr-fallback'
                    fallback_occurred = True
                    fallback_reason = "rapidocr_empty_or_low_conf"
                else:
                    raw_prediction = joined_text
                    final_text = joined_text
                    final_conf = max(0.40, avg_conf)
                    model_used = 'rapidocr-printed'
            else:
                raw_prediction = joined_text
                final_text = joined_text
                final_conf = max(0.40, avg_conf)
                model_used = 'rapidocr-printed'

        # 3. Medical token normalization
        normalized_text = self.postprocessor.clean_text(final_text)
        normalization_applied = (raw_prediction.strip() != normalized_text.strip())
        final_text = normalized_text

        if not final_text:
            return None

        # 4. Model Provenance Tracking
        provenance = {
            "model_used": model_used,
            "region_type": region_type,
            "classifier_confidence": class_conf,
            "classification_reasons": class_reasons,
            "routing_decision": f"routed_to_{region_type}",
            "fallback_occurred": fallback_occurred,
            "fallback_reason": fallback_reason,
            "hallucination_mitigated": hallucination_mitigated,
            "raw_prediction": raw_prediction,
            "normalized_prediction": final_text,
            "normalization_applied": normalization_applied
        }

        # 5. Automated OCR Error Detection
        error_analysis = self.error_detector.analyze(
            text=final_text,
            confidence=final_conf,
            crop=line_crop,
            provenance=provenance
        )

        bw = max(1, xmax - xmin)
        bh = max(1, ymax - ymin)
        norm_bbox = [
            round(float(xmin) / max(1, w_img), 5),
            round(float(ymin) / max(1, h_img), 5),
            round(float(xmax) / max(1, w_img), 5),
            round(float(ymax) / max(1, h_img), 5)
        ]

        return {
            'text': final_text,
            'confidence': round(final_conf, 4),
            'source': region_type,
            'model_used': model_used,
            'bbox': [xmin, ymin, xmax, ymax],
            'normalized_bbox': norm_bbox,
            'width': bw,
            'height': bh,
            'status': self._get_status(final_conf, error_analysis),
            'provenance': provenance,
            'error_analysis': error_analysis
        }

    def group_and_merge_lines(self, items: List[Dict[str, Any]], image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Consolidates detection fragments into complete text-line candidates using spatial
        baseline overlap and horizontal proximity, then runs complete line recognition.
        """
        if not items:
            return []

        # 1. Filter micro-noise fragments
        valid_items = []
        for it in items:
            w = it['bbox'][2] - it['bbox'][0]
            h = it['bbox'][3] - it['bbox'][1]
            conf = it['confidence']
            text = it.get('text', '')
            if w < 6 or h < 6:
                continue
            if conf < 0.40 and len(text) <= 2:
                continue
            valid_items.append(it)

        if not valid_items:
            valid_items = items

        # 2. Sort primarily by ymin, secondarily by xmin
        sorted_items = sorted(valid_items, key=lambda b: (b['bbox'][1], b['bbox'][0]))

        # 3. Cluster into lines based on baseline overlap
        lines = []
        for item in sorted_items:
            b_ymin, b_ymax = item['bbox'][1], item['bbox'][3]
            b_h = max(1, b_ymax - b_ymin)
            b_mid = (b_ymin + b_ymax) / 2.0

            placed = False
            for line in lines:
                line_ymin = min(it['bbox'][1] for it in line)
                line_ymax = max(it['bbox'][3] for it in line)
                line_h = max(1, line_ymax - line_ymin)
                line_mid = (line_ymin + line_ymax) / 2.0

                overlap = max(0, min(b_ymax, line_ymax) - max(b_ymin, line_ymin))
                overlap_ratio = overlap / min(b_h, line_h)
                mid_diff = abs(b_mid - line_mid)

                if overlap_ratio >= 0.45 or mid_diff <= 0.4 * min(b_h, line_h):
                    line.append(item)
                    placed = True
                    break
            if not placed:
                lines.append([item])

        # 4. Within each line, merge adjacent boxes into complete line crops
        consolidated_blocks = []
        for line in lines:
            line.sort(key=lambda it: it['bbox'][0])

            cur_group = []
            for item in line:
                if not cur_group:
                    cur_group = [item]
                else:
                    prev_x2 = max(it['bbox'][2] for it in cur_group)
                    cur_x1 = item['bbox'][0]
                    line_h = max(max(it['bbox'][3] - it['bbox'][1] for it in cur_group), item['bbox'][3] - item['bbox'][1])
                    gap = cur_x1 - prev_x2

                    if -0.3 * line_h <= gap <= 2.2 * line_h:
                        cur_group.append(item)
                    else:
                        block = self._recognize_line_group(cur_group, image)
                        if block:
                            consolidated_blocks.append(block)
                        cur_group = [item]
            if cur_group:
                block = self._recognize_line_group(cur_group, image)
                if block:
                    consolidated_blocks.append(block)

        consolidated_blocks.sort(key=lambda b: (b['bbox'][1], b['bbox'][0]))
        return consolidated_blocks

    def process_document(
        self,
        image: np.ndarray,
        doc_name: str = 'document',
        page_num: int = 1,
        input_mode: str = 'auto',
        debug: bool = False
    ) -> Dict[str, Any]:
        """
        True Hybrid Processing Pipeline:
        1. High-resolution text detection.
        2. Spatial grouping into complete line candidates.
        3. Line-level crop recognition (RapidOCR / TrOCR).
        4. Medical lexicon normalization.
        5. Reading-order reconstruction.
        """
        h_img, w_img = image.shape[:2]
        raw_items = []

        # 1. Primary: RapidOCR Detection
        if self._rapid_ocr is not None:
            try:
                if input_mode in ('screen', 'digital'):
                    det_kwargs = {'box_thresh': 0.42, 'unclip_ratio': 1.85, 'text_score': 0.38}
                else:
                    det_kwargs = {'box_thresh': 0.45, 'unclip_ratio': 1.75, 'text_score': 0.40}
                ocr_results, elapse = self._rapid_ocr(image, **det_kwargs)
                if ocr_results:
                    for idx, item in enumerate(ocr_results):
                        box, rapid_text, rapid_score = item[0], item[1], float(item[2])
                        xs = [int(p[0]) for p in box]
                        ys = [int(p[1]) for p in box]
                        xmin, xmax = max(0, min(xs)), min(w_img, max(xs))
                        ymin, ymax = max(0, min(ys)), min(h_img, max(ys))

                        rapid_text_clean = rapid_text.replace('\u53e3', '[ ]').replace('\u25a1', '[ ]')
                        raw_items.append({
                            'id': f'raw_{idx + 1}',
                            'text': rapid_text_clean,
                            'confidence': round(rapid_score, 4),
                            'bbox': [xmin, ymin, xmax, ymax]
                        })
            except Exception as e:
                logger.error(f'RapidOCR execution failed: {e}')

        # 2. Secondary: Contour Detection Fallback
        if not raw_items:
            detected_regions = self.detect_regions(image)
            for idx, r in enumerate(detected_regions):
                xmin, ymin, xmax, ymax = r['bbox']
                raw_items.append({
                    'id': f'raw_{idx + 1}',
                    'text': '',
                    'confidence': 0.70,
                    'bbox': [xmin, ymin, xmax, ymax]
                })

        # 3. Spatial Line Grouping & Complete Line Crop Recognition
        consolidated_blocks = self.group_and_merge_lines(raw_items, image)

        # 4. Extract Comprehensive Layout Intelligence (Columns, Tables, Forms, Key-Values, Checkboxes)
        layout_data = self.layout_engine.extract_full_layout_intelligence(
            image=image,
            blocks=consolidated_blocks,
            page_num=page_num,
            total_pages=1
        )
        sorted_blocks = layout_data["reading_order_blocks"]
        raw_text = layout_data["raw_text"]
        tables = layout_data["tables"]
        key_values = layout_data["key_value_pairs"]
        checkboxes = layout_data["checkboxes"]
        columns = layout_data["columns"]
        baseline_summary = layout_data["baseline_summary"]

        overall_conf = float(np.mean([b['confidence'] for b in sorted_blocks])) if sorted_blocks else 0.0

        # Confidence distribution & Provenance breakdowns
        high_conf_count = sum(1 for b in sorted_blocks if b.get('confidence', 0) >= 0.88)
        med_conf_count = sum(1 for b in sorted_blocks if 0.65 <= b.get('confidence', 0) < 0.88)
        review_count = sum(1 for b in sorted_blocks if b.get('confidence', 0) < 0.65)

        printed_count = sum(1 for b in sorted_blocks if b.get('source') == 'printed')
        hw_count = sum(1 for b in sorted_blocks if b.get('source') == 'handwritten')
        fallback_count = sum(1 for b in sorted_blocks if b.get('provenance', {}).get('fallback_occurred', False))

        error_flagged_count = sum(1 for b in sorted_blocks if b.get('error_analysis', {}).get('has_errors', False))

        # 5. Debug Artifacts
        if debug or os.environ.get('DEBUG_OCR', '').lower() in ('true', '1'):
            self._save_debug_artifacts(image, sorted_blocks, doc_name)

        return {
            'status': 'success',
            'document': doc_name,
            'page': page_num,
            'pages': 1,
            'image_dimensions': [w_img, h_img],
            'total_blocks': len(sorted_blocks),
            'overall_confidence': round(overall_conf, 4),
            'confidence_distribution': {
                'high_confidence_blocks': high_conf_count,
                'medium_confidence_blocks': med_conf_count,
                'review_required_blocks': review_count
            },
            'hybrid_routing': {
                'printed_blocks': printed_count,
                'handwritten_blocks': hw_count,
                'fallbacks_triggered': fallback_count
            },
            'error_summary': {
                'total_flagged_blocks': error_flagged_count,
                'total_clean_blocks': len(sorted_blocks) - error_flagged_count
            },
            'layout': {
                'column_count': len(columns),
                'columns': columns,
                'tables': tables,
                'key_value_pairs': key_values,
                'checkboxes': checkboxes,
                'baseline_summary': baseline_summary
            },
            'blocks': sorted_blocks,
            'raw_text': raw_text
        }

    def process_region(
        self,
        image: np.ndarray,
        region_bbox: List[int],
        doc_name: str = 'snippet',
        input_mode: str = 'screen',
        preprocessing_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processes a focused sub-region / marquee snippet within a larger document.
        Applies resolution-preserving upscaling (2.5x) for small crops,
        runs line-level detection & recognition, and translates all bounding boxes
        back to the original global coordinates.
        """
        h_img, w_img = image.shape[:2]
        rx1, ry1, rx2, ry2 = region_bbox
        rx1, rx2 = max(0, min(rx1, rx2)), min(w_img, max(rx1, rx2))
        ry1, ry2 = max(0, min(ry1, ry2)), min(h_img, max(ry1, ry2))

        crop_w = rx2 - rx1
        crop_h = ry2 - ry1
        if crop_w < 10 or crop_h < 8:
            return {
                'status': 'error',
                'message': 'Selected region too small for text recognition',
                'document': doc_name,
                'pages': 1,
                'image_dimensions': [w_img, h_img],
                'total_blocks': 0,
                'overall_confidence': 0.0,
                'blocks': [],
                'raw_text': ''
            }

        snippet_crop = image[ry1:ry2, rx1:rx2]

        # Multi-scale upscale for screen snippets where font height may be small (12-24px)
        scale = 1.0
        if crop_h < 400 or input_mode in ('screen', 'digital'):
            scale = 2.5 if crop_h < 250 else 1.8
            upscaled_snippet = cv2.resize(snippet_crop, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        else:
            upscaled_snippet = snippet_crop

        preproc_snippet = run_preprocessing_pipeline(upscaled_snippet, input_mode=input_mode, preprocessing_mode=preprocessing_mode)
        res = self.process_document(preproc_snippet, doc_name=doc_name, input_mode=input_mode)

        # Unscale coordinates back to snippet space, then offset to global document coordinates
        for b in res.get('blocks', []):
            local_x1, local_y1, local_x2, local_y2 = b['bbox']
            ux1 = local_x1 / scale
            uy1 = local_y1 / scale
            ux2 = local_x2 / scale
            uy2 = local_y2 / scale

            gx1 = int(round(rx1 + ux1))
            gy1 = int(round(ry1 + uy1))
            gx2 = int(round(rx1 + ux2))
            gy2 = int(round(ry1 + uy2))

            b['bbox'] = [gx1, gy1, gx2, gy2]
            b['normalized_bbox'] = [
                round(float(gx1) / max(1, w_img), 5),
                round(float(gy1) / max(1, h_img), 5),
                round(float(gx2) / max(1, w_img), 5),
                round(float(gy2) / max(1, h_img), 5)
            ]
            b['width'] = gx2 - gx1
            b['height'] = gy2 - gy1

        res['region_bbox'] = [rx1, ry1, rx2, ry2]
        res['image_dimensions'] = [w_img, h_img]
        return res

    def _save_debug_artifacts(self, image: np.ndarray, blocks: List[Dict[str, Any]], doc_name: str):
        """Saves annotated debug image and block JSON for visual pipeline inspection."""
        try:
            debug_dir = os.path.join("outputs", "debug")
            os.makedirs(debug_dir, exist_ok=True)
            ts = int(time.time())
            safe_name = os.path.splitext(os.path.basename(doc_name))[0]

            annotated = image.copy()
            for b in blocks:
                x1, y1, x2, y2 = b['bbox']
                color = (0, 200, 0) if b.get('source') == 'printed' else (0, 140, 255)
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                cv2.putText(annotated, b['id'], (x1, max(12, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

            cv2.imwrite(os.path.join(debug_dir, f"{safe_name}_{ts}_lines.png"), annotated)
            with open(os.path.join(debug_dir, f"{safe_name}_{ts}_blocks.json"), 'w', encoding='utf-8') as f:
                json.dump(blocks, f, indent=2)
            logger.info(f"Saved debug artifacts to {debug_dir} for {doc_name}")
        except Exception as e:
            logger.warning(f"Failed to save debug artifacts: {e}")

    def _get_status(self, conf: float, error_analysis: Optional[Dict[str, Any]] = None) -> str:
        if error_analysis and error_analysis.get("severity") == "high":
            return 'HUMAN_VERIFICATION_NEEDED'
        if conf >= 0.88:
            return 'HIGH_CONFIDENCE'
        elif conf >= 0.65:
            return 'MEDIUM_CONFIDENCE'
        else:
            return 'REVIEW_REQUIRED'
# Backwards-compatible alias
MedIntelOCREngine = OCRDocumentReadingEngine
