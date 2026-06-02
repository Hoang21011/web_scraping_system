from crawler import PaginationOneHousingCrawler
from logger_config import logger

def main():
    logger.info("Starting OneHousing Pagination Crawler (Method 2)...")
    crawler = PaginationOneHousingCrawler()
    
    # Optional: If the API requires specific filters, you can define them here.
    # For example, filtering by a specific project ID or category.
    # extra_payload = {"projectIds": ["cf917354-48bf-11eb-b378-0242ac130002"]}
    extra_payload = None
    
    # We will test crawl with 5 pages max to see if it works.
    crawler.crawl(start_page=0, size=20, extra_payload=extra_payload, max_pages=5)
    
if __name__ == "__main__":
    main()
