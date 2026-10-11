import time
from typing import Any, Dict, List

from app.core.logging import logger
from app.services.ocr_service import OCRService


def edit_distance(a, b):
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


class BenchmarkService:
    def __init__(self, ocr_service: OCRService):
        self.ocr_service = ocr_service

    def run(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        elapsed, confidences, char_accuracies, word_accuracies, exact = [], [], [], [], []
        successful = 0
        for sample in samples:
            start = time.perf_counter()
            try:
                result = self.ocr_service.extract(sample["data"], sample["filename"])
                successful += 1
                elapsed.append(time.perf_counter() - start)
                confidences.append(result["confidence"])
                if sample.get("ground_truth") is not None:
                    truth, output = sample["ground_truth"].strip(), result["raw_text"].strip()
                    char_accuracies.append(max(0.0, 1.0 - edit_distance(truth, output) / max(1, len(truth))))
                    tw, ow = truth.lower().split(), output.lower().split()
                    word_accuracies.append(max(0.0, 1.0 - edit_distance(tw, ow) / max(1, len(tw))))
                    exact.append(float(truth == output))
            except Exception:
                logger.exception("Benchmark sample failed")
        mean = lambda values: round(sum(values) / len(values), 6) if values else None
        return {"success": True, "samples_processed": len(samples), "successful_samples": successful,
                "failed_samples": len(samples) - successful, "average_processing_time": mean(elapsed),
                "average_confidence": mean(confidences), "character_accuracy": mean(char_accuracies),
                "word_accuracy": mean(word_accuracies), "exact_match_accuracy": mean(exact),
                "ground_truth_samples": len(char_accuracies)}
