import os
import sys
import time
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from app.ai.pipeline.pipeline_controller import PipelineController
from scripts.benchmark_ocr import calculate_cer, calculate_wer

def evaluate_number_symbol_accuracy(gt_text: str, pred_text: str) -> float:
    """
    Evaluates exact matching of critical numeric and symbol tokens
    (e.g. phone numbers, dosages, dates, vitals, units, list indices).
    """
    num_pattern = r'\b(?:\d{10}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d+(?:\.\d+)?\s*(?:mg|ml|mcg|g|%|bpm|tab|cap)|(?:BP:?\s*\d+/\d+)|[012]-[012]-[012]|\d+\+\d+x\d+)\b'
    gt_tokens = re.findall(num_pattern, gt_text, flags=re.IGNORECASE)
    if not gt_tokens:
        # Fallback to general numbers
        gt_tokens = re.findall(r'\b\d+\b', gt_text)
    if not gt_tokens:
        return 1.0

    pred_tokens = re.findall(r'[0-9]+[0-9a-zA-Z/.:%-]*', pred_text)
    pred_str = " ".join(pred_tokens).lower()

    matches = 0
    for tok in gt_tokens:
        clean_tok = tok.strip().lower()
        if clean_tok in pred_str or re.sub(r'\s+', '', clean_tok) in re.sub(r'\s+', '', pred_str):
            matches += 1

    return matches / len(gt_tokens)

def evaluate_medical_term_accuracy(gt_text: str, pred_text: str) -> float:
    """
    Evaluates matching of medical terms and clinical keywords.
    """
    med_terms = [
        "consultant", "physician", "surgeon", "hospital", "clinic", "timing",
        "paracetamol", "amoxicillin", "dolo", "pan", "pantocid", "styplon", "sigru",
        "chandraprabha", "kanchanar", "thyroid", "psoriasis", "diabetes", "hypertension",
        "asthma", "allergy", "infection", "creatinine", "hemoglobin", "blood",
        "pressure", "pulse", "spo2", "temperature", "vitals", "tab", "cap", "syp", "inj"
    ]
    gt_lower = gt_text.lower()
    present_terms = [t for t in med_terms if t in gt_lower]
    if not present_terms:
        return 1.0

    pred_lower = pred_text.lower()
    matches = sum(1 for t in present_terms if t in pred_lower)
    return matches / len(present_terms)

def run_printed_benchmark():
    print("=" * 80)
    print("       PHASE 2: PRINTED OCR BENCHMARK & EVALUATION SUITE")
    print("=" * 80)
    
    controller = PipelineController()
    
    # 1. Standard Printed Form Datasets
    eval_dirs = [
        ("Admission Forms", root_dir / "datasets" / "admission_forms"),
        ("Consent Forms", root_dir / "datasets" / "consent_forms"),
        ("Discharge Summaries", root_dir / "datasets" / "discharge_summaries"),
        ("Lab Reports", root_dir / "datasets" / "lab_reports"),
    ]
    
    results = {}
    print(f"\n{'Category':<22} | {'CER':<7} | {'WER':<7} | {'Num/Sym':<8} | {'Med Term':<9} | {'Latency':<8} | {'Pages'}")
    print("-" * 80)

    total_cer, total_wer, total_num, total_med, total_times = [], [], [], [], []
    total_docs = 0

    for cat_name, cat_path in eval_dirs:
        if not cat_path.exists():
            continue
        docs = list(cat_path.glob("*.jpg")) + list(cat_path.glob("*.png")) + list(cat_path.glob("*.pdf"))
        cers, wers, nums, meds, times = [], [], [], [], []

        for d in docs:
            gt_p = d.with_suffix(".txt")
            if not gt_p.exists():
                continue
            gt_text = gt_p.read_text(encoding="utf-8")
            
            t0 = time.time()
            res = controller.process_document(str(d), doc_name=d.name)
            elapsed = time.time() - t0

            pred_text = res.get("raw_text", "")
            c = calculate_cer(gt_text, pred_text)
            w = calculate_wer(gt_text, pred_text)
            n_acc = evaluate_number_symbol_accuracy(gt_text, pred_text)
            m_acc = evaluate_medical_term_accuracy(gt_text, pred_text)

            cers.append(c)
            wers.append(w)
            nums.append(n_acc)
            meds.append(m_acc)
            times.append(elapsed)

        if cers:
            avg_c = float(np.mean(cers))
            avg_w = float(np.mean(wers))
            avg_n = float(np.mean(nums))
            avg_m = float(np.mean(meds))
            avg_t = float(np.mean(times))
            count = len(cers)
            total_docs += count
            total_cer.extend(cers)
            total_wer.extend(wers)
            total_num.extend(nums)
            total_med.extend(meds)
            total_times.extend(times)

            results[cat_name] = {
                "cer": f"{avg_c * 100:.1f}%",
                "wer": f"{avg_w * 100:.1f}%",
                "number_accuracy": f"{avg_n * 100:.1f}%",
                "medical_term_accuracy": f"{avg_m * 100:.1f}%",
                "avg_latency": f"{avg_t:.3f}s",
                "samples": count
            }
            print(f"{cat_name:<22} | {avg_c*100:>5.1f}% | {avg_w*100:>5.1f}% | {avg_n*100:>6.1f}% | {avg_m*100:>7.1f}% | {avg_t:>6.3f}s | {count}")

    # 2. Testing Images Benchmark (Sample of 5 real clinical prescription forms)
    test_img_dir = root_dir / "testing images"
    if test_img_dir.exists():
        test_samples = ["10.jpg", "11.jpg", "12.jpg", "13.jpg", "14.jpg"]
        t_cers, t_wers, t_nums, t_meds, t_times = [], [], [], [], []
        
        for name in test_samples:
            p = test_img_dir / name
            gt_p = p.with_suffix(".txt")
            if not p.exists() or not gt_p.exists():
                continue
            gt_text = gt_p.read_text(encoding="utf-8")
            if not gt_text.strip():
                continue
            
            t0 = time.time()
            res = controller.process_document(str(p), doc_name=name)
            elapsed = time.time() - t0
            pred_text = res.get("raw_text", "")
            
            t_cers.append(calculate_cer(gt_text, pred_text))
            t_wers.append(calculate_wer(gt_text, pred_text))
            t_nums.append(evaluate_number_symbol_accuracy(gt_text, pred_text))
            t_meds.append(evaluate_medical_term_accuracy(gt_text, pred_text))
            t_times.append(elapsed)
            
        if t_cers:
            avg_c = float(np.mean(t_cers))
            avg_w = float(np.mean(t_wers))
            avg_n = float(np.mean(t_nums))
            avg_m = float(np.mean(t_meds))
            avg_t = float(np.mean(t_times))
            results["Clinical Photos (Test)"] = {
                "cer": f"{avg_c * 100:.1f}%",
                "wer": f"{avg_w * 100:.1f}%",
                "number_accuracy": f"{avg_n * 100:.1f}%",
                "medical_term_accuracy": f"{avg_m * 100:.1f}%",
                "avg_latency": f"{avg_t:.3f}s",
                "samples": len(t_cers)
            }
            print(f"{'Clinical Photos (Test)':<22} | {avg_c*100:>5.1f}% | {avg_w*100:>5.1f}% | {avg_n*100:>6.1f}% | {avg_m*100:>7.1f}% | {avg_t:>6.3f}s | {len(t_cers)}")

    print("=" * 80)
    overall_cer = float(np.mean(total_cer)) if total_cer else 0.0
    overall_wer = float(np.mean(total_wer)) if total_wer else 0.0
    overall_num = float(np.mean(total_num)) if total_num else 0.0
    overall_med = float(np.mean(total_med)) if total_med else 0.0
    overall_t = float(np.mean(total_times)) if total_times else 0.0
    
    print(f"{'OVERALL PRINTED OCR':<22} | {overall_cer*100:>5.1f}% | {overall_wer*100:>5.1f}% | {overall_num*100:>6.1f}% | {overall_med*100:>7.1f}% | {overall_t:>6.3f}s | {total_docs} docs")
    print("=" * 80)

    # Save to outputs
    out_dir = root_dir / "outputs"
    out_dir.mkdir(exist_ok=True)
    report_file = out_dir / "printed_ocr_benchmark.json"
    report_data = {
        "status": "success",
        "phase": "Phase 2 — Printed OCR",
        "summary": {
            "overall_cer": f"{overall_cer * 100:.1f}%",
            "overall_wer": f"{overall_wer * 100:.1f}%",
            "number_and_symbol_accuracy": f"{overall_num * 100:.1f}%",
            "medical_term_accuracy": f"{overall_med * 100:.1f}%",
            "average_latency_sec": round(overall_t, 3),
            "total_documents": total_docs
        },
        "breakdown": results
    }
    report_file.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
    print(f"Report saved to {report_file}")

if __name__ == "__main__":
    import numpy as np
    run_printed_benchmark()
