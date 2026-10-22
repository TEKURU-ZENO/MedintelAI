import os
import random
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from typing import List, Tuple, Dict, Any, Optional

class HandwritingAugmentationEngine:
    """
    Document-Agnostic Handwriting Augmenter & Synthetic Line Generator.
    Produces high-fidelity handwriting variations:
    - Cursive ligature & connected script styling
    - Slanted handwriting (affine shear transformations)
    - Distinct writing styles (stroke thickness, baseline wandering, variable kerning)
    - Real-world noise (paper grain, ink pressure dropout, ruled notebook lines)
    """

    # Comprehensive clinical & form line templates
    HANDWRITING_TEMPLATES = [
        # Prescriptions & Regimens
        "Tab Amoxicillin 500mg - 1-0-1 x 5 days after meals",
        "Cap Augmentin 625mg 1-0-1 x 7 days",
        "Tab Paracetamol 650mg SOS for fever",
        "Tab Metformin 500mg - 1-0-1 with meals",
        "Tab Atorvastatin 20mg - 0-0-1 at bedtime",
        "Cap Omeprazole 20mg - 1-0-0 AC morning",
        "Tab Pantocid 40mg 1-0-0 before food",
        "Tab Cetirizine 10mg 0-0-1 for allergy",
        "Syp Liv-52 2 tsp BID x 1 month",
        "Kanchanar guggulu 2 tab x 3 with water",
        "Chandraprabha vati 1 tab x 2 with milk",
        "Sigru 1 cap x 2 after food",
        "Styplon 1 tab x 2 for bleeding",
        # Doctor Vitals & Clinical Examination
        "BP: 120/80 mmHg, Pulse: 72 bpm, Temp: 98.6 F",
        "SPO2: 98% on room air, RR: 16/min",
        "Chest: Clear to auscultation bilaterally",
        "Abdomen: Soft, non-tender, no organomegaly",
        "Adv: Plenty of oral fluids, bed rest x 3 days",
        "Review after 5 days with CBC and urine report",
        "Patient complains of severe headache and nausea",
        "Known case of Type 2 Diabetes x 5 years",
        "No known drug allergies reported",
        # Form Demographics & Hospital Entries
        "Patient Name: Rahul Kumar Sharma, Age: 42, Sex: M",
        "Date of Consultation: 13/06/2026",
        "Dr. Vishnu Gupta, MBBS, MS (General Surgery)",
        "Dr. Vinay Kumar, BAMS, Consultant Ayurvedic Physician",
        "Registration No: CGMC 643/2006",
        "Ph: 9871033775, Emergency: 8800918136",
        "Timing: Mon & Wed 7.00 pm to 9.00 pm",
        "Diagnosis: Acute Gastritis with acid reflux"
    ]

    def __init__(self, seed: int = 42):
        random.seed(seed)
        np.random.seed(seed)
        self.available_fonts = []
        candidate_fonts = [
            "segoepr.ttf",      # Segoe Print (casual handwriting)
            "segoesc.ttf",      # Segoe Script (cursive handwriting)
            "Inkfree.ttf",      # Ink Free (ballpoint handwriting)
            "Gabriola.ttf",     # Gabriola (flourished script)
            "comic.ttf",        # Comic Sans (print style)
        ]
        for f in candidate_fonts:
            try:
                _ = ImageFont.truetype(f, 24)
                self.available_fonts.append(f)
            except Exception:
                pass

    def apply_slant(self, img: np.ndarray, angle_deg: float = None) -> np.ndarray:
        """
        Applies natural affine shear to simulate forward or backward handwriting slant.
        """
        if angle_deg is None:
            # Typical human slant ranges from -18 (backward) to +22 (forward)
            angle_deg = random.uniform(-18.0, 22.0)
        
        h, w = img.shape[:2]
        shear_factor = np.tan(np.radians(angle_deg))
        
        # Affine shear matrix: x' = x + shear * (h - y)
        M = np.float32([
            [1, shear_factor, -shear_factor * (h / 2.0)],
            [0, 1, 0]
        ])
        
        bg_val = int(np.mean(img[0:5, 0:5])) if img.size > 0 else 255
        sheared = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=(bg_val, bg_val, bg_val))
        return sheared

    def apply_baseline_wandering(self, img: np.ndarray, amplitude: float = 2.5, frequency: float = 0.02) -> np.ndarray:
        """
        Simulates organic hand-drift where handwriting deviates slightly from a straight ruler baseline.
        """
        h, w = img.shape[:2]
        map_x = np.zeros((h, w), np.float32)
        map_y = np.zeros((h, w), np.float32)

        phase = random.uniform(0, 2 * np.pi)
        for i in range(h):
            for j in range(w):
                map_x[i, j] = j
                map_y[i, j] = i + amplitude * np.sin(frequency * j + phase)

        bg_val = int(np.mean(img[0:5, 0:5])) if img.size > 0 else 255
        wandered = cv2.remap(img, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(bg_val, bg_val, bg_val))
        return wandered

    def apply_stroke_variation(self, img: np.ndarray) -> np.ndarray:
        """
        Simulates varying pen tip thickness (fine ballpoint vs gel pen vs felt marker).
        """
        style = random.choice(["normal", "fine", "thick", "feathered"])
        if style == "normal":
            return img
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        if style == "fine":
            # Erode dark strokes (inverting binary for morphological operations)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            inv = cv2.bitwise_not(gray)
            eroded = cv2.erode(inv, kernel, iterations=1)
            result = cv2.bitwise_not(eroded)
        elif style == "thick":
            # Dilate dark strokes
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            inv = cv2.bitwise_not(gray)
            dilated = cv2.dilate(inv, kernel, iterations=1)
            result = cv2.bitwise_not(dilated)
        else: # feathered / ink bleed
            blurred = cv2.GaussianBlur(gray, (3, 3), 0.5)
            result = cv2.addWeighted(gray, 0.7, blurred, 0.3, 0)

        if len(img.shape) == 3:
            return cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)
        return result

    def apply_paper_and_ink_noise(self, img: np.ndarray) -> np.ndarray:
        """
        Simulates realistic paper texture, ink pressure drops, and notebook guidelines.
        """
        h, w = img.shape[:2]
        noisy = img.astype(np.float32)

        # 1. Paper grain texture
        grain = np.random.normal(0, 3.5, (h, w, 3) if len(img.shape) == 3 else (h, w))
        noisy = np.clip(noisy + grain, 0, 255).astype(np.uint8)

        # 2. Occasional ruled guideline (e.g. blue or gray prescription notebook line)
        if random.random() < 0.45:
            line_y = random.randint(int(h * 0.75), int(h * 0.88))
            line_color = (random.randint(210, 230), random.randint(215, 235), random.randint(230, 245))
            cv2.line(noisy, (0, line_y), (w, line_y), line_color, 1)

        # 3. Ink pressure fading
        if random.random() < 0.35:
            mask = np.tile(np.linspace(0.88, 1.05, w), (h, 1))
            if len(noisy.shape) == 3:
                mask = np.stack([mask]*3, axis=2)
            noisy = np.clip(noisy * mask, 0, 255).astype(np.uint8)

        return noisy

    def render_handwritten_line(
        self,
        text: str,
        target_width: int = 384,
        target_height: int = 64,
        style: Optional[str] = None
    ) -> Tuple[np.ndarray, str]:
        """
        Renders a synthetic line of clinical handwriting with organic slant, baseline drift, and paper noise.
        Preserves natural aspect ratio without horizontal distortion.
        Returns (OpenCV_BGR_array, clean_text).
        """
        # Choose font and font size
        font_name = None
        if style == "cursive":
            cursive_candidates = [f for f in self.available_fonts if "segoesc" in f.lower() or "gabriola" in f.lower()]
            font_name = cursive_candidates[0] if cursive_candidates else (self.available_fonts[0] if self.available_fonts else None)
        elif self.available_fonts:
            font_name = random.choice(self.available_fonts)

        font_size = random.randint(22, 28)
        try:
            font = ImageFont.truetype(font_name, font_size) if font_name else ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()

        # Measure text dimensions
        try:
            bbox = font.getbbox(text)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
        except Exception:
            text_w = len(text) * 14
            text_h = 24

        # Canvas dimensions
        canvas_w = max(target_width, text_w + 40)
        canvas_h = max(target_height, text_h + 24)

        # Background color
        bg = random.randint(242, 255)
        pil_img = Image.new("RGB", (canvas_w, canvas_h), color=(bg, bg, bg))
        draw = ImageDraw.Draw(pil_img)

        # Realistic pen ink colors
        ink_style = random.choice(["blue_ballpoint", "black_gel", "faded_blue", "dark_gray"])
        if ink_style == "blue_ballpoint":
            ink_color = (random.randint(15, 35), random.randint(30, 65), random.randint(110, 160))
        elif ink_style == "black_gel":
            v = random.randint(20, 45)
            ink_color = (v, v, v)
        elif ink_style == "faded_blue":
            ink_color = (random.randint(50, 75), random.randint(70, 95), random.randint(130, 175))
        else:
            ink_color = (random.randint(40, 60), random.randint(40, 60), random.randint(45, 65))

        # Render characters with slight jitter
        y_pos = max(4, (canvas_h - text_h) // 2 + random.randint(-3, 3))
        draw.text((16, y_pos), text, font=font, fill=ink_color)

        cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        # Apply augmentation transforms:
        # A. Slant (shear)
        cv_img = self.apply_slant(cv_img)
        # B. Baseline wandering
        cv_img = self.apply_baseline_wandering(cv_img, amplitude=random.uniform(1.0, 2.5))
        # C. Stroke variation
        cv_img = self.apply_stroke_variation(cv_img)
        # D. Paper and ink noise
        cv_img = self.apply_paper_and_ink_noise(cv_img)

        # Standardize output size to (384, 64) with aspect-ratio preserving fit + padding
        h, w = cv_img.shape[:2]
        scale = float(target_height) / float(h)
        scaled_w = int(w * scale)
        scaled_h = target_height

        if scaled_w <= target_width:
            scaled = cv2.resize(cv_img, (scaled_w, scaled_h), interpolation=cv2.INTER_AREA)
            pad_left = (target_width - scaled_w) // 2
            pad_right = target_width - scaled_w - pad_left
            standardized = cv2.copyMakeBorder(
                scaled, 0, 0, pad_left, pad_right,
                cv2.BORDER_CONSTANT, value=(bg, bg, bg)
            )
        else:
            standardized = cv2.resize(cv_img, (target_width, target_height), interpolation=cv2.INTER_AREA)

        return standardized, text

    def generate_dataset_split(
        self,
        total_samples: int = 100,
        train_ratio: float = 0.80,
        val_ratio: float = 0.10
    ) -> Dict[str, List[Tuple[np.ndarray, str]]]:
        """
        Creates train/validation/test splits of line-level handwriting crops.
        """
        samples = []
        for i in range(total_samples):
            text = random.choice(self.HANDWRITING_TEMPLATES)
            img, t = self.render_handwritten_line(text)
            samples.append((img, t))

        random.shuffle(samples)
        n_train = int(total_samples * train_ratio)
        n_val = int(total_samples * val_ratio)

        splits = {
            "train": samples[:n_train],
            "val": samples[n_train:n_train + n_val],
            "test": samples[n_train + n_val:]
        }
        return splits
