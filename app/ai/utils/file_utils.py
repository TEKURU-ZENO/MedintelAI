import os
import glob
from pathlib import Path
from typing import List
from app.ai.utils.logger import get_logger

logger = get_logger(__name__)

def ensure_directory_exists(dir_path: str) -> None:
    """
    Creates a directory if it does not already exist.
    """
    path = Path(dir_path)
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created directory: {dir_path}")

def get_image_files(directory: str, extensions: List[str] = None) -> List[str]:
    """
    Returns a list of image files in a directory (recursively).
    """
    if extensions is None:
        extensions = ['*.png', '*.jpg', '*.jpeg', '*.tif', '*.tiff']
        
    files = []
    path = Path(directory)
    if not path.is_dir():
        logger.warning(f"Directory not found: {directory}")
        return files
        
    for ext in extensions:
        # Recursive search using **
        files.extend(glob.glob(os.path.join(directory, '**', ext), recursive=True))
        files.extend(glob.glob(os.path.join(directory, '**', ext.upper()), recursive=True))
        
    # Deduplicate and sort
    return sorted(list(set(files)))
