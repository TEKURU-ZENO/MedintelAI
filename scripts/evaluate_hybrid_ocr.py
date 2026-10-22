import os
import sys
import time
import json
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Any

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from app.ai.ocr.ocr_engine import OCRDocumentReadingEngine
from scripts.benchmark_ocr import calculate_cer, calculate_wer


def evaluate_hybrid_ocr():
    print("=" * 85)
    print("         PHASE 5: HYBRID OCR COMPREHENSIVE BENCHMARK & EVALUATION")
    print("=" * 85)

    dataset_manifest_path = root_dir / "datasets" / "medical_dataset" / "metadata.json"
    if not dataset_manifest_path.exists():
        print(f"Error: Manifest not found at {dataset_manifest_path}. Run medical_dataset_builder.py first.")
        return

    manifest = json.loads(dataset_manifest_path.read_text(encoding="utf-8"))
    samples = manifest.get("samples", [])
    print(f"Loaded {len(samples)} evaluation documents from {dataset_manifest_path.name}")

    engine = OCRDocumentReadingEngine()

    total_blocks = 0
    total_printed_routed = 0
    total_hw_routed = 0
    total_fallbacks = 0
    total_hallucinations_mitigated = 0
    total_normalizations = 0
    total_flagged_errors = 0
    total_provenance_complete = 0

    category_stats = {}
    all_cers, all_wers, all_latencies = [], [], []
    detailed_results = []

    for idx, s in enumerate(samples, 1):
        cat = s["category"]
        img_path = s["image_path"]
        gt_text = s["text"]

        if not os.path.exists(img_path):
            continue

        if cat not in category_stats:
            category_stats[cat] = {
                "cers": [],
                "wers": [],
                "latencies": [],
                "blocks": 0,
                "printed": 0,
                "handwritten": 0,
                "fallbacks": 0,
                "flagged_errors": 0
            }

        img = cv2.imread(img_path)
        t0 = time.time()
        result = engine.process_document(img, doc_name=s["id"])
        latency = time.time() - t0

        pred_text = result.get("raw_text", "")
        cer = calculate_cer(gt_text, pred_text)
        wer = calculate_wer(gt_text, pred_text)

        blocks = result.get("blocks", [])
        num_blocks = len(blocks)
        total_blocks += num_blocks
        category_stats[cat]["blocks"] += num_blocks

        # Analyze blocks
        for b in blocks:
            prov = b.get("provenance", {})
            err = b.get("error_analysis", {})

            if "model_used" in prov and "region_type" in prov and "routing_decision" in prov:
                total_provenance_complete += 1

            if prov.get("model_used") == "rapidocr-printed":
                total_printed_routed += 1
                category_stats[cat]["printed"] += 1
            elif prov.get("model_used") == "trocr-handwritten":
                total_hw_routed += 1
                category_stats[cat]["handwritten"] += 1
            elif "fallback" in prov.get("model_used", ""):
                total_fallbacks += 1
                category_stats[cat]["fallbacks"] += 1

            if prov.get("hallucination_mitigated", False):
                total_hallucinations_mitigated += 1

            if prov.get("normalization_applied", False):
                total_normalizations += 1

            if err.get("has_errors", False):
                total_flagged_errors += 1
                category_stats[cat]["flagged_errors"] += 1

        category_stats[cat]["cers"].append(cer)
        category_stats[cat]["wers"].append(wer)
        category_stats[cat]["latencies"].append(latency)

        all_cers.append(cer)
        all_wers.append(wer)
        all_latencies.append(latency)

        detailed_results.append({
            "id": s["id"],
            "category": cat,
            "cer": round(cer, 4),
            "wer": round(wer, 4),
            "latency": round(latency, 3),
            "blocks_count": num_blocks,
            "hybrid_routing": result.get("hybrid_routing", {}),
            "error_summary": result.get("error_summary", {})
        })

    # Print Summary Table
    print("\n" + "=" * 92)
    print(f"{'Category':<20} | {'CER':<8} | {'WER':<8} | {'Blocks':<8} | {'Printed':<8} | {'HW':<6} | {'Avg Latency'}")
    print("-" * 92)

    summary_by_cat = {}
    for cat, st in category_stats.items():
        m_cer = float(np.mean(st["cers"])) if st["cers"] else 0.0
        m_wer = float(np.mean(st["wers"])) if st["wers"] else 0.0
        m_lat = float(np.mean(st["latencies"])) if st["latencies"] else 0.0

        summary_by_cat[cat] = {
            "cer": f"{m_cer*100:.1f}%",
            "wer": f"{m_wer*100:.1f}%",
            "total_blocks": st["blocks"],
            "printed_routed": st["printed"],
            "handwritten_routed": st["handwritten"],
            "fallbacks": st["fallbacks"],
            "flagged_errors": st["flagged_errors"],
            "avg_latency": f"{m_lat:.3f}s",
            "samples": len(st["cers"])
        }
        print(f"{cat:<20} | {m_cer*100:>6.1f}% | {m_wer*100:>6.1f}% | {st['blocks']:>8} | {st['printed']:>8} | {st['handwritten']:>6} | {m_lat:>9.3f}s")

    overall_cer = float(np.mean(all_cers)) if all_cers else 0.0
    overall_wer = float(np.mean(all_wers)) if all_wers else 0.0
    overall_lat = float(np.mean(all_latencies)) if all_latencies else 0.0
    provenance_rate = (total_provenance_complete / total_blocks * 100) if total_blocks > 0 else 100.0

    print("=" * 92)
    print(f"{'OVERALL HYBRID OCR':<20} | {overall_cer*100:>6.1f}% | {overall_wer*100:>6.1f}% | {total_blocks:>8} | {total_printed_routed:>8} | {total_hw_routed:>6} | {overall_lat:>9.3f}s")
    print("=" * 92)

    print("\nHybrid OCR Architectural Integrity:")
    print(f"  Model Provenance Coverage:         {provenance_rate:.1f}% ({total_provenance_complete}/{total_blocks} blocks)")
    print(f"  Total Printed Regions (RapidOCR):  {total_printed_routed}")
    print(f"  Total Handwritten Regions (TrOCR): {total_hw_routed}")
    print(f"  Fallback Routes Triggered:         {total_fallbacks}")
    print(f"  Anti-Hallucination Mitigations:    {total_hallucinations_mitigated}")
    print(f"  Medical Token Normalizations:      {total_normalizations}")
    print(f"  OCR Errors Flagged & Diagnosed:    {total_flagged_errors}")

    # Save to outputs
    out_dir = root_dir / "outputs"
    out_dir.mkdir(exist_ok=True)
    report_file = out_dir / "hybrid_ocr_benchmark.json"

    benchmark_data = {
        "status": "success",
        "phase": "Phase 5 — Hybrid OCR",
        "summary": {
            "overall_cer": f"{overall_cer*100:.1f}%",
            "overall_wer": f"{overall_wer*100:.1f}%",
            "total_blocks_analyzed": total_blocks,
            "model_provenance_coverage": f"{provenance_rate:.1f}%",
            "printed_routed_count": total_printed_routed,
            "handwritten_routed_count": total_hw_routed,
            "fallbacks_triggered_count": total_fallbacks,
            "hallucinations_mitigated_count": total_hallucinations_mitigated,
            "normalizations_applied_count": total_normalizations,
            "errors_flagged_count": total_flagged_errors,
            "average_latency_sec": round(overall_lat, 3),
            "total_documents": len(samples)
        },
        "breakdown": summary_by_cat,
        "detailed_results": detailed_results
    }

    report_file.write_text(json.dumps(benchmark_data, indent=2), encoding="utf-8")
    print(f"\nDetailed Hybrid OCR benchmark saved to {report_file}")


if __name__ == "__main__":
    evaluate_hybrid_ocr()
