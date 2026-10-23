import os
import re
import cv2
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from pathlib import Path


class BoundingBoxNormalizer:
    """
    Standardized Coordinate Mapping Engine:
    - Normalizes absolute bounding boxes to [0.0, 1.0] relative coordinates.
    - Denormalizes relative coordinates back to exact document pixels.
    - Maps localized snippet/marquee crops back to global full-document space.
    """
    @staticmethod
    def normalize(bbox: List[int], img_w: int, img_h: int, precision: int = 5) -> List[float]:
        if not bbox or len(bbox) != 4 or img_w <= 0 or img_h <= 0:
            return [0.0, 0.0, 0.0, 0.0]
        x1, y1, x2, y2 = bbox
        return [
            round(max(0.0, min(1.0, float(x1) / float(img_w))), precision),
            round(max(0.0, min(1.0, float(y1) / float(img_h))), precision),
            round(max(0.0, min(1.0, float(x2) / float(img_w))), precision),
            round(max(0.0, min(1.0, float(y2) / float(img_h))), precision)
        ]

    @staticmethod
    def denormalize(norm_bbox: List[float], img_w: int, img_h: int) -> List[int]:
        if not norm_bbox or len(norm_bbox) != 4:
            return [0, 0, 0, 0]
        nx1, ny1, nx2, ny2 = norm_bbox
        return [
            int(round(nx1 * img_w)),
            int(round(ny1 * img_h)),
            int(round(nx2 * img_w)),
            int(round(ny2 * img_h))
        ]

    @staticmethod
    def transform_snippet_to_global(
        local_bbox: List[int],
        snippet_origin: Tuple[int, int],
        scale_factor: float = 1.0
    ) -> List[int]:
        rx, ry = snippet_origin
        lx1, ly1, lx2, ly2 = local_bbox
        gx1 = int(round(rx + (lx1 / scale_factor)))
        gy1 = int(round(ry + (ly1 / scale_factor)))
        gx2 = int(round(rx + (lx2 / scale_factor)))
        gy2 = int(round(ry + (ly2 / scale_factor)))
        return [gx1, gy1, gx2, gy2]


class BaselineAnalyzer:
    """
    Geometric baseline slope and drift estimation:
    - Calculates baseline angle / tilt slope (degrees)
    - Measures baseline height and ascender/descender ratios
    - Assesses vertical drift across connected strokes
    """
    @staticmethod
    def analyze_line_baseline(crop: np.ndarray) -> Dict[str, Any]:
        if crop is None or crop.size == 0:
            return {"slope_deg": 0.0, "baseline_y": 0, "drift_ratio": 0.0}

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if len(crop.shape) == 3 else crop
        h, w = gray.shape[:2]
        if h < 8 or w < 12:
            return {"slope_deg": 0.0, "baseline_y": int(h * 0.75), "drift_ratio": 0.0}

        # Find stroke bottom points across horizontal slices
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        cols = np.where(thresh > 0)
        if len(cols[0]) == 0:
            return {"slope_deg": 0.0, "baseline_y": int(h * 0.75), "drift_ratio": 0.0}

        # Collect bottom-most active pixel per x-slice (step 4px)
        x_pts, y_pts = [], []
        step = max(2, w // 40)
        for x in range(0, w, step):
            col_pixels = np.where(thresh[:, x] > 0)[0]
            if len(col_pixels) > 0:
                x_pts.append(x)
                y_pts.append(int(np.max(col_pixels)))

        if len(x_pts) < 4:
            return {"slope_deg": 0.0, "baseline_y": int(h * 0.75), "drift_ratio": 0.0}

        # Linear fit: y = m*x + c
        m, c = np.polyfit(x_pts, y_pts, 1)
        slope_deg = float(np.degrees(np.arctan(m)))
        drift = float(np.std(y_pts) / max(1.0, float(h)))

        return {
            "slope_deg": round(slope_deg, 2),
            "baseline_y": int(round(c + m * (w / 2.0))),
            "drift_ratio": round(drift, 3)
        }


class LineClusterer:
    """
    Clusters horizontally co-linear fragments into text line candidates.
    Uses baseline overlap ratio (>= 0.45) and vertical midpoint proximity.
    """
    def __init__(self, vertical_overlap_ratio: float = 0.45):
        self.vertical_overlap_ratio = vertical_overlap_ratio

    def cluster_into_lines(self, items: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        if not items:
            return []

        sorted_items = sorted(items, key=lambda b: (b['bbox'][1], b['bbox'][0]))
        lines = []

        for item in sorted_items:
            b_ymin, b_ymax = item['bbox'][1], item['bbox'][3]
            b_h = max(1, b_ymax - b_ymin)
            b_mid = (b_ymin + b_ymax) / 2.0

            placed = False
            for line in lines:
                l_ymin = min(it['bbox'][1] for it in line)
                l_ymax = max(it['bbox'][3] for it in line)
                l_h = max(1, l_ymax - l_ymin)
                l_mid = (l_ymin + l_ymax) / 2.0

                overlap = max(0, min(b_ymax, l_ymax) - max(b_ymin, l_ymin))
                overlap_ratio = overlap / float(min(b_h, l_h))
                mid_diff = abs(b_mid - l_mid)

                if overlap_ratio >= self.vertical_overlap_ratio or mid_diff <= 0.40 * min(b_h, l_h):
                    line.append(item)
                    placed = True
                    break

            if not placed:
                lines.append([item])

        # Sort lines top-to-bottom, and elements within each line left-to-right
        lines.sort(key=lambda line: min(it['bbox'][1] for it in line))
        for line in lines:
            line.sort(key=lambda it: it['bbox'][0])

        return lines


class AdjacentBoxMerger:
    """
    Consolidates fragmented adjacent word boxes on the same line into unified line candidate crops.
    Permits slight overlap (-0.3 * line_h) up to natural inter-word spacing (2.2 * line_h).
    """
    @staticmethod
    def merge_line_fragments(line: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        if not line:
            return []
        line_sorted = sorted(line, key=lambda it: it['bbox'][0])

        groups = []
        cur_group = []

        for item in line_sorted:
            if not cur_group:
                cur_group = [item]
            else:
                prev_x2 = max(it['bbox'][2] for it in cur_group)
                cur_x1 = item['bbox'][0]
                line_h = max(max(it['bbox'][3] - it['bbox'][1] for it in cur_group), item['bbox'][3] - item['bbox'][1])
                gap = cur_x1 - prev_x2

                if -0.35 * line_h <= gap <= 2.2 * line_h:
                    cur_group.append(item)
                else:
                    groups.append(cur_group)
                    cur_group = [item]

        if cur_group:
            groups.append(cur_group)

        return groups


class ColumnDetector:
    """
    Multi-Column Layout Analyzer:
    - Identifies vertical whitespace gutters spanning multiple text lines.
    - Partitions document into 1, 2, or 3 distinct column zones.
    - Ensures reading order flows down column 1 before proceeding to column 2.
    """
    @staticmethod
    def detect_columns(blocks: List[Dict[str, Any]], page_width: int) -> List[Tuple[int, int]]:
        """
        Returns a list of column bounds: [(col1_left, col1_right), (col2_left, col2_right), ...]
        """
        if not blocks or page_width <= 0:
            return [(0, max(1, page_width))]

        # Horizontal occupancy histogram
        occupancy = np.zeros(page_width, dtype=int)
        for b in blocks:
            x1, _, x2, _ = b['bbox']
            x1, x2 = max(0, min(page_width - 1, x1)), max(0, min(page_width - 1, x2))
            if x2 > x1:
                occupancy[x1:x2] += 1

        # Search for central vertical whitespace gutters (width >= 28px, zero or very low occupancy)
        min_gutter_w = max(24, int(page_width * 0.035))
        gutters = []

        in_gutter = False
        g_start = 0
        search_min = int(page_width * 0.22)
        search_max = int(page_width * 0.78)

        for x in range(search_min, search_max):
            if occupancy[x] == 0:
                if not in_gutter:
                    in_gutter = True
                    g_start = x
            else:
                if in_gutter:
                    in_gutter = False
                    if (x - g_start) >= min_gutter_w:
                        gutters.append((g_start, x))

        if not gutters:
            return [(0, page_width)]

        # Construct column intervals
        columns = []
        cur_left = 0
        for g_start, g_end in gutters:
            columns.append((cur_left, g_start))
            cur_left = g_end
        columns.append((cur_left, page_width))

        return columns


class TableDetector:
    """
    Detects tabular structures and grid cell relationships in clinical documents:
    - Identifies table borders, header rows, and data cells (e.g. Lab reports, discharge medications).
    - Extracts structured table objects with headers and rows.
    """
    TABLE_HEADER_KEYWORDS = [
        "test name", "result", "units", "reference range", "normal range",
        "s.no", "medication", "dosage", "frequency", "duration", "instructions",
        "parameter", "observed value", "biological reference", "item", "description"
    ]

    @classmethod
    def detect_tables(cls, image: np.ndarray, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        tables = []
        if image is None or image.size == 0 or not blocks:
            return tables

        h_img, w_img = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # 1. Morphological horizontal and vertical grid lines
        horiz_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(20, w_img // 40), 1))
        vert_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(15, h_img // 50)))

        _, binary = cv2.threshold(gray, 210, 255, cv2.THRESH_BINARY_INV)
        horiz_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horiz_kernel)
        vert_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vert_kernel)
        table_grid = cv2.add(horiz_lines, vert_lines)

        contours, _ = cv2.findContours(table_grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        grid_boxes = []
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if w > w_img * 0.35 and h > 50:
                grid_boxes.append([x, y, x + w, y + h])

        # 2. Check blocks for table headers (e.g. 'TEST NAME | RESULT | UNITS')
        for i, b in enumerate(blocks):
            txt_lower = b.get("text", "").lower()
            matched_keywords = [k for k in cls.TABLE_HEADER_KEYWORDS if k in txt_lower]

            if len(matched_keywords) >= 2 or "|" in b.get("text", ""):
                # Potential table header block found
                header_bbox = b["bbox"]
                t_ymin = header_bbox[1]
                t_xmin = header_bbox[0]
                t_xmax = header_bbox[2]
                t_ymax = min(h_img, t_ymin + 350)

                # Collect subsequent lines falling within the table bounding region
                table_lines = [b.get("text", "")]
                table_row_blocks = [b]

                for next_b in blocks[i + 1:]:
                    nx1, ny1, nx2, ny2 = next_b["bbox"]
                    if ny1 > t_ymax:
                        break
                    if abs(nx1 - t_xmin) < 180 or (t_xmin <= nx1 <= t_xmax):
                        table_lines.append(next_b.get("text", ""))
                        table_row_blocks.append(next_b)
                        t_ymax = max(t_ymax, ny2 + 10)

                if len(table_lines) >= 3:
                    # Parse into header & rows
                    header_line = table_lines[0]
                    headers = [h.strip() for h in re.split(r'\||\s{3,}', header_line) if h.strip()]
                    rows = []
                    for row_str in table_lines[1:]:
                        cells = [c.strip() for c in re.split(r'\||\s{3,}', row_str) if c.strip()]
                        if cells:
                            rows.append(cells)

                    t_bbox = [
                        min(it["bbox"][0] for it in table_row_blocks),
                        min(it["bbox"][1] for it in table_row_blocks),
                        max(it["bbox"][2] for it in table_row_blocks),
                        max(it["bbox"][3] for it in table_row_blocks)
                    ]

                    tables.append({
                        "table_id": f"table_{len(tables)+1}",
                        "bbox": t_bbox,
                        "headers": headers,
                        "rows": rows,
                        "row_count": len(rows),
                        "column_count": len(headers) if headers else (len(rows[0]) if rows else 0)
                    })

        return tables


class FormKeyValueExtractor:
    """
    Extracts key-value fields and form metadata:
    - Pairs field keys (e.g. 'Patient Name:', 'Age:', 'Date:', 'BP:', 'Diagnosis:')
      with associated value strings directly to the right or below.
    """
    KEY_PATTERNS = [
        r'\b(?:Patient(?:\s*Name)?|Name)\s*:',
        r'\b(?:Age(?:\s*/\s*Sex)?)\s*:',
        r'\b(?:Date(?:\s*of\s*Admission|\s*of\s*Discharge|\s*of\s*Consultation)?)\s*:',
        r'\b(?:Ref(?:\.|\s*By)?)\s*:',
        r'\b(?:Consultant(?:\s*Doctor|\s*Physician)?)\s*:',
        r'\b(?:Department)\s*:',
        r'\b(?:Diagnosis|Dx)\s*(?:\([^\)]*\))?\s*:',
        r'\b(?:Condition\s*at\s*Discharge)\s*:',
        r'\b(?:Vitals)\s*:',
        r'\b(?:BP|Blood\s*Pressure)\s*:',
        r'\b(?:HR|Pulse|Heart\s*Rate)\s*:',
        r'\b(?:SpO2|SPO2)\s*:',
        r'\b(?:Temp|Temperature)\s*:',
        r'\b(?:Reg(?:\.|\s*No)?)\s*:',
        r'\b(?:Timing)\s*:',
        r'\b(?:Adv(?:ised)?)\s*:',
        r'\b(?:Plan)\s*:'
    ]

    @classmethod
    def extract_key_values(cls, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        pairs = []
        if not blocks:
            return pairs

        for i, b in enumerate(blocks):
            text = b.get("text", "").strip()
            for pat in cls.KEY_PATTERNS:
                m = re.search(pat, text, flags=re.IGNORECASE)
                if m:
                    key_str = m.group(0).rstrip(":").strip()
                    val_str = text[m.end():].strip()

                    # Value found inline on the same block
                    if val_str:
                        pairs.append({
                            "key": key_str,
                            "value": val_str,
                            "key_bbox": b["bbox"],
                            "value_bbox": b["bbox"],
                            "confidence": b.get("confidence", 0.90),
                            "layout_relationship": "inline"
                        })
                    else:
                        # Value may be in the adjacent block horizontally
                        bx1, by1, bx2, by2 = b["bbox"]
                        matched_next = False

                        for next_b in blocks[i+1:i+4]:
                            nx1, ny1, nx2, ny2 = next_b["bbox"]
                            # Horizontally adjacent (within 250px, vertical overlap)
                            if 0 <= nx1 - bx2 <= 250 and abs(ny1 - by1) < 20:
                                pairs.append({
                                    "key": key_str,
                                    "value": next_b.get("text", "").strip(),
                                    "key_bbox": b["bbox"],
                                    "value_bbox": next_b["bbox"],
                                    "confidence": next_b.get("confidence", 0.85),
                                    "layout_relationship": "horizontal_adjacent"
                                })
                                matched_next = True
                                break

                        if not matched_next:
                            pairs.append({
                                "key": key_str,
                                "value": "",
                                "key_bbox": b["bbox"],
                                "value_bbox": None,
                                "confidence": b.get("confidence", 0.80),
                                "layout_relationship": "unassigned"
                            })
                    break

        return pairs


class CheckboxDetector:
    """
    Detects and classifies form checkboxes:
    - Text glyph checkboxes: '[ ]', '[x]', '[X]', '□', '✓'
    - Morphological square contours on documents (aspect ratio 0.85-1.15)
    - Determines 'checked' vs 'unchecked' state from central stroke pixel fill.
    """
    @classmethod
    def detect_checkboxes(cls, image: Optional[np.ndarray], blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        checkboxes = []

        # 1. Text-level checkbox glyphs
        for b in blocks:
            text = b.get("text", "")
            # Check for unicode boxes or bracket notations
            m = re.search(r'(\[\s*\]|\[\s*[xX✓✔]\s*\]|[\u25a1\u53e3\u2610\u2611\u2612])\s*(.*)', text)
            if m:
                raw_glyph = m.group(1)
                label = m.group(2).strip()
                is_checked = any(char in raw_glyph.lower() for char in ['x', '✓', '✔', '\u2611', '\u2612'])
                checkboxes.append({
                    "state": "checked" if is_checked else "unchecked",
                    "label": label,
                    "bbox": b["bbox"],
                    "detection_type": "text_glyph"
                })

        # 2. Image contour square detection (if image provided)
        if image is not None and image.size > 0:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            h_img, w_img = gray.shape[:2]
            _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
            contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            for c in contours:
                x, y, w, h = cv2.boundingRect(c)
                # Square form checkbox criteria: 12 <= w, h <= 26, aspect ratio ~ 1.0
                if 12 <= w <= 26 and 12 <= h <= 26:
                    aspect = float(w) / float(h)
                    area = cv2.contourArea(c)
                    rect_ratio = area / float(w * h)

                    # Must have closed box geometry and not be inside a word bounding box
                    if 0.85 <= aspect <= 1.18 and rect_ratio >= 0.70:
                        is_inside_word = False
                        for b in blocks:
                            bx1, by1, bx2, by2 = b["bbox"]
                            if bx1 <= x and y >= by1 and (x + w) <= bx2 and (y + h) <= by2:
                                is_inside_word = True
                                break

                        if not is_inside_word:
                            # Associate with closest text label directly to the right
                            label = ""
                            for b in blocks:
                                bx1, by1, bx2, by2 = b["bbox"]
                                if 5 <= bx1 - (x + w) <= 150 and abs(by1 - y) < 16:
                                    label = b.get("text", "")
                                    break

                            if label:
                                inner_margin = max(2, int(w * 0.22))
                                inner_crop = thresh[y + inner_margin:y + h - inner_margin, x + inner_margin:x + w - inner_margin]
                                fill_ratio = (np.count_nonzero(inner_crop) / max(1, inner_crop.size)) if inner_crop.size > 0 else 0.0
                                is_checked = fill_ratio > 0.22

                                if not any(abs(cb["bbox"][0] - x) < 8 and abs(cb["bbox"][1] - y) < 8 for cb in checkboxes):
                                    checkboxes.append({
                                        "state": "checked" if is_checked else "unchecked",
                                        "label": label,
                                        "bbox": [x, y, x + w, y + h],
                                        "fill_ratio": round(float(fill_ratio), 3),
                                        "detection_type": "morphological_contour"
                                    })

        return checkboxes


class LayoutIntelligenceEngine:
    """
    Unified Layout Intelligence Engine (Phase 6):
    - Text region detection & baseline slope/drift analysis
    - Multi-scale bounding box normalization & coordinate tracking
    - Line clustering & adjacent box consolidation
    - Column gutter detection & natural multi-column reading-order reconstruction
    - Table detection & structured grid cell extraction
    - Form field key-value pair association
    - Checkbox state classification (checked vs unchecked)
    - Multi-page document aggregation
    """
    def __init__(self, vertical_overlap_ratio: float = 0.45):
        self.normalizer = BoundingBoxNormalizer()
        self.baseline_analyzer = BaselineAnalyzer()
        self.line_clusterer = LineClusterer(vertical_overlap_ratio=vertical_overlap_ratio)
        self.adjacent_merger = AdjacentBoxMerger()
        self.column_detector = ColumnDetector()
        self.table_detector = TableDetector()
        self.kv_extractor = FormKeyValueExtractor()
        self.checkbox_detector = CheckboxDetector()

    def rebuild_reading_order_with_columns(
        self,
        blocks: List[Dict[str, Any]],
        page_width: int,
        page_height: int
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Reconstructs human reading order respecting multi-column layouts:
        - Detects vertical gutters between columns.
        - Sorts Column 1 top-to-bottom, then Column 2 top-to-bottom.
        """
        if not blocks:
            return [], ""

        # 1. Detect columns
        col_intervals = self.column_detector.detect_columns(blocks, page_width)

        # 2. Partition blocks into columns
        column_buckets = [[] for _ in col_intervals]
        for b in blocks:
            x1, y1, x2, y2 = b['bbox']
            mid_x = (x1 + x2) / 2.0

            assigned = False
            for c_idx, (c_start, c_end) in enumerate(col_intervals):
                if c_start <= mid_x <= c_end:
                    column_buckets[c_idx].append(b)
                    assigned = True
                    break
            if not assigned:
                column_buckets[0].append(b)

        # 3. Within each column, cluster into lines and sort
        ordered_blocks = []
        text_lines = []
        global_idx = 1

        for c_idx, col_blocks in enumerate(column_buckets, 1):
            if not col_blocks:
                continue

            lines = self.line_clusterer.cluster_into_lines(col_blocks)
            for line_idx, line in enumerate(lines, 1):
                line_texts = []
                for b in line:
                    b_copy = dict(b)
                    b_copy['reading_order'] = global_idx
                    b_copy['column_number'] = c_idx
                    b_copy['line_number'] = line_idx
                    ordered_blocks.append(b_copy)
                    global_idx += 1
                    if b.get('text'):
                        line_texts.append(b['text'].strip())
                if line_texts:
                    text_lines.append("  ".join(line_texts))

        raw_text = "\n".join(text_lines)
        return ordered_blocks, raw_text

    def extract_full_layout_intelligence(
        self,
        image: np.ndarray,
        blocks: List[Dict[str, Any]],
        page_num: int = 1,
        total_pages: int = 1
    ) -> Dict[str, Any]:
        """
        Runs comprehensive layout intelligence across a processed page:
        - Reconstructed reading order with column flow
        - Table structures
        - Form key-value pairs
        - Checkboxes
        - Baseline slope and drift metrics
        """
        h_img, w_img = image.shape[:2] if image is not None else (1000, 800)

        # 1. Reconstruct reading order with column awareness
        ordered_blocks, raw_text = self.rebuild_reading_order_with_columns(blocks, w_img, h_img)

        # 2. Extract tables
        tables = self.table_detector.detect_tables(image, ordered_blocks)

        # 3. Extract form key-value fields
        key_values = self.kv_extractor.extract_key_values(ordered_blocks)

        # 4. Extract checkboxes
        checkboxes = self.checkbox_detector.detect_checkboxes(image, ordered_blocks)

        # 5. Baseline analysis on the first few lines
        baselines = []
        for b in ordered_blocks[:8]:
            x1, y1, x2, y2 = b["bbox"]
            if image is not None and x2 > x1 and y2 > y1:
                crop = image[y1:y2, x1:x2]
                b_stats = self.baseline_analyzer.analyze_line_baseline(crop)
                b["baseline_stats"] = b_stats
                baselines.append(b_stats)

        # Multi-column summary
        cols = self.column_detector.detect_columns(blocks, w_img)

        return {
            "page_number": page_num,
            "total_pages": total_pages,
            "dimensions": [w_img, h_img],
            "column_count": len(cols),
            "columns": [{"column_id": i+1, "bounds": list(c)} for i, c in enumerate(cols)],
            "reading_order_blocks": ordered_blocks,
            "tables": tables,
            "key_value_pairs": key_values,
            "checkboxes": checkboxes,
            "baseline_summary": {
                "avg_slope_deg": round(float(np.mean([b["slope_deg"] for b in baselines])), 2) if baselines else 0.0,
                "avg_drift_ratio": round(float(np.mean([b["drift_ratio"] for b in baselines])), 3) if baselines else 0.0
            },
            "raw_text": raw_text
        }
