"""
AI word suggestions: a local vision-language model re-reads the lines a reviewer would check and proposes words.

Nothing here edits the text. For each unsure line (flagged words, a low-confidence line, or recognisers that
disagree) the model reads the line image twice, as cropped and enlarged with boosted contrast, given both OCR
readings and the neighbouring lines. A word is proposed only when both views agree on it, it stays close to what
was read, and it does not swap a known word for an unknown one. Proposals join block["review"]:

  an existing flag on the word   gains `ai_suggestion`, listed first among its suggestions
  otherwise                      a new flag of kind "ai"

Each carries `evidence` (views_agree, in_dictionary, matches_other_reader, ink, confidence), the line's `bbox`,
`normalized_bbox` and `page` so the reviewer can look at the writing, and `confirm: true` for medicines and numbers.
The model runs on this machine only.
"""
import difflib
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np

from app.ai.ocr.htr_language_model import _DOSE_OR_FORM
from app.ai.ocr.text_review import _levenshtein, _words

DEFAULT_PARAMS: Dict[str, float] = {
    "max_lines": 40,        # lines re-read per document, least confident first
    "line_conf": 0.85,      # lines under this are re-read even with no flagged word
    "min_conf": 0.85,       # the model's mean token probability, on both views
    "min_line_similarity": 0.5,  # its reading must resemble the line or the other reader's reading
    "max_word_change": 0.6,      # edit distance / word length, unless the other reader read the same word
}


def enhanced_view(crop: np.ndarray, min_height: int = 64) -> np.ndarray:
    """The line enlarged with local contrast boosted: a second look at faint or small writing."""
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
    scale = max(1.0, min_height / max(1, gray.shape[0]))
    if scale > 1.0:
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def _key(w: Dict[str, Any]) -> str:
    return (w["word"] or w["token"].strip(".,;:()[]")).lower()


def word_pairs(text: str, other: str) -> List[Tuple[Dict[str, Any], str]]:
    """(word of `text`, what `other` has in its place) where the two differ word for word."""
    a, b = _words(text), _words(other)
    pairs = []
    sm = difflib.SequenceMatcher(a=[_key(w) for w in a], b=[_key(w) for w in b], autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "replace" and i2 - i1 == j2 - j1:
            for k in range(i2 - i1):
                theirs = b[j1 + k]["word"] or b[j1 + k]["token"].strip(".,;:()[]")
                if theirs and re.search(r"\w", a[i1 + k]["token"]):
                    pairs.append((a[i1 + k], theirs))
    return pairs


class AIWordReviewer:
    def __init__(self, reader, is_known: Callable[[str], bool], drugs: Sequence[str] = (),
                 ink_score: Optional[Callable[[np.ndarray, List[str]], List[float]]] = None,
                 params: Optional[Dict[str, float]] = None):
        self.reader = reader
        self.is_known = is_known
        self.drugs = {d.lower() for d in drugs}
        self.ink_score = ink_score
        self.params = {**DEFAULT_PARAMS, **(params or {})}

    def needs_check(self, block: Dict[str, Any]) -> bool:
        if not block.get("text") or block.get("role") == "signature" or not block.get("bbox"):
            return False
        return bool(block.get("review") or block.get("needs_review")
                    or float(block.get("confidence") or 0.0) < self.params["line_conf"])

    @staticmethod
    def _other_readings(block: Dict[str, Any]) -> List[str]:
        return [r for r in (block.get("readings") or {}).values() if r and r != block.get("text")]

    def proposals(self, block: Dict[str, Any], reads: Sequence[Tuple[str, float]]) -> List[Dict[str, Any]]:
        """Word proposals for a line from the model's reading of each view."""
        text, others = block["text"], self._other_readings(block)
        per_view, confs = [], []
        for reading, conf in reads:
            refs = [text] + others
            similar = max(difflib.SequenceMatcher(a=reading.lower(), b=r.lower()).ratio() for r in refs)
            if not reading or conf < self.params["min_conf"] or similar < self.params["min_line_similarity"]:
                return []
            per_view.append({w["start"]: (w, alt) for w, alt in word_pairs(text, reading)})
            confs.append(conf)
        if not per_view:
            return []
        other_words = {_key(w) for r in others for w in _words(r)}
        tokens = [w["token"] for w in _words(text)]
        out = []
        for start, (w, alt) in per_view[0].items():
            if any(start not in v or v[start][1].lower() != alt.lower() for v in per_view[1:]):
                continue  # the two looks at the line disagree
            mine, cand = _key(w), alt.lower()
            if not cand.isascii():
                continue  # "1)" re-read as a circled digit is the same mark, not a correction
            matches_other = cand in other_words
            same_size_number = mine.isdigit() and cand.isdigit() and len(mine) == len(cand)  # "500" / "650": worth a look
            if not matches_other and not same_size_number                     and _levenshtein(mine, cand) / max(len(mine), len(cand)) > self.params["max_word_change"]:
                continue
            known = self.is_known(cand) if cand.isalpha() else False
            if w["word"] and self.is_known(mine) and not known and not matches_other:
                continue  # a real word is not traded for something unknown
            i = next((n for n, t in enumerate(_words(text)) if t["start"] == w["start"]), 0)
            neighbours = tokens[max(0, i - 1): i] + tokens[i + 1: i + 2]
            numeric = bool(re.search(r"\d", w["token"] + alt))
            medicine = mine in self.drugs or cand in self.drugs or any(
                _DOSE_OR_FORM.match(n.strip(",;:")) for n in neighbours)
            if medicine and not numeric and not matches_other and cand not in self.drugs:
                continue  # the model is weak on drug names: it must name a listed drug or match the other reader
            out.append({"word": w["word"] or w["token"], "start": w["start"], "end": w["end"], "suggestion": alt,
                        "confirm": numeric or medicine,
                        "evidence": {"views_agree": len(per_view) > 1, "in_dictionary": known,
                                     "matches_other_reader": matches_other, "ink": None,
                                     "confidence": round(min(confs), 3)}})
        return out

    def _check_ink(self, block, crop, found) -> None:
        if self.ink_score is None:
            return
        text = block["text"]
        variants = [text[:p["start"]] + p["suggestion"] + text[p["end"]:] for p in found]
        scores = self.ink_score(crop, [text] + variants)
        for p, score in zip(found, scores[1:]):
            p["evidence"]["ink"] = "supports" if score >= scores[0] else "against"

    @staticmethod
    def _reason(p: Dict[str, Any]) -> str:
        e = p["evidence"]
        why = ["read the same way on two looks at the line"]
        if e["matches_other_reader"]:
            why.append("one OCR reader agrees")
        if e["in_dictionary"]:
            why.append("a known word")
        if e["ink"] == "against":
            why.append("the handwriting model prefers the current word")
        text = "Local AI suggestion: " + ", ".join(why)
        return text + ". Confirm against the page." if p["confirm"] else text + "."

    @staticmethod
    def apply(block: Dict[str, Any], found: Sequence[Dict[str, Any]], reason: Callable[[Dict], str]) -> int:
        flags = block.setdefault("review", [])
        for p in found:
            info = {"evidence": p["evidence"], "confirm": p["confirm"], "bbox": block.get("bbox"),
                    "normalized_bbox": block.get("normalized_bbox"), "page": block.get("page", 1),
                    "ai_suggestion": p["suggestion"]}
            flag = next((f for f in flags if f["start"] == p["start"]), None)
            if flag is None:
                flags.append({"word": p["word"], "start": p["start"], "end": p["end"], "kind": "ai",
                              "suggestions": [p["suggestion"]], "reason": reason(p), **info})
            else:
                rest = [s for s in flag.get("suggestions", []) if s.lower() != p["suggestion"].lower()]
                flag.update(suggestions=[p["suggestion"]] + rest, **info)
        flags.sort(key=lambda f: f["start"])
        if not flags:
            block.pop("review", None)
        return len(found)

    def review(self, blocks: List[Dict[str, Any]], crop_for: Callable[[Dict[str, Any]], Optional[np.ndarray]]) -> int:
        """Adds proposals to the blocks and returns how many were made."""
        lines = sorted((b for b in blocks if self.needs_check(b)), key=lambda b: float(b.get("confidence") or 0.0))
        lines = lines[: int(self.params["max_lines"])]
        order = sorted(blocks, key=lambda b: (b.get("page", 1), b.get("reading_order", 0)))
        at = {id(b): i for i, b in enumerate(order)}
        todo, crops, prompts = [], [], []
        for b in lines:
            crop = crop_for(b)
            if crop is None or crop.size == 0:
                continue
            i = at[id(b)]
            context = [o["text"] for o in order[max(0, i - 1): i] + order[i + 1: i + 2]
                       if o.get("page", 1) == b.get("page", 1) and o.get("text")]
            prompt = self.reader.context_prompt([b["text"]] + self._other_readings(b), context)
            todo.append((b, crop))
            crops += [crop, enhanced_view(crop)]
            prompts += [prompt, prompt]
        if not todo:
            return 0
        reads = self.reader.read(crops, prompts=prompts, batch_size=4)
        total = 0
        for k, (b, crop) in enumerate(todo):
            found = self.proposals(b, reads[2 * k: 2 * k + 2])
            if not found:
                continue
            try:
                self._check_ink(b, crop, found)
            except Exception:
                pass  # the check is extra evidence; the proposal stands without it
            total += self.apply(b, found, self._reason)
        return total
