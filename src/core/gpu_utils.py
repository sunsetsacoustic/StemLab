import torch
from src.utils.logger import logger

def get_gpu_info():
    """
    Returns a tuple (is_available, device_name)
    """
    if torch.cuda.is_available():
        device_name = torch.cuda.get_device_name(0)
        logger.info(f"GPU Detected: {device_name}")
        return True, device_name
    else:
        logger.info("No GPU detected, using CPU.")
        return False, "CPU"
