# OCR Document Reading System — Verification & Test Plan

> **Version:** 2.0.0 | **Focus:** Accuracy, Resolution Preservation & Non-Regression

---

## 1. Overview & Test Strategy

This document establishes the formal verification methodology for the **OCR Document Reading System**. The testing strategy guarantees that:
1. **Resolution Preservation**: No document is degraded by downscaling or destructive binarization.
2. **Line Coherence**: Adjacent detection fragments are correctly merged into unified line crops before recognition.
3. **Hybrid Engine Accuracy**: RapidOCR and TrOCR are routed accurately with CER $< 5\%$ on printed documents.
4. **Spatial Fidelity**: Overlay bounding boxes align with physical pixels without visual drift across viewport sizes.

---

## 2. Test Classification Matrix

| Level | Component | Focus | Primary Tools |
| :--- | :--- | :--- | :--- |
| **Unit Tests** | Preprocessing & Normalization | Dual-path filtering, no destructive thresholding on digital screen captures | PyTest, OpenCV |
| **Unit Tests** | Spatial Line Grouping | Vertical overlap ($\ge 0.45$) and horizontal gap bounding | NumPy, PyTest |
| **Integration Tests** | Hybrid OCR Engine & Controller | Full multi-page PDF rendering, TrOCR fallback, 2D rebuilder | FastAPI TestClient, Requests |
| **Acceptance Suite** | 4 Canonical Documents | Ground-truth CER, WER, latency, and confidence validation | `scripts/run_acceptance_tests.py` |
| **Frontend Tests** | Studio UI & Canvas | Normalized SVG overlay, marquee crosshair, clipboard copy | React Testing Library, Vite |

---

## 3. The 4 Acceptance Benchmarks

The automated acceptance test suite executes on every major pipeline revision:

### Test 1: Digital Document / Resume PDF (`DevMehta_Groww_IT.pdf`)
- **Category**: Digital / Screen Vector Document
- **Input Dimensions**: $1191 \times 1684\text{px}$ (Page 1)
- **Validation Criteria**:
  - Detection confidence $\ge 85\%$ (Current: **89.3%**).
  - Complete line coherence: "Dev Mehta", "Software Engineering", "Education", "Skills".
  - Absence of micro-fragmentation artifacts (e.g. `Doy ela`).
  - Total coherent line blocks: 60–75 lines.

### Test 2: Printed Medical Report (`mvd_medical_report.jpg`)
- **Category**: Physical Scanned Form
- **Validation Criteria**:
  - 100% of lines classified as printed (RapidOCR).
  - Confidence $\ge 80\%$ (Current: **82.8%**).
  - Correct extraction of legal headers: "MEDICAL REPORT", "DRIVER LICENSE".

### Test 3: Prescription Form (`prescription.png`)
- **Category**: Mixed Form & Clinical Handwriting
- **Validation Criteria**:
  - RapidOCR printed headers + TrOCR clinical notes.
  - Confidence $\ge 80\%$ (Current: **84.7%**).
  - Preservation of numerical dosages and medication instructions.

### Test 4: Digital Screen Snippet Crop (UI Action Buttons)
- **Category**: Marquee Screen Capture / Small Font (12–18px)
- **Validation Criteria**:
  - 2.5× multi-scale bicubic upscaling applied.
  - Complete button labels recognized: "Submit another application", "Cookie Preferences", "Allow all analytics cookies", "Decline Optional".
  - Total execution latency $< 1.0\text{s}$ (Current: **0.50s**).

---

## 4. Quantitative Metrics & Thresholds

### Character Error Rate (CER)
$$\text{CER} = \frac{S + D + I}{N}$$
Where $S$ is substitutions, $D$ is deletions, $I$ is insertions, and $N$ is total ground-truth characters.
- **Printed text target**: $\text{CER} \le 3.0\%$
- **Handwritten text target**: $\text{CER} \le 12.0\%$

### Word Error Rate (WER)
$$\text{WER} = \frac{S_w + D_w + I_w}{N_w}$$
- **Printed text target**: $\text{WER} \le 5.0\%$
- **Handwritten text target**: $\text{WER} \le 18.0\%$

---

## 5. Execution Commands

### Running the Full Acceptance Suite:
```bash
python scripts/run_acceptance_tests.py
```

### Running Specific Regression Benchmarks:
```bash
python scripts/benchmark_prescriptions.py
```

### Running Backend Unit & Route Tests:
```bash
pytest tests/ -v
```

### Running Frontend Build & Typechecks:
```bash
cd frontend
npm run build
```
