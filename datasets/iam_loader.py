import os
from typing import List
from datasets.base_loader import BaseLoader
from app.ai.utils.logger import get_logger

logger = get_logger(__name__)

class IAMLoader(BaseLoader):
    """
    Loader for the IAM Handwriting Database.
    Scans the provided directory recursively for images.
    """
    def get_files(self) -> List[str]:
        if not os.path.exists(self.root_dir):
            logger.warning(f"IAM dataset directory not found: {self.root_dir}")
            return []
            
        from app.ai.utils.file_utils import get_image_files
        # The configuration directly points to the 'words' directory
        return get_image_files(self.root_dir)
