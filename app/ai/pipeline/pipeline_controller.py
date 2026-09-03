import os
import json
from typing import Dict, Any

from app.ai.utils.logger import get_logger
from app.ai.utils.image_io import load_image
from app.ai.preprocessing.preprocessing_pipeline import run_preprocessing_pipeline
from app.ai.ocr.ocr_engine import MedIntelOCREngine

logger = get_logger(__name__)

class PipelineController:
    """
    Coordinates MedIntel Medical Document OCR processing for single and batch images.
    """
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.preprocess_config = self.config.get("preprocessing", {})
        self.ocr_engine = MedIntelOCREngine()
        self.output_dir = "outputs/json"
        
    def process_image(self, image_path: str, output_path: str = None) -> Dict[str, Any]:
        """
        Runs document preprocessing and OCR extraction on a given image.
        
        Args:
            image_path (str): Path to input image file.
            output_path (str): Path to save structured output JSON.
            
        Returns:
            Dict[str, Any]: Structured MedIntel OCR JSON output.
        """
        logger.info(f"Processing document image: {image_path}")
        image_id = os.path.basename(image_path)
        
        if output_path is None:
            output_path = os.path.join(self.output_dir, f"{os.path.splitext(image_id)[0]}.json")
            
        image = load_image(image_path, grayscale=False)
        if image is None:
            logger.error(f"Failed to load image from {image_path}")
            return None
            
        try:
            # 1. OpenCV Medical Document Preprocessing
            clean_image = run_preprocessing_pipeline(image, self.preprocess_config)
            
            # 2. Hybrid OCR Extraction
            ocr_result = self.ocr_engine.process_document(clean_image, doc_name=image_id)
            
            # 3. Save Structured JSON Output
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(ocr_result, f, indent=2)
                
            logger.info(f"Successfully processed OCR and saved JSON to {output_path}")
            return ocr_result
        except Exception as e:
            logger.error(f"OCR Pipeline failed for {image_path}: {e}")
            return None

