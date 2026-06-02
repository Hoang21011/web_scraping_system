import os
import json
import time
import random
from collections import deque
from logger_config import logger
from api_client import get_vinhomes_projects, get_similar_properties
from data_cleaner import parse_vinhomes_project_ids, clean_and_filter_properties

class BFSOneHousingCrawler:
    def __init__(self, seed_ids: list, target_count=500, resume_file=None):
        self.seed_ids = seed_ids
        self.target_count = target_count
        self.queue = deque(self.seed_ids if seed_ids else [])
        self.visited_ids = set()
        self.vinhomes_project_ids = set()
        self.saved_ids = set()
        
        # Prepare data directory
        self.data_dir = os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.output_file = os.path.join(self.data_dir, f"properties_{int(time.time())}.jsonl")
        
        if resume_file and os.path.exists(resume_file):
            logger.info(f"Resuming from {resume_file}...")
            self.output_file = resume_file
            try:
                with open(resume_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if not line.strip():
                            continue
                        item = json.loads(line)
                        prop_id = item.get('inventory_code') or item.get('id')
                        if prop_id:
                            self.saved_ids.add(prop_id)
                            # Seed queue with previously saved IDs to continue BFS
                            if prop_id not in self.queue:
                                self.queue.append(prop_id)
                logger.info(f"Loaded {len(self.saved_ids)} existing properties.")
            except Exception as e:
                logger.error(f"Error loading resume file: {e}")
                
        self.total_saved = len(self.saved_ids)

    def init_projects_filter(self):
        """
        Step 2: Collect Category and build filter
        """
        logger.info("Initializing Vinhomes project filter...")
        raw_data = get_vinhomes_projects()
        if raw_data:
            self.vinhomes_project_ids = parse_vinhomes_project_ids(raw_data)
            logger.info(f"Loaded {len(self.vinhomes_project_ids)} Vinhomes projects.")
        else:
            logger.warning("Failed to get Vinhomes projects. Proceeding without filter or will retry later.")
            # Depending on strictness, we might want to stop here.
            # But suggestion API sometimes returns different formats. We proceed for now.
    
    def save_item(self, item):
        """
        Step 8: Export Standardized Data
        Append item as JSON line.
        """
        try:
            with open(self.output_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
            self.total_saved += 1
        except Exception as e:
            logger.error(f"Error saving item: {e}")

    def run(self):
        """
        Main BFS pipeline loop
        """
        logger.info(f"Starting BFS Crawler with Seed IDs: {self.seed_ids}, Target: {self.target_count}")
        start_time = time.time()
        
        self.init_projects_filter()
        
        while self.queue and (self.target_count is None or self.total_saved < self.target_count):
            # Step 4: Check Duplicates
            current_id = self.queue.popleft()
            
            if current_id in self.visited_ids:
                continue
                
            self.visited_ids.add(current_id)
            logger.info(f"Processing ID: {current_id} | Queue size: {len(self.queue)} | Saved: {self.total_saved}/{self.target_count}")
            
            # Step 5: Call API & Bypass Security
            properties_data = get_similar_properties(current_id)
            
            # Sleep 1-2 seconds
            sleep_time = random.uniform(1.0, 2.0)
            time.sleep(sleep_time)
            
            if not properties_data:
                continue
                
            # Step 6 & 7: Clean Data and Expand Queue
            cleaned_props, new_ids = clean_and_filter_properties(
                properties_data, 
                vinhomes_project_ids=self.vinhomes_project_ids if self.vinhomes_project_ids else None
            )
            
            # Step 7 (Expand)
            for nid in new_ids:
                if nid not in self.visited_ids:
                    self.queue.append(nid)
            
            # Step 8 (Save)
            for prop in cleaned_props:
                # We need to make sure we don't save duplicates as well
                prop_id = prop.get('inventory_code') or prop.get('id')
                if prop_id in self.saved_ids:
                    continue
                    
                # If we want to strictly stop at target_count:
                if self.target_count is not None and self.total_saved >= self.target_count:
                    break
                    
                self.save_item(prop)
                self.saved_ids.add(prop_id)
                
        end_time = time.time()
        logger.info(f"Crawler finished. Total saved: {self.total_saved}. Time taken: {end_time - start_time:.2f} seconds.")
        logger.info(f"Data saved to {self.output_file}")
