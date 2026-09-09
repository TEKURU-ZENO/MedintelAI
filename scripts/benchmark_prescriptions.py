import os
import sys
import cv2
import numpy as np
from typing import Dict, List, Tuple

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.ai.ocr.ocr_engine import MedIntelOCREngine

def levenshtein_distance(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
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

def calculate_cer(predicted: str, ground_truth: str) -> float:
    pred_clean = " ".join(predicted.strip().split())
    gt_clean = " ".join(ground_truth.strip().split())
    if not gt_clean:
        return 0.0 if not pred_clean else 1.0
    dist = levenshtein_distance(pred_clean, gt_clean)
    return min(1.0, dist / float(len(gt_clean)))

def calculate_wer(predicted: str, ground_truth: str) -> float:
    pred_words = predicted.strip().split()
    gt_words = ground_truth.strip().split()
    if not gt_words:
        return 0.0 if not pred_words else 1.0
    
    # Word-level Levenshtein
    d = np.zeros((len(gt_words) + 1, len(pred_words) + 1), dtype=int)
    for i in range(len(gt_words) + 1):
        d[i][0] = i
    for j in range(len(pred_words) + 1):
        d[0][j] = j
        
    for i in range(1, len(gt_words) + 1):
        for j in range(1, len(pred_words) + 1):
            if gt_words[i - 1].lower() == pred_words[j - 1].lower():
                d[i][j] = d[i - 1][j - 1]
            else:
                d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + 1)
                
    return min(1.0, float(d[len(gt_words)][len(pred_words)]) / float(len(gt_words)))

def run_prescription_benchmark():
    engine = MedIntelOCREngine()
    
    test_cases = [
        {
            "id": "presc_sample_01",
            "image_path": "datasets/prescriptions/sample_1.png",
            "ground_truth": (
                "CITY CARE HOSPITAL - PRESCRIPTION\n"
                "Patient : Rahul Kumar Ages 42 Date : 05/09/2026\n"
                "rxi\n"
                "1 . Tab Amoxicillin 500 mg - 1-0-1 x 5 days\n"
                "2 . Tab Paracetamol 650 mg - 1-0-1 SOS\n"
                "3 . Syp. cough Relief 10 ml - 0-0-1 at night\n"
                "Dr. S. Mehta, MD (Physician)"
            ),
            "critical_tokens": ["Amoxicillin", "500 mg", "1-0-1", "5 days", "Paracetamol", "650 mg", "SOS", "10 ml"]
        }
    ]

    print("=" * 80)
    print("OCR DOCUMENT READING SYSTEM — PRESCRIPTION HANDWRITING BENCHMARK")
    print("Evaluating TrOCR (Handwritten) + RapidOCR (Printed) + Medical PostProcessor")
    print("=" * 80)

    total_cer = []
    total_wer = []
    token_results = []

    for tc in test_cases:
        img_path = tc["image_path"]
        if not os.path.exists(img_path):
            print(f"Skipping {tc['id']}, file not found: {img_path}")
            continue

        img = cv2.imread(img_path)
        result = engine.process_document(img, doc_name=tc["id"])
        pred_text = result["raw_text"]
        gt_text = tc["ground_truth"]

        cer = calculate_cer(pred_text, gt_text)
        wer = calculate_wer(pred_text, gt_text)
        total_cer.append(cer)
        total_wer.append(wer)

        print(f"\nDocument ID: {tc['id']}")
        print(f"Blocks Detected: {len(result['blocks'])}")
        print(f"Model Routing Provenance:")
        for b in result["blocks"]:
            print(f"  - [{b['id']}] {b['model_used']:<18} ({b['source']:<11}, conf: {b['confidence']:.3f}): {b['text']}")

        print("\n--- GROUND TRUTH ---")
        print(gt_text)
        print("\n--- OCR PREDICTION ---")
        print(pred_text)
        print("\n--- ACCURACY METRICS ---")
        print(f"Character Error Rate (CER): {cer * 100:.2f}%")
        print(f"Word Error Rate (WER)     : {wer * 100:.2f}%")

        # Critical medical tokens check
        print("\n--- CRITICAL MEDICAL TOKENS EVALUATION ---")
        for token in tc["critical_tokens"]:
            present = token.lower() in pred_text.lower()
            token_results.append(present)
            status_str = "MATCH [PASS]" if present else "MISMATCH [FAIL]"
            print(f"  * {token:<15} : {status_str}")

    avg_cer = np.mean(total_cer) if total_cer else 0.0
    avg_wer = np.mean(total_wer) if total_wer else 0.0
    token_acc = (sum(token_results) / float(len(token_results))) * 100 if token_results else 0.0

    print("\n" + "=" * 80)
    print("OVERALL BENCHMARK SUMMARY")
    print("=" * 80)
    print(f"Average Character Error Rate (CER) : {avg_cer * 100:.2f}%")
    print(f"Average Word Error Rate (WER)      : {avg_wer * 100:.2f}%")
    print(f"Critical Medical Token Accuracy    : {token_acc:.1f}%")
    print("=" * 80)

if __name__ == "__main__":
    run_prescription_benchmark()
