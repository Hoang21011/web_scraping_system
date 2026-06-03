import logging
import os
from datetime import datetime
from dotenv import load_dotenv

# Load .env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

def setup_logger():
    # Ensure logs directory exists
    log_dir_name = os.getenv("LOG_DIR")
    if not log_dir_name:
        raise ValueError("Thiếu biến môi trường LOG_DIR")
    log_dir = log_dir_name if os.path.isabs(log_dir_name) else os.path.join(os.path.dirname(__file__), "..", log_dir_name)
    os.makedirs(log_dir, exist_ok=True)
    
    # Generate log file name based on current time
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"crawler_{timestamp}.log")
    
    # Create logger
    logger = logging.getLogger("CrawlerLogger")
    logger.setLevel(logging.DEBUG)
    
    # File handler (logs all debug and above)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler (logs info and above)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
    return logger

logger = setup_logger()
