import os
from typing import List
from datasets.base_loader import BaseLoader
from app.ai.utils.logger import get_logger

logger = get_logger(__name__)

class InternalLoader(BaseLoader):
    """
    Loader for proprietary internal datasets.
    """
    def get_files(self) -> List[str]:
        if not os.path.exists(self.root_dir):
            logger.warning(f"Internal dataset directory not found: {self.root_dir}")
            return []
            
        from app.ai.utils.file_utils import get_image_files
        return get_image_files(self.root_dir)
