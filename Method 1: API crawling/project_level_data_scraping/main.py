import sys
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(__file__))

from crawler import ProjectCrawler
from logger_config import logger

def main():
    logger.info("Starting Project Level Scraper Pipeline...")
    
    try:
        crawler = ProjectCrawler()
        crawler.run()
    except KeyboardInterrupt:
        logger.info("Crawler manually interrupted by user.")
    except Exception as e:
        logger.exception(f"Fatal error running crawler: {e}")

if __name__ == "__main__":
    main()
