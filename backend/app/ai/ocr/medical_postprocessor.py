import re
from typing import Dict, List, Tuple, Optional

class MedicalVocabularyPostProcessor:
    """
    Domain-Specific Medical Lexicon & Pattern Normalizer.
    Specialized for clinical prescriptions and handwritten notes:
    - Normalizes dosages (e.g. '500 mq' -> '500 mg', 'S00 mg' -> '500 mg')
    - Standardizes dosing frequencies ('l-0-l' -> '1-0-1', 'b.i.d' -> 'BID')
    - Corrects durations ('S days' -> '5 days', '5 cloys' -> '5 days')
    - Normalizes formulations ('1ab' -> 'Tab.', 'Tob.' -> 'Tab.')
    - Validates common pharmaceutical names using Levenshtein distance against known formulary.
    """

    # Common pharmaceutical lexicon
    KNOWN_MEDICINES = [
        "Amoxicillin", "Augmentin", "Paracetamol", "Acetaminophen", "Azithromycin",
        "Ciprofloxacin", "Cefixime", "Ceftriaxone", "Metformin", "Glimepiride",
        "Atorvastatin", "Rosuvastatin", "Amlodipine", "Telmisartan", "Losartan",
        "Omeprazole", "Pantoprazole", "Rabeprazole", "Ranitidine", "Ibuprofen",
        "Diclofenac", "Aceclofenac", "Tramadol", "Cetirizine", "Levocetirizine",
        "Montelukast", "Dolo 650", "Combiflam", "Pan-D", "Pantocid", "Shelcal",
        "Becosules", "Neurobion", "Clavulanic Acid", "Doxycycline", "Metronidazole"
    ]

    # Common dosage units
    UNITS = ["mg", "mcg", "g", "ml", "iu", "IU", "gm", "tablet", "tablets", "cap", "capsule", "pills"]

    def __init__(self):
        self.medicine_lookup = {m.lower(): m for m in self.KNOWN_MEDICINES}

    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        
        # 1. Normalize whitespace & strip noisy symbols
        cleaned = re.sub(r'[\r\t]+', ' ', text)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        # 2. Fix dosage unit typos first (mq, ng, rnq, m9 -> mg)
        cleaned = re.sub(r'(\d+|[Ss]00|[Zz]50)\s*(?:mq|ng|rnq|rny|m9)\b', r'\1 mg', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'(\d+)\s*(?:m1|mI|rnL|rnl)\b', r'\1 ml', cleaned)
        cleaned = re.sub(r'(\d+)\s*(mg|ml|mcg|gm|g)\b', r'\1 \2', cleaned, flags=re.IGNORECASE)

        # 3. Fix OCR digit-letter confusions in dosage patterns (e.g., 'S00 mg' -> '500 mg')
        cleaned = re.sub(r'\b[Ss]00\s*(mg|ml|g)\b', r'500 \1', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\b[Zz]50\s*(mg|ml|g)\b', r'250 \1', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\b[oO]0\s*(mg|ml|g)\b', r'50 \1', cleaned, flags=re.IGNORECASE)

        # 4. Standardize dosage frequency schedules (e.g., 'l-0-l' -> '1-0-1', '1 - 0 - 1' -> '1-0-1')
        def fix_frequency(match):
            raw = match.group(0)
            fixed = raw.replace('l', '1').replace('I', '1').replace('|', '1').replace('o', '0').replace('O', '0')
            digits = re.findall(r'[012]', fixed)
            if len(digits) in (2, 3, 4):
                return "-".join(digits)
            return raw

        cleaned = re.sub(r'\b[012lIoO|]\s*[-–—/]\s*[012lIoO|]\s*[-–—/]\s*[012lIoO|]\b', fix_frequency, cleaned)
        cleaned = re.sub(r'\b[012lIoO|]\s*[-–—/]\s*[012lIoO|]\b', fix_frequency, cleaned)

        # Standardize Latin frequency terms
        cleaned = re.sub(r'\b[bB][\.\s]*[iI][\.\s]*[dD]\b', 'BID', cleaned)
        cleaned = re.sub(r'\b[tT][\.\s]*[iI][\.\s]*[dD]\b', 'TID', cleaned)
        cleaned = re.sub(r'\b[qQ][\.\s]*[iI][\.\s]*[dD]\b', 'QID', cleaned)
        cleaned = re.sub(r'\b[oO][\.\s]*[dD]\b', 'OD', cleaned)
        cleaned = re.sub(r'\b[sS][\.\s]*[oO][\.\s]*[sS]\b', 'SOS', cleaned)
        cleaned = re.sub(r'\b[hH][\.\s]*[sS]\b', 'HS', cleaned)

        # 5. Fix duration notations (e.g., 'S days' -> '5 days', '5 cloys' -> '5 days')
        cleaned = re.sub(r'\b[Ss]\s*(?:days|day|clays|cloys|days)\b', '5 days', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'(\d+)\s*(?:clays|cloys|dasy|daps)\b', r'\1 days', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'(\d+)\s*(?:wks|weks|wek)\b', r'\1 weeks', cleaned, flags=re.IGNORECASE)

        # 6. Normalize formulation prefixes
        cleaned = re.sub(r'\b(?:1ab|Tob|Tah|Tabl|Tsb)\.?\s*', 'Tab. ', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\b(?:C@p|Cap|Csap)\.?\s*', 'Cap. ', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\b(?:Syp|Syr|Surp)\.?\s*', 'Syp. ', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\b(?:1nj|Inj|Injl)\.?\s*', 'Inj. ', cleaned, flags=re.IGNORECASE)

        # 7. Check for known medicine matching using fuzzy similarity
        words = cleaned.split()
        normalized_words = []
        for w in words:
            clean_w = re.sub(r'[^\w]', '', w).lower()
            best_match = self._match_medicine(clean_w)
            if best_match:
                # Retain punctuation if any
                prefix = re.match(r'^[^\w]*', w).group(0)
                suffix = re.search(r'[^\w]*$', w).group(0)
                normalized_words.append(f"{prefix}{best_match}{suffix}")
            else:
                normalized_words.append(w)

        return " ".join(normalized_words)

    def _match_medicine(self, word: str) -> Optional[str]:
        if len(word) < 5:
            return None
        
        # Exact case-insensitive match
        if word in self.medicine_lookup:
            return self.medicine_lookup[word]

        # Levenshtein distance check for common OCR misspellings
        for med_lower, med_orig in self.medicine_lookup.items():
            if abs(len(word) - len(med_lower)) <= 2:
                dist = self._levenshtein(word, med_lower)
                # Allow distance of 1 for 5-7 chars, distance of 2 for 8+ chars
                max_allowable = 1 if len(med_lower) <= 7 else 2
                if dist <= max_allowable:
                    return med_orig
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
