"""
Handwriting page layout: turns text-detector quadrilaterals into clean, rectified handwritten LINE crops
for the HTR engine.

Printed-text detectors (RapidOCR / DBNet) behave poorly on handwritten pages:
  - they return slanted quads, and cropping their axis-aligned bounding boxes pulls in neighbouring lines
  - they fragment a line into several pieces, or merge two lines into one tall box
  - they miss faint or irregular lines entirely
This module fixes each failure:
  1. quads are kept and rectified with a perspective warp (the same geometry used for GNHK training crops)
  2. fragments are merged along the line's own slant (collinearity), not by box overlap
  3. boxes spanning several lines are split at ink-projection valleys
  4. missed lines are recovered by re-detecting on a residual image with found text masked out, keeping
     only regions whose ink is as dark as the page's real writing (rejects bleed-through from the back)
"""
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np

Quad = np.ndarray  # (4, 2) float32: tl, tr, br, bl


def order_quad(pts) -> Quad:
    """Orders 4 points as top-left, top-right, bottom-right, bottom-left."""
    pts = np.asarray(pts, dtype=np.float32).reshape(4, 2)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]], dtype=np.float32)


def quad_geometry(q: Quad) -> Tuple[np.ndarray, float, float, float]:
    """(center, angle_rad, width, height) measured along the quad's own edges."""
    tl, tr, br, bl = q
    top, bottom = tr - tl, br - bl
    angle = float(np.arctan2(top[1] + bottom[1], top[0] + bottom[0]))
    width = float((np.linalg.norm(top) + np.linalg.norm(bottom)) / 2.0)
    height = float((np.linalg.norm(bl - tl) + np.linalg.norm(br - tr)) / 2.0)
    return q.mean(axis=0), angle, width, height


def quad_bbox(q: Quad, w_img: int, h_img: int) -> List[int]:
    xs, ys = q[:, 0], q[:, 1]
    return [int(max(0, xs.min())), int(max(0, ys.min())), int(min(w_img, xs.max())), int(min(h_img, ys.max()))]


def rectify_quad(image: np.ndarray, q: Quad, pad_ratio: float = 0.12, max_height: int = 160) -> Optional[np.ndarray]:
    """Perspective-warps a (possibly slanted) quad into an upright crop with a small extrapolated margin."""
    _, _, w, h = quad_geometry(q)
    if w < 6 or h < 6:
        return None
    scale = min(1.0, max_height / h)
    sw, sh = w * scale, h * scale
    p = pad_ratio * sh
    dst = np.array([[p, p], [p + sw, p], [p + sw, p + sh], [p, p + sh]], dtype=np.float32)
    M = cv2.getPerspectiveTransform(q.astype(np.float32), dst)
    size = (max(8, int(round(sw + 2 * p))), max(8, int(round(sh + 2 * p))))
    return cv2.warpPerspective(image, M, size, flags=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_REPLICATE)


def _ink_level(image: np.ndarray, q: Quad) -> float:
    """5th-percentile grey level inside the quad: how dark the darkest strokes are."""
    crop = rectify_quad(image, q, pad_ratio=0.0)
    if crop is None:
        return 255.0
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
    return float(np.percentile(gray, 5))


def _lerp(a: np.ndarray, b: np.ndarray, t: float) -> np.ndarray:
    return a + (b - a) * t


def piecewise_line_crop(
    image: np.ndarray,
    member_quads: Sequence[Quad],
    pad_ratio: float = 0.15,
    max_height: int = 128
) -> Optional[np.ndarray]:
    """
    Straightens a curved / unevenly slanted handwritten line: each member quad is rectified on its own and
    the pieces are concatenated left-to-right. Overlapping pieces are trimmed at the midpoint of their
    overlap (no ink is read twice); real gaps between words become blank space.
    """
    if not member_quads:
        return None
    if len(member_quads) == 1:
        return rectify_quad(image, member_quads[0], pad_ratio=pad_ratio, max_height=max_height)

    geo = [quad_geometry(q) for q in member_quads]
    ang = float(np.median([g[1] for g in geo]))
    d = np.array([np.cos(ang), np.sin(ang)], dtype=np.float32)
    order = sorted(range(len(member_quads)), key=lambda i: float(geo[i][0] @ d))
    quads = [member_quads[i].astype(np.float32).copy() for i in order]
    heights = [geo[i][3] for i in order]
    H = int(min(max_height, max(24, np.median(heights))))

    # Along-line extent of each quad (left edge = tl/bl, right edge = tr/br)
    def span(q):
        return float(min(q[0] @ d, q[3] @ d)), float(max(q[1] @ d, q[2] @ d))

    def trim(q, cut, side):
        tl, tr, br, bl = q
        def at(a, b):
            pa, pb = float(a @ d), float(b @ d)
            t = 0.0 if abs(pb - pa) < 1e-6 else min(1.0, max(0.0, (cut - pa) / (pb - pa)))
            return _lerp(a, b, t)
        if side == "right":
            return np.array([tl, at(tl, tr), at(bl, br), bl], dtype=np.float32)
        return np.array([at(tl, tr), tr, br, at(bl, br)], dtype=np.float32)

    for i in range(1, len(quads)):
        _, prev_end = span(quads[i - 1])
        cur_start, _ = span(quads[i])
        if prev_end > cur_start:
            cut = (prev_end + cur_start) / 2.0
            quads[i - 1] = trim(quads[i - 1], cut, "right")
            quads[i] = trim(quads[i], cut, "left")

    # One scale for the whole line keeps glyph size consistent across pieces whose boxes fit the ink
    # more or less tightly; each piece is then centred vertically on a common canvas height.
    scale = H / max(1.0, float(np.median(heights)))
    pieces, bg = [], None
    out_heights = []
    for i, q in enumerate(quads):
        _, _, w, h = quad_geometry(q)
        if w < 2 or h < 2:
            pieces.append(None)
            out_heights.append(0)
            continue
        # Grow the quad along its own normal so ascenders / descenders are kept
        tl, tr, br, bl = q
        grow_l, grow_r = (tl - bl) * pad_ratio, (tr - br) * pad_ratio
        g = np.array([tl + grow_l, tr + grow_r, br - grow_r, bl - grow_l], dtype=np.float32)
        out_h = max(4, int(round(h * scale * (1 + 2 * pad_ratio))))
        out_w = max(2, int(round(w * scale)))
        dst = np.array([[0, 0], [out_w - 1, 0], [out_w - 1, out_h - 1], [0, out_h - 1]], dtype=np.float32)
        piece = cv2.warpPerspective(image, cv2.getPerspectiveTransform(g, dst), (out_w, out_h),
                                    flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REPLICATE)
        if bg is None:
            gray = cv2.cvtColor(piece, cv2.COLOR_BGR2GRAY) if piece.ndim == 3 else piece
            bg = int(np.percentile(gray, 90))
        pieces.append(piece)
        out_heights.append(out_h)

    canvas_h = max(out_heights) if out_heights else 0
    if canvas_h == 0 or bg is None:
        return None
    strip_parts = []
    for i, piece in enumerate(pieces):
        if piece is None:
            continue
        top = (canvas_h - piece.shape[0]) // 2
        piece = cv2.copyMakeBorder(piece, top, canvas_h - piece.shape[0] - top, 0, 0,
                                   cv2.BORDER_CONSTANT, value=(bg, bg, bg))
        if strip_parts:
            gap_px = (span(quads[i])[0] - span(quads[i - 1])[1]) * scale
            gap_w = int(min(0.8 * H, max(0.25 * H, gap_px)))
            strip_parts.append(np.full((canvas_h, gap_w, 3), bg, dtype=np.uint8))
        strip_parts.append(piece)
    pad = int(0.1 * H)
    strip = np.hstack(strip_parts)
    return cv2.copyMakeBorder(strip, 0, 0, pad, pad, cv2.BORDER_CONSTANT, value=(bg, bg, bg))


def split_long_line(crop: np.ndarray, max_aspect: float = 16.0, min_aspect: float = 4.0) -> List[np.ndarray]:
    """
    Splits a line strip wider than the training distribution (IAM / GNHK lines reach aspect ~15) at the
    widest blank column gap nearest its middle, recursively, so each chunk keeps legible character widths
    after the recogniser's square resize. Measured: chunking in-distribution lines (aspect 9-12) does not
    help, so only out-of-distribution strips (e.g. stitched curved lines) are split.
    """
    h, w = crop.shape[:2]
    if w <= max_aspect * h:
        return [crop]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
    _, ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    cols = (ink > 0).sum(axis=0)
    blank = cols <= max(1, int(0.02 * h))
    # Trim blank margins first so no chunk can end up without ink (the recogniser would invent text)
    inked = np.nonzero(~blank)[0]
    if inked.size == 0:
        return [crop]
    pad = int(0.15 * h)
    x0, x1 = max(0, int(inked[0]) - pad), min(w, int(inked[-1]) + 1 + pad)
    if x0 > 0 or x1 < w:
        return split_long_line(crop[:, x0:x1], max_aspect, min_aspect)
    # Candidate cut = centre of each blank run that is wide enough to be an inter-word space
    best, best_score = None, None
    x = 0
    while x < w:
        if blank[x]:
            s = x
            while x < w and blank[x]:
                x += 1
            run = x - s
            c = (s + x) // 2
            if run >= 0.12 * h and min_aspect * h <= c <= w - min_aspect * h:
                score = abs(c - w / 2) - 2.0 * run  # prefer central and wide gaps
                if best_score is None or score < best_score:
                    best, best_score = c, score
        else:
            x += 1
    if best is None:
        return [crop]
    return split_long_line(crop[:, :best], max_aspect, min_aspect) + split_long_line(crop[:, best:], max_aspect, min_aspect)


class HandwritingLineBuilder:
    """Builds rectified handwritten line crops from detector quads."""

    def __init__(
        self,
        detector: Optional[Callable] = None,
        recovery_kwargs: Optional[Dict] = None,
        bleed_through_margin: float = 45.0
    ):
        self.detector = detector
        self.recovery_kwargs = recovery_kwargs or {"box_thresh": 0.30, "unclip_ratio": 1.6, "text_score": 0.20}
        self.bleed_through_margin = bleed_through_margin

    # ------------------------------------------------------------------
    @staticmethod
    def median_height(quads: Sequence[Quad]) -> float:
        """Width-weighted median height: full text lines dominate, small fragments cannot drag it down."""
        if not quads:
            return 0.0
        geo = [quad_geometry(q) for q in quads]
        hs = np.array([g[3] for g in geo])
        ws = np.array([max(1.0, g[2]) for g in geo])
        order = np.argsort(hs)
        cum = np.cumsum(ws[order])
        return float(hs[order][int(np.searchsorted(cum, cum[-1] / 2.0))])

    def split_multiline(self, image: np.ndarray, quads: List[Quad], line_h: float) -> List[Quad]:
        """Splits quads taller than ~1.7 line heights at the deepest ink-projection valleys."""
        if line_h <= 0:
            return quads
        out: List[Quad] = []
        for q in quads:
            _, _, _, h = quad_geometry(q)
            n_lines = int(round(h / line_h))
            if h < 1.7 * line_h or n_lines < 2:
                out.append(q)
                continue
            crop = rectify_quad(image, q, pad_ratio=0.0, max_height=int(h))
            if crop is None:
                out.append(q)
                continue
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
            _, ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            prof = ink.sum(axis=1).astype(np.float32)
            k = max(3, int(line_h * 0.25) | 1)
            prof = np.convolve(prof, np.ones(k) / k, mode="same")
            H = len(prof)
            typical = float(np.median(prof[prof > 0])) if np.any(prof > 0) else 0.0
            cuts = []
            for i in range(1, n_lines):
                # Search for the valley near each expected boundary; only a genuine gap between lines
                # (nearly ink-free rows) counts, never the ascender/descender zone of a single line
                c = int(H * i / n_lines)
                lo, hi = max(1, c - int(0.35 * line_h)), min(H - 1, c + int(0.35 * line_h))
                if hi > lo:
                    k_min = lo + int(np.argmin(prof[lo:hi]))
                    if prof[k_min] <= 0.2 * typical:
                        cuts.append(k_min / float(H))
            if not cuts:
                out.append(q)
                continue
            tl, tr, br, bl = q
            fracs = [0.0] + cuts + [1.0]
            for a, b in zip(fracs[:-1], fracs[1:]):
                out.append(np.array([_lerp(tl, bl, a), _lerp(tr, br, a), _lerp(tr, br, b), _lerp(tl, bl, b)],
                                    dtype=np.float32))
        return out

    def recover_missed(self, image: np.ndarray, quads: List[Quad], line_h: float,
                       mask_quads: Sequence[Quad] = (), recovery_image: Optional[np.ndarray] = None) -> List[Quad]:
        """
        Re-detects on a residual image (all found text masked out) to catch lines the first pass missed.
        `recovery_image` (same geometry, e.g. the original un-enhanced page) is searched instead of `image`
        when given: enhancement tuned for print can make faint handwritten lines undetectable.
        """
        known = list(quads) + [order_quad(m) for m in mask_quads]
        if self.detector is None or not known or line_h <= 0:
            return []
        if recovery_image is not None and recovery_image.shape[:2] == image.shape[:2]:
            image = recovery_image
        residual = image.copy()
        bg = int(np.median(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)))
        for q in known:
            c = q.mean(axis=0)
            grown = c + (q - c) * 1.08
            cv2.fillPoly(residual, [grown.astype(np.int32)], (bg, bg, bg))
        try:
            results, _ = self.detector(residual, **self.recovery_kwargs)
        except Exception:
            return []
        if not results:
            return []
        page_ink = float(np.median([_ink_level(image, q) for q in known]))
        found = []
        for item in results:
            q = order_quad(item[0])
            _, _, w, h = quad_geometry(q)
            if h < 0.5 * line_h or w < 1.0 * line_h or h > 2.5 * line_h:
                continue
            if _ink_level(image, q) > page_ink + self.bleed_through_margin:
                continue  # faint show-through from the reverse side, not real writing
            found.append(q)
        return found

    @staticmethod
    def merge_into_lines(quads: List[Quad]) -> List[List[int]]:
        """Union-find over quads that lie on the same slanted text line."""
        n = len(quads)
        geo = [quad_geometry(q) for q in quads]
        parent = list(range(n))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        for i in range(n):
            ci, ai, wi, hi = geo[i]
            for j in range(i + 1, n):
                cj, aj, wj, hj = geo[j]
                ang = (ai + aj) / 2.0
                d = np.array([np.cos(ang), np.sin(ang)])
                nrm = np.array([-np.sin(ang), np.cos(ang)])
                delta = cj - ci
                offset = abs(float(delta @ nrm))
                along = abs(float(delta @ d))
                gap = along - (wi + wj) / 2.0
                min_h, max_h = min(hi, hj), max(hi, hj)
                if offset <= 0.45 * min_h and -0.5 * min(wi, wj) <= gap <= 2.5 * max_h and max_h <= 3.0 * min_h:
                    parent[find(j)] = find(i)

        groups: Dict[int, List[int]] = {}
        for i in range(n):
            groups.setdefault(find(i), []).append(i)
        return list(groups.values())

    @staticmethod
    def line_quad(member_quads: List[Quad]) -> Quad:
        rect = cv2.minAreaRect(np.concatenate(member_quads).astype(np.float32))
        return order_quad(cv2.boxPoints(rect))

    # ------------------------------------------------------------------
    def build(self, image: np.ndarray, quads: Sequence[Quad], mask_quads: Sequence[Quad] = (),
              recovery_image: Optional[np.ndarray] = None) -> List[Dict]:
        """
        `mask_quads` are text regions handled elsewhere (e.g. the printed path): they are masked out of the
        missed-line recovery so they are not read twice.
        Returns line records sorted top-to-bottom:
          {"quad": line quad, "crop": rectified BGR crop, "bbox": [x0,y0,x1,y1], "members": n, "recovered": n}
        """
        h_img, w_img = image.shape[:2]
        quads = [order_quad(q) for q in quads]
        masks = [order_quad(m) for m in mask_quads]
        if not quads and not masks:
            return []
        line_h = self.median_height(quads or masks)
        quads = self.split_multiline(image, quads, line_h)
        line_h = self.median_height(quads or masks)
        recovered = self.recover_missed(image, quads, line_h, masks, recovery_image)
        all_quads = quads + recovered
        rec_ids = set(range(len(quads), len(all_quads)))

        lines = []
        for members in self.merge_into_lines(all_quads):
            member_quads = [all_quads[i] for i in members]
            lq = self.line_quad(member_quads)
            crop = piecewise_line_crop(image, member_quads)
            if crop is None or crop.shape[1] < crop.shape[0] * 0.8:
                continue
            lines.append({
                "quad": lq,
                "crop": crop,
                "bbox": quad_bbox(lq, w_img, h_img),
                "members": len(members),
                "recovered": sum(1 for i in members if i in rec_ids),
            })
        lines.sort(key=lambda r: (quad_geometry(r["quad"])[0][1], r["bbox"][0]))
        return lines
