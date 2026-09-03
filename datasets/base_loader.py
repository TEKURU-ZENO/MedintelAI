from abc import ABC, abstractmethod
from typing import List, Generator

class BaseLoader(ABC):
    """
    Abstract base class for dataset loaders.
    Ensures all datasets provide a standardized iteration interface.
    """
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        
    @abstractmethod
    def get_files(self) -> List[str]:
        """Returns a list of image file paths in the dataset."""
        pass
        
    def stream_files(self) -> Generator[str, None, None]:
        """Generator yielding file paths."""
        for file in self.get_files():
            yield file
