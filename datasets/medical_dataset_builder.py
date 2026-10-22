import os
import sys
import json
import random
import cv2
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, List, Tuple, Any, Optional

# Ensure repository root is on sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from datasets.handwriting_pipeline import HandwritingAugmentationEngine
from app.ai.ocr.medical_postprocessor import MedicalVocabularyPostProcessor


class MedicalDatasetBuilder:
    """
    Comprehensive Medical OCR Dataset Generator & Builder (Phase 4).
    Produces authentic synthetic medical documents, lines, and forms across 4 core categories:
    1. Prescriptions (Doctor letterheads, Rx lines, regimens, advice, signature)
    2. Clinical Notes (Progress notes, vitals, physical examination, impressions)
    3. Lab Reports (CBC, lipid profile, metabolic panels, units, reference intervals)
    4. Mixed Documents (Printed hospital templates with handwritten fill-in entries)

    Integrates comprehensive clinical entities:
    - Drug names (Allopathic & Ayurvedic/Herbal formulary)
    - Dosages (Metric mass, volume, microgram, IU, puffs, drops)
    - Frequencies (Numerical, Latin abbreviations, multiplier expressions)
    - Units (Medication & clinical laboratory diagnostic units)
    - Medical Abbreviations (Clinical headers, labs, radiology, vitals, orders)
    """

    # 1. Comprehensive Drug Formulary
    DRUGS_ALLOPATHIC = [
        "Amoxicillin", "Augmentin", "Azithromycin", "Ciprofloxacin", "Cefixime",
        "Ceftriaxone", "Doxycycline", "Metronidazole", "Clindamycin", "Levofloxacin",
        "Paracetamol", "Acetaminophen", "Ibuprofen", "Diclofenac", "Aceclofenac",
        "Tramadol", "Dolo 650", "Combiflam", "Aspirin", "Naproxen",
        "Omeprazole", "Pantoprazole", "Rabeprazole", "Ranitidine", "Famotidine",
        "Domperidone", "Ondansetron", "Pan-D", "Pantocid", "Sucralfate",
        "Metformin", "Glimepiride", "Atorvastatin", "Rosuvastatin", "Amlodipine",
        "Telmisartan", "Losartan", "Hydrochlorothiazide", "Atenolol", "Enalapril",
        "Cetirizine", "Levocetirizine", "Montelukast", "Fexofenadine", "Salbutamol",
        "Budesonide", "Ambroxol", "Shelcal", "Becosules", "Neurobion"
    ]

    DRUGS_AYURVEDIC = [
        "Kanchanar Guggulu", "Chandraprabha Vati", "Sigru", "Styplon", "Cruel",
        "Ashwagandha", "Brahmi", "Triphala", "Liv-52", "Shatavari",
        "Trikatu", "Septilin", "Cystone", "Rumalaya", "Geriforte"
    ]

    # 2. Dosages
    DOSAGES = [
        "10 mg", "20 mg", "40 mg", "50 mg", "100 mg", "250 mg", "500 mg", "625 mg", "650 mg",
        "1 g", "2.5 ml", "5 ml", "10 ml", "15 ml", "20 ml", "50 mcg", "100 mcg",
        "1000 IU", "5000 IU", "60000 IU", "1 puff", "2 puffs", "2 drops", "1 sachet"
    ]

    # 3. Frequencies & Regimens
    FREQUENCIES = [
        "1-0-1", "1-1-1", "1-0-0", "0-0-1", "0-1-0", "1-0-1-0", "2-0-2",
        "OD", "BD", "BID", "TDS", "TID", "QID", "SOS", "PRN", "STAT", "HS", "AC", "PC",
        "1 tab x 2", "1 cap x 3", "1 tab x 3 with water", "1+2x3", "2 tsp BID"
    ]

    # 4. Units
    MEDICATION_UNITS = ["mg", "mcg", "g", "gm", "ml", "IU", "tab", "cap", "puff", "drops", "sachet", "tsp", "tbsp"]
    LAB_UNITS = ["mmHg", "bpm", "/min", "F", "%", "mg/dL", "g/dL", "K/uL", "mEq/L", "U/L", "ng/mL", "/cu.mm"]

    # 5. Medical Abbreviations
    ABBREVIATIONS = [
        "Rx", "Dx", "Hx", "Sx", "CC", "HPI", "PE", "O/E", "C/O", "K/C/O", "Adv", "Inv",
        "BP", "PR", "HR", "RR", "Temp", "SpO2", "CBC", "WBC", "RBC", "Hb", "PLT", "ESR",
        "CRP", "LFT", "SGOT", "SGPT", "KFT", "RFT", "BUN", "Cr", "FBS", "PPBS", "HbA1c",
        "CXR", "ECG", "USG", "CT", "MRI", "OD", "BD", "BID", "TID", "QID", "SOS", "STAT", "HS"
    ]

    # 6. Doctor & Clinic Profiles
    DOCTORS = [
        {"name": "Dr. Vinay Kumar", "deg": "BAMS, MBA (Healthcare)", "spec": "Consultant Ayurvedic Physician", "reg": "CGMC 643/2006", "phone": "9871033775"},
        {"name": "Dr. S. Mehta", "deg": "MBBS, MD (Medicine)", "spec": "Senior Consultant Physician", "reg": "DMC 48291/2012", "phone": "9811442299"},
        {"name": "Dr. Vishnu Gupta", "deg": "MBBS, MS (General Surgery)", "spec": "Consultant Surgeon", "reg": "MCI 2008/1192", "phone": "9899123456"},
        {"name": "Dr. Ananya Roy", "deg": "MBBS, DCH, DNB (Pediatrics)", "spec": "Consultant Pediatrician", "reg": "WBMC 59281", "phone": "9748012345"},
        {"name": "Dr. R. K. Sharma", "deg": "MBBS, MD (Cardiology)", "spec": "Consultant Cardiologist", "reg": "DMC 31920/2005", "phone": "9810998877"}
    ]

    CLINICS = [
        {"name": "CITY CARE HOSPITAL & RESEARCH CENTER", "addr": "D-96, Amar Colony, Lajpat Nagar-IV, New Delhi-110024"},
        {"name": "METROPOLITAN MULTISPECIALTY CLINIC", "addr": "Plot 14, Sector 12, Dwarka, New Delhi-110078"},
        {"name": "ST. JUDE HEALTHCARE & DIAGNOSTIC CENTER", "addr": "B-22, Civil Lines, North Campus, Delhi-110054"},
        {"name": "APEX CLINICAL WELLNESS & AYURVEDA KENDRA", "addr": "C-916, Arya Vidyasala, Sec-7, New Delhi-110075"}
    ]

    def __init__(self, output_root: Optional[str] = None, seed: int = 42):
        random.seed(seed)
        np.random.seed(seed)
        self.output_root = Path(output_root) if output_root else root_dir / "datasets" / "medical_dataset"
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.engine = HandwritingAugmentationEngine(seed=seed)
        self.postprocessor = MedicalVocabularyPostProcessor()

        # Load typography fonts
        self.printed_font = self._load_font("arial.ttf", 20)
        self.printed_bold = self._load_font("arialbd.ttf", 22)
        self.printed_header = self._load_font("arialbd.ttf", 26)
        self.printed_small = self._load_font("arial.ttf", 16)

    def _load_font(self, font_name: str, size: int) -> ImageFont.FreeTypeFont:
        try:
            return ImageFont.truetype(font_name, size)
        except Exception:
            try:
                return ImageFont.truetype(f"C:/Windows/Fonts/{font_name}", size)
            except Exception:
                return ImageFont.load_default()

    def _get_handwriting_font(self, cursive: bool = False, size: int = 22) -> ImageFont.FreeTypeFont:
        if cursive:
            candidates = ["segoesc.ttf", "Gabriola.ttf"]
        else:
            candidates = ["segoepr.ttf", "Inkfree.ttf", "comic.ttf"]
        
        for name in candidates:
            try:
                return ImageFont.truetype(name, size)
            except Exception:
                pass
        return ImageFont.load_default()

    # =========================================================================
    # A. PRESCRIPTION SAMPLES
    # =========================================================================
    def generate_prescription_sample(self, idx: int) -> Dict[str, Any]:
        """
        Generates an authentic synthetic prescription document:
        - Hospital/Clinic header (printed)
        - Doctor credentials & registration (printed)
        - Patient demographics (printed/handwritten)
        - Rx symbol & handwritten medical item lines with drug, dosage, frequency, duration
        - Advice, vitals, follow-up, and doctor signature
        """
        w, h = 850, 1100
        canvas = Image.new("RGB", (w, h), color=(252, 252, 250))
        draw = ImageDraw.Draw(canvas)

        doc = random.choice(self.DOCTORS)
        clinic = random.choice(self.CLINICS)
        date_str = f"{random.randint(1, 28):02d}/{random.randint(1, 12):02d}/2026"
        pt_name = random.choice(["Rahul Kumar", "Priya Sharma", "Rajesh Patel", "Anita Devi", "Suresh Verma", "Kavita Singh"])
        pt_age = random.randint(22, 68)
        pt_sex = random.choice(["M", "F"])

        text_lines = []

        # 1. Clinic Header
        draw.text((w // 2 - 220, 35), clinic["name"], font=self.printed_header, fill=(20, 30, 80))
        draw.text((w // 2 - 180, 72), clinic["addr"], font=self.printed_small, fill=(70, 70, 70))
        draw.line([(40, 100), (w - 40, 100)], fill=(40, 60, 120), width=2)
        text_lines.append(clinic["name"])
        text_lines.append(clinic["addr"])

        # 2. Doctor Info
        draw.text((50, 115), f"{doc['name']}, {doc['deg']}", font=self.printed_bold, fill=(20, 20, 30))
        draw.text((50, 142), f"{doc['spec']} | Reg No: {doc['reg']}", font=self.printed_small, fill=(60, 60, 60))
        draw.text((w - 200, 115), f"Ph: {doc['phone']}", font=self.printed_small, fill=(60, 60, 60))
        draw.line([(40, 170), (w - 40, 170)], fill=(180, 180, 190), width=1)
        text_lines.append(f"{doc['name']}, {doc['deg']}")
        text_lines.append(f"{doc['spec']} | Reg No: {doc['reg']}")
        text_lines.append(f"Ph: {doc['phone']}")

        # 3. Patient Demographics Line
        pt_line = f"Patient: {pt_name}    Age: {pt_age} yrs    Sex: {pt_sex}    Date: {date_str}"
        draw.text((50, 185), pt_line, font=self.printed_font, fill=(30, 30, 30))
        draw.line([(40, 220), (w - 40, 220)], fill=(200, 200, 200), width=1)
        text_lines.append(pt_line)

        # 4. Vitals & Diagnosis
        bp_val = f"{random.choice([110, 120, 124, 130])}/{random.choice([70, 80, 84, 88])}"
        hr_val = random.randint(68, 86)
        spo2_val = random.randint(97, 99)
        vitals_line = f"Vitals: BP: {bp_val} mmHg, HR: {hr_val} bpm, SpO2: {spo2_val}% on RA"
        draw.text((50, 235), vitals_line, font=self.printed_small, fill=(40, 40, 40))
        text_lines.append(vitals_line)

        diag = random.choice([
            "Acute Bronchitis with URI",
            "Type 2 Diabetes Mellitus with Essential Hypertension",
            "Acute Gastritis with Acid Reflux",
            "Seasonal Allergic Rhinitis & Pharyngitis",
            "Osteoarthritis Knee with Joint Pain"
        ])
        diag_line = f"Diagnosis (Dx): {diag}"
        draw.text((50, 260), diag_line, font=self.printed_font, fill=(15, 25, 60))
        text_lines.append(diag_line)

        # 5. Rx Symbol
        draw.text((50, 305), "Rx:", font=self.printed_header, fill=(20, 40, 100))
        text_lines.append("Rx:")

        # 6. Prescription Items (Handwritten)
        num_items = random.randint(3, 5)
        available_drugs = list(self.DRUGS_ALLOPATHIC)
        if "Ayurvedic" in doc["spec"]:
            available_drugs = list(self.DRUGS_AYURVEDIC) + ["Paracetamol", "Pantocid"]
        random.shuffle(available_drugs)

        y_pos = 350
        hw_font = self._get_handwriting_font(cursive=random.choice([True, False]), size=24)
        ink_color = (random.randint(15, 30), random.randint(20, 45), random.randint(90, 140))

        items_text = []
        for i in range(1, num_items + 1):
            med = available_drugs[i - 1]
            dose = random.choice(["250 mg", "500 mg", "625 mg", "650 mg", "40 mg", "20 mg", "10 mg"])
            freq = random.choice(["1-0-1", "1-0-0", "0-0-1", "1-1-1", "1-0-1 SOS", "BID", "TID"])
            duration = random.choice(["x 5 days", "x 7 days", "x 10 days", "x 1 month", "x 3 days"])
            form = "Tab." if "mg" in dose else "Syp."
            if "Guggulu" in med or "Vati" in med:
                form = ""
                dose = "2 tab" if "Guggulu" in med else "1 tab"
                freq = "x 2 with water"

            item_str = f"{i}. {form} {med} {dose} - {freq} {duration}".strip()
            draw.text((70, y_pos), item_str, font=hw_font, fill=ink_color)
            text_lines.append(item_str)
            items_text.append(item_str)
            y_pos += 52

        # 7. Advice & Sign-off
        adv_text = random.choice([
            "Adv: Plenty of oral fluids, rest x 3 days, avoid cold drinks",
            "Adv: Low salt diet, regular morning walk, review after 1 month with FBS/PPBS",
            "Adv: Avoid oily/spicy food, take medicines after meals, review after 5 days",
            "Adv: Warm saline gargles TID, steam inhalation BID, rest"
        ])
        y_pos = max(y_pos + 30, 680)
        draw.text((50, y_pos), adv_text, font=hw_font, fill=(20, 20, 40))
        text_lines.append(adv_text)

        sign_line = f"{doc['name']}\n{doc['deg']}"
        draw.text((w - 240, h - 140), "Doctor's Signature:", font=self.printed_small, fill=(70, 70, 70))
        draw.text((w - 240, h - 110), doc['name'], font=hw_font, fill=ink_color)
        text_lines.append(f"Doctor's Signature: {doc['name']}")

        # OpenCV Post-Processing: Slant & Paper noise
        cv_img = cv2.cvtColor(np.array(canvas), cv2.COLOR_RGB2BGR)
        cv_img = self.engine.apply_paper_and_ink_noise(cv_img)

        # Save files
        cat_dir = self.output_root / "prescriptions"
        cat_dir.mkdir(parents=True, exist_ok=True)
        img_file = cat_dir / f"prescription_{idx:03d}.png"
        txt_file = cat_dir / f"prescription_{idx:03d}.txt"

        cv2.imwrite(str(img_file), cv_img)
        full_text = "\n".join(text_lines)
        txt_file.write_text(full_text, encoding="utf-8")

        entities = self.postprocessor.extract_medical_entities(full_text)
        return {
            "id": f"prescription_{idx:03d}",
            "category": "prescription",
            "image_path": str(img_file),
            "ground_truth_path": str(txt_file),
            "text": full_text,
            "entities": entities
        }

    # =========================================================================
    # B. CLINICAL NOTES SAMPLES
    # =========================================================================
    def generate_clinical_note_sample(self, idx: int) -> Dict[str, Any]:
        """
        Generates realistic bedside / OPD physician clinical notes:
        - Ward / Department header
        - Chief Complaints (C/O)
        - History of Present Illness (HPI) & Known Case (K/C/O)
        - Physical Examination (O/E) & Vitals (BP, HR, RR, SpO2, Temp)
        - Clinical Impression (Dx)
        - Treatment Plan & Orders
        """
        w, h = 850, 1100
        canvas = Image.new("RGB", (w, h), color=(250, 250, 248))
        draw = ImageDraw.Draw(canvas)

        ward = random.choice(["WARD 4B (INTERNAL MEDICINE)", "OPD CONSULTATION CLINIC", "INTENSIVE CARE UNIT (STEP DOWN)", "SURGICAL WARD 2A"])
        pt_name = random.choice(["Vikram Malhotra", "Meera Sen", "Deepak Joshi", "Ritu Agarwal", "Mohd. Tariq"])
        pt_age = random.randint(28, 74)
        date_str = f"{random.randint(1, 28):02d}/{random.randint(1, 12):02d}/2026"
        time_str = f"{random.randint(9, 17):02d}:{random.choice(['00', '15', '30', '45'])} {random.choice(['AM', 'PM'])}"

        text_lines = []

        # Header
        draw.text((50, 35), f"PROGRESS NOTE — {ward}", font=self.printed_header, fill=(20, 30, 70))
        draw.text((50, 72), f"Patient: {pt_name}    Age: {pt_age}    Date: {date_str}    Time: {time_str}", font=self.printed_font, fill=(50, 50, 50))
        draw.line([(40, 105), (w - 40, 105)], fill=(160, 160, 170), width=2)
        text_lines.append(f"PROGRESS NOTE — {ward}")
        text_lines.append(f"Patient: {pt_name}    Age: {pt_age}    Date: {date_str}    Time: {time_str}")

        # Note entries in handwriting
        hw_font = self._get_handwriting_font(cursive=random.choice([True, False]), size=23)
        ink_color = (random.randint(10, 30), random.randint(15, 35), random.randint(20, 45))

        bp = f"{random.choice([118, 120, 132, 140])}/{random.choice([76, 80, 84, 90])}"
        pulse = random.randint(68, 88)
        spo2 = random.randint(96, 99)
        temp = f"{random.choice(['98.4', '98.6', '99.2', '100.4'])} F"

        note_blocks = [
            f"C/O: Pt c/o fever with chills, productive cough and headache x 3 days",
            f"K/C/O: Type 2 DM x 6 yrs on Tab Metformin 500 mg BD. No drug allergies",
            f"Vitals: BP: {bp} mmHg, HR: {pulse} bpm, Temp: {temp}, SpO2: {spo2}% on RA",
            f"O/E: Chest: Bilateral coarse crepitations, air entry equal bilaterally",
            f"     CVS: S1 S2 heard regular, no murmur. P/A: Soft, non-tender",
            f"Impression (Dx): Community Acquired Pneumonia (CAP) with URI",
            f"Plan: 1. Inj Ceftriaxone 1 g IV BD after test dose",
            f"      2. Tab Azithromycin 500 mg OD x 5 days",
            f"      3. Tab Paracetamol 650 mg SOS for fever",
            f"      4. Nebulization with Salbutamol + Budesonide Q8H",
            f"      5. Send CBC, CRP, Blood Culture, CXR PA view stat",
            f"Review in evening round with lab reports."
        ]

        # Draw lined guide sheet (faint prescription rule)
        y = 145
        for line_str in note_blocks:
            draw.line([(45, y + 30), (w - 45, y + 30)], fill=(230, 230, 240), width=1)
            draw.text((55, y), line_str, font=hw_font, fill=ink_color)
            text_lines.append(line_str)
            y += 58

        draw.text((w - 220, h - 120), "Attending Physician:", font=self.printed_small, fill=(70, 70, 70))
        draw.text((w - 220, h - 90), "Dr. S. Mehta, MD", font=hw_font, fill=ink_color)
        text_lines.append("Attending Physician: Dr. S. Mehta, MD")

        cv_img = cv2.cvtColor(np.array(canvas), cv2.COLOR_RGB2BGR)
        cv_img = self.engine.apply_paper_and_ink_noise(cv_img)

        cat_dir = self.output_root / "clinical_notes"
        cat_dir.mkdir(parents=True, exist_ok=True)
        img_file = cat_dir / f"clinical_note_{idx:03d}.png"
        txt_file = cat_dir / f"clinical_note_{idx:03d}.txt"

        cv2.imwrite(str(img_file), cv_img)
        full_text = "\n".join(text_lines)
        txt_file.write_text(full_text, encoding="utf-8")

        entities = self.postprocessor.extract_medical_entities(full_text)
        return {
            "id": f"clinical_note_{idx:03d}",
            "category": "clinical_note",
            "image_path": str(img_file),
            "ground_truth_path": str(txt_file),
            "text": full_text,
            "entities": entities
        }

    # =========================================================================
    # C. LAB REPORT SAMPLES
    # =========================================================================
    def generate_lab_report_sample(self, idx: int) -> Dict[str, Any]:
        """
        Generates clinical laboratory test reports:
        - Diagnostic Laboratory header (printed)
        - Patient demographics & referring doctor
        - Tabular laboratory parameters (Test Name, Observed Value, Units, Biological Reference Intervals)
        - Pathology remarks & authorization
        """
        w, h = 850, 1100
        canvas = Image.new("RGB", (w, h), color=(255, 255, 255))
        draw = ImageDraw.Draw(canvas)

        pt_name = random.choice(["Manoj Tiwary", "Sunita Nair", "Arjun Reddy", "Farida Begum", "Harish Chandra"])
        pt_age = random.randint(24, 70)
        pt_sex = random.choice(["Male", "Female"])
        date_str = f"{random.randint(1, 28):02d}/{random.randint(1, 12):02d}/2026"
        doc = random.choice(self.DOCTORS)

        text_lines = []

        # 1. Lab Header
        draw.text((50, 30), "METROPATH CLINICAL LABORATORIES", font=self.printed_header, fill=(150, 20, 30))
        draw.text((50, 65), "ISO 15189 Certified Diagnostic Pathology & Molecular Medicine", font=self.printed_small, fill=(80, 80, 80))
        draw.line([(40, 95), (w - 40, 95)], fill=(150, 20, 30), width=2)
        text_lines.append("METROPATH CLINICAL LABORATORIES")
        text_lines.append("ISO 15189 Certified Diagnostic Pathology & Molecular Medicine")

        # 2. Patient Demographics Table
        draw.text((50, 110), f"Patient Name: {pt_name}", font=self.printed_bold, fill=(20, 20, 20))
        draw.text((450, 110), f"Sample Date: {date_str}", font=self.printed_font, fill=(30, 30, 30))
        draw.text((50, 135), f"Age / Sex: {pt_age} Yrs / {pt_sex}", font=self.printed_font, fill=(30, 30, 30))
        draw.text((450, 135), f"Ref. By: {doc['name']}", font=self.printed_font, fill=(30, 30, 30))
        draw.line([(40, 165), (w - 40, 165)], fill=(200, 200, 200), width=1)
        text_lines.append(f"Patient Name: {pt_name}    Sample Date: {date_str}")
        text_lines.append(f"Age / Sex: {pt_age} Yrs / {pt_sex}    Ref. By: {doc['name']}")

        # 3. Test Department Header
        test_type = random.choice(["COMPLETE BLOOD COUNT (CBC)", "COMPREHENSIVE METABOLIC PANEL (CMP)"])
        draw.text((50, 180), f"DEPARTMENT OF BIOCHEMISTRY & HEMATOLOGY — {test_type}", font=self.printed_bold, fill=(10, 30, 80))
        text_lines.append(f"DEPARTMENT OF BIOCHEMISTRY & HEMATOLOGY — {test_type}")

        # 4. Table Header
        draw.rectangle([(40, 215), (w - 40, 245)], fill=(240, 242, 248))
        draw.text((50, 222), "TEST NAME", font=self.printed_bold, fill=(20, 30, 60))
        draw.text((330, 222), "RESULT", font=self.printed_bold, fill=(20, 30, 60))
        draw.text((460, 222), "UNITS", font=self.printed_bold, fill=(20, 30, 60))
        draw.text((600, 222), "REFERENCE RANGE", font=self.printed_bold, fill=(20, 30, 60))
        draw.line([(40, 245), (w - 40, 245)], fill=(180, 190, 210), width=1)
        text_lines.append(f"{'TEST NAME':<30} | {'RESULT':<10} | {'UNITS':<12} | {'REFERENCE RANGE'}")

        # 5. Table Rows
        if "CBC" in test_type:
            rows = [
                ("Hemoglobin (Hb)", f"{round(random.uniform(11.5, 15.5), 1)}", "g/dL", "12.0 - 16.0"),
                ("Total Leukocyte Count (WBC)", f"{random.randint(5200, 10800)}", "/cu.mm", "4000 - 11000"),
                ("Platelet Count (PLT)", f"{random.randint(160, 380)}", "K/uL", "150 - 450"),
                ("RBC Count", f"{round(random.uniform(4.0, 5.4), 2)}", "million/uL", "4.2 - 5.5"),
                ("Hematocrit (PCV)", f"{round(random.uniform(36.0, 46.0), 1)}", "%", "37.0 - 48.0"),
                ("ESR (Westergren)", f"{random.randint(8, 22)}", "mm/hr", "0 - 20")
            ]
        else:
            rows = [
                ("Fasting Blood Sugar (FBS)", f"{random.randint(82, 114)}", "mg/dL", "70 - 100"),
                ("Post Prandial Sugar (PPBS)", f"{random.randint(118, 158)}", "mg/dL", "< 140"),
                ("HbA1c (Glycated Hb)", f"{round(random.uniform(5.4, 6.8), 1)}", "%", "< 5.7 Normal"),
                ("Serum Creatinine (Cr)", f"{round(random.uniform(0.7, 1.2), 2)}", "mg/dL", "0.6 - 1.2"),
                ("Blood Urea Nitrogen (BUN)", f"{random.randint(10, 19)}", "mg/dL", "7 - 20"),
                ("Total Cholesterol", f"{random.randint(155, 215)}", "mg/dL", "< 200"),
                ("Serum Bilirubin Total", f"{round(random.uniform(0.5, 1.1), 2)}", "mg/dL", "0.2 - 1.2")
            ]

        y = 260
        for name, res_val, unit, ref in rows:
            draw.text((50, y), name, font=self.printed_font, fill=(30, 30, 30))
            draw.text((330, y), res_val, font=self.printed_bold, fill=(10, 10, 10))
            draw.text((460, y), unit, font=self.printed_font, fill=(40, 40, 40))
            draw.text((600, y), ref, font=self.printed_small, fill=(70, 70, 70))
            draw.line([(40, y + 28), (w - 40, y + 28)], fill=(235, 235, 235), width=1)
            text_lines.append(f"{name:<30} | {res_val:<10} | {unit:<12} | {ref}")
            y += 38

        # 6. Pathologist Remarks in handwriting
        y += 40
        draw.text((50, y), "Pathologist Remarks / Observations:", font=self.printed_bold, fill=(20, 20, 20))
        text_lines.append("Pathologist Remarks / Observations:")
        y += 30

        hw_font = self._get_handwriting_font(cursive=False, size=22)
        remark = "Sample processed under controlled temperature. Vitals & morphology correlate with clinical history."
        draw.text((60, y), remark, font=hw_font, fill=(15, 25, 55))
        text_lines.append(remark)

        draw.text((w - 240, h - 100), "Dr. K. N. Sen, MD (Pathology)", font=self.printed_small, fill=(40, 40, 40))
        draw.text((w - 240, h - 80), "Senior Consultant Pathologist", font=self.printed_small, fill=(70, 70, 70))
        text_lines.append("Dr. K. N. Sen, MD (Pathology) — Senior Consultant Pathologist")

        cv_img = cv2.cvtColor(np.array(canvas), cv2.COLOR_RGB2BGR)
        cv_img = self.engine.apply_paper_and_ink_noise(cv_img)

        cat_dir = self.output_root / "lab_reports"
        cat_dir.mkdir(parents=True, exist_ok=True)
        img_file = cat_dir / f"lab_report_{idx:03d}.png"
        txt_file = cat_dir / f"lab_report_{idx:03d}.txt"

        cv2.imwrite(str(img_file), cv_img)
        full_text = "\n".join(text_lines)
        txt_file.write_text(full_text, encoding="utf-8")

        entities = self.postprocessor.extract_medical_entities(full_text)
        return {
            "id": f"lab_report_{idx:03d}",
            "category": "lab_report",
            "image_path": str(img_file),
            "ground_truth_path": str(txt_file),
            "text": full_text,
            "entities": entities
        }

    # =========================================================================
    # D. MIXED PRINTED / HANDWRITTEN SAMPLES
    # =========================================================================
    def generate_mixed_document_sample(self, idx: int) -> Dict[str, Any]:
        """
        Generates dual-layer hybrid forms (Hospital Admission & Discharge Summaries):
        - Formal printed table frames, borders, field tags, and checkboxes
        - Handwritten patient entries, clinical observations, and discharge instructions
        """
        w, h = 850, 1100
        canvas = Image.new("RGB", (w, h), color=(252, 252, 250))
        draw = ImageDraw.Draw(canvas)

        pt_name = random.choice(["Gopal Krishna", "Savita Deshmukh", "Nitin Gadhavi", "Pooja Bose"])
        pt_age = random.randint(25, 72)
        pt_sex = random.choice(["M", "F"])
        adm_date = f"{random.randint(1, 25):02d}/{random.randint(1, 12):02d}/2026"
        dis_date = f"{int(adm_date[:2]) + random.randint(2, 4):02d}{adm_date[2:]}"
        doc = random.choice(self.DOCTORS)

        text_lines = []

        # 1. Header
        draw.text((w // 2 - 200, 35), "HOSPITAL DISCHARGE SUMMARY", font=self.printed_header, fill=(20, 40, 80))
        draw.line([(40, 75), (w - 40, 75)], fill=(40, 60, 100), width=2)
        text_lines.append("HOSPITAL DISCHARGE SUMMARY")

        # 2. Form Fields (Printed labels, Handwritten fill-ins)
        hw_font = self._get_handwriting_font(cursive=random.choice([True, False]), size=22)
        ink_blue = (random.randint(15, 30), random.randint(25, 55), random.randint(100, 160))

        fields = [
            ("Patient Name:", pt_name, 50, 95),
            ("Age / Sex:", f"{pt_age} Yrs / {pt_sex}", 460, 95),
            ("Date of Admission:", adm_date, 50, 135),
            ("Date of Discharge:", dis_date, 460, 135),
            ("Consultant Doctor:", doc["name"], 50, 175),
            ("Department:", doc["spec"], 460, 175)
        ]

        for label, val, x, y in fields:
            draw.text((x, y), label, font=self.printed_bold, fill=(30, 30, 30))
            draw.text((x + 160, y - 2), val, font=hw_font, fill=ink_blue)
            draw.line([(x + 155, y + 24), (x + 350, y + 24)], fill=(190, 190, 200), width=1)
            text_lines.append(f"{label} {val}")

        draw.line([(40, 220), (w - 40, 220)], fill=(180, 180, 180), width=1)

        # 3. Final Diagnosis & Condition on Discharge
        draw.text((50, 240), "FINAL DIAGNOSIS (Dx):", font=self.printed_bold, fill=(20, 20, 40))
        diag_val = "Acute Calculous Cholecystitis s/p Laparoscopic Cholecystectomy"
        draw.text((260, 238), diag_val, font=hw_font, fill=ink_blue)
        text_lines.append(f"FINAL DIAGNOSIS (Dx): {diag_val}")

        draw.text((50, 280), "CONDITION AT DISCHARGE:", font=self.printed_bold, fill=(20, 20, 40))
        cond_val = "Hemodynamically stable, afebrile, surgical wound clean and dry"
        draw.text((300, 278), cond_val, font=hw_font, fill=ink_blue)
        text_lines.append(f"CONDITION AT DISCHARGE: {cond_val}")

        # 4. Discharge Medications (Printed frame + Handwritten prescription table)
        draw.text((50, 330), "DISCHARGE MEDICATIONS & REGIMEN:", font=self.printed_bold, fill=(20, 30, 80))
        text_lines.append("DISCHARGE MEDICATIONS & REGIMEN:")

        draw.rectangle([(40, 360), (w - 40, 395)], fill=(238, 242, 250))
        draw.text((50, 368), "S.No", font=self.printed_bold, fill=(20, 20, 20))
        draw.text((110, 368), "Medication & Dosage", font=self.printed_bold, fill=(20, 20, 20))
        draw.text((430, 368), "Frequency", font=self.printed_bold, fill=(20, 20, 20))
        draw.text((580, 368), "Duration", font=self.printed_bold, fill=(20, 20, 20))
        draw.text((690, 368), "Instructions", font=self.printed_bold, fill=(20, 20, 20))
        draw.line([(40, 395), (w - 40, 395)], fill=(170, 180, 200), width=1)

        med_rows = [
            ("1", "Tab Augmentin 625 mg", "1-0-1", "x 5 days", "After food"),
            ("2", "Tab Pantoprazole 40 mg", "1-0-0", "x 7 days", "Before breakfast"),
            ("3", "Tab Paracetamol 650 mg", "1-0-1", "SOS", "For pain/fever"),
            ("4", "Syp Liv-52", "2 tsp BID", "x 15 days", "With water")
        ]

        y_med = 410
        for s_no, med_name, freq, dur, inst in med_rows:
            draw.text((55, y_med), s_no, font=self.printed_font, fill=(30, 30, 30))
            draw.text((110, y_med), med_name, font=hw_font, fill=ink_blue)
            draw.text((430, y_med), freq, font=hw_font, fill=ink_blue)
            draw.text((580, y_med), dur, font=hw_font, fill=ink_blue)
            draw.text((690, y_med), inst, font=self.printed_small, fill=(50, 50, 50))
            draw.line([(40, y_med + 32), (w - 40, y_med + 32)], fill=(230, 230, 230), width=1)
            text_lines.append(f"{s_no}. {med_name} | {freq} | {dur} | {inst}")
            y_med += 45

        # 5. Follow-up and Instructions
        draw.text((50, y_med + 20), "FOLLOW-UP & POST-OP ADVICE:", font=self.printed_bold, fill=(20, 20, 20))
        text_lines.append("FOLLOW-UP & POST-OP ADVICE:")
        adv_str = "Review in OPD after 7 days for suture removal. Emergency visit if fever or severe pain."
        draw.text((55, y_med + 50), adv_str, font=hw_font, fill=ink_blue)
        text_lines.append(adv_str)

        draw.text((w - 240, h - 100), "Authorized Medical Officer:", font=self.printed_small, fill=(70, 70, 70))
        draw.text((w - 240, h - 75), doc["name"], font=hw_font, fill=ink_blue)
        text_lines.append(f"Authorized Medical Officer: {doc['name']}")

        cv_img = cv2.cvtColor(np.array(canvas), cv2.COLOR_RGB2BGR)
        cv_img = self.engine.apply_paper_and_ink_noise(cv_img)

        cat_dir = self.output_root / "mixed_documents"
        cat_dir.mkdir(parents=True, exist_ok=True)
        img_file = cat_dir / f"mixed_document_{idx:03d}.png"
        txt_file = cat_dir / f"mixed_document_{idx:03d}.txt"

        cv2.imwrite(str(img_file), cv_img)
        full_text = "\n".join(text_lines)
        txt_file.write_text(full_text, encoding="utf-8")

        entities = self.postprocessor.extract_medical_entities(full_text)
        return {
            "id": f"mixed_document_{idx:03d}",
            "category": "mixed_document",
            "image_path": str(img_file),
            "ground_truth_path": str(txt_file),
            "text": full_text,
            "entities": entities
        }

    # =========================================================================
    # BUILD ENTIRE DATASET
    # =========================================================================
    def build_dataset(self, samples_per_category: int = 5) -> Dict[str, Any]:
        """
        Builds the complete multi-source medical handwriting dataset across:
        - prescriptions
        - clinical_notes
        - lab_reports
        - mixed_documents
        Outputs metadata.json indexing all samples and extracted medical entities.
        """
        print("=" * 80)
        print("    BUILDING COMPREHENSIVE MEDICAL OCR DATASET (PHASE 4)")
        print("=" * 80)

        all_samples = []
        counts = {"prescription": 0, "clinical_note": 0, "lab_report": 0, "mixed_document": 0}

        print(f"Generating {samples_per_category} prescription samples...")
        for i in range(1, samples_per_category + 1):
            s = self.generate_prescription_sample(i)
            all_samples.append(s)
            counts["prescription"] += 1

        print(f"Generating {samples_per_category} clinical note samples...")
        for i in range(1, samples_per_category + 1):
            s = self.generate_clinical_note_sample(i)
            all_samples.append(s)
            counts["clinical_note"] += 1

        print(f"Generating {samples_per_category} lab report samples...")
        for i in range(1, samples_per_category + 1):
            s = self.generate_lab_report_sample(i)
            all_samples.append(s)
            counts["lab_report"] += 1

        print(f"Generating {samples_per_category} mixed document samples...")
        for i in range(1, samples_per_category + 1):
            s = self.generate_mixed_document_sample(i)
            all_samples.append(s)
            counts["mixed_document"] += 1

        # Manifest
        metadata_file = self.output_root / "metadata.json"
        manifest = {
            "dataset_name": "MedIntel Medical OCR Comprehensive Dataset",
            "total_samples": len(all_samples),
            "categories": counts,
            "samples": all_samples
        }
        metadata_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        print(f"\nDataset build complete! Total: {len(all_samples)} documents.")
        print(f"Saved manifest to {metadata_file}")
        return manifest


if __name__ == "__main__":
    builder = MedicalDatasetBuilder()
    builder.build_dataset(samples_per_category=5)
