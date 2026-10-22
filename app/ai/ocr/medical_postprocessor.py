import re
from typing import Dict, List, Tuple, Optional

class MedicalVocabularyPostProcessor:
    """
    Comprehensive Medical Lexicon, Symbol & Numerical Pattern Normalizer:
    - Normalizes dosages (e.g. '500 mq' -> '500 mg', 'S00 mg' -> '500 mg', 'O.5 ml' -> '0.5 ml')
    - Standardizes dosing schedules ('l-0-l' -> '1-0-1', '1+2x3', '1 tab x2', 'BID', 'TID')
    - Corrects duration notations ('S days' -> '5 days', '1 marth' -> '1 month')
    - Normalizes formulations ('1ab' -> 'Tab.', 'Tob.' -> 'Tab.', 'Colcap' -> 'Cap.', 'vati' -> 'Vati')
    - Cleans phone numbers, registration numbers, dates, patient demographics (Age, Sex, Timing)
    - Validates clinical vitals: BP (e.g. 'l20/80' -> '120/80'), SPO2, Pulse, Temp
    - Recognizes common clinical terminology, diagnoses, and pharmaceutical formulary
    """

    KNOWN_MEDICINES = [
        # Antibiotics & Antimicrobials
        "Amoxicillin", "Augmentin", "Azithromycin", "Ciprofloxacin", "Cefixime",
        "Ceftriaxone", "Doxycycline", "Metronidazole", "Clindamycin", "Levofloxacin",
        "Ampicillin", "Gentamicin", "Ofloxacin", "Clarithromycin", "Cefpodoxime",
        # Analgesics, Antipyretics & Anti-inflammatory
        "Paracetamol", "Acetaminophen", "Ibuprofen", "Diclofenac", "Aceclofenac",
        "Tramadol", "Dolo 650", "Combiflam", "Aspirin", "Naproxen", "Mefenamic Acid",
        "Piroxicam", "Ketorolac", "Indomethacin", "Etoricoxib",
        # Gastrointestinal & Antacids
        "Omeprazole", "Pantoprazole", "Rabeprazole", "Ranitidine", "Famotidine",
        "Domperidone", "Ondansetron", "Pan-D", "Pantocid", "Sucralfate",
        "Esomeprazole", "Lansoprazole", "Metoclopramide", "Gerd-Off",
        # Cardiovascular, Antihypertensive & Diabetic
        "Metformin", "Glimepiride", "Atorvastatin", "Rosuvastatin", "Amlodipine",
        "Telmisartan", "Losartan", "Hydrochlorothiazide", "Atenolol", "Enalapril",
        "Ramipril", "Gliclazide", "Vildagliptin", "Sitagliptin", "Dapagliflozin",
        # Respiratory & Antiallergic
        "Cetirizine", "Levocetirizine", "Montelukast", "Fexofenadine", "Salbutamol",
        "Budesonide", "Ambroxol", "Chlorpheniramine", "Deriphyllin", "Asthalin",
        # Vitamins, Minerals & Supplements
        "Shelcal", "Becosules", "Neurobion", "Calcium D3", "Vitamin C", "Zincovit",
        "Folvite", "Folic Acid", "Cobalamin", "Iron Folic",
        # Common Ayurvedic / Herbal / Formulations
        "Kanchanar Guggulu", "Chandraprabha Vati", "Sigru", "Styplon", "Cruel",
        "Ashwagandha", "Brahmi", "Triphala", "Liv-52", "Shatavari", "Trikatu",
        "Septilin", "Cystone", "Rumalaya", "Geriforte", "Tentex", "Abana"
    ]

    CLINICAL_TERMS = [
        "Consultant", "Physician", "Surgeon", "General Surgery", "Ayurvedic",
        "Pediatrics", "Cardiology", "Neurology", "Orthopedics", "Dermatology",
        "Gynecology", "Ophthalmology", "Registration", "Patient", "Timing",
        "Hypertension", "Diabetes", "Thyroid Problem", "Psoriasis", "Leucoderma",
        "Joint Pain", "Kidney Dysfunction", "Infertility", "Menstrual Problem",
        "Sexual Problem", "Liver Disorders", "Constipation", "Hyper Acidity",
        "Piles", "Rhinitis", "Asthma", "Allergy", "Bladder", "Haematuria",
        "Appointment", "Hospital", "Clinic", "Healthcare", "Pathology",
        "Diagnosis", "Progress Note", "Clinical Notes", "Impression", "Prescription",
        "Advice", "Investigation", "Examination", "Complaints", "Discharge"
    ]

    UNITS = [
        # Medication Units
        "mg", "mcg", "g", "gm", "ml", "iu", "IU", "tab", "tabs", "tablet", "tablets",
        "cap", "caps", "capsule", "capsules", "drop", "drops", "puff", "puffs",
        "sachet", "sachets", "tsp", "tbsp", "ampoule", "vial",
        # Diagnostic & Clinical Laboratory Units
        "mmHg", "bpm", "/min", "F", "C", "%", "mg/dL", "g/dL", "K/uL", "mEq/L",
        "U/L", "ng/mL", "pg/mL", "mmol/L", "mm/hr", "/cu.mm", "cells/cu.mm"
    ]

    MEDICAL_ABBREVIATIONS = {
        "Rx": "Prescription / Recipe",
        "Dx": "Diagnosis",
        "Hx": "History",
        "Sx": "Symptoms",
        "CC": "Chief Complaint",
        "HPI": "History of Present Illness",
        "PE": "Physical Examination",
        "O/E": "On Examination",
        "C/O": "Complaining Of",
        "K/C/O": "Known Case Of",
        "Adv": "Advice",
        "Inv": "Investigations",
        "BP": "Blood Pressure",
        "PR": "Pulse Rate",
        "HR": "Heart Rate",
        "RR": "Respiratory Rate",
        "Temp": "Temperature",
        "SpO2": "Oxygen Saturation",
        "SPO2": "Oxygen Saturation",
        "CBC": "Complete Blood Count",
        "WBC": "White Blood Cell Count",
        "RBC": "Red Blood Cell Count",
        "Hb": "Hemoglobin",
        "PLT": "Platelet Count",
        "ESR": "Erythrocyte Sedimentation Rate",
        "CRP": "C-Reactive Protein",
        "LFT": "Liver Function Test",
        "SGOT": "Serum Glutamic Oxaloacetic Transaminase",
        "SGPT": "Serum Glutamic Pyruvic Transaminase",
        "KFT": "Kidney Function Test",
        "RFT": "Renal Function Test",
        "BUN": "Blood Urea Nitrogen",
        "Cr": "Serum Creatinine",
        "FBS": "Fasting Blood Sugar",
        "PPBS": "Post Prandial Blood Sugar",
        "HbA1c": "Glycated Hemoglobin",
        "CXR": "Chest X-Ray",
        "ECG": "Electrocardiogram",
        "USG": "Ultrasonography",
        "CT": "Computed Tomography",
        "MRI": "Magnetic Resonance Imaging",
        "ECHO": "Echocardiogram",
        "OD": "Once Daily",
        "BD": "Twice Daily",
        "BID": "Twice Daily",
        "TID": "Three Times Daily",
        "TDS": "Three Times Daily",
        "QID": "Four Times Daily",
        "SOS": "As Needed (Si Opus Sit)",
        "PRN": "As Needed (Pro Re Nata)",
        "STAT": "Immediately",
        "HS": "At Bedtime (Hora Somni)",
        "AC": "Before Meals (Ante Cibum)",
        "PC": "After Meals (Post Cibum)",
        "NPO": "Nothing by Mouth"
    }

    def __init__(self):
        self.medicine_lookup = {m.lower(): m for m in self.KNOWN_MEDICINES}
        self.clinical_lookup = {t.lower(): t for t in self.CLINICAL_TERMS}

    def clean_text(self, text: str) -> str:
        if not text:
            return ""

        # 1. Normalize unicode characters & noisy symbols
        cleaned = re.sub(r'[\r\t]+', ' ', text)
        cleaned = cleaned.replace('\u53e3', '[ ]').replace('\u25a1', '[ ]')  # Checkbox glyphs
        cleaned = cleaned.replace('\u2013', '-').replace('\u2014', '-').replace('\u2212', '-')
        cleaned = cleaned.replace('\u2022', '*').replace('\u25cf', '*')      # Bullets
        cleaned = cleaned.replace('①', '1)').replace('②', '2)').replace('③', '3)').replace('④', '4)').replace('⑤', '5)')
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        # 2. Fix OCR digit-letter confusions in phone numbers (e.g. 'Ph.: 987IO33775' -> '9871033775')
        def fix_phone(match):
            prefix = match.group(1) or ""
            raw_digits = match.group(2)
            fixed_digits = raw_digits.replace('O', '0').replace('o', '0').replace('I', '1').replace('l', '1').replace('S', '5').replace('s', '5')
            return f"{prefix}{fixed_digits}"

        cleaned = re.sub(r'(Ph\.?\s*:?\s*|\b)([89]\d[0-9IOlSs]{8})\b', fix_phone, cleaned)

        # 3. Fix OCR digit-letter confusions in dates (e.g. '13/O6/2OO' -> '13/06/200')
        def fix_date(match):
            raw = match.group(0)
            return raw.replace('O', '0').replace('o', '0').replace('I', '1').replace('l', '1')

        cleaned = re.sub(r'\b\d{1,2}[/-][0-9OolI]{1,2}[/-][0-9OolI]{2,4}\b', fix_date, cleaned)

        # 4. Standardize Patient Vitals
        # Blood Pressure (BP): e.g. 'BP: l20/80' -> 'BP: 120/80'
        def fix_bp(match):
            p1 = match.group(1).replace('l', '1').replace('I', '1').replace('O', '0').replace('o', '0')
            p2 = match.group(2).replace('l', '1').replace('I', '1').replace('O', '0').replace('o', '0')
            return f"BP: {p1}/{p2}"

        cleaned = re.sub(r'\bBP\s*:?\s*([0-9lIOo]{2,3})\s*/\s*([0-9lIOo]{2,3})\b', fix_bp, cleaned, flags=re.IGNORECASE)

        # SPO2: e.g. 'SPO2: 98%'
        cleaned = re.sub(r'\bSP[O0]2\s*:?\s*([0-9]{2,3})\s*%?\b', r'SPO2: \1%', cleaned, flags=re.IGNORECASE)

        # 5. Fix dosage unit typos & numbers (mq, ng, rnq, m9 -> mg)
        cleaned = re.sub(r'(\d+|[Ss]00|[Zz]50)\s*(?:mq|ng|rnq|rny|m9)\b', r'\1 mg', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'(\d+)\s*(?:m1|mI|rnL|rnl)\b', r'\1 ml', cleaned)
        cleaned = re.sub(r'(\d+)\s*(mg|ml|mcg|gm|g|IU)\b', r'\1 \2', cleaned, flags=re.IGNORECASE)

        # Decimal numbers (e.g., 'O.5' -> '0.5', '1.S' -> '1.5')
        cleaned = re.sub(r'\b[oO]\.(\d+)\b', r'0.\1', cleaned)
        cleaned = re.sub(r'\b(\d+)\.[Ss]\b', r'\1.5', cleaned)

        # Standardize 500 / 250 / 650 mg dosages
        cleaned = re.sub(r'\b[Ss]00\s*(mg|ml|g)\b', r'500 \1', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\b[Zz]50\s*(mg|ml|g)\b', r'250 \1', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\b6[Ss]0\s*(mg|ml|g)\b', r'650 \1', cleaned, flags=re.IGNORECASE)

        # 6. Standardize dosage frequency schedules (e.g. 'l-0-l' -> '1-0-1', '1+2x3', '1 tab x2')
        def fix_frequency(match):
            raw = match.group(0)
            fixed = raw.replace('l', '1').replace('I', '1').replace('|', '1').replace('o', '0').replace('O', '0')
            digits = re.findall(r'[012]', fixed)
            if len(digits) in (2, 3, 4):
                return "-".join(digits)
            return raw

        cleaned = re.sub(r'\b[012lIoO|]\s*[-–—/]\s*[012lIoO|]\s*[-–—/]\s*[012lIoO|]\b', fix_frequency, cleaned)
        cleaned = re.sub(r'\b[012lIoO|]\s*[-–—/]\s*[012lIoO|]\b', fix_frequency, cleaned)

        # Multiplier expressions e.g. '1 tab x2', '1 Cap x2 with milk'
        cleaned = re.sub(r'\b(\d+)\s*(tab|cap|pill|capsule)\s*[xX]\s*(\d+)\b', r'\1 \2 x\3', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\b[xX]\s*(\d+)\b', r'x\1', cleaned)

        # Standardize Latin frequency terms
        cleaned = re.sub(r'\b[bB][\.\s]*[iI][\.\s]*[dD]\b', 'BID', cleaned)
        cleaned = re.sub(r'\b[tT][\.\s]*[iI][\.\s]*[dD]\b', 'TID', cleaned)
        cleaned = re.sub(r'\b[qQ][\.\s]*[iI][\.\s]*[dD]\b', 'QID', cleaned)
        cleaned = re.sub(r'\b[oO][\.\s]*[dD]\b', 'OD', cleaned)
        cleaned = re.sub(r'\b[sS][\.\s]*[oO][\.\s]*[sS]\b', 'SOS', cleaned)
        cleaned = re.sub(r'\b[hH][\.\s]*[sS]\b', 'HS', cleaned)

        # 7. Fix duration notations ('S days' -> '5 days', '1 marth' -> '1 month')
        cleaned = re.sub(r'\b[Ss]\s*(?:days|day|clays|cloys)\b', '5 days', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'(\d+)\s*(?:clays|cloys|dasy|daps)\b', r'\1 days', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'(\d+)\s*(?:wks|weks|wek)\b', r'\1 weeks', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'(\d+)\s*(?:marth|morth|mth|mths)\b', r'\1 month', cleaned, flags=re.IGNORECASE)

        # 8. Normalize formulation prefixes
        cleaned = re.sub(r'\b(?:1ab|Tob|Tah|Tabl|Tsb)\.?\s*', 'Tab. ', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\b(?:C@p|Cap|Csap|Colcap)\.?\s*', 'Cap. ', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\b(?:Syp|Syr|Surp)\.?\s*', 'Syp. ', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\b(?:1nj|Inj|Injl)\.?\s*', 'Inj. ', cleaned, flags=re.IGNORECASE)

        # 9. Medical vocabulary matching & clinical term normalization
        words = cleaned.split()
        normalized_words = []
        for w in words:
            clean_w = re.sub(r'[^\w]', '', w).lower()
            matched = self._match_term(clean_w)
            if matched:
                prefix = re.match(r'^[^\w]*', w).group(0)
                suffix = re.search(r'[^\w]*$', w).group(0)
                normalized_words.append(f"{prefix}{matched}{suffix}")
            else:
                normalized_words.append(w)

        return " ".join(normalized_words)

    def _match_term(self, word: str) -> Optional[str]:
        if len(word) < 5:
            return None

        # Check exact matches
        if word in self.medicine_lookup:
            return self.medicine_lookup[word]
        if word in self.clinical_lookup:
            return self.clinical_lookup[word]

        # Fuzzy matching against medicine vocabulary
        for med_lower, med_orig in self.medicine_lookup.items():
            if abs(len(word) - len(med_lower)) <= 2:
                dist = self._levenshtein(word, med_lower)
                max_allowable = 1 if len(med_lower) <= 7 else 2
                if dist <= max_allowable:
                    return med_orig

        # Fuzzy matching against clinical terms
        for term_lower, term_orig in self.clinical_lookup.items():
            if abs(len(word) - len(term_lower)) <= 2:
                dist = self._levenshtein(word, term_lower)
                max_allowable = 1 if len(term_lower) <= 7 else 2
                if dist <= max_allowable:
                    return term_orig

        return None

    @staticmethod
    def _levenshtein(s1: str, s2: str) -> int:
        if len(s1) < len(s2):
            return MedicalVocabularyPostProcessor._levenshtein(s2, s1)
        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]

    def extract_medical_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Parses OCR text and extracts structured medical entities:
        - drugs
        - dosages
        - frequencies
        - units
        - abbreviations
        """
        if not text:
            return {
                "drugs": [],
                "dosages": [],
                "frequencies": [],
                "units": [],
                "abbreviations": []
            }

        extracted_drugs = []
        extracted_dosages = []
        extracted_frequencies = []
        extracted_units = []
        extracted_abbrs = []

        # 1. Extract drugs
        lower_text = text.lower()
        for med in self.KNOWN_MEDICINES:
            pattern = r'\b' + re.escape(med.lower()) + r'\b'
            if re.search(pattern, lower_text):
                if med not in extracted_drugs:
                    extracted_drugs.append(med)

        # 2. Extract dosages (e.g. '500 mg', '625mg', '10 ml', '0.5 ml', '200 mcg', '5000 IU', '1 puff')
        dosage_matches = re.findall(
            r'\b(?:\d+(?:\.\d+)?|\d+/\d+)\s*(?:mg|mcg|g|gm|ml|iu|IU|puffs?|drops?|sachets?|tsp|tbsp)\b',
            text,
            flags=re.IGNORECASE
        )
        for d in dosage_matches:
            d_norm = d.strip()
            if d_norm not in extracted_dosages:
                extracted_dosages.append(d_norm)

        # 3. Extract frequencies (e.g. '1-0-1', '1-1-1', '0-0-1', 'BID', 'TID', 'QID', 'OD', 'SOS', 'HS', '1 tab x2')
        freq_matches = re.findall(
            r'\b(?:[012]\s*[-–—]\s*[012]\s*[-–—]\s*[012](?:\s*[-–—]\s*[012])?|BID|TID|TDS|QID|OD|SOS|PRN|STAT|HS|AC|PC|\d+\s*(?:tab|cap|tabs|caps)\s*[xX]\s*\d+)\b',
            text,
            flags=re.IGNORECASE
        )
        for f in freq_matches:
            f_norm = f.strip().upper()
            if f_norm not in extracted_frequencies:
                extracted_frequencies.append(f_norm)

        # 4. Extract units
        unit_pattern = r'\b(' + '|'.join(re.escape(u) for u in self.UNITS) + r')\b'
        unit_matches = re.findall(unit_pattern, text, flags=re.IGNORECASE)
        for u in unit_matches:
            u_clean = u.strip()
            if u_clean.lower() not in [x.lower() for x in extracted_units]:
                extracted_units.append(u_clean)

        # 5. Extract abbreviations
        for abbr in self.MEDICAL_ABBREVIATIONS.keys():
            # Match word boundary, case-sensitive for short 2-char tokens, or case-insensitive for clear acronyms
            pattern = r'\b' + re.escape(abbr) + r'\b'
            if re.search(pattern, text):
                if abbr not in extracted_abbrs:
                    extracted_abbrs.append(abbr)

        return {
            "drugs": extracted_drugs,
            "dosages": extracted_dosages,
            "frequencies": extracted_frequencies,
            "units": extracted_units,
            "abbreviations": extracted_abbrs
        }
