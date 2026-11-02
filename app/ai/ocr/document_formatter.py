"""
Formatted reading of a document: the text a clinician would retype, built from the layout roles and the
structured extraction, so detector order (margin notes, table cells, wrapped lines) reads as a document.

  letterhead lines first, footer last, a detected signature as "[Signature]"
  one patient line ("Patient: ... | Age/Sex: ... | Date: ...") when those fields were found
  prescriptions  "Rx" and one numbered line per medicine with dose, frequency, duration, timing and
                 instructions; a margin note such as "after meals" is folded into the medicines it covers
  lab reports    one row per test: name | result unit | reference range | HIGH / LOW
  other text     wrapped lines rejoined into paragraphs; list items, "Label: value" rows and headings
                 stay on their own lines; blank lines between paragraphs
The as-read text (raw_text) is unchanged; this is an additional view.
"""
import json
import os
import re
from typing import Any, Callable, Dict, List, Optional

_LIST_ITEM = re.compile(r"^\s*(?:[-*•→>]|\d{1,2}[.)]|[a-z][.)])\s+")
_LABEL_ROW = re.compile(r"^\s*[A-Za-z][\w /()'.&-]{0,30}\s*:\s*\S")
_TERMINAL = re.compile(r"[.!?:;]\s*$")
_DATE = re.compile(r"\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b")
_AGE_SEX = re.compile(r"\b\d{1,3}\s*(?:y(?:rs?|ears?)?)?\s*[/,]\s*(?:m|f|male|female)\b", re.IGNORECASE)
_WEIGHT = re.compile(r"\b\d{1,3}(?:\.\d{1,2})?\s*kgs?\b", re.IGNORECASE)
_FIELD_WORDS = re.compile(r"\b(?:patient(?:'s)?|name|pt|age|sex|gender|date|dob|mr|mrs|ms|miss|master|smt|shri|me|"
                          r"ref(?:erred)?(?:[ \t]+by)?|consultant|doctor|dr|weight|wt)\b\.?", re.IGNORECASE)


def _rows(blocks: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """Reading rows (blocks sharing page + line number), in reading order."""
    rows: Dict[tuple, List[Dict[str, Any]]] = {}
    for b in sorted(blocks, key=lambda b: (b.get("page", 1), b.get("reading_order", 0))):
        if (b.get("text") or "").strip():
            rows.setdefault((b.get("page", 1), b.get("line_number", b.get("reading_order", 0))), []).append(b)
    return list(rows.values())


def _row_text(row: List[Dict[str, Any]]) -> str:
    """Cells far apart on the page (table columns) are separated by " | ", neighbouring fragments by a space."""
    parts, prev = [], None
    for b in sorted(row, key=lambda b: (b.get("bbox") or [0])[0]):
        text = b["text"].strip()
        if prev is not None:
            h = max(1, (b["bbox"][3] - b["bbox"][1]) if b.get("bbox") else 20)
            gap = (b["bbox"][0] - prev["bbox"][2]) if b.get("bbox") and prev.get("bbox") else 0
            parts.append(" | " if gap > 2.5 * h else " ")
        parts.append(text)
        prev = b
    return "".join(parts)


def _med_line(n: int, m: Dict[str, Any]) -> str:
    drug = m.get("drug") or ""
    if drug.isupper() and (m.get("normalized_drug") or "").lower() == drug.lower():
        drug = m["normalized_drug"]  # "CALPOL" written in capitals: the lexicon's spelling reads better
    conc = f"({m['concentration']})" if m.get("concentration") else ""
    head = " ".join(p for p in (m.get("form"), drug, conc, m.get("preparation"), m.get("strength")) if p)
    sig = []
    if m.get("frequency"):
        sig.append(m["frequency"])
    if m.get("duration"):
        sig.append(f"for {m['duration']}" if sig else m["duration"])
    details = [" ".join(sig)] if sig else []
    details += [m[k] for k in ("timing", "instructions", "route") if m.get(k)]
    return f"{n}. {head}" + (f" — {', '.join(details)}" if details else "")


def _lab_line(r: Dict[str, Any]) -> str:
    cells = [r.get("test", ""), " ".join(p for p in (r.get("value"), r.get("unit")) if p)]
    if r.get("reference_range"):
        cells.append(f"ref {r['reference_range']}")
    if r.get("flag"):
        cells.append({"H": "HIGH", "L": "LOW"}.get(r["flag"], r["flag"]))
    return " | ".join(c for c in cells if c)


def _patient_line(s: Dict[str, Any]) -> Optional[str]:
    parts = []
    if s.get("patient_name"):
        parts.append(f"Patient: {s['patient_name']}")
    age_sex = "/".join(p for p in (s.get("age"), s.get("sex")) if p)
    if age_sex:
        parts.append(f"{'Age/Sex' if s.get('age') and s.get('sex') else ('Age' if s.get('age') else 'Sex')}: {age_sex}")
    if s.get("weight"):
        parts.append(f"Weight: {s['weight']}")
    if s.get("date"):
        parts.append(f"Date: {s['date']}")
    if s.get("doctor"):
        parts.append(f"Doctor: {s['doctor']}")
    return " | ".join(parts) if parts else None


def _explained_by_fields(text: str, s: Dict[str, Any]) -> bool:
    """True when a row holds nothing but the patient fields already shown on the patient line."""
    rest = _field_leftover(text, s)
    return rest is not None and len(re.sub(r"[^A-Za-z0-9]", "", rest)) <= 2


def _field_leftover(text: str, s: Dict[str, Any]) -> Optional[str]:
    """What is left of a row once the patient fields are taken out; None when the row holds none of them."""
    rest, found = text, False
    for value in (s.get("patient_name"), s.get("doctor")):
        if value and value in rest:
            rest, found = rest.replace(value, " "), True
    for field, pattern in (("date", _DATE), ("age", _AGE_SEX), ("weight", _WEIGHT)):
        if s.get(field) and pattern.search(rest):
            rest, found = pattern.sub(" ", rest), True
    rest = _FIELD_WORDS.sub(" ", rest)
    if s.get("age") and re.search(rf"\b{re.escape(s['age'])}\b", rest):
        rest, found = re.sub(rf"\b{re.escape(s['age'])}\b", " ", rest), True
    return " ".join(rest.split()) if found else None


def _mentions_fields(text: str, s: Dict[str, Any]) -> bool:
    return bool((s.get("patient_name") and s["patient_name"] in text) or (s.get("date") and s["date"] in text))


def _reflow(lines: List[str], is_word: Optional[Callable[[str], bool]] = None) -> List[str]:
    """Rejoin wrapped lines into paragraphs; keep list items, label rows and headings on their own lines."""
    out: List[str] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        standalone = bool(_LIST_ITEM.match(line) or _LABEL_ROW.match(line) or " | " in line)
        if out and not standalone and out[-1] and line[:1].islower():
            prev = out[-1]
            prev_standalone = bool(_LIST_ITEM.match(prev) or _LABEL_ROW.match(prev) or " | " in prev)
            if not _TERMINAL.search(prev) and (not prev_standalone or _LIST_ITEM.match(prev)):
                tail, head = prev.split()[-1], line.split()[0]
                if prev.endswith("-") and not prev.endswith(" -"):
                    out[-1] = prev[:-1] + line  # hyphenated word split across lines
                elif is_word and tail.isalpha() and head.isalpha() and not is_word(tail) and is_word(tail + head):
                    out[-1] = prev + line  # word broken across lines without a hyphen ("recommenda" / "tion")
                else:
                    out[-1] = f"{prev} {line}"
                continue
        if out and out[-1] and (standalone != bool(_LIST_ITEM.match(out[-1]) or _LABEL_ROW.match(out[-1]))):
            out.append("")  # blank line between a run of list / label rows and prose
        out.append(line)
    return out


def _y_iou(a: List[float], b: List[float]) -> float:
    inter = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    union = max(a[3], b[3]) - min(a[1], b[1])
    return inter / union if union > 0 else 0.0


def _columns(blocks: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """
    A page's body split at a clear vertical gutter into reading columns (main text, then side notes), unless the
    two sides line up row by row like a table or form, in which case rows are kept across the gutter.
    """
    boxed = [b for b in blocks if b.get("bbox")]
    if len(boxed) < 5:
        return [blocks]
    h = sorted(b["bbox"][3] - b["bbox"][1] for b in boxed)[len(boxed) // 2]
    spans = sorted((b["bbox"][0], b["bbox"][2]) for b in boxed)
    gaps, reach = [], spans[0][1]
    for x0, x1 in spans[1:]:
        if x0 > reach:
            gaps.append((x0 - reach, reach, x0))
        reach = max(reach, x1)
    gaps = [g for g in gaps if g[0] >= 1.5 * h]
    if not gaps:
        return [blocks]
    _, g0, g1 = max(gaps)
    left = [b for b in blocks if b.get("bbox") and b["bbox"][2] <= g0]
    right = [b for b in blocks if b.get("bbox") and b["bbox"][0] >= g1]
    if len(left) < 2 or len(right) < 2 or len(left) + len(right) < len(boxed):
        return [blocks]
    # Table / form: cells on the two sides share their rows closely
    small, big = (left, right) if len(left) <= len(right) else (right, left)
    aligned = sorted(max(_y_iou(b["bbox"], o["bbox"]) for o in big) for b in small)
    if aligned[len(aligned) // 2] >= 0.5:
        return [blocks]
    return [left, right]


def _collect(blocks: List[Dict[str, Any]], s: Dict[str, Any]):
    """Letterhead, footer and body rows in reading order (None marks a column break), margin notes by target."""
    meds = s.get("medications") or []
    labs = s.get("lab_results") or []
    med_ids = {i for m in meds for i in m.get("source_blocks") or []}
    lab_ids = {i for r in labs for i in r.get("source_blocks") or []}
    by_id = {b.get("id"): b for b in blocks}

    header, footer, body, notes_for = [], [], [], {}
    signature = False
    for b in blocks:
        if b.get("role") == "margin_note":
            covered = set(b.get("applies_to") or [])
            # A margin note whose timing was folded into the medicines it covers is not repeated
            if not (covered & med_ids and any(m.get("timing") for m in meds if covered & set(m.get("source_blocks") or []))):
                target = next((t for t in b.get("applies_to") or [] if t in by_id), None)
                notes_for.setdefault(target, []).append(b["text"].strip())
    content = [b for b in blocks if b.get("role") != "margin_note"]
    ordered_rows = []
    for page in sorted({b.get("page", 1) for b in content}):
        on_page = [b for b in content if b.get("page", 1) == page]
        top = [b for b in on_page if b.get("role") == "header"]
        bottom = [b for b in on_page if b.get("role") in ("footer", "signature")]
        middle = [b for b in on_page if b.get("role") not in ("header", "footer", "signature")]
        ordered_rows += _rows(top)
        for n, column in enumerate(_columns(middle)):
            if n:
                ordered_rows.append(None)  # column break: the side column starts its own paragraph
            ordered_rows += _rows(column)
        ordered_rows += _rows(bottom)
    for row in ordered_rows:
        if row is None:
            body.append((None, None))
            continue
        if any(b.get("role") == "signature" for b in row):
            signature = True
            row = [b for b in row if b.get("role") != "signature"]
            if not row:
                continue
        roles = {b.get("role") for b in row}
        text = _row_text(row)
        notes = [n for b in row for n in notes_for.pop(b.get("id"), [])]
        if notes:
            text += f"  (note: {'; '.join(notes)})"
        if roles <= {"header"}:
            header.append(text)
        elif roles <= {"footer"}:
            footer.append(text)
        else:
            body.append((row, text))

    return header, footer, body, notes_for, signature, meds, labs, med_ids, lab_ids


def _plain(header, footer, body, notes_for, signature, s, meds, labs, med_ids, lab_ids, is_word) -> str:
    out: List[str] = list(header)
    patient = _patient_line(s)
    pending: List[str] = []
    meds_done = labs_done = patient_done = False

    def flush():
        if pending:
            out.extend([""] + _reflow(pending, is_word) if out else _reflow(pending, is_word))
            pending.clear()

    def emit_patient():
        nonlocal patient_done
        if patient and not patient_done:
            flush()
            out.extend(([""] if out else []) + [patient])
            patient_done = True

    for row, text in body:
        if row is None:
            flush()
            continue
        ids = {b.get("id") for b in row}
        if patient and not patient_done and (_explained_by_fields(text, s) or ids & (med_ids | lab_ids)
                                             or _mentions_fields(text, s)):
            emit_patient()  # where the patient details sit on the page (below the letterhead)
        if ids & med_ids:
            if not meds_done:
                flush()
                out.extend(([""] if out else []) + ["Rx"] + [_med_line(n, m) for n, m in enumerate(meds, 1)])
                meds_done = True
            continue
        if ids & lab_ids:
            if not labs_done:
                flush()
                out.extend(([""] if out else []) + [_lab_line(r) for r in labs])
                labs_done = True
            continue
        if re.fullmatch(r"\s*R[xₓ]\s*\.?\s*", text) and meds:
            continue  # the printed "Rx" mark; the list above carries its own
        if patient and _explained_by_fields(text, s):
            continue
        rest = _field_leftover(text, s) if patient and out and out[-1] == patient else None
        if rest and len(rest.split()) <= 2 and len(rest) <= 10:
            out[-1] = f"{patient} | {rest}"  # the patient row with a short unparsed bit ("28 mg"): keep it there once
            continue
        pending.append(text)
    flush()
    if patient and not patient_done:  # no row carried the fields: the patient line goes under the letterhead
        out[len(header):len(header)] = ([""] if header else []) + [patient] + ([""] if len(out) > len(header) else [])
    leftover = [n for ns in notes_for.values() for n in ns]
    if leftover:
        out += ["", "Notes: " + "; ".join(leftover)]
    if signature:
        out += ["", "[Signature]"]
    if footer:
        out += [""] + footer
    text = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


# ---------------------------------------------------------------------------------------------------------------
# Clinical pages: a fixed section order from a template (the hospital's format), whatever order the page is in

_VITALS = re.compile(r"\b(?:B\.?P|pulse|P\.?R|H\.?R|temp(?:erature)?|SpO2|R\.?R|RBS|GRBS|BMI|ht|height|wt|weight)"
                     r"\b\.?\s*[-:=]?\s*\d", re.IGNORECASE)
_FOLLOW_UP = re.compile(r"\b(?:review|follow[\s-]?up|f/u|revisit|next\s+visit|come\s+(?:back|again))\b", re.IGNORECASE)
_RX_MARK = re.compile(r"\s*R[xₓ]\s*\.?\s*")
_TEMPLATE_CACHE: Dict[str, Dict[str, Any]] = {}


def load_template(path: Optional[str] = None) -> Dict[str, Any]:
    """The section template: OCR_FORMAT_TEMPLATE (the hospital's format) or the bundled format_template.json."""
    path = path or os.getenv("OCR_FORMAT_TEMPLATE") or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                                     "format_template.json")
    if path not in _TEMPLATE_CACHE:
        with open(path, "r", encoding="utf-8") as f:
            _TEMPLATE_CACHE[path] = prepare_template(json.load(f))
    return _TEMPLATE_CACHE[path]


def prepare_template(template: Dict[str, Any]) -> Dict[str, Any]:
    """Adds the fixed sections a template leaves out (at the end) and compiles its heading matcher."""
    keys = [sec["key"] for sec in template["sections"]]
    for key in ("patient", "rx", "labs", template.get("unlabelled", "notes"), template.get("after_rx", "advice")):
        if key not in keys:
            template["sections"].append({"key": key, "title": None if key in ("patient", "labs") else
                                         key.replace("_", " ").capitalize()})
            keys.append(key)
    heads = {" ".join(h.lower().split()): sec["key"] for sec in template["sections"] for h in sec.get("headings", [])}
    alts = sorted(heads, key=len, reverse=True)
    template["_heads"] = heads
    template["_heading_re"] = re.compile(
        r"^\s*(" + "|".join(re.escape(h).replace(r"\ ", r"\s+") for h in alts) + r")(?![A-Za-z])\s*([:.\-–)]*)\s*",
        re.IGNORECASE) if alts else None
    template["_by_key"] = {sec["key"]: sec for sec in template["sections"]}
    return template


def _heading(text: str, template: Dict[str, Any]):
    """(section key, text without the heading, written as a heading) for a line that starts with one, else None."""
    m = template["_heading_re"].match(text) if template.get("_heading_re") else None
    if not m:
        return None
    key = template["_heads"][" ".join(m.group(1).lower().split())]
    rest = text[m.end():].strip()
    marked = bool(m.group(2)) or not rest or "/" in m.group(1)  # "Adv:", "Advice" alone, "C/O fever"
    if not marked and template["_by_key"][key].get("keep_unpunctuated"):
        return key, text.strip(), False  # "Review after one week" reads as written
    return key, rest, marked


def _sections(header, body, notes_for, s, meds, labs, med_ids, lab_ids, template) -> Optional[Dict[str, Any]]:
    """
    Body rows assigned to template sections, or None for a page with no clinical structure (notes, letters),
    which keeps the plain reading. A line goes to the section its heading names; else medicines to rx, lab rows
    to labs, vitals ("BP 120/80", "RR - 22/min") to vitals, follow-up phrases to follow_up; else to the section
    of the heading above it, the after_rx section below the medicines, or the unlabelled section. Lines above
    the row that holds the patient details stay under the letterhead.
    """
    patient = _patient_line(s)
    unlabelled, after_rx = template.get("unlabelled", "notes"), template.get("after_rx", "advice")
    found: Dict[str, List[str]] = {k: [] for k in template["_by_key"]}
    intro: List[str] = []
    clinical = bool(meds or labs)
    patient_row = next((i for i, (row, text) in enumerate(body) if row is not None and (
        _explained_by_fields(text, s) or _mentions_fields(text, s) or {b.get("id") for b in row} & (med_ids | lab_ids))),
        None) if patient else None
    current = None
    for i, (row, text) in enumerate(body):
        if row is None:
            current = None  # a side column starts its own context
            continue
        ids = {b.get("id") for b in row}
        if ids & med_ids:
            current = "rx"
            continue
        if ids & lab_ids:
            current = "labs"
            continue
        if _RX_MARK.fullmatch(text):
            current, clinical = "rx", True
            continue
        if patient and _explained_by_fields(text, s):
            continue
        rest = _field_leftover(text, s) if patient and i == patient_row else None
        if rest and len(rest.split()) <= 2 and len(rest) <= 10:
            patient = f"{patient} | {rest}"  # the patient row with a short unparsed bit ("28 mg"): keep it there
            continue
        head = _heading(text, template)
        if head:
            key, text, marked = head
            clinical |= marked
            current = key
            if text:
                found[key].append(text)
            continue
        if _VITALS.search(text):
            found["vitals"].append(text)
            clinical = True
            continue
        if _FOLLOW_UP.search(text):
            found["follow_up"].append(text)
            continue
        if patient_row is not None and i < patient_row and current is None:
            intro.append(text)
            continue
        if current == "rx":
            current = after_rx
        found.setdefault(current or unlabelled, []).append(text)
    if not clinical:
        return None
    leftover = [n for ns in notes_for.values() for n in ns]
    if leftover:
        found[unlabelled].append("; ".join(leftover))
    sections = []
    for sec in template["sections"]:
        key = sec["key"]
        if key == "patient":
            lines = [patient] if patient else []
        elif key == "rx":
            lines = [_med_line(n, m) for n, m in enumerate(meds, 1)] + found["rx"]
        elif key == "labs":
            lines = [_lab_line(r) for r in labs] + found["labs"]
        else:
            lines = [l for l in found.get(key, []) if l.strip()]
        if lines:
            entry = {"key": key, "title": sec.get("title"), "lines": lines}
            if key == "rx":
                entry["medications"] = meds
            sections.append(entry)
    return {"template": template.get("name", "custom"), "letterhead": list(header) + intro, "sections": sections,
            "unlabelled": unlabelled}


def _render_sections(doc: Dict[str, Any], footer, signature, is_word) -> str:
    out: List[str] = list(doc["letterhead"])
    for sec in doc["sections"]:
        title, key = sec["title"], sec["key"]
        if key == "rx":
            n = len(sec.get("medications") or [])
            lines = ([title] if title else []) + sec["lines"][:n] + [l for l in _reflow(sec["lines"][n:], is_word) if l]
        elif key in ("patient", "labs") or not title:
            lines = sec["lines"]
        else:
            # Clinical sections keep the doctor's lines as items ("fever since 3 days" / "loose motions");
            # only free text with no section is reflowed into paragraphs
            body = [l for l in (_reflow(sec["lines"], is_word) if key == doc["unlabelled"] else sec["lines"]) if l]
            lines = [f"{title}: {body[0]}"] if len(body) == 1 else [f"{title}:"] + body
        out += ([""] if out else []) + lines
    if signature:
        out += ["", "[Signature]"]
    if footer:
        out += [""] + list(footer)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def format_sections(blocks: List[Dict[str, Any]], structured: Optional[Dict[str, Any]],
                    template: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    A clinical page as template sections, for an HIS to fill its own form:
    {"template", "letterhead": [...], "sections": [{"key", "title", "lines", ("medications")}], "signature"};
    None for pages with no clinical structure.
    """
    s = structured or {}
    header, footer, body, notes_for, signature, meds, labs, med_ids, lab_ids = _collect(blocks, s)
    doc = _sections(header, body, notes_for, s, meds, labs, med_ids, lab_ids, template or load_template())
    if doc is not None:
        doc["signature"] = signature
    return doc


def format_document(blocks: List[Dict[str, Any]], structured: Optional[Dict[str, Any]],
                    is_word: Optional[Callable[[str], bool]] = None,
                    template: Optional[Dict[str, Any]] = None) -> str:
    """Clinical pages in the template's section order; other pages as plain paragraphs (see the module doc)."""
    s = structured or {}
    header, footer, body, notes_for, signature, meds, labs, med_ids, lab_ids = _collect(blocks, s)
    doc = _sections(header, body, notes_for, s, meds, labs, med_ids, lab_ids, template or load_template())
    if doc is not None:
        return _render_sections(doc, footer, signature, is_word)
    return _plain(header, footer, body, notes_for, signature, s, meds, labs, med_ids, lab_ids, is_word)
