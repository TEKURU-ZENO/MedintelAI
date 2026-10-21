import numpy as np

def compute_horizontal_projection(image: np.ndarray) -> np.ndarray:
    """
    Computes the horizontal projection profile (sum of pixel values along each row).
    Expects a binary image where text is 255.
    
    Args:
        image (np.ndarray): Binary image.
        
    Returns:
        np.ndarray: 1D array of row sums.
    """
    # Summing across columns to get a value per row
    profile = np.sum(image, axis=1)
    return profile

def compute_vertical_projection(image: np.ndarray) -> np.ndarray:
    """
    Computes the vertical projection profile (sum of pixel values along each column).
    Expects a binary image where text is 255.
    
    Args:
        image (np.ndarray): Binary image.
        
    Returns:
        np.ndarray: 1D array of column sums.
    """
    # Summing across rows to get a value per column
    profile = np.sum(image, axis=0)
    return profile
