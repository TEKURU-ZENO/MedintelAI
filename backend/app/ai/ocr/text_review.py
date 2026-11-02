"""
Grammarly-style review of OCR text: the words a reader should check, each with ranked suggestions.

Each block gets `review`, a list of flags with character offsets into block["text"]:
  corrected   the spelling layer changed the word; the suggestion is the original reading (one click reverts)
  ambiguous   the two recognisers read the word differently; the suggestions are the other reading(s)
  spelling    not a known word, drug, number or abbreviation; the suggestions are the nearest dictionary words
              (ranked in context by the language model) and drug names
A block whose line confidence is low gets `needs_review` so the whole line is checked. The text is never edited.
"""
import difflib
import re
from typing import Any, Dict, Iterable, List, Optional

from app.ai.ocr.htr_language_model import _DOSE_OR_FORM

_TOKEN = re.compile(r"\S+")
_CORE = re.compile(r"^([^A-Za-z]*)([A-Za-z](?:[A-Za-z'-]*[A-Za-z])?)([^A-Za-z]*)$")
LOW_LINE_CONF = 0.6     # below this the whole line is marked for review
NAME_CHECK_CONF = 0.85  # capitalised unknown words (names, brands) are flagged only on lines less confident than this


def _levenshtein(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _words(text: str) -> List[Dict[str, Any]]:
    """Tokens of `text` with the span of their alphabetic core (punctuation stripped)."""
    out = []
    for m in _TOKEN.finditer(text):
        core = _CORE.match(m.group(0))
        if core:
            start = m.start() + len(core.group(1))
            out.append({"token": m.group(0), "word": core.group(2), "start": start, "end": start + len(core.group(2))})
        else:
            out.append({"token": m.group(0), "word": None, "start": m.start(), "end": m.end()})
    return out


class TextReviewer:
    def __init__(self, common_words: Iterable[str] = (), drug_terms: Iterable[str] = (), spell=None,
                 max_suggestions: int = 3):
        self.known = {w.lower() for w in common_words if w}
        self.drugs: Dict[str, str] = {}
        self.drugs_by_len: Dict[int, List[str]] = {}
        for t in drug_terms:
            if t and len(t) >= 3 and t.lower() not in self.drugs:
                self.drugs[t.lower()] = t
                self.drugs_by_len.setdefault(len(t), []).append(t)
        self.spell = spell
        self.n = max_suggestions

    def _is_known(self, word: str) -> bool:
        w = word.lower()
        if w in self.known or w in self.drugs:
            return True
        return self.spell is not None and self.spell._is_known(w)

    def _drug_suggestions(self, word: str) -> List[str]:
        limit = 1 if len(word) <= 5 else (2 if len(word) <= 9 else 3)
        scored = []
        for n in range(len(word) - limit, len(word) + limit + 1):
            for term in self.drugs_by_len.get(n, []):
                d = _levenshtein(word.lower(), term.lower())
                if d <= limit:
                    scored.append((d, term))
        return [t for _, t in sorted(scored)[: self.n]]

    def _spelling_suggestions(self, tokens: List[str], i: int, word: str) -> List[str]:
        out: List[str] = []
        if self.spell is not None:
            try:
                out += self.spell.suggest(tokens, i, n=self.n)
            except Exception:
                pass
        out += self._drug_suggestions(word)
        seen, unique = set(), []
        for s in out:
            if s.lower() != word.lower() and s.lower() not in seen:
                seen.add(s.lower())
                unique.append(s)
        return unique[: self.n]

    @staticmethod
    def _alternatives(words: List[Dict[str, Any]], readings: Dict[str, str], text: str) -> Dict[int, List[str]]:
        """Word index -> what the other recogniser read at that position."""
        alts: Dict[int, List[str]] = {}
        mine = [(w["word"] or w["token"]).lower() for w in words]
        for reading in readings.values():
            other = _words(reading)
            theirs = [(w["word"] or w["token"]).lower() for w in other]
            if not theirs or difflib.SequenceMatcher(a=text.lower(), b=reading.lower()).ratio() < 0.5:
                continue  # the other reading is a different (garbled) line: nothing to align
            sm = difflib.SequenceMatcher(a=mine, b=theirs, autojunk=False)
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag != "replace":
                    continue
                if i2 - i1 == j2 - j1:
                    pairs = [(i1 + k, other[j1 + k]["word"] or other[j1 + k]["token"]) for k in range(i2 - i1)]
                elif i2 - i1 == 1:  # one word read as several ("Pan D" vs "Pan-D")
                    pairs = [(i1, " ".join(o["token"] for o in other[j1:j2]))]
                else:
                    continue
                for idx, alt in pairs:
                    if words[idx]["word"] and alt.lower() != words[idx]["word"].lower():
                        alts.setdefault(idx, [])
                        if alt not in alts[idx]:
                            alts[idx].append(alt)
        return alts

    def review_block(self, block: Dict[str, Any]) -> List[Dict[str, Any]]:
        text = block.get("text") or ""
        if not text or block.get("role") == "signature":
            return []
        words = _words(text)
        tokens = [w["token"] for w in words]
        conf = float(block.get("confidence") or 0.0)
        handwritten = block.get("source") == "handwritten"
        corrected = {c["to"].lower(): c["from"] for c in block.get("corrections") or [] if c.get("to")}
        alts = self._alternatives(words, block.get("readings") or {}, text) if handwritten else {}
        flags = []
        for i, w in enumerate(words):
            word = w["word"]
            if not word:
                continue
            flag = None
            known = self._is_known(word)
            # Only a real word counts as another reading; the other recogniser's garbles are noise
            other = [a for a in alts.get(i, []) if all(self._is_known(p) for p in re.findall(r"[A-Za-z]+", a))
                     and re.search(r"[A-Za-z]{2}", a)]
            if word.lower() in corrected:
                flag = {"kind": "corrected", "suggestions": [corrected.pop(word.lower())],
                        "reason": "Spelling corrected automatically; the original reading is offered"}
            elif other and len(word) >= 2:
                flag = {"kind": "ambiguous", "suggestions": other[: self.n],
                        "reason": "The two recognisers read this word differently"}
            elif len(word) >= 3 and not word.isupper() and not known:
                neighbours = tokens[max(0, i - 1): i] + tokens[i + 1: i + 2]
                name_like = word[:1].isupper() and i > 0
                near_dose = any(_DOSE_OR_FORM.match(n.strip(",;:")) for n in neighbours)
                if (name_like or near_dose) and (not handwritten or conf >= NAME_CHECK_CONF):
                    continue  # a name / brand on a confident line, or a drug beside its dose
                # Beside a dose / dosage form the word is a medicine: offer drug names, not English words
                suggestions = self._drug_suggestions(word) if near_dose else self._spelling_suggestions(tokens, i, word)
                if not suggestions and conf >= LOW_LINE_CONF:
                    continue  # unknown but nothing close ("datasets", handles): a rare real word, not a misread
                flag = {"kind": "spelling", "suggestions": suggestions,
                        "reason": "Not a known word, drug or abbreviation" if suggestions else
                                  "Not a known word; no close match"}
            if flag:
                flags.append({"word": word, "start": w["start"], "end": w["end"], **flag})
        return flags

    def review(self, blocks: List[Dict[str, Any]]) -> Dict[str, int]:
        flagged = lines = 0
        for b in blocks:
            flags = self.review_block(b)
            if flags:
                b["review"] = flags
                flagged += len(flags)
            if b.get("text") and b.get("role") != "signature" and float(b.get("confidence") or 0.0) < LOW_LINE_CONF:
                b["needs_review"] = True
                lines += 1
        return {"flagged_words": flagged, "lines_to_check": lines}
