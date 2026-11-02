"""
Structured extraction and clinical validation over OCR output (reading-ordered blocks).

Never edits the OCR text: it returns facts with provenance (source block ids) for the studio / HIS:
  document_type   prescription | lab_report | form | note
  patient fields  patient_name, age, sex, date, doctor
  medications     form, drug (+ normalized lexicon match), strength, frequency, duration, timing, route
                  - a dose-only line ("1 - 0 - 1 x 5days") attaches to the medicine above it
                  - a margin note ("after meals") applies to the medicines its brace spans
  lab_results     test, value, unit, reference range, flag (H / L)
  key_values      "Key: value" pairs of forms
  issues          validation findings (strength unit vs form, implausible frequency / duration, unknown drug)
"""
import re
from typing import Callable, Dict, List, Optional, Sequence

FORMS = {
    "tab": "Tab", "tabs": "Tab", "tablet": "Tab", "cap": "Cap", "caps": "Cap", "capsule": "Cap", "syp": "Syp",
    "syr": "Syp", "syrup": "Syp", "inj": "Inj", "injection": "Inj", "oint": "Oint", "ointment": "Oint",
    "gel": "Gel", "drop": "Drops", "drops": "Drops", "susp": "Susp", "cream": "Cream", "inh": "Inh", "sachet": "Sachet",
}
LIQUID_FORMS = {"Syp", "Susp", "Drops", "Inj"}
SOLID_FORMS = {"Tab", "Cap", "Sachet"}

_NUM = r"\d+(?:\.\d+)?"
_STRENGTH = re.compile(rf"\b({_NUM})\s*(mg|mcg|g|gm|ml|iu|%)(?![a-z/])", re.IGNORECASE)
_FREQ_DIGITS = re.compile(r"(?<![\d/])([0-2](?:/2)?|½)\s*[-–—]+\s*([0-2](?:/2)?|½)\s*[-–—]+\s*([0-2](?:/2)?|½)(?:\s*[-–—]+\s*([0-2]))?(?![\d/])")
_FREQ_WORDS = re.compile(r"\b(OD|BD|BID|TDS|TID|QID|QDS|Q\d{1,2}H|QHS|HS|SOS|PRN|STAT|once daily|twice daily|thrice daily|at night|at bedtime)\b", re.IGNORECASE)
_DURATION = re.compile(rf"(?:\bx|\bfor|×)\s*({_NUM})\s*(days?|d|weeks?|wks?|w|months?|m)\b|\b({_NUM})\s*(days?|weeks?|months?)\b", re.IGNORECASE)
_TIMING = re.compile(r"\b(after (?:meals?|food|breakfast|lunch|dinner)|before (?:meals?|food|breakfast|lunch|dinner)|"
                     r"empty stomach|with (?:meals?|food|milk|water)|at bedtime|AC|PC)\b", re.IGNORECASE)
_TIMING_TAIL = re.compile(r"(?:meals?|food|breakfast|lunch|dinner)", re.IGNORECASE)
_FUSED_TIMING = re.compile(r"^\s*(before|after)\b[\s&,.-]*(?=(?:tab|cap|syp|inj|oint|gel|drops?|susp|t|c)\b)", re.IGNORECASE)
# Syrup / suspension concentration written after the name: "Calpol (250/5)" = 250 mg per 5 ml
_CONCENTRATION = re.compile(r"\(\s*(\d+(?:\.\d+)?\s*(?:mg)?\s*/\s*\d+(?:\.\d+)?\s*(?:ml)?)\s*\)", re.IGNORECASE)
_WEIGHT = re.compile(r"\b(?:Weight|Wt)\.?\s*[:=\-]?\s*(\d{1,3}(?:\.\d{1,2})?)\s*(kg|kgs)\b", re.IGNORECASE)
# "Review after 5 days" carries a duration but is the follow-up, not a dosing line of the medicine above it
_FOLLOW_UP = re.compile(r"^\W*(?:review|follow[\s-]?up|f/u|revisit|next\s+visit|come\s+(?:back|again))\b", re.IGNORECASE)
_ROUTE = re.compile(r"\b(oral(?:ly)?|topical(?:ly)?|IV|IM|SC|sublingual|inhal(?:ed|ation))\b", re.IGNORECASE)
_LAB = re.compile(rf"^(?P<test>[A-Za-z][A-Za-z0-9 ()/.,'-]{{1,40}}?)\s+(?P<value>[<>]?\s*{_NUM})\s*(?P<unit>[a-zA-Z%/µ^0-9.]+(?:/[a-zA-Z.]+)?)?"
                  rf"\s+(?P<range>(?:[<>]\s*{_NUM})|(?:{_NUM}\s*[-–]\s*{_NUM}))\s*$")
_KV = re.compile(r"(?P<key>[A-Z][A-Za-z .'/()-]{1,30}?)\s*:\s*(?P<value>[^:]+?)(?=\s{2,}[A-Z][A-Za-z .'/()-]{1,30}?\s*:|$)")
_DATE = re.compile(r"\b(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}|\d{4}-\d{2}-\d{2})\b")
_AGE_SEX = re.compile(r"\b(\d{1,3})\s*(?:y(?:rs?|ears?)?)?\s*[/,]\s*(m|f|male|female)\b", re.IGNORECASE)
_AGE = re.compile(r"\bAge\s*[:=]?\s*(\d{1,3})", re.IGNORECASE)
_SEX = re.compile(r"\b(?:Sex|Gender)\s*[:=]?\s*(male|female|m|f)\b", re.IGNORECASE)
_NAME = re.compile(r"(?:\b(?:Patient(?:'s)?(?:[ \t]+Name)?|Pt\.?|Name)[ \t]*[:\-][ \t]*|\b(?:Mr|Mrs|Ms|Miss|Master)\.?[ \t]+)"
                   r"(?P<name>[A-Z][A-Za-z.]*(?: [A-Z][A-Za-z.]*){0,3})")
_DOCTOR = re.compile(r"\b(Dr\.?[ \t]+[A-Z][A-Za-z.]*(?: [A-Z][A-Za-z.]*){0,3})")
_FIELD_LABELS = {"ref", "age", "sex", "date", "gender", "dob", "ward", "bed", "id", "uhid", "mrn", "phone", "ph", "ipd", "opd", "no"}
_ADVICE = re.compile(r"^\s*(?:Adv|Advice|Apply|Local)\s*[:.\-]\s*(?P<rest>.+)$", re.IGNORECASE)
_LABELLED_LINE = re.compile(r"^\s*[A-Za-z][A-Za-z .'/()]{1,30}:")
_INSTRUCTION = re.compile(r"\b(as directed|as needed(?: for [a-z]+)?|when required|if required|every \d+ (?:hours?|hrs?)|"
                          r"take (?:once|twice|thrice|three times) (?:a day|daily))\b", re.IGNORECASE)
# Field labels as handwriting recognition garbles them ("Pauent:", "Apr: 42"): (label, edit budget, value shape
# that allows one more edit)
_LABEL_FORMS = (("Patient", 2, None), ("Name", 1, None), ("Age", 1, r"\s*\d{1,3}\b"), ("Sex", 1, r"\s*[MFmf]\b"),
                ("Gender", 2, None), ("Date", 1, r"\s*\d"))
_REAL_LABELS = _FIELD_LABELS | {"bed", "ward", "room", "unit", "dept", "reg", "tel", "fax", "rx", "adv", "ref", "mob", "pin",
                                 "fee", "time", "bp", "pulse", "temp", "wt", "ht", "weight", "height", "spo", "rr", "hr"}
_GARBLED_MR = re.compile(r"(?<![A-Za-z])(?:Me|Mi|Hr|Nr|Mn|MR)\.?(?=[ \t]+[A-Z][a-z]+[ \t]+[A-Z][a-z]+)")
_LABEL_TOKEN = re.compile(r"(?<![A-Za-z])([A-Za-z]{3,8})(?=\s*:)")


def _edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _repair_labels(text: str) -> str:
    """Field-label spellings fixed for field extraction only (the OCR text shown to the user is untouched)."""
    def fix(m):
        word, after = m.group(1), text[m.end():]
        if word.lower() in _REAL_LABELS:
            return word  # "Bed: 12", "Ref: 123" are labels of their own, not a garbled "Age"
        best = []
        for label, budget, shape in _LABEL_FORMS:
            if shape and re.match(r"\s*:" + shape, after):
                budget += 1
            d = _edit_distance(word.lower(), label.lower())
            if d <= min(budget, len(label) - 1):
                best.append((d, label))
        best.sort()
        if not best or (len(best) > 1 and best[0][0] == best[1][0]):
            return word
        return best[0][1]
    text = _LABEL_TOKEN.sub(fix, text)
    # A garbled honorific before a full name ("Me Sachin Sansare", "Hr. Ravi Kumar") is "Mr."
    return _GARBLED_MR.sub("Mr.", text)


def _clean_name(name: str) -> str:
    words = []
    for w in name.split(" "):
        if w.lower().strip(".:") in _FIELD_LABELS or not w:
            break
        words.append(w)
    return " ".join(words).strip(" .")


def _norm_freq(m) -> str:
    parts = [p for p in m.groups() if p]
    return "-".join(p.replace("½", "1/2") for p in parts)


def _norm_duration(text: str) -> Optional[str]:
    m = _DURATION.search(text)
    if not m:
        return None
    num = m.group(1) or m.group(3)
    unit = (m.group(2) or m.group(4) or "").lower()
    unit = {"d": "days", "day": "days", "w": "weeks", "wk": "weeks", "wks": "weeks", "week": "weeks",
            "m": "months", "month": "months"}.get(unit, unit)
    if num == "1" and unit.endswith("s"):
        unit = unit[:-1]
    return f"{num} {unit}"


class MedicalStructurer:
    def __init__(self, drug_lexicon: Sequence[str] = (), common_words: Sequence[str] = ()):
        self.drugs = {d.lower(): d for d in drug_lexicon}
        self.common = {w.lower() for w in common_words}

    # ------------------------------------------------------------------
    def _match_drug(self, word: str) -> Optional[str]:
        w = re.sub(r"[^a-z0-9-]", "", word.lower())
        if not w:
            return None
        if w in self.drugs:
            return self.drugs[w]
        from app.ai.ocr.htr_engine import _levenshtein
        best, best_d = None, 3
        for key, canon in self.drugs.items():
            if abs(len(key) - len(w)) > 2 or key[:1] != w[:1]:
                continue
            d = _levenshtein(w, key)
            limit = 1 if len(w) <= 6 else 2
            if d <= limit and d < best_d:
                best, best_d = canon, d
        return best

    @staticmethod
    def _fused_margin_timing(body: List[Dict], timing_for: Dict[str, str]) -> None:
        """A margin "before" / "after" the detector fused onto the front of a medicine line, with its second word
        ("meals") left alone on the next row, is cut off the line and applied to it."""
        for i, b in enumerate(body):
            m = _FUSED_TIMING.match(b["text"])
            if not m or b.get("role") == "margin_note":
                continue
            rest = body[i + 1:i + 3]
            tail = next((n for n in rest if _TIMING_TAIL.fullmatch(n["text"].strip())), None)
            if tail is None:
                continue
            timing_for[b.get("id")] = f"{m.group(1).lower()} {tail['text'].strip().lower()}"
            b["text"] = b["text"][m.end(1):].lstrip(" &,.-")
            tail["text"] = ""

    def _parse_med_line(self, text: str) -> Optional[Dict]:
        advice = _ADVICE.match(text)
        if advice:
            text = advice.group("rest")
        elif _LABELLED_LINE.match(text) and not re.search(r"\b(?:Tab|Cap|Syp|Inj)\b", text, re.IGNORECASE):
            return None  # "Patient: ...", "Diagnosis: ..." are fields, not medicines
        tokens = text.replace(",", " ").split()
        form, drug_tokens, idx = None, [], 0
        for i, t in enumerate(tokens[:2]):
            key = t.lower().rstrip(".:")
            # A form starts the line (after at most a list number or "Rx"): "Cap." inside a sentence is not one
            if key in FORMS and (i == 0 or re.fullmatch(r"\(?\d{1,2}[.)]?|rx|r/", tokens[0].lower())):
                form, idx = FORMS[key], i + 1
                break
        rest = tokens[idx:] if form else tokens
        for t in rest:
            if _STRENGTH.match(t) or re.match(r"^[\d(]", t) or _FREQ_WORDS.fullmatch(t) or t.lower() in ("x", "-", "—"):
                break
            # Brand / generic names: the first word, then only capitalised or hyphenated / numbered parts
            # ("Pan-D", "Liv 52", "Cough Relief"); lowercase words ("gum paint") describe the form
            if drug_tokens and not (t[:1].isupper() or "-" in t or any(c.isdigit() for c in t)):
                break
            drug_tokens.append(t.strip(".:"))
            if len(drug_tokens) == 3:
                break
        # The preparation written after the name, kept as read ("Hexigel gum paint", "Chlorhexidine mouth wash")
        preparation = []
        after = rest[len(drug_tokens):] if drug_tokens else []
        for k, t in enumerate(after):
            tail = " ".join(after[k:])
            if not re.fullmatch(r"[a-z]{2,}", t) or len(preparation) == 3 or t in ("for", "x") \
                    or any(p.match(tail) for p in (_FREQ_WORDS, _TIMING, _INSTRUCTION, _DURATION)):
                break
            preparation.append(t)
        concentration = _CONCENTRATION.search(text)
        strength = _STRENGTH.search(_CONCENTRATION.sub(" ", text))
        freq = _FREQ_DIGITS.search(text)
        freq_w = _FREQ_WORDS.search(text)
        duration = _norm_duration(text)
        timing = _TIMING.search(text)
        drug = " ".join(drug_tokens).strip("-")
        lexicon_hit = None
        if drug:
            lexicon_hit = self._match_drug(drug_tokens[0]) or self._match_drug(drug.replace(" ", ""))
        instruction = _INSTRUCTION.search(text)
        has_sig = bool(freq or freq_w or duration or instruction)
        first = drug_tokens[0].lower().strip(".:") if drug_tokens else ""
        looks_like_drug = bool(drug_tokens) and drug_tokens[0][:1].isupper() and first not in self.common \
            and not drug.isupper()
        # Without a dosage form, a line is a medication only with medication evidence beside the name:
        # an advice line ("Adv: Hexigel gum paint"), or a strength / dosing instruction on the same line
        if not form and not (looks_like_drug and (advice or ((lexicon_hit or strength) and (strength or has_sig)))):
            return {"sig_only": True, "frequency": _norm_freq(freq) if freq else (freq_w.group(1).upper() if freq_w else None),
                    "duration": duration, "timing": timing.group(1).lower() if timing else None,
                    "instructions": instruction.group(1).lower() if instruction else None} if has_sig else None
        return {
            "form": form or "", "drug": drug, "normalized_drug": lexicon_hit,
            "strength": f"{strength.group(1)}{strength.group(2).lower()}" if strength else "",
            "frequency": _norm_freq(freq) if freq else (freq_w.group(1).upper() if freq_w else ""),
            "duration": duration or "", "timing": timing.group(1).lower() if timing else "",
            "instructions": instruction.group(1).lower() if instruction else "",
            "route": (_ROUTE.search(text).group(1).lower() if _ROUTE.search(text) else ""),
            "preparation": " ".join(preparation),
            "concentration": re.sub(r"\s+", "", concentration.group(1)) if concentration else "",
        }

    def _validate(self, med: Dict) -> List[str]:
        issues = []
        unit = re.sub(r"[\d.]", "", med.get("strength", ""))
        if med.get("form") in SOLID_FORMS and unit == "ml":
            issues.append("strength in ml for a solid dosage form")
        if med.get("form") in LIQUID_FORMS - {"Inj"} and unit in ("mg",) and not med.get("strength", "").endswith("ml"):
            pass  # syrups are often prescribed by mg; not an error
        freq = med.get("frequency", "")
        if re.fullmatch(r"[0-2/-]+", freq or "") and all(p in ("0",) for p in freq.split("-")):
            issues.append("frequency 0-0-0")
        dur = med.get("duration", "")
        m = re.match(r"(\d+)\s*(\w+)", dur or "")
        if m and ((m.group(2).startswith("day") and int(m.group(1)) > 365) or int(m.group(1)) == 0):
            issues.append("implausible duration")
        if med.get("drug") and not med.get("normalized_drug"):
            issues.append("drug not found in lexicon (verify spelling)")
        elif med.get("normalized_drug") and med["normalized_drug"].lower() not in \
                {med["drug"].lower(), med["drug"].lower().replace(" ", ""), med["drug"].split()[0].lower()}:
            issues.append(f"drug matched approximately to {med['normalized_drug']} (verify)")
        return issues

    # ------------------------------------------------------------------
    def extract(self, blocks: List[Dict]) -> Dict:
        body = [dict(b) for b in blocks if b.get("role") not in ("signature",) and b.get("text")]  # copies: never edit OCR output
        body.sort(key=lambda b: (b.get("page", 1), b.get("reading_order", 0)))  # reading order, not detector order
        full = _repair_labels("\n".join(b["text"] for b in body))
        out: Dict = {"document_type": "note", "medications": [], "lab_results": [], "key_values": [], "issues": []}

        # Patient / encounter fields
        m = _NAME.search(full)
        if m:
            out["patient_name"] = _clean_name(m.group("name"))
        m = _AGE_SEX.search(full)
        if m:
            out["age"], out["sex"] = m.group(1), m.group(2)[0].upper()
        else:
            if _AGE.search(full):
                out["age"] = _AGE.search(full).group(1)
            if _SEX.search(full):
                out["sex"] = _SEX.search(full).group(1)[0].upper()
        m = _DATE.search(full)
        if m:
            out["date"] = m.group(1)
        m = _DOCTOR.search(full)
        if m:
            out["doctor"] = _clean_name(m.group(1))
        m = _WEIGHT.search(full)
        if m:
            out["weight"] = f"{m.group(1)} kg"

        # Margin-note timing applies to the blocks it spans; a note written over two lines ("after" / "meals")
        # is several blocks sharing one scope, so they are read together
        timing_for: Dict[str, str] = {}
        notes: Dict[tuple, List[Dict]] = {}
        for b in blocks:
            if b.get("role") == "margin_note" and b.get("applies_to"):
                notes.setdefault(tuple(b["applies_to"]), []).append(b)
        for scope, group in notes.items():
            group.sort(key=lambda b: (b.get("reading_order", 0), (b.get("bbox") or [0, 0])[1]))
            timing = _TIMING.search(" ".join(b.get("text", "") for b in group))
            if timing:
                for bid in scope:
                    timing_for[bid] = timing.group(1).lower()
        self._fused_margin_timing(body, timing_for)

        # Table rows of a report arrive as cell blocks ("Hemoglobin 13.8" | "g/dL 12.0 - 15.5"): read lab rows whole
        in_lab_row = set()
        rows: Dict[tuple, List[Dict]] = {}
        for b in body:
            if b.get("line_number") is not None and b.get("role") != "margin_note":
                rows.setdefault((b.get("page", 1), b["line_number"]), []).append(b)
        for cells in rows.values():
            if len(cells) < 2:
                continue
            cells.sort(key=lambda b: b.get("reading_order", 0))
            row_text = " ".join(c["text"].strip() for c in cells)
            lab = _LAB.match(row_text)
            if lab and not _FREQ_DIGITS.search(row_text):
                entry = self._lab_entry(lab, cells[0])
                entry["source_blocks"] = [c.get("id") for c in cells]
                out["lab_results"].append(entry)
                in_lab_row.update(id(c) for c in cells)

        meds: List[Dict] = []
        after_med = False  # the previous line was a medicine or its dosing line
        for b in body:
            if b.get("role") == "margin_note" or id(b) in in_lab_row:
                continue
            text = b["text"]
            if not text.strip():
                continue  # consumed above (the "meals" of a fused margin timing)
            lab = _LAB.match(text.strip())
            if lab and not _FREQ_DIGITS.search(text):
                out["lab_results"].append(self._lab_entry(lab, b))
                after_med = False
                continue
            parsed = self._parse_med_line(text)
            if _FOLLOW_UP.match(text):
                out.setdefault("follow_up", text.strip())
                after_med = False
                continue
            # The rest of a medicine line wrapped onto its own row ("Hexigel gum paint" / "massage")
            if parsed is None and after_med and meds and re.fullmatch(r"[a-z]{3,}(?: [a-z]{2,}){0,2}\.?", text.strip()):
                last = meds[-1]
                key = "preparation" if last.get("preparation") and not last.get("frequency") else "instructions"
                last[key] = f"{last.get(key) or ''} {text.strip().rstrip('.')}".strip()
                last["source_blocks"].append(b.get("id"))
                continue
            if parsed is not None and parsed.get("sig_only") and not after_med:
                parsed = None  # a duration elsewhere on the page ("C/O fever x 3 days") is not the medicine's dosing
            after_med = parsed is not None
            if parsed is None:
                if ":" in text and not parsed:
                    for kv in _KV.finditer(text):
                        out["key_values"].append({"key": kv.group("key").strip(), "value": kv.group("value").strip(),
                                                  "source_blocks": [b.get("id")]})
                continue
            if parsed.get("sig_only"):
                if meds:
                    last = meds[-1]
                    for k in ("frequency", "duration", "timing", "instructions"):
                        if parsed.get(k) and not last.get(k):
                            last[k] = parsed[k]
                    last["source_blocks"].append(b.get("id"))
                continue
            parsed["source_blocks"] = [b.get("id")]
            meds.append(parsed)
        for med in meds:
            if not med.get("timing"):
                for bid in med["source_blocks"]:
                    if bid in timing_for:
                        med["timing"] = timing_for[bid]
                        break
            med["issues"] = self._validate(med)
            out["issues"].extend(f"{med.get('drug') or 'medication'}: {i}" for i in med["issues"])
        out["medications"] = meds

        title = "\n".join(b["text"] for b in body[:4]).lower()
        titled = [(k, t) for k, t in (("discharge summary", "discharge_summary"), ("consent", "consent_form"),
                                       ("referral", "referral_form"), ("admission", "admission_form"),
                                       ("progress note", "clinical_note"), ("clinical note", "clinical_note"),
                                       ("biochemistry", "lab_report"), ("laboratory", "lab_report"),
                                       ("pathology", "lab_report")) if k in title]
        if titled:
            out["document_type"] = titled[0][1]
        elif meds and (re.search(r"\bR[x×]\b|\bTab\b|\bCap\b", full) or len(meds) >= 2):
            out["document_type"] = "prescription"
        elif len(out["lab_results"]) >= 2:
            out["document_type"] = "lab_report"
        elif len(out["key_values"]) >= 3:
            out["document_type"] = "form"
        return out

    @staticmethod
    def _lab_entry(m, block) -> Dict:
        value = m.group("value").replace(" ", "")
        rng = m.group("range").replace(" ", "")
        flag = ""
        try:
            v = float(value.lstrip("<>"))
            if "-" in rng or "–" in rng:
                lo, hi = [float(x) for x in re.split(r"[-–]", rng)]
                flag = "H" if v > hi else ("L" if v < lo else "")
            elif rng.startswith("<"):
                flag = "H" if v >= float(rng[1:]) else ""
            elif rng.startswith(">"):
                flag = "L" if v <= float(rng[1:]) else ""
        except ValueError:
            pass
        return {"test": m.group("test").strip(), "value": value, "unit": (m.group("unit") or "").strip(),
                "reference_range": rng, "flag": flag, "source_blocks": [block.get("id")]}
