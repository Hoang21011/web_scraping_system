import logging
import os
from datetime import datetime
from dotenv import load_dotenv

# Load .env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(os.getenv("CONFIG_FILE_PATH"), override=True)

# File này có nhiệm vụ:
# - Ghi lại các bug 
# - Hiện thị quá trình trên màn hình terminal

import argparse
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('--log-dir', default=os.getenv("LOG_DIR"))
args, _ = parser.parse_known_args()

LOG_DIR = args.log_dir
if not LOG_DIR:
    raise ValueError("Thiếu cấu hình LOG_DIR (từ tham số dòng lệnh hoặc .env)")

def setup_logger():
    # Ensure logs directory exists
    log_dir_name = LOG_DIR
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
