import os
import json
import time
from api_client import search_properties
from logger_config import logger

class PaginationOneHousingCrawler:
    def __init__(self, data_dir="data"):
        self.data_dir = os.path.join(os.path.dirname(__file__), data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.output_file = os.path.join(self.data_dir, "properties_pagination.jsonl")
        self.saved_ids = self._load_saved_ids()
        
    def _load_saved_ids(self):
        """Load already saved property IDs to prevent duplicates."""
        saved_ids = set()
        if os.path.exists(self.output_file):
            with open(self.output_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        if 'id' in data:
                            saved_ids.add(data['id'])
                        elif 'object_code' in data:
                            saved_ids.add(data['object_code'])
                    except json.JSONDecodeError:
                        pass
        logger.info(f"Loaded {len(saved_ids)} existing items from {self.output_file}")
        return saved_ids

    def save_items(self, items):
        """Save new items to the JSONL file."""
        new_count = 0
        with open(self.output_file, 'a', encoding='utf-8') as f:
            for item in items:
                # API data structure could have 'id' or 'object_code' depending on the exact endpoint
                item_id = item.get('id') or item.get('object_code')
                if item_id and item_id not in self.saved_ids:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
                    self.saved_ids.add(item_id)
                    new_count += 1
        return new_count

    def crawl(self, start_page=0, size=20, extra_payload=None, max_pages=None):
        """
        Main loop to paginate through the search API.
        """
        current_page = start_page
        total_saved = 0
        
        logger.info(f"Starting pagination crawler from page {current_page}...")
        
        while True:
            # Check max pages limit
            if max_pages is not None and current_page >= start_page + max_pages:
                logger.info(f"Reached max pages limit ({max_pages}). Stopping.")
                break
                
            response_data = search_properties(page=current_page, size=size, extra_payload=extra_payload)
            
            if not response_data:
                logger.error(f"Failed to fetch data at page {current_page}. Stopping.")
                break
            
            # Depending on API, items might be under 'data' -> 'items' or directly under 'data'
            # Let's handle both
            items = []
            if isinstance(response_data.get('data'), list):
                items = response_data['data']
            elif isinstance(response_data.get('data'), dict):
                items = response_data['data'].get('items', [])
            else:
                logger.warning(f"Unexpected data format at page {current_page}. Keys: {response_data.keys()}")
                break
                
            if not items:
                logger.info(f"No items found at page {current_page}. We've reached the end.")
                break
                
            new_saved = self.save_items(items)
            total_saved += new_saved
            logger.info(f"Page {current_page}: Found {len(items)} items. Saved {new_saved} new items. Total items in DB: {len(self.saved_ids)}")
            
            # Check if we should stop (e.g. if we fetched fewer items than 'size', it might be the last page)
            if len(items) < size:
                logger.info(f"Fetched {len(items)} items which is less than size {size}. Reached the end.")
                break
                
            current_page += 1
            
            # Anti-ban sleep
            time.sleep(2)
            
        logger.info(f"Crawler finished. Total new items saved this run: {total_saved}")
        return total_saved
