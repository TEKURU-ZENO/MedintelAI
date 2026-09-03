import yaml
from pathlib import Path
from typing import Dict, Any
from app.ai.utils.logger import get_logger

logger = get_logger(__name__)

def load_config(filepath: str) -> Dict[str, Any]:
    """
    Loads a YAML configuration file.
    
    Args:
        filepath (str): The path to the YAML file.
        
    Returns:
        Dict[str, Any]: The loaded configuration dictionary.
    """
    path = Path(filepath)
    if not path.is_file():
        logger.error(f"Configuration file not found: {filepath}")
        raise FileNotFoundError(f"Missing config file: {filepath}")
        
    with open(path, 'r', encoding='utf-8') as f:
        try:
            config = yaml.safe_load(f)
            logger.info(f"Successfully loaded configuration from {filepath}")
            return config if config is not None else {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file {filepath}: {e}")
            raise
