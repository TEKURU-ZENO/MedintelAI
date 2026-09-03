import os
import sys
import json
import time
import numpy as np
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.ai.pipeline.pipeline_controller import PipelineController
from app.ai.utils.logger import get_logger

logger = get_logger("benchmark_ocr")

def levenshtein_dist(s1, s2):
    if len(s1) < len(s2):
        return levenshtein_dist(s2, s1)
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

def calculate_cer(reference: str, hypothesis: str) -> float:
    if not reference:
        return 0.0 if not hypothesis else 1.0
    dist = levenshtein_dist(reference, hypothesis)
    return float(dist) / float(len(reference))

def calculate_wer(reference: str, hypothesis: str) -> float:
    ref_words = reference.strip().split()
    hyp_words = hypothesis.strip().split()
    if not ref_words:
        return 0.0 if not hyp_words else 1.0
    dist = levenshtein_dist(ref_words, hyp_words)
    return float(dist) / float(len(ref_words))

def run_benchmark():
    logger.info("Starting MedIntel OCR Evaluation & Benchmark Suite...")
    controller = PipelineController()
    
    test_cases = [
        {
            "category": "Printed",
            "doc_name": "printed_lab_report_01.jpg",
            "ground_truth": "Patient Name: Rahul Kumar Age: 42 BP: 130/80 Pulse: 78 bpm",
        },
        {
            "category": "Handwritten",
            "doc_name": "handwritten_note_01.jpg",
            "ground_truth": "Diagnosis: Acute Pharyngitis Medication: Amoxicillin 500mg Dosage: 1 tablet 8 hourly",
        },
        {
            "category": "Mixed",
            "doc_name": "discharge_summary_01.jpg",
            "ground_truth": "Patient Name: Rahul Kumar Diagnosis: Acute Pharyngitis Follow-up: 5 days",
        },
        {
            "category": "Low-quality/scanned",
            "doc_name": "scanned_prescription_01.jpg",
            "ground_truth": "Medication: Amoxicillin 500mg Dosage: 1 tablet 8 hourly Follow-up: 5 days",
        }
    ]
    
    os.makedirs("outputs/temp", exist_ok=True)
    import cv2
    for item in test_cases:
        path = os.path.join("outputs/temp", item["doc_name"])
        if not os.path.exists(path):
            img = np.ones((600, 800, 3), dtype=np.uint8) * 245
            cv2.putText(img, item["category"] + " Document Sample", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (20, 20, 20), 2)
            cv2.putText(img, item["ground_truth"][:40], (50, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (40, 40, 40), 2)
            cv2.imwrite(path, img)
        item["file_path"] = path

    results_by_cat = {}
    for item in test_cases:
        cat = item["category"]
        start_time = time.time()
        res = controller.process_image(item["file_path"])
        proc_time = time.time() - start_time
        
        extracted_text = " ".join([b["text"] for b in res.get("blocks", [])]) if res else ""
        cer = calculate_cer(item["ground_truth"], extracted_text)
        wer = calculate_wer(item["ground_truth"], extracted_text)
        
        if cat not in results_by_cat:
            results_by_cat[cat] = {"cers": [], "wers": [], "times": []}
            
        results_by_cat[cat]["cers"].append(cer)
        results_by_cat[cat]["wers"].append(wer)
        results_by_cat[cat]["times"].append(proc_time)
        
    summary = {}
    for cat, data in results_by_cat.items():
        avg_cer = float(np.mean(data["cers"])) * 100
        avg_wer = float(np.mean(data["wers"])) * 100
        avg_time = float(np.mean(data["times"]))
        summary[cat] = {
            "cer": f"{avg_cer:.1f}%",
            "wer": f"{avg_wer:.1f}%",
            "avg_time_sec": round(avg_time, 3)
        }
        
    report = {
        "status": "success",
        "system": "MedIntel OCR Engine Benchmark",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "metrics": summary
    }
    
    os.makedirs("outputs", exist_ok=True)
    with open("outputs/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    print("=====================================================")
    print("          MEDINTEL OCR BENCHMARK REPORT              ")
    print("=====================================================")
    print("Category                  WER        CER        Avg Time")
    print("-----------------------------------------------------")
    for cat, metrics in summary.items():
        print(f"{cat:<25} {metrics['wer']:<10} {metrics['cer']:<10} {metrics['avg_time_sec']}s")
    print("=====================================================")
    print("Saved benchmark results to outputs/benchmark_results.json")

if __name__ == "__main__":
    run_benchmark()
