import os
from typing import List
from datasets.base_loader import BaseLoader
from app.ai.utils.logger import get_logger

logger = get_logger(__name__)

class CvlLoader(BaseLoader):
    """
    Loader for the CVL Database.
    Scans trainset and testset folders.
    """
    def get_files(self) -> List[str]:
        if not os.path.exists(self.root_dir):
            logger.warning(f"CVL directory not found: {self.root_dir}")
            return []
            
        from app.ai.utils.file_utils import get_image_files
        
        all_files = []
        train_dir = os.path.join(self.root_dir, 'trainset')
        test_dir = os.path.join(self.root_dir, 'testset')
        
        if os.path.exists(train_dir):
            all_files.extend(get_image_files(train_dir))
            
        if os.path.exists(test_dir):
            all_files.extend(get_image_files(test_dir))
            
        if not all_files:
            # Fallback to recursively scanning the root if subfolders aren't found
            all_files = get_image_files(self.root_dir)
            
        return all_files
