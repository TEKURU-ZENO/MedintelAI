import os
import sys
import time
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datasets.funsd_loader import FUNSDLoader
from app.ai.pipeline.pipeline_controller import PipelineController
from scripts.benchmark_ocr import calculate_cer, calculate_wer

def benchmark_report_dataset(samples: int = 10):
    print("=" * 76)
    print("      MEDINTEL AI — REPORT DATASET (FUNSD) BENCHMARK REPORT")
    print("=" * 76)

    loader = FUNSDLoader("datasets/report dataset")
    test_docs = loader.get_documents(split="testing")
    
    if not test_docs:
        print("No test documents found in datasets/report dataset/testing_data/")
        return

    if samples > 0:
        eval_docs = test_docs[:samples]
    else:
        eval_docs = test_docs

    controller = PipelineController()
    results = []
    total_cer = 0.0
    total_wer = 0.0
    total_time = 0.0

    print(f"{'Document ID':<16} | {'CER':<8} | {'WER':<8} | {'Blocks':<8} | {'Latency':<10}")
    print("-" * 76)

    for doc in eval_docs:
        doc_id = doc["id"]
        img_path = doc["image_path"]
        gt_text = doc["ground_truth_text"]

        t0 = time.time()
        res = controller.process_document(img_path, doc_name=f"{doc_id}.png")
        latency = time.time() - t0

        pred_text = res.get("raw_text", "")
        blocks_count = len(res.get("blocks", []))

        cer = calculate_cer(gt_text, pred_text)
        wer = calculate_wer(gt_text, pred_text)

        total_cer += cer
        total_wer += wer
        total_time += latency

        results.append({
            "doc_id": doc_id,
            "cer": round(cer, 4),
            "wer": round(wer, 4),
            "blocks": blocks_count,
            "latency_sec": round(latency, 3)
        })

        print(f"{doc_id:<16} | {cer * 100:6.1f}% | {wer * 100:6.1f}% | {blocks_count:<8} | {latency:6.2f}s")

    n = len(eval_docs)
    avg_cer = total_cer / n
    avg_wer = total_wer / n
    avg_latency = total_time / n

    print("=" * 76)
    print(f"AVERAGE ({n} documents):")
    print(f"  Character Error Rate (CER): {avg_cer * 100:.2f}%")
    print(f"  Word Error Rate (WER)     : {avg_wer * 100:.2f}%")
    print(f"  Average Processing Latency: {avg_latency:.3f}s")
    print("=" * 76)

    output_dir = Path("outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    report_file = output_dir / "report_dataset_benchmark.json"

    report_payload = {
        "dataset": "FUNSD Report Dataset (testing split)",
        "total_evaluated": n,
        "summary": {
            "average_cer": f"{avg_cer * 100:.2f}%",
            "average_wer": f"{avg_wer * 100:.2f}%",
            "average_latency_sec": round(avg_latency, 3)
        },
        "documents": results
    }

    report_file.write_text(json.dumps(report_payload, indent=2), encoding="utf-8")
    print(f"Benchmark results saved to: {report_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark MedIntel OCR on Report Dataset")
    parser.add_argument("--samples", type=int, default=10, help="Number of test samples (default: 10, 0 for all 50)")
    args = parser.parse_args()
    benchmark_report_dataset(samples=args.samples)