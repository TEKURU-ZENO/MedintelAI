import logging
import sys

def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    Returns a configured logger instance.
    
    Args:
        name (str): The name of the logger (usually __name__).
        level (str): The logging level (e.g., 'INFO', 'DEBUG').
        
    Returns:
        logging.Logger: The configured logger.
    """
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.handlers:
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        logger.setLevel(numeric_level)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Output to stdout
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Prevent propagation to the root logger
        logger.propagate = False
        
    return logger
