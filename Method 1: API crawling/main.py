import sys
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(__file__))

from crawler import BFSOneHousingCrawler
from logger_config import logger

def main():
    # Các hạt giống mà user cung cấp để quét BFS
    SEED_IDS = ["DZAII9", "MAAXVL", "5W0OGE"]
    
    # Số lượng mục tiêu
    TARGET_COUNT = None
    
    # File lưu trữ dữ liệu
    RESUME_FILE = os.path.join(os.path.dirname(__file__), "data", "properties_data.jsonl")
    
    logger.info("Khởi tạo Crawler với thuật toán BFS...")
    try:
        crawler = BFSOneHousingCrawler(seed_ids=SEED_IDS, target_count=TARGET_COUNT, resume_file=RESUME_FILE)
        crawler.run()
    except KeyboardInterrupt:
        logger.info("Crawler manually interrupted by user.")
    except Exception as e:
        logger.exception(f"Fatal error running crawler: {e}")

if __name__ == "__main__":
    main()
