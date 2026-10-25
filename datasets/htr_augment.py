"""
Training-time augmentation for handwritten crops and a synthetic medical handwriting line generator.

HTRAugmenter            Photometric + geometric distortions that mimic scanner / phone-camera / HIS
                        screenshot conditions (slant, rotation, elastic baseline drift, pen width,
                        blur, noise, JPEG artefacts, faded ink, ruled lines).
SyntheticMedicalLines   Renders prescription-style lines (drug + dose + frequency + duration, clinical
                        notes, vitals) with handwriting fonts so the decoder learns medical vocabulary
                        and dosage grammar that the real corpora cover only sparsely.
"""
import os
import random
from typing import List, Optional, Sequence

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HANDWRITING_FONT_FILES = [
    "segoepr.ttf", "segoeprb.ttf", "segoesc.ttf", "Inkfree.ttf", "LHANDW.TTF", "BRADHITC.TTF",
    "ITCKRIST.TTF", "mvboli.ttf", "comic.ttf", "comici.ttf", "PRISTINA.TTF", "JUICE___.TTF",
    "VLADIMIR.TTF", "MISTRAL.TTF", "FRSCRIPT.TTF", "BRUSHSCI.TTF", "Gabriola.ttf",
]
FONT_DIRS = [
    os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"),
    "/usr/share/fonts/truetype",
    "/Library/Fonts",
]


REQUIRED_GLYPHS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-/.:,%()")
EXTRA_FONT_DIRS = [os.path.join(os.path.dirname(os.path.abspath(__file__)), "htr_corpora", "fonts")]


def _has_required_glyphs(path: str) -> bool:
    """Rejects fonts missing digits / dose punctuation (they would render empty boxes)."""
    try:
        from fontTools.ttLib import TTFont
        cmap = TTFont(path, lazy=True).getBestCmap() or {}
        return all(ord(ch) in cmap for ch in REQUIRED_GLYPHS)
    except ImportError:
        return True
    except Exception:
        return False


def discover_handwriting_fonts(extra_dirs: Optional[Sequence[str]] = None) -> List[str]:
    found = []
    for d in list(extra_dirs or []) + EXTRA_FONT_DIRS + FONT_DIRS:
        if not d or not os.path.isdir(d):
            continue
        names = os.listdir(d) if d in EXTRA_FONT_DIRS else HANDWRITING_FONT_FILES
        for name in names:
            path = os.path.join(d, name)
            if not (os.path.exists(path) and name.lower().endswith(".ttf")):
                continue
            try:
                ImageFont.truetype(path, 24)
            except Exception:
                continue
            if _has_required_glyphs(path):
                found.append(path)
    return sorted(set(found))


class HTRAugmenter:
    """Randomised distortions applied to BGR uint8 crops. Each op fires with its own probability."""

    def __init__(self, strength: float = 1.0, seed: Optional[int] = None):
        self.s = strength
        self.rng = random.Random(seed)

    def _bg(self, img: np.ndarray) -> int:
        border = np.concatenate([img[0].reshape(-1), img[-1].reshape(-1)])
        return int(np.median(border))

    def shear(self, img: np.ndarray) -> np.ndarray:
        h, w = img.shape[:2]
        # k > 0 leans the tops of glyphs to the right (forward slant), k < 0 backward slant
        k = float(np.tan(np.radians(self.rng.uniform(-14, 18) * self.s)))
        extra = int(abs(k) * h) + 2
        M = np.float32([[1, -k, k * h if k > 0 else 0.0], [0, 1, 0]])
        bg = self._bg(img)
        return cv2.warpAffine(img, M, (w + extra, h), borderMode=cv2.BORDER_CONSTANT, borderValue=(bg, bg, bg))

    def rotate(self, img: np.ndarray) -> np.ndarray:
        h, w = img.shape[:2]
        ang = self.rng.uniform(-3.0, 3.0) * self.s
        M = cv2.getRotationMatrix2D((w / 2.0, h / 2.0), ang, 1.0)
        bg = self._bg(img)
        return cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=(bg, bg, bg))

    def baseline_wave(self, img: np.ndarray) -> np.ndarray:
        h, w = img.shape[:2]
        amp = self.rng.uniform(0.5, 0.06 * h) * self.s
        freq = self.rng.uniform(0.5, 2.5) * 2 * np.pi / max(1, w)
        phase = self.rng.uniform(0, 2 * np.pi)
        xs, ys = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
        map_y = ys + (amp * np.sin(freq * xs + phase)).astype(np.float32)
        bg = self._bg(img)
        return cv2.remap(img, xs, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(bg, bg, bg))

    def pen_width(self, img: np.ndarray) -> np.ndarray:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
        # Ink is dark: erode() thickens strokes, dilate() thins them
        return cv2.erode(img, k) if self.rng.random() < 0.5 else cv2.dilate(img, k)

    def scale(self, img: np.ndarray) -> np.ndarray:
        h, w = img.shape[:2]
        sy = self.rng.uniform(0.6, 1.3)
        sx = sy * self.rng.uniform(0.85, 1.15)
        nh, nw = max(12, int(h * sy)), max(12, int(w * sx))
        return cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA if sy < 1 else cv2.INTER_CUBIC)

    def blur(self, img: np.ndarray) -> np.ndarray:
        if self.rng.random() < 0.5:
            return cv2.GaussianBlur(img, (3, 3), self.rng.uniform(0.3, 1.1))
        k = self.rng.choice([3, 5])
        kernel = np.zeros((k, k), np.float32)
        kernel[k // 2, :] = 1.0 / k  # horizontal motion blur
        return cv2.filter2D(img, -1, kernel)

    def photometric(self, img: np.ndarray) -> np.ndarray:
        out = img.astype(np.float32)
        alpha = self.rng.uniform(0.7, 1.25)   # contrast
        beta = self.rng.uniform(-25, 25)      # brightness
        out = out * alpha + beta
        if self.rng.random() < 0.4:            # paper tint
            tint = np.array([self.rng.uniform(-12, 12) for _ in range(3)], np.float32)
            out = out + tint
        if self.rng.random() < 0.5:            # sensor / paper grain
            out = out + np.random.normal(0, self.rng.uniform(2, 9), out.shape).astype(np.float32)
        return np.clip(out, 0, 255).astype(np.uint8)

    def faded_ink(self, img: np.ndarray) -> np.ndarray:
        h, w = img.shape[:2]
        ramp = np.linspace(self.rng.uniform(0.0, 0.35), 0.0, w, dtype=np.float32)
        if self.rng.random() < 0.5:
            ramp = ramp[::-1]
        fade = np.tile(ramp, (h, 1))[..., None]
        out = img.astype(np.float32)
        return np.clip(out + (255.0 - out) * fade, 0, 255).astype(np.uint8)

    def ruled_line(self, img: np.ndarray) -> np.ndarray:
        h, w = img.shape[:2]
        y = int(h * self.rng.uniform(0.78, 0.95))
        color = (self.rng.randint(170, 225), self.rng.randint(170, 215), self.rng.randint(150, 200))
        out = img.copy()
        cv2.line(out, (0, y), (w, y), color, 1)
        return out

    def jpeg(self, img: np.ndarray) -> np.ndarray:
        ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, self.rng.randint(30, 80)])
        return cv2.imdecode(buf, cv2.IMREAD_COLOR) if ok else img

    def pad(self, img: np.ndarray) -> np.ndarray:
        h, _ = img.shape[:2]
        bg = self._bg(img)
        t, b = self.rng.randint(0, h // 5 + 1), self.rng.randint(0, h // 5 + 1)
        l, r = self.rng.randint(0, h // 3 + 1), self.rng.randint(0, h // 3 + 1)
        return cv2.copyMakeBorder(img, t, b, l, r, cv2.BORDER_CONSTANT, value=(bg, bg, bg))

    def __call__(self, img: np.ndarray) -> np.ndarray:
        if img.ndim == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        ops = [
            (0.35, self.shear), (0.30, self.rotate), (0.25, self.baseline_wave), (0.25, self.pen_width),
            (0.35, self.scale), (0.25, self.blur), (0.70, self.photometric), (0.15, self.faded_ink),
            (0.12, self.ruled_line), (0.25, self.jpeg), (0.30, self.pad),
        ]
        for p, op in ops:
            if self.rng.random() < p * min(1.0, self.s):
                try:
                    img = op(img)
                except Exception:
                    pass
        return img


class SyntheticMedicalLines:
    """Generates (BGR image, text) pairs of prescription-style handwriting."""

    FORMS = ["Tab", "Tab.", "Cap", "Cap.", "Syp", "Syp.", "Inj", "Inj.", "Oint", "Drops", "Susp"]
    DOSES = ["5 mg", "10 mg", "20 mg", "25 mg", "40 mg", "50 mg", "75 mg", "100 mg", "150 mg", "250 mg",
             "400 mg", "500 mg", "625 mg", "650 mg", "1 g", "2 mg", "0.5 mg", "5 ml", "10 ml", "2 tsp",
             "1 tab", "1 cap", "2 puffs", "1000 IU", "60000 IU", "500mg", "250mg", "40mg"]
    FREQS = ["1-0-1", "1-1-1", "1-0-0", "0-0-1", "0-1-0", "1-1-0", "1/2-0-1/2", "BD", "BID", "TID", "TDS",
             "QID", "OD", "HS", "SOS", "PRN", "STAT", "once daily", "twice daily", "at night"]
    DURATIONS = ["3 days", "5 days", "7 days", "10 days", "14 days", "1 month", "2 weeks", "x 5d", "x 7d",
                 "continue", "x 1 month"]
    INSTRUCTIONS = ["after meals", "before meals", "after food", "empty stomach", "with milk", "AC", "PC",
                    "for fever", "for pain", "if needed"]
    CLINICAL = [
        "C/O fever x 3 days", "K/C/O DM, HTN", "BP 130/80 mmHg", "Pulse 84/min", "SpO2 97% RA",
        "Temp 101 F", "RBS 182 mg/dL", "Adv: CBC, LFT, RFT", "Review after 1 week", "Dx: Acute gastritis",
        "Dx: URTI", "O/E: chest clear", "Hb 11.2 g/dL", "HbA1c 7.4%", "Plenty of oral fluids",
        "Avoid oily food", "Follow up SOS", "Rx", "Inv: USG abdomen", "ECG - NAD",
    ]

    def __init__(
        self,
        drug_names: Sequence[str],
        medication_lines: Optional[Sequence[str]] = None,
        fonts: Optional[Sequence[str]] = None,
        seed: Optional[int] = None
    ):
        self.rng = random.Random(seed)
        self.drugs = [d for d in drug_names if d] or ["Paracetamol", "Amoxicillin", "Metformin"]
        self.med_lines = list(medication_lines or [])
        self.fonts = list(fonts or discover_handwriting_fonts())

    def sample_text(self) -> str:
        r = self.rng.random()
        drug = self.rng.choice(self.drugs)
        if r < 0.30 and self.med_lines:
            return self.rng.choice(self.med_lines)
        if r < 0.65:
            parts = []
            if self.rng.random() < 0.7:
                parts.append(self.rng.choice(self.FORMS))
            parts.append(drug)
            if self.rng.random() < 0.85:
                parts.append(self.rng.choice(self.DOSES))
            if self.rng.random() < 0.75:
                parts.append(self.rng.choice(self.FREQS))
            if self.rng.random() < 0.5:
                parts.append(self.rng.choice(self.DURATIONS))
            if self.rng.random() < 0.3:
                parts.append(self.rng.choice(self.INSTRUCTIONS))
            return " ".join(parts)
        if r < 0.80:
            return self.rng.choice(self.CLINICAL)
        if r < 0.92:
            return drug
        return f"{drug} {self.rng.choice(self.DOSES)}"

    def render(self, text: str) -> np.ndarray:
        size = self.rng.randint(26, 44)
        font = None
        if self.fonts:
            try:
                font = ImageFont.truetype(self.rng.choice(self.fonts), size)
            except Exception:
                font = None
        if font is None:
            font = ImageFont.load_default()

        bbox = font.getbbox(text)
        tw, th = max(1, bbox[2] - bbox[0]), max(1, bbox[3] - bbox[1])
        pad_x, pad_y = self.rng.randint(6, 24), self.rng.randint(6, 16)
        paper = self.rng.randint(225, 255)
        img = Image.new("RGB", (tw + 2 * pad_x, th + 2 * pad_y), (paper, paper, paper - self.rng.randint(0, 12)))
        draw = ImageDraw.Draw(img)

        ink_choice = self.rng.random()
        if ink_choice < 0.45:
            ink = (self.rng.randint(10, 50), self.rng.randint(20, 60), self.rng.randint(90, 160))   # blue ballpoint
        elif ink_choice < 0.9:
            ink = (self.rng.randint(5, 50),) * 3                                                   # black
        else:
            ink = (self.rng.randint(20, 60), self.rng.randint(80, 120), self.rng.randint(20, 60))  # green
        draw.text((pad_x - bbox[0], pad_y - bbox[1]), text, font=font, fill=ink)

        # PIL renders RGB; OpenCV pipeline expects BGR
        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    def sample(self):
        text = self.sample_text()
        return self.render(text), text
