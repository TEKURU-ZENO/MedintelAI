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
from app.ai.ocr.medical_postprocessor import MedicalVocabularyPostProcessor
from scripts.benchmark_ocr import calculate_cer, calculate_wer


def evaluate_medical_ocr():
    print("=" * 80)
    print("      PHASE 4: MEDICAL OCR COMPREHENSIVE BENCHMARK & EVALUATION")
    print("=" * 80)

    dataset_manifest_path = root_dir / "datasets" / "medical_dataset" / "metadata.json"
    if not dataset_manifest_path.exists():
        print(f"Error: Manifest not found at {dataset_manifest_path}. Run medical_dataset_builder.py first.")
        return

    manifest = json.loads(dataset_manifest_path.read_text(encoding="utf-8"))
    samples = manifest.get("samples", [])
    print(f"Loaded {len(samples)} medical documents from {dataset_manifest_path.name}")

    engine = OCRDocumentReadingEngine()
    postprocessor = MedicalVocabularyPostProcessor()

    category_stats = {}
    total_drugs_gt, total_drugs_matched = 0, 0
    total_dosages_gt, total_dosages_matched = 0, 0
    total_freqs_gt, total_freqs_matched = 0, 0
    total_units_gt, total_units_matched = 0, 0
    total_abbrs_gt, total_abbrs_matched = 0, 0

    detailed_results = []

    for idx, s in enumerate(samples, 1):
        cat = s["category"]
        img_path = s["image_path"]
        gt_text = s["text"]
        gt_entities = s.get("entities", {})

        if not os.path.exists(img_path):
            continue

        if cat not in category_stats:
            category_stats[cat] = {
                "cers": [],
                "wers": [],
                "latencies": [],
                "drugs_gt": 0, "drugs_pred": 0,
                "dosages_gt": 0, "dosages_pred": 0,
                "freqs_gt": 0, "freqs_pred": 0
            }

        img = cv2.imread(img_path)
        t0 = time.time()
        result = engine.process_document(img, doc_name=s["id"])
        latency = time.time() - t0

        pred_text = result.get("raw_text", "")
        pred_entities = postprocessor.extract_medical_entities(pred_text)

        cer = calculate_cer(gt_text, pred_text)
        wer = calculate_wer(gt_text, pred_text)

        category_stats[cat]["cers"].append(cer)
        category_stats[cat]["wers"].append(wer)
        category_stats[cat]["latencies"].append(latency)

        # Entity Matching
        gt_drugs = set(d.lower() for d in gt_entities.get("drugs", []))
        pred_drugs = set(d.lower() for d in pred_entities.get("drugs", []))
        matched_drugs = len(gt_drugs.intersection(pred_drugs))
        category_stats[cat]["drugs_gt"] += len(gt_drugs)
        category_stats[cat]["drugs_pred"] += matched_drugs
        total_drugs_gt += len(gt_drugs)
        total_drugs_matched += matched_drugs

        gt_dosages = set(d.lower().replace(" ", "") for d in gt_entities.get("dosages", []))
        pred_dosages = set(d.lower().replace(" ", "") for d in pred_entities.get("dosages", []))
        matched_dosages = len(gt_dosages.intersection(pred_dosages))
        category_stats[cat]["dosages_gt"] += len(gt_dosages)
        category_stats[cat]["dosages_pred"] += matched_dosages
        total_dosages_gt += len(gt_dosages)
        total_dosages_matched += matched_dosages

        gt_freqs = set(f.lower().replace(" ", "") for f in gt_entities.get("frequencies", []))
        pred_freqs = set(f.lower().replace(" ", "") for f in pred_entities.get("frequencies", []))
        matched_freqs = len(gt_freqs.intersection(pred_freqs))
        category_stats[cat]["freqs_gt"] += len(gt_freqs)
        category_stats[cat]["freqs_pred"] += matched_freqs
        total_freqs_gt += len(gt_freqs)
        total_freqs_matched += matched_freqs

        # Units and abbreviations
        gt_units = set(u.lower() for u in gt_entities.get("units", []))
        pred_units = set(u.lower() for u in pred_entities.get("units", []))
        total_units_gt += len(gt_units)
        total_units_matched += len(gt_units.intersection(pred_units))

        gt_abbrs = set(a.upper() for a in gt_entities.get("abbreviations", []))
        pred_abbrs = set(a.upper() for a in pred_entities.get("abbreviations", []))
        total_abbrs_gt += len(gt_abbrs)
        total_abbrs_matched += len(gt_abbrs.intersection(pred_abbrs))

        detailed_results.append({
            "id": s["id"],
            "category": cat,
            "cer": round(cer, 4),
            "wer": round(wer, 4),
            "latency": round(latency, 3),
            "gt_drugs": list(gt_drugs),
            "pred_drugs": list(pred_drugs),
            "blocks_count": len(result.get("blocks", []))
        })

    # Summary table
    print("\n" + "=" * 90)
    print(f"{'Category':<22} | {'CER':<8} | {'WER':<8} | {'Drug Acc':<10} | {'Dose Acc':<10} | {'Avg Latency'}")
    print("-" * 90)

    summary_by_cat = {}
    all_cers, all_wers, all_lats = [], [], []

    for cat, st in category_stats.items():
        mean_cer = float(np.mean(st["cers"])) if st["cers"] else 0.0
        mean_wer = float(np.mean(st["wers"])) if st["wers"] else 0.0
        mean_lat = float(np.mean(st["latencies"])) if st["latencies"] else 0.0
        drug_acc = (st["drugs_pred"] / st["drugs_gt"] * 100) if st["drugs_gt"] > 0 else 100.0
        dose_acc = (st["dosages_pred"] / st["dosages_gt"] * 100) if st["dosages_gt"] > 0 else 100.0

        all_cers.extend(st["cers"])
        all_wers.extend(st["wers"])
        all_lats.extend(st["latencies"])

        summary_by_cat[cat] = {
            "cer": f"{mean_cer*100:.1f}%",
            "wer": f"{mean_wer*100:.1f}%",
            "drug_accuracy": f"{drug_acc:.1f}%",
            "dosage_accuracy": f"{dose_acc:.1f}%",
            "avg_latency": f"{mean_lat:.3f}s",
            "samples": len(st["cers"])
        }

        print(f"{cat:<22} | {mean_cer*100:>6.1f}% | {mean_wer*100:>6.1f}% | {drug_acc:>8.1f}% | {dose_acc:>8.1f}% | {mean_lat:>9.3f}s")

    overall_cer = float(np.mean(all_cers)) if all_cers else 0.0
    overall_wer = float(np.mean(all_wers)) if all_wers else 0.0
    overall_lat = float(np.mean(all_lats)) if all_lats else 0.0
    overall_drug_acc = (total_drugs_matched / total_drugs_gt * 100) if total_drugs_gt > 0 else 100.0
    overall_dose_acc = (total_dosages_matched / total_dosages_gt * 100) if total_dosages_gt > 0 else 100.0
    overall_freq_acc = (total_freqs_matched / total_freqs_gt * 100) if total_freqs_gt > 0 else 100.0
    overall_unit_acc = (total_units_matched / total_units_gt * 100) if total_units_gt > 0 else 100.0
    overall_abbr_acc = (total_abbrs_matched / total_abbrs_gt * 100) if total_abbrs_gt > 0 else 100.0

    print("=" * 90)
    print(f"{'OVERALL MEDICAL OCR':<22} | {overall_cer*100:>6.1f}% | {overall_wer*100:>6.1f}% | {overall_drug_acc:>8.1f}% | {overall_dose_acc:>8.1f}% | {overall_lat:>9.3f}s")
    print("=" * 90)

    print("\nClinical Entity Recognition Accuracy:")
    print(f"  Drug Name Accuracy:         {overall_drug_acc:.1f}% ({total_drugs_matched}/{total_drugs_gt})")
    print(f"  Dosage Accuracy:            {overall_dose_acc:.1f}% ({total_dosages_matched}/{total_dosages_gt})")
    print(f"  Frequency Accuracy:         {overall_freq_acc:.1f}% ({total_freqs_matched}/{total_freqs_gt})")
    print(f"  Units Recall:               {overall_unit_acc:.1f}% ({total_units_matched}/{total_units_gt})")
    print(f"  Abbreviations Recall:       {overall_abbr_acc:.1f}% ({total_abbrs_matched}/{total_abbrs_gt})")

    # Save to outputs
    out_dir = root_dir / "outputs"
    out_dir.mkdir(exist_ok=True)
    report_file = out_dir / "medical_ocr_benchmark.json"

    benchmark_data = {
        "status": "success",
        "phase": "Phase 4 — Medical OCR",
        "summary": {
            "overall_cer": f"{overall_cer*100:.1f}%",
            "overall_wer": f"{overall_wer*100:.1f}%",
            "drug_accuracy": f"{overall_drug_acc:.1f}%",
            "dosage_accuracy": f"{overall_dose_acc:.1f}%",
            "frequency_accuracy": f"{overall_freq_acc:.1f}%",
            "units_recall": f"{overall_unit_acc:.1f}%",
            "abbreviations_recall": f"{overall_abbr_acc:.1f}%",
            "average_latency_sec": round(overall_lat, 3),
            "total_documents": len(samples)
        },
        "breakdown": summary_by_cat,
        "detailed_results": detailed_results
    }

    report_file.write_text(json.dumps(benchmark_data, indent=2), encoding="utf-8")
    print(f"\nDetailed benchmark report saved to {report_file}")


if __name__ == "__main__":
    evaluate_medical_ocr()
