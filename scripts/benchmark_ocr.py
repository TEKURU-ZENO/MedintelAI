import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ai.pipeline.pipeline_controller import PipelineController


def compute_levenshtein(s1: str, s2: str) -> int:
    """Computes character Levenshtein edit distance."""
    if len(s1) < len(s2):
        return compute_levenshtein(s2, s1)
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
    ref = reference.strip()
    hyp = hypothesis.strip()
    if not ref:
        return 0.0 if not hyp else 1.0
    dist = compute_levenshtein(ref, hyp)
    return min(1.0, dist / len(ref))

def calculate_wer(reference: str, hypothesis: str) -> float:
    ref_words = reference.strip().split()
    hyp_words = hypothesis.strip().split()
    if not ref_words:
        return 0.0 if not hyp_words else 1.0
    # Word-level edit distance
    n, m = len(ref_words), len(hyp_words)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if ref_words[i - 1].lower() == hyp_words[j - 1].lower() else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)
    return min(1.0, dp[n][m] / len(ref_words))

def run_benchmark():
    datasets_dir = Path("datasets")
    controller = PipelineController()
    
    category_dirs = [d for d in datasets_dir.iterdir() if d.is_dir() and not d.name.startswith(('.', '__'))]
    if not category_dirs:
        print("No dataset categories found under datasets/")
        return

    print("==========================================================================")
    print("      OCR DOCUMENT READING SYSTEM — GENERAL BENCHMARK REPORT             ")
    print("==========================================================================")
    print(f"{'Category':<24} | {'CER':<8} | {'WER':<8} | {'Avg Latency':<12} | {'Pages'}")
    print("-" * 74)

    metrics_by_category = {}
    all_cer, all_wer, all_times = [], [], []

    for cat_dir in sorted(category_dirs, key=lambda d: d.name):
        cat_name = cat_dir.name
        img_files = list(cat_dir.glob("*.png")) + list(cat_dir.glob("*.jpg")) + list(cat_dir.glob("*.pdf"))
        
        if not img_files:
            continue
            
        cers, wers, times = [], [], []
        total_pages = 0

        for doc_path in img_files:
            gt_path = doc_path.with_suffix(".txt")
            if not gt_path.exists():
                continue
                
            gt_text = gt_path.read_text(encoding="utf-8")
            
            start_t = time.time()
            result = controller.process_document(str(doc_path), doc_name=doc_path.name)
            elapsed = time.time() - start_t
            
            pred_text = result.get("raw_text", "")
            pages_count = result.get("pages", 1)
            total_pages += pages_count
            
            cer = calculate_cer(gt_text, pred_text)
            wer = calculate_wer(gt_text, pred_text)
            
            cers.append(cer)
            wers.append(wer)
            times.append(elapsed)

        if cers:
            avg_cer = sum(cers) / len(cers)
            avg_wer = sum(wers) / len(wers)
            avg_time = sum(times) / len(times)
            
            all_cer.extend(cers)
            all_wer.extend(wers)
            all_times.extend(times)
            
            metrics_by_category[cat_name] = {
                "cer": f"{avg_cer * 100:.1f}%",
                "wer": f"{avg_wer * 100:.1f}%",
                "avg_time_sec": round(avg_time, 3),
                "samples_evaluated": len(cers)
            }
            
            display_name = cat_name.replace("_", " ").title()
            print(f"{display_name:<24} | {avg_cer * 100:>6.1f}% | {avg_wer * 100:>6.1f}% | {avg_time:>9.3f}s   | {total_pages}")

    print("==========================================================================")
    if all_cer:
        overall_cer = sum(all_cer) / len(all_cer)
        overall_wer = sum(all_wer) / len(all_wer)
        overall_time = sum(all_times) / len(all_times)
        print(f"{'OVERALL PLATFORM':<24} | {overall_cer * 100:>6.1f}% | {overall_wer * 100:>6.1f}% | {overall_time:>9.3f}s   | {len(all_cer)} docs")
        print("==========================================================================")

    output_data = {
        "status": "success",
        "system": "OCR Document Reading System Engine",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "overall": {
            "cer": f"{sum(all_cer)/max(1, len(all_cer)) * 100:.1f}%",
            "wer": f"{sum(all_wer)/max(1, len(all_wer)) * 100:.1f}%",
            "avg_time_sec": round(sum(all_times)/max(1, len(all_times)), 3)
        },
        "metrics": metrics_by_category
    }

    os.makedirs("outputs", exist_ok=True)
    with open("outputs/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)
    print("Saved benchmark report to outputs/benchmark_results.json")

if __name__ == "__main__":
    run_benchmark()
