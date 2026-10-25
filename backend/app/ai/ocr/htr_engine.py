"""
Medical Handwritten Text Recognition (HTR) engine built on a fine-tuned TrOCR checkpoint.

Shared by the OCR engines (inference) and scripts/train_trocr_medical.py (training / evaluation) so that
image preparation is identical in both places:
  - prepare_htr_image(): ink-aware trimming of blank margins, minimum-height upscaling, aspect padding
  - MedicalHTREngine:    beam-search decoding, calibrated sequence + per-word confidence,
                         confidence-gated medical lexicon correction (drug names learnt from the
                         training corpora and shipped next to the weights as medical_lexicon.json)
"""
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np

LEXICON_FILENAME = "medical_lexicon.json"
MODEL_DIRNAME = "trocr_medical_finetuned"
CPU_DEFAULT_BEAMS = 2


def resolve_trocr_model_dir() -> Optional[str]:
    """
    Locates the fine-tuned medical TrOCR checkpoint:
      1. TROCR_FINETUNED_MODEL_PATH (or legacy TROCR_MODEL_PATH) environment variable
      2. <this package>/../models/trocr_medical_finetuned
      3. app/ai/models/trocr_medical_finetuned in any parent directory (lets backend/app reuse the
         checkpoint trained into the repository-level app/ tree without duplicating 250 MB of weights)
    """
    for var in ("TROCR_FINETUNED_MODEL_PATH", "TROCR_MODEL_PATH"):
        env_path = os.getenv(var)
        if env_path and os.path.isdir(os.path.expanduser(env_path)):
            return os.path.expanduser(env_path)

    here = Path(__file__).resolve()
    local = here.parent.parent / "models" / MODEL_DIRNAME
    if local.is_dir():
        return str(local)

    for parent in here.parents:
        candidate = parent / "app" / "ai" / "models" / MODEL_DIRNAME
        if candidate.is_dir():
            return str(candidate)
    return None


def _read_lexicon_file(model_dir: Optional[str]) -> Dict[str, Any]:
    if not model_dir:
        return {}
    path = os.path.join(model_dir, LEXICON_FILENAME)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"terms": data}
    except Exception:
        return {}


def load_lexicon(model_dir: Optional[str]) -> List[str]:
    terms = _read_lexicon_file(model_dir).get("terms", [])
    return [t for t in terms if isinstance(t, str) and t]


def load_vocabularies(model_dir: Optional[str]) -> Dict[str, Any]:
    """
    Keyword arguments for MedicalHTREngine from the checkpoint's medical_lexicon.json:
      lexicon        drug / clinical terms used for correction and n-best rescoring
      common_words   general English vocabulary (never "corrected" into a drug name)
      rescore_weight tuned weight of the word-validity prior in n-best rescoring
    """
    data = _read_lexicon_file(model_dir)
    out: Dict[str, Any] = {
        "lexicon": [t for t in data.get("terms", []) if isinstance(t, str) and t],
        "common_words": [t for t in data.get("common_words", []) if isinstance(t, str) and t],
    }
    if isinstance(data.get("decoding"), dict):
        dec = data["decoding"]
        for key in ("rescore_weight", "lexicon_conf_gate"):
            if isinstance(dec.get(key), (int, float)):
                out[key] = float(dec[key])
    return out


_DOSE_TOKEN = re.compile(
    r"^(?:\d+(?:[./]\d+)?(?:mg|mcg|g|gm|ml|iu|%|d)?|[0-9½]+(?:[-+/][0-9½]+){1,3}|x\d+|"
    r"mg|mcg|g|gm|ml|iu|tab|tab\.|cap|cap\.|syp|syp\.|inj|inj\.|od|bd|bid|tid|tds|qid|hs|sos|prn|stat|ac|pc)$",
    re.IGNORECASE,
)


def _main_text_band(gray: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
    """
    Returns (x0, y0, x1, y1) of the dominant handwriting band. Strokes are smeared horizontally into
    word blobs; the heaviest blob defines the band and any blob sharing most of its vertical extent
    with the band is kept, so fragments of neighbouring lines (common in prescription crops) are dropped.
    """
    h, w = gray.shape[:2]
    _, ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    ink_ratio = float(np.count_nonzero(ink)) / float(ink.size)
    if not (0.002 < ink_ratio < 0.5):
        return None

    kx = max(3, int(min(h, w) * 0.06))
    smeared = cv2.dilate(ink, cv2.getStructuringElement(cv2.MORPH_RECT, (kx, max(1, kx // 3))))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(smeared, connectivity=8)
    if n <= 1:
        return None

    # Weight blobs by the real ink they contain, not their dilated area
    ink_counts = np.bincount(labels[ink > 0].ravel(), minlength=n)
    ink_counts[0] = 0
    main = int(np.argmax(ink_counts))
    if ink_counts[main] == 0:
        return None
    _, my, _, mh, _ = stats[main]
    band_y0, band_y1 = my, my + mh

    x0, y0, x1, y1 = w, h, 0, 0
    for i in range(1, n):
        bx, by, bw, bh, _ = stats[i]
        overlap = max(0, min(by + bh, band_y1) - max(by, band_y0))
        if i == main or (overlap >= 0.5 * bh and ink_counts[i] > 0):
            x0, y0 = min(x0, bx), min(y0, by)
            x1, y1 = max(x1, bx + bw), max(y1, by + bh)
    # Undo the dilation padding approximately
    pad_x, pad_y = kx // 2, max(1, kx // 3) // 2
    box = max(0, x0 + pad_x), max(0, y0 + pad_y), min(w, x1 - pad_x), min(h, y1 - pad_y)

    # Only trust the band when it holds most of the ink. A heavy underline or scribble can be the
    # biggest blob while the text sits beside it; trimming would then cut the text away.
    total_ink = int(np.count_nonzero(ink))
    kept_ink = int(np.count_nonzero(ink[box[1]:box[3], box[0]:box[2]]))
    if total_ink == 0 or kept_ink < 0.6 * total_ink:
        return None
    return box


def prepare_htr_image(img: np.ndarray, min_height: int = 32):
    """
    Converts a BGR / gray crop into the RGB PIL image fed to the TrOCR processor.
    - Trims large blank margins around the ink (word crops are often padded onto big canvases)
    - Upscales tiny crops so the ViT patch grid still sees strokes
    - Pads near-square or tall crops horizontally so the 384x384 resize does not stretch glyphs
    """
    from PIL import Image

    if img is None or img.size == 0:
        raise ValueError("Empty crop")

    if img.ndim == 2:
        rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
    elif img.shape[2] == 4:
        rgb = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
    else:
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    h, w = rgb.shape[:2]
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)

    # 1. Ink-aware trimming (only when the content clearly occupies a fraction of the canvas)
    if h >= 16 and w >= 16 and float(gray.std()) > 8.0:
        box = _main_text_band(gray)
        if box is not None:
            x0, y0, x1, y1 = box
            ch, cw = max(1, y1 - y0), max(1, x1 - x0)
            if ch < 0.85 * h or cw < 0.85 * w:
                margin = max(4, int(0.12 * ch))
                y0, y1 = max(0, y0 - margin), min(h, y1 + margin)
                x0, x1 = max(0, x0 - margin), min(w, x1 + margin)
                rgb = rgb[y0:y1, x0:x1]
                h, w = rgb.shape[:2]

    # 2. Minimum height
    if h < min_height:
        scale = float(min_height) / float(h)
        rgb = cv2.resize(rgb, (max(1, int(round(w * scale))), min_height), interpolation=cv2.INTER_CUBIC)
        h, w = rgb.shape[:2]

    # 3. Horizontal padding for crops narrower than they are tall
    if w < h:
        bg = int(np.median(np.concatenate([rgb[0].reshape(-1), rgb[-1].reshape(-1)])))
        pad = h - w
        rgb = cv2.copyMakeBorder(rgb, 0, 0, pad // 2, pad - pad // 2, cv2.BORDER_CONSTANT, value=(bg, bg, bg))

    return Image.fromarray(np.ascontiguousarray(rgb))


def _levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


class MedicalLexiconCorrector:
    """
    Snaps low-confidence recognised words onto the nearest known medical term.
    Only fires when the decoder itself was unsure about the word and the match is unambiguous.
    """

    def __init__(self, terms: Sequence[str], min_len: int = 4, common_words: Optional[Sequence[str]] = None):
        self.min_len = min_len
        self.by_len: Dict[int, List[Tuple[str, str]]] = {}
        self.exact = set()
        self.common = {w.lower() for w in (common_words or [])}
        for t in terms:
            key = t.lower()
            # Correction targets are drug / clinical terms only: never snap a word onto ordinary English
            if len(key) < min_len or key in self.common:
                continue
            self.exact.add(key)
            self.by_len.setdefault(len(key), []).append((key, t))

    def __len__(self):
        return len(self.exact)

    @staticmethod
    def _max_dist(n: int) -> int:
        return 1 if n <= 6 else (2 if n <= 10 else 3)

    def match(self, word: str) -> Optional[str]:
        key = word.lower()
        if len(key) < self.min_len or not key.isalpha() or key in self.exact or key in self.common:
            return None
        limit = self._max_dist(len(key))
        best, best_d, tie = None, limit + 1, False
        for n in range(len(key) - limit, len(key) + limit + 1):
            for cand_key, cand in self.by_len.get(n, []):
                d = _levenshtein(key, cand_key)
                if d < best_d:
                    best, best_d, tie = cand, d, False
                elif d == best_d and best is not None and cand_key != best.lower():
                    tie = True
        if best is None or tie or best_d > limit:
            return None
        return best


class MedicalHTREngine:
    """Fine-tuned TrOCR wrapper used for handwritten line / word crops."""

    def __init__(
        self,
        processor,
        model,
        lexicon: Optional[Sequence[str]] = None,
        device: Optional[str] = None,
        num_beams: Optional[int] = None,
        lexicon_conf_gate: float = 0.7,
        common_words: Optional[Sequence[str]] = None,
        rescore_weight: float = 0.0,
        quantize_cpu: Optional[bool] = None
    ):
        import torch

        self.processor = processor
        self.lexicon_conf_gate = lexicon_conf_gate
        self.rescore_weight = rescore_weight
        self.corrector = MedicalLexiconCorrector(lexicon, common_words=common_words) if lexicon else None
        self.known_words = {w.lower() for w in (lexicon or [])} | {w.lower() for w in (common_words or [])}
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = torch.device(device)
        model.to(self.device)
        model.eval()

        # Beam width: GPU affords the full beam; on CPU the beam dominates latency for an interactive
        # plugin, so it defaults lower. HTR_NUM_BEAMS overrides both.
        if num_beams is None:
            env_beams = os.getenv("HTR_NUM_BEAMS", "")
            num_beams = int(env_beams) if env_beams.isdigit() else (4 if self.device.type == "cuda" else CPU_DEFAULT_BEAMS)
        self.num_beams = max(1, num_beams)

        # Dynamic int8 quantisation of Linear layers roughly halves CPU latency. Opt out with HTR_INT8=0.
        if quantize_cpu is None:
            quantize_cpu = os.getenv("HTR_INT8", "1") != "0"
        self.quantized = False
        if quantize_cpu and self.device.type == "cpu":
            try:
                model = torch.ao.quantization.quantize_dynamic(model, {torch.nn.Linear}, dtype=torch.qint8)
                self.quantized = True
            except Exception:
                pass
        self.model = model
        tok = processor.tokenizer
        self._space_markers = ("▁", "Ġ", " ")  # sentencepiece, byte-level BPE, plain
        self._special_ids = set(tok.all_special_ids)

    @classmethod
    def from_pretrained(cls, model_dir: str, device: Optional[str] = None, **kwargs) -> "MedicalHTREngine":
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel

        processor = TrOCRProcessor.from_pretrained(model_dir)
        model = VisionEncoderDecoderModel.from_pretrained(model_dir)
        params = load_vocabularies(model_dir)
        params.update(kwargs)
        return cls(processor, model, device=device, **params)

    # ------------------------------------------------------------------
    def word_validity(self, text: str) -> float:
        """Fraction of words that are known drug/clinical terms, English words, or dose/frequency tokens."""
        words = [re.sub(r"^[^\w½]+|[^\w½.]+$", "", w) for w in text.split()]
        words = [w for w in words if w]
        if not words:
            return 0.0
        hits = sum(1 for w in words if w.lower().rstrip(".") in self.known_words or _DOSE_TOKEN.match(w))
        return hits / len(words)

    # ------------------------------------------------------------------
    def _word_confidences(self, token_ids: List[int], token_probs: List[float]) -> List[Tuple[str, float]]:
        """Groups decoded sub-word tokens into words and assigns each the min token probability."""
        tokens = self.processor.tokenizer.convert_ids_to_tokens(token_ids)
        words: List[Tuple[str, float]] = []
        cur_ids: List[int] = []
        cur_p: List[float] = []
        for tid, tok, p in zip(token_ids, tokens, token_probs):
            if tid in self._special_ids:
                continue
            if tok.startswith(self._space_markers) and cur_ids:
                words.append((self.processor.tokenizer.decode(cur_ids).strip(), min(cur_p)))
                cur_ids, cur_p = [], []
            cur_ids.append(tid)
            cur_p.append(p)
        if cur_ids:
            words.append((self.processor.tokenizer.decode(cur_ids).strip(), min(cur_p)))
        return [(w, c) for w, c in words if w]

    def _apply_lexicon(
        self,
        text: str,
        word_confs: List[Tuple[str, float]],
        sequence_conf: float
    ) -> Tuple[str, List[Dict[str, Any]]]:
        if not self.corrector or not text:
            return text, []
        words = text.split()
        # Positional alignment when tokenizer word grouping matches whitespace splitting,
        # otherwise every word inherits the sequence-level confidence.
        if len(word_confs) == len(words):
            confs = [c for _, c in word_confs]
        else:
            confs = [sequence_conf] * len(words)
        corrections = []
        out = []
        for raw, conf in zip(words, confs):
            m = re.match(r"^([^A-Za-z]*)([A-Za-z]+)([^A-Za-z]*)$", raw)
            if m and conf < self.lexicon_conf_gate:
                fixed = self.corrector.match(m.group(2))
                if fixed:
                    corrections.append({"from": m.group(2), "to": fixed, "word_confidence": round(conf, 4)})
                    raw = f"{m.group(1)}{fixed}{m.group(3)}"
            out.append(raw)
        return " ".join(out), corrections

    def decode_nbest(
        self,
        crops: Sequence[np.ndarray],
        max_new_tokens: Optional[int] = None,
        n_best: Optional[int] = None
    ) -> List[List[Dict[str, Any]]]:
        """
        Beam-search decodes each crop and returns its n-best candidates
        (raw_text, mean_logp, confidence, token_ids, token_probs). Empty crops get an empty list.
        """
        import torch

        out_lists: List[List[Dict[str, Any]]] = [[] for _ in crops]
        valid = [(i, c) for i, c in enumerate(crops) if c is not None and c.size > 0]
        if not valid:
            return out_lists

        images = [prepare_htr_image(c) for _, c in valid]
        if max_new_tokens is None:
            widest = max(c.shape[1] for _, c in valid)
            max_new_tokens = min(48, max(12, int(widest / 6)))
        if n_best is None:
            n_best = self.num_beams if (self.num_beams > 1 and self.rescore_weight > 0 and self.known_words) else 1
        n_best = max(1, min(n_best, self.num_beams))

        pixel_values = self.processor(images=images, return_tensors="pt").pixel_values.to(self.device)
        gen_kwargs: Dict[str, Any] = {"num_beams": self.num_beams}
        if self.num_beams > 1:
            gen_kwargs["early_stopping"] = True
            gen_kwargs["num_return_sequences"] = n_best
        with torch.inference_mode():
            out = self.model.generate(
                pixel_values,
                max_new_tokens=max_new_tokens,
                no_repeat_ngram_size=4,
                repetition_penalty=1.15,
                return_dict_in_generate=True,
                output_scores=True,
                **gen_kwargs
            )
            transition = self.model.compute_transition_scores(
                out.sequences, out.scores, getattr(out, "beam_indices", None), normalize_logits=False
            )

        sequences = out.sequences.cpu().tolist()
        transition = transition.float().cpu().numpy()
        pad_id = self.processor.tokenizer.pad_token_id
        for item, (orig_idx, _) in enumerate(valid):
            for row in range(item * n_best, (item + 1) * n_best):
                # transition scores align with sequences[:, 1:] (decoder start token has no score)
                ids = sequences[row][1:]
                logps = transition[row][: len(ids)]
                keep = [(t, lp) for t, lp in zip(ids, logps) if t != pad_id and np.isfinite(lp)]
                token_ids = [t for t, _ in keep]
                token_probs = [float(np.exp(lp)) for _, lp in keep]
                raw_text = self.processor.tokenizer.decode(token_ids, skip_special_tokens=True).strip()
                content_probs = [p for t, p in zip(token_ids, token_probs) if t not in self._special_ids] or token_probs
                if content_probs:
                    mean_logp = float(np.mean(np.log(np.clip(content_probs, 1e-6, 1.0))))
                    conf = 0.8 * float(np.exp(mean_logp)) + 0.2 * float(min(content_probs))
                else:
                    mean_logp, conf = -50.0, 0.0
                out_lists[orig_idx].append({
                    "raw_text": raw_text, "mean_logp": mean_logp, "confidence": conf,
                    "token_ids": token_ids, "token_probs": token_probs,
                })
        return out_lists

    def select(self, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Picks the best candidate (decoder likelihood + rescore_weight x word-validity prior) and applies
        confidence-gated lexicon correction to it.
        """
        if not candidates:
            return {"text": "", "raw_text": "", "confidence": 0.0, "word_confidences": [], "lexicon_corrections": []}
        if len(candidates) > 1 and self.rescore_weight > 0:
            best = max(candidates, key=lambda c: c["mean_logp"] + self.rescore_weight * self.word_validity(c["raw_text"]))
        else:
            best = candidates[0]
        word_confs = self._word_confidences(best["token_ids"], best["token_probs"])
        text, corrections = self._apply_lexicon(best["raw_text"], word_confs, best["confidence"])
        return {
            "text": text,
            "raw_text": best["raw_text"],
            "confidence": round(best["confidence"], 4),
            "word_confidences": [{"word": w, "confidence": round(c, 4)} for w, c in word_confs],
            "lexicon_corrections": corrections,
        }

    def recognize_batch(self, crops: Sequence[np.ndarray], max_new_tokens: Optional[int] = None) -> List[Dict[str, Any]]:
        return [self.select(c) for c in self.decode_nbest(crops, max_new_tokens=max_new_tokens)]

    def recognize_detailed(self, crop: np.ndarray, max_new_tokens: Optional[int] = None) -> Dict[str, Any]:
        return self.recognize_batch([crop], max_new_tokens=max_new_tokens)[0]

    def recognize(self, crop: np.ndarray, max_new_tokens: Optional[int] = None) -> Tuple[str, float]:
        """Engine-compatible signature: returns (text, confidence)."""
        res = self.recognize_detailed(crop, max_new_tokens=max_new_tokens)
        return res["text"], res["confidence"]
