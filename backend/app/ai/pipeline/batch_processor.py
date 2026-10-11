import os
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.ai.utils.logger import get_logger
from app.ai.pipeline.pipeline_controller import PipelineController

logger = get_logger(__name__)

class BatchProcessor:
    """
    Handles processing multiple images or datasets.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.controller = PipelineController(config)
        self.max_workers = config.get("pipeline", {}).get("execution", {}).get("batch_size", 4)
        
    def process_directory(self, input_dir: str, output_dir: str = None) -> None:
        """
        Processes all images in a directory.
        """
        logger.info(f"Starting batch process on directory: {input_dir}")
        from app.ai.utils.file_utils import get_image_files
        
        files = get_image_files(input_dir)
        if not files:
            logger.warning(f"No images found in {input_dir}")
            return
            
        self.process_files(files, output_dir)
            
    def process_files(self, file_paths: List[str], output_dir: str = None) -> None:
        """
        Runs the pipeline over a list of files concurrently.
        """
        logger.info(f"Processing {len(file_paths)} files using {self.max_workers} workers.")
        
        success_count = 0
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {}
            for path in file_paths:
                out_path = None
                if output_dir:
                    base = os.path.basename(path)
                    out_path = os.path.join(output_dir, f"{os.path.splitext(base)[0]}.json")
                
                future = executor.submit(self.controller.process_image, path, out_path)
                future_to_file[future] = path
                
            for future in as_completed(future_to_file):
                path = future_to_file[future]
                try:
                    is_success = future.result()
                    if is_success:
                        success_count += 1
                except Exception as exc:
                    logger.error(f"{path} generated an exception: {exc}")
                    
        logger.info(f"Batch processing completed. Successful: {success_count}/{len(file_paths)}")
