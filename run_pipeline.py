import os
import argparse
from app.ai.utils.logger import get_logger
from app.ai.utils.config_loader import load_config
from app.ai.pipeline.pipeline_controller import PipelineController
from app.ai.pipeline.batch_processor import BatchProcessor

logger = get_logger("run_pipeline")

def main():
    parser = argparse.ArgumentParser(description="OCR Document Reading System Engine")
    parser.add_argument("--config", type=str, default="config/default.yaml", help="Path to default configuration")
    parser.add_argument("--input", type=str, help="Path to input medical document image file")
    parser.add_argument("--dir", type=str, help="Path to input directory for batch OCR processing")
    parser.add_argument("--output", type=str, help="Path to output JSON file (or directory if using --dir)")
    
    args = parser.parse_args()
    
    if not (args.input or args.dir):
        parser.error("Must provide either --input or --dir")
        
    logger.info("Initializing OCR Document Reading System Engine")
    
    main_config = load_config(args.config) if os.path.exists(args.config) else {}
    prep_cfg_path = "config/preprocessing.yaml"
    if os.path.exists(prep_cfg_path):
        main_config["preprocessing"] = load_config(prep_cfg_path)
        
    if args.input:
        controller = PipelineController(main_config)
        res = controller.process_image(args.input, args.output)
        if res:
            logger.info(f"Processed document successfully: {res.get('document', '')} with overall confidence {res.get('overall_confidence', 0.0)}")
    elif args.dir:
        processor = BatchProcessor(main_config)
        processor.process_directory(args.dir, args.output)

if __name__ == "__main__":
    main()

