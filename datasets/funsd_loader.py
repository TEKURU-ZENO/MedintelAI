import os
import json
import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from datasets.base_loader import BaseLoader
from app.ai.utils.logger import get_logger

logger = get_logger(__name__)

class FUNSDLoader(BaseLoader):
    """
    Loader for the FUNSD (Form Understanding in Noisy Scanned Documents) Report Dataset.
    Supports both training (149 forms) and testing (50 forms) splits.
    Extracts structured entities, bounding boxes, entity linking, and word/line level image crops.
    """
    def __init__(self, root_dir: str = "datasets/report dataset"):
        super().__init__(root_dir)
        self.root_path = Path(root_dir)

    def get_files(self, split: Optional[str] = None) -> List[str]:
        """Returns list of image file paths."""
        if not self.root_path.exists():
            logger.warning(f"FUNSD root directory not found: {self.root_dir}")
            return []
            
        splits = [f"{split}_data"] if split else ["training_data", "testing_data"]
        images = []
        for s in splits:
            img_dir = self.root_path / s / "images"
            if img_dir.exists():
                images.extend([str(p) for p in sorted(img_dir.glob("*.png"))])
        return images

    def get_documents(self, split: str = "testing") -> List[Dict[str, Any]]:
        """
        Parses all forms in the specified split.
        Returns metadata, image paths, bounding boxes, labels, and reconstructed ground truth.
        """
        split_dir = self.root_path / f"{split}_data"
        img_dir = split_dir / "images"
        anno_dir = split_dir / "annotations"

        if not img_dir.exists() or not anno_dir.exists():
            logger.warning(f"FUNSD split directory not found: {split_dir}")
            return []

        documents = []
        for img_path in sorted(img_dir.glob("*.png")):
            anno_path = anno_dir / f"{img_path.stem}.json"
            if not anno_path.exists():
                continue

            try:
                with open(anno_path, "r", encoding="utf-8") as f:
                    anno_data = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load annotation {anno_path}: {e}")
                continue

            items = anno_data.get("form", [])
            # Sort items by top-to-bottom, left-to-right
            sorted_items = sorted(items, key=lambda it: (it["box"][1], it["box"][0]))
            
            ground_truth_lines = []
            for it in sorted_items:
                txt = it.get("text", "").strip()
                if txt:
                    ground_truth_lines.append(txt)

            documents.append({
                "id": img_path.stem,
                "image_path": str(img_path),
                "annotation_path": str(anno_path),
                "items": items,
                "ground_truth_text": "\n".join(ground_truth_lines)
            })

        return documents

    def extract_line_crops(self, split: str = "training", max_crops: int = 150) -> List[Dict[str, Any]]:
        """
        Extracts cropped line images with paired text for OCR training / fine-tuning.
        """
        docs = self.get_documents(split=split)
        crops = []

        for doc in docs:
            img = cv2.imread(doc["image_path"])
            if img is None:
                continue
            h_img, w_img = img.shape[:2]

            for item in doc["items"]:
                text = item.get("text", "").strip()
                box = item.get("box", [])
                if not text or len(box) != 4 or len(text) < 3:
                    continue

                x1, y1, x2, y2 = box
                xmin, xmax = max(0, min(x1, x2)), min(w_img, max(x1, x2))
                ymin, ymax = max(0, min(y1, y2)), min(h_img, max(y1, y2))

                if (xmax - xmin) < 20 or (ymax - ymin) < 8:
                    continue

                crop = img[ymin:ymax, xmin:xmax]
                crops.append({
                    "crop": crop,
                    "text": text,
                    "label": item.get("label", "other"),
                    "doc_id": doc["id"]
                })

                if len(crops) >= max_crops:
                    return crops

        return crops