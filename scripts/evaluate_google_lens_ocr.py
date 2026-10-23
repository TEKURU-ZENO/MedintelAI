import os
import sys
import time
import json
import cv2
import numpy as np

# Ensure utf-8 output encoding on Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.ocr.lens_engine import (
    GoogleLensOCREngine,
    ScreenCoordinateMapper,
    ScreenCaptureOptimizer,
    HISScreenOptimizer,
    BrowserWindowOptimizer,
    PDFViewerOptimizer,
    SnippetOCREngine,
    LineLevelBlockProducer,
)
from app.ai.pipeline.pipeline_controller import PipelineController

def create_synthetic_screen_capture() -> np.ndarray:
    """Creates a synthetic 1280x720 screen capture with digital antialiased UI text."""
    canvas = np.ones((720, 1280, 3), dtype=np.uint8) * 248  # Light gray UI background
    
    # Title bar
    cv2.rectangle(canvas, (0, 0), (1280, 48), (235, 235, 235), -1)
    cv2.putText(canvas, "MedIntel Clinical Workstation v2.4", (20, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (40, 40, 40), 2)
    
    # Content cards
    cv2.rectangle(canvas, (40, 70), (600, 350), (255, 255, 255), -1)
    cv2.rectangle(canvas, (40, 70), (600, 350), (220, 220, 220), 1)
    cv2.putText(canvas, "Encounter Overview", (60, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (20, 20, 20), 2)
    cv2.putText(canvas, "Chief Complaint: Severe Acute Migraine", (60, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (50, 50, 50), 2)
    cv2.putText(canvas, "Onset: 3 days prior with nausea and photophobia", (60, 205), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 50, 50), 2)
    cv2.putText(canvas, "Current Status: Stable under observation", (60, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 50, 50), 2)
    cv2.putText(canvas, "Attending Physician: Dr. Sarah Jenkins MD", (60, 295), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 50, 50), 2)
    
    # Action buttons
    cv2.rectangle(canvas, (650, 70), (1240, 350), (255, 255, 255), -1)
    cv2.rectangle(canvas, (650, 70), (1240, 350), (220, 220, 220), 1)
    cv2.putText(canvas, "Prescribed Medications", (670, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (20, 20, 20), 2)
    cv2.putText(canvas, "1. Sumatriptan 50mg Oral Tablet PRN", (670, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (30, 30, 30), 2)
    cv2.putText(canvas, "2. Ondansetron 4mg ODT Q8H PRN", (670, 205), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (30, 30, 30), 2)
    cv2.putText(canvas, "3. Acetaminophen 500mg Oral Capsule Q6H", (670, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (30, 30, 30), 2)
    cv2.putText(canvas, "Pharmacy Dispense Status: Verified and Active", (670, 295), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 120, 40), 2)

    return canvas

def create_synthetic_his_screenshot() -> np.ndarray:
    """Creates a synthetic Hospital Information System (EHR) chart screenshot."""
    canvas = np.ones((600, 1000, 3), dtype=np.uint8) * 255
    
    # Dark blue inverted patient banner (typical of Epic/Cerner)
    cv2.rectangle(canvas, (0, 0), (1000, 70), (80, 40, 20), -1)  # Dark navy BGR
    cv2.putText(canvas, "PATIENT: DOE, JANE | MRN: 94820194 | DOB: 04/12/1982 | BED: 402-B", (25, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.68, (255, 255, 255), 2)

    # EHR Tabular Grid with grid lines
    y_start = 110
    headers = ["VITAL SIGN", "RECORDED VALUE", "NORMAL RANGE", "FLAG"]
    col_x = [30, 250, 500, 750, 970]
    
    # Header bar
    cv2.rectangle(canvas, (col_x[0], y_start), (col_x[-1], y_start + 35), (230, 235, 240), -1)
    for i in range(len(headers)):
        cv2.putText(canvas, headers[i], (col_x[i] + 10, y_start + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (30, 30, 30), 2)

    rows = [
        ("BP: 120/80", "120/80 mmHg", "90/60 - 120/80", "NORMAL"),
        ("HR: 72 bpm", "72 bpm", "60 - 100 bpm", "NORMAL"),
        ("RR: 16", "16 breaths/min", "12 - 20", "NORMAL"),
        ("TEMP: 98.6 F", "98.6 F", "97.8 - 99.1 F", "NORMAL"),
        ("SPO2: 99%", "99% on room air", "95 - 100%", "NORMAL")
    ]

    for r_idx, row in enumerate(rows):
        y = y_start + 35 + (r_idx * 40)
        cv2.rectangle(canvas, (col_x[0], y), (col_x[-1], y + 40), (255, 255, 255) if r_idx % 2 == 0 else (245, 248, 250), -1)
        for c_idx, val in enumerate(row):
            cv2.putText(canvas, val, (col_x[c_idx] + 10, y + 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (20, 20, 20), 1)

    # Draw thin EHR table grid lines
    for i in range(len(rows) + 2):
        y = y_start + (i * 40 if i > 0 else 0)
        cv2.line(canvas, (col_x[0], y), (col_x[-1], y), (200, 205, 210), 1)
    for x in col_x:
        cv2.line(canvas, (x, y_start), (x, y_start + 35 + (len(rows) * 40)), (200, 205, 210), 1)

    # Clinical order footer
    cv2.putText(canvas, "Active Rx: Metformin 500mg PO BID | Lisinopril 10mg QD", (30, 520), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (30, 30, 30), 2)
    return canvas

def create_synthetic_browser_window() -> np.ndarray:
    """Creates a synthetic web browser capture with URL bar and responsive layout."""
    canvas = np.ones((600, 1000, 3), dtype=np.uint8) * 255
    
    # Browser chrome (tabs & URL address bar)
    cv2.rectangle(canvas, (0, 0), (1000, 75), (238, 240, 244), -1)
    cv2.rectangle(canvas, (120, 35), (850, 68), (255, 255, 255), -1)
    cv2.rectangle(canvas, (120, 35), (850, 68), (210, 215, 220), 1)
    cv2.putText(canvas, "https://medintel.health/patients/4920/chart", (135, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (50, 50, 50), 1)

    # Web Page Content
    cv2.putText(canvas, "Home / Patients / Cardiology / Patient 4920", (40, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (100, 100, 100), 1)
    cv2.putText(canvas, "Cardiology Consultation Summary", (40, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (10, 10, 10), 2)
    cv2.putText(canvas, "Patient presents for routine follow-up of hypertension and hyperlipidemia.", (40, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (40, 40, 40), 1)
    cv2.putText(canvas, "Electrocardiogram demonstrates normal sinus rhythm at 68 bpm.", (40, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (40, 40, 40), 1)
    cv2.putText(canvas, "Echocardiogram reveals preserved left ventricular ejection fraction of 60%.", (40, 290), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (40, 40, 40), 1)
    cv2.putText(canvas, "Plan: Continue Atorvastatin 20mg daily. Repeat lipid panel in 6 months.", (40, 335), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (20, 20, 20), 2)

    return canvas

def create_synthetic_pdf_viewer() -> np.ndarray:
    """Creates a synthetic PDF viewer screenshot (dark gray background with centered white page)."""
    canvas = np.ones((700, 1000, 3), dtype=np.uint8)
    canvas[:, :] = (82, 86, 89)  # Chrome PDF viewer background #525659

    # Viewer toolbar
    cv2.rectangle(canvas, (0, 0), (1000, 45), (50, 54, 57), -1)
    cv2.putText(canvas, "medical_discharge_summary.pdf - Page 1 of 3", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (220, 220, 220), 1)

    # Centered Document Page with drop shadow
    page_x1, page_y1, page_x2, page_y2 = 200, 65, 800, 670
    cv2.rectangle(canvas, (page_x1 + 4, page_y1 + 4), (page_x2 + 4, page_y2 + 4), (40, 40, 40), -1)  # Shadow
    cv2.rectangle(canvas, (page_x1, page_y1), (page_x2, page_y2), (255, 255, 255), -1)  # White Page

    # Page Content
    cv2.putText(canvas, "METROPOLITAN GENERAL HOSPITAL", (page_x1 + 40, page_y1 + 55), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (20, 20, 20), 2)
    cv2.putText(canvas, "INPATIENT DISCHARGE SUMMARY", (page_x1 + 40, page_y1 + 95), cv2.FONT_HERSHEY_SIMPLEX, 0.68, (20, 20, 20), 2)
    cv2.putText(canvas, "Admission Date: 2026-10-14  |  Discharge Date: 2026-10-22", (page_x1 + 40, page_y1 + 140), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (50, 50, 50), 1)
    cv2.putText(canvas, "Discharge Diagnosis: Community Acquired Pneumonia", (page_x1 + 40, page_y1 + 185), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (20, 20, 20), 2)
    cv2.putText(canvas, "Hospital Course: Treated with IV Ceftriaxone and Azithromycin.", (page_x1 + 40, page_y1 + 230), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (40, 40, 40), 1)
    cv2.putText(canvas, "Patient afebrile for 48 hours with improved oxygenation.", (page_x1 + 40, page_y1 + 270), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (40, 40, 40), 1)
    cv2.putText(canvas, "Discharge Medications: Amoxicillin-Clavulanate 875mg BID x 5 days", (page_x1 + 40, page_y1 + 320), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (20, 20, 20), 2)
    cv2.putText(canvas, "Follow-up: Primary care clinic in 10 to 14 days.", (page_x1 + 40, page_y1 + 365), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (40, 40, 40), 1)

    return canvas

def main():
    print("=" * 75)
    print("EVALUATION SUITE: PHASE 7 - GOOGLE-LENS OCR")
    print("=" * 75)
    
    lens_engine = GoogleLensOCREngine()
    results = {}

    # TEST 1: Optimize OCR for Screen Captures
    print("\n--- [Test 1/9] Optimize OCR for Screen Captures ---")
    screen_img = create_synthetic_screen_capture()
    t0 = time.perf_counter()
    screen_res = lens_engine.process_screen_capture(screen_img, screen_origin=(100, 100), screen_scale_factor=1.25, mode="screen")
    t1 = time.perf_counter()
    screen_latency = (t1 - t0) * 1000.0
    
    print(f"Total Blocks Detected: {screen_res['total_blocks']}")
    print(f"Overall Confidence: {screen_res['overall_confidence']:.4f}")
    print(f"Execution Latency: {screen_latency:.1f}ms")
    
    has_encounter = "Encounter Overview" in screen_res['raw_text']
    has_meds = "Sumatriptan" in screen_res['raw_text']
    test1_pass = screen_res['total_blocks'] >= 8 and screen_res['overall_confidence'] >= 0.85 and has_encounter
    print(f"Verification: {'PASS' if test1_pass else 'FAIL'} (Encounter={has_encounter}, Meds={has_meds})")
    results['screen_captures'] = {
        'status': 'PASS' if test1_pass else 'FAIL',
        'blocks': screen_res['total_blocks'],
        'confidence': screen_res['overall_confidence'],
        'latency_ms': screen_latency
    }

    # TEST 2: Optimize OCR for HIS Screenshots
    print("\n--- [Test 2/9] Optimize OCR for HIS Screenshots ---")
    his_img = create_synthetic_his_screenshot()
    his_res = lens_engine.process_screen_capture(his_img, mode="his")
    
    entities = his_res.get('clinical_entities', {})
    print(f"HIS Total Blocks: {his_res['total_blocks']}")
    print(f"HIS Overall Confidence: {his_res['overall_confidence']:.4f}")
    print(f"HIS Clinical Entities Extracted: {entities}")
    
    has_banner = "JANE" in his_res['raw_text'] or "94820194" in his_res['raw_text']
    has_vitals = "120/80" in his_res['raw_text'] or "blood_pressure" in entities
    test2_pass = his_res['total_blocks'] >= 5 and (has_banner or has_vitals)
    print(f"Verification: {'PASS' if test2_pass else 'FAIL'} (Banner Inverted Match={has_banner}, Vitals Match={has_vitals})")
    results['his_screenshots'] = {
        'status': 'PASS' if test2_pass else 'FAIL',
        'blocks': his_res['total_blocks'],
        'confidence': his_res['overall_confidence'],
        'entities': entities
    }

    # TEST 3: Optimize OCR for Browser Windows
    print("\n--- [Test 3/9] Optimize OCR for Browser Windows ---")
    browser_img = create_synthetic_browser_window()
    browser_res = lens_engine.process_screen_capture(browser_img, mode="browser")
    
    has_url = "medintel.health" in browser_res['raw_text']
    has_cardio = "Cardiology" in browser_res['raw_text']
    test3_pass = browser_res['total_blocks'] >= 6 and (has_url or has_cardio)
    print(f"Browser Blocks: {browser_res['total_blocks']}")
    print(f"Browser Confidence: {browser_res['overall_confidence']:.4f}")
    print(f"Verification: {'PASS' if test3_pass else 'FAIL'} (URL Clean Match={has_url}, Cardiology={has_cardio})")
    results['browser_windows'] = {
        'status': 'PASS' if test3_pass else 'FAIL',
        'blocks': browser_res['total_blocks'],
        'confidence': browser_res['overall_confidence'],
        'url_detected': has_url
    }

    # TEST 4: Optimize OCR for PDF Viewers
    print("\n--- [Test 4/9] Optimize OCR for PDF Viewers ---")
    pdf_viewer_img = create_synthetic_pdf_viewer()
    bounds = PDFViewerOptimizer.detect_document_page_bounds(pdf_viewer_img)
    print(f"Detected PDF Page Bounds: {bounds} (Expected: [200, 65, 800, 670])")
    
    pdf_res = lens_engine.process_screen_capture(pdf_viewer_img, mode="pdf_viewer")
    has_hosp = "METROPOLITAN" in pdf_res['raw_text'] or "DISCHARGE" in pdf_res['raw_text']
    bounds_accurate = bounds is not None and abs(bounds[0] - 200) <= 25 and abs(bounds[2] - 800) <= 25
    test4_pass = bounds_accurate and has_hosp
    print(f"Verification: {'PASS' if test4_pass else 'FAIL'} (Bounds Match={bounds_accurate}, Text Match={has_hosp})")
    results['pdf_viewers'] = {
        'status': 'PASS' if test4_pass else 'FAIL',
        'page_bounds': bounds,
        'blocks': pdf_res['total_blocks'],
        'confidence': pdf_res['overall_confidence']
    }

    # TEST 5: Implement Region-Only Inference
    print("\n--- [Test 5/9] Implement Region-Only Inference ---")
    # Select region containing chief complaint from screen capture
    region_bbox = [50, 90, 580, 270]
    reg_res = lens_engine.process_snippet_region(screen_img, region_bbox=region_bbox)
    
    print(f"Region Total Blocks: {reg_res['total_blocks']}")
    print(f"Region Text Extracted:\n{reg_res['raw_text']}")
    print(f"Region Latency: {reg_res['latency_ms']:.1f}ms")
    
    has_region_text = "Migraine" in reg_res['raw_text'] or "Overview" in reg_res['raw_text']
    test5_pass = reg_res['total_blocks'] >= 2 and has_region_text
    print(f"Verification: {'PASS' if test5_pass else 'FAIL'}")
    results['region_only_inference'] = {
        'status': 'PASS' if test5_pass else 'FAIL',
        'blocks': reg_res['total_blocks'],
        'latency_ms': reg_res['latency_ms']
    }

    # TEST 6: Implement Snippet OCR
    print("\n--- [Test 6/9] Implement Snippet OCR ---")
    # Micro-crop of single line dosage
    snippet_crop = screen_img[140:180, 660:1150]
    coord_mapper = ScreenCoordinateMapper(doc_width=1280, doc_height=720)
    snippet_res = lens_engine.snippet_engine.process_snippet(snippet_crop, coord_mapper=coord_mapper, region_offset=(660, 140))
    
    print(f"Snippet Text: '{snippet_res['text']}'")
    print(f"Snippet Confidence: {snippet_res['overall_confidence']:.4f}")
    print(f"Snippet Single Line Fast-Path: {snippet_res['is_single_line']}")
    print(f"Snippet Latency: {snippet_res['latency_ms']:.1f}ms")
    
    has_sumatriptan = "Sumatriptan" in snippet_res['text'] or "50mg" in snippet_res['text']
    test6_pass = snippet_res['overall_confidence'] >= 0.80 and (has_sumatriptan or len(snippet_res['text']) > 5)
    print(f"Verification: {'PASS' if test6_pass else 'FAIL'}")
    results['snippet_ocr'] = {
        'status': 'PASS' if test6_pass else 'FAIL',
        'text': snippet_res['text'],
        'confidence': snippet_res['overall_confidence'],
        'latency_ms': snippet_res['latency_ms']
    }

    # TEST 7: Map OCR Coordinates Back to Screen
    print("\n--- [Test 7/9] Map OCR Coordinates Back to Screen ---")
    mapper = ScreenCoordinateMapper(
        doc_width=1000,
        doc_height=600,
        screen_origin_x=150,
        screen_origin_y=80,
        screen_scale_factor=1.5
    )
    mapped = mapper.map_box(local_bbox=[10, 20, 110, 60], region_offset=(200, 100), upscale_factor=1.0)
    print(f"Original Box: [10, 20, 110, 60] with Offset (200, 100)")
    print(f"Mapped Global BBox: {mapped['bbox']} (Expected: [210, 120, 310, 160])")
    print(f"Mapped Normalized BBox: {mapped['normalized_bbox']} (Expected: [0.21, 0.20, 0.31, 0.267])")
    print(f"Mapped Absolute Screen BBox: {mapped['screen_bbox']} (Expected: [540, 300, 690, 360])")
    print(f"Client Rect: {mapped['client_rect']}")
    
    test7_pass = (
        mapped['bbox'] == [210, 120, 310, 160] and
        mapped['screen_bbox'] == [540, 300, 690, 360] and
        mapped['normalized_bbox'][0] == 0.21
    )
    print(f"Verification: {'PASS' if test7_pass else 'FAIL'}")
    results['screen_coordinate_mapping'] = {
        'status': 'PASS' if test7_pass else 'FAIL',
        'bbox': mapped['bbox'],
        'screen_bbox': mapped['screen_bbox'],
        'normalized_bbox': mapped['normalized_bbox']
    }

    # TEST 8: Produce Line-Level OCR Blocks
    print("\n--- [Test 8/9] Produce Line-Level OCR Blocks ---")
    all_blocks = screen_res['blocks']
    has_line_numbers = all('line_number' in b for b in all_blocks)
    has_screen_bboxes = all('screen_bbox' in b for b in all_blocks)
    has_words = any(len(b.get('words', [])) > 0 for b in all_blocks)
    
    print(f"Total Line Blocks: {len(all_blocks)}")
    print(f"All blocks have line_number: {has_line_numbers}")
    print(f"All blocks have screen_bbox: {has_screen_bboxes}")
    print(f"Word tokens embedded in lines: {has_words}")
    
    test8_pass = len(all_blocks) > 0 and has_line_numbers and has_screen_bboxes
    print(f"Verification: {'PASS' if test8_pass else 'FAIL'}")
    results['line_level_blocks'] = {
        'status': 'PASS' if test8_pass else 'FAIL',
        'total_lines': len(all_blocks),
        'has_line_numbers': has_line_numbers,
        'has_screen_bboxes': has_screen_bboxes
    }

    # TEST 9: Optimize OCR Latency
    print("\n--- [Test 9/9] Optimize OCR Latency ---")
    warm_latencies = []
    for _ in range(5):
        t_start = time.perf_counter()
        _ = lens_engine.snippet_engine.process_snippet(snippet_crop, coord_mapper=coord_mapper, region_offset=(660, 140))
        t_end = time.perf_counter()
        warm_latencies.append((t_end - t_start) * 1000.0)

    avg_snippet_latency = float(np.mean(warm_latencies))
    min_snippet_latency = float(np.min(warm_latencies))
    print(f"Snippet Latency over 5 warm runs:")
    print(f"  Min Latency: {min_snippet_latency:.1f}ms")
    print(f"  Avg Latency: {avg_snippet_latency:.1f}ms")
    print(f"Target: < 150ms")
    
    test9_pass = avg_snippet_latency < 150.0
    print(f"Verification: {'PASS' if test9_pass else 'FAIL'}")
    results['ocr_latency'] = {
        'status': 'PASS' if test9_pass else 'FAIL',
        'min_ms': min_snippet_latency,
        'avg_ms': avg_snippet_latency,
        'target_ms': 150.0
    }

    # Summary
    print("\n" + "=" * 75)
    print("PHASE 7 - GOOGLE-LENS OCR SUMMARY")
    print("=" * 75)
    all_passed = all(r.get('status') == 'PASS' for r in results.values())
    for k, v in results.items():
        print(f"  - {k:28}: {v['status']}")
    print(f"\nOVERALL RESULT: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")

    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs"))
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "google_lens_ocr_benchmark.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Saved benchmark report to {out_path}")

if __name__ == "__main__":
    main()
