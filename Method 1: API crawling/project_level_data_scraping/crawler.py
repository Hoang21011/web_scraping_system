import time
from collections import deque
from logger_config import logger
from api_client import (
    get_vinhomes_projects, 
    get_project_insights, 
    get_project_price_history, 
    get_project_price_chart, 
    get_project_surrounding
)
from data_processor import DataProcessor

class ProjectCrawler:
    def __init__(self):
        self.project_queue = deque()
        self.visited_projects = set()
        self.processor = DataProcessor()
        
    def init_seed_list(self):
        """
        Step 1: Get list of Vinhomes projects from suggestion API.
        Extract object_codes (project IDs).
        """
        logger.info("Initializing Seed List with Vinhomes projects...")
        raw_data = get_vinhomes_projects()
        
        if not raw_data:
            logger.error("Failed to get Vinhomes projects suggestion. Crawler cannot start.")
            return False
            
        try:
            data = raw_data.get('data', {}) if isinstance(raw_data, dict) else {}
            # Based on OneHousing suggestion API structure, projects are inside data -> projects
            items = data.get('projects', [])
            
            for item in items:
                # Extract project ID
                obj_code = item.get('object_code') or item.get('id')
                if obj_code:
                    self.project_queue.append(obj_code)
                    
            logger.info(f"Successfully extracted {len(self.project_queue)} Vinhomes projects for the queue.")
            return True
        except Exception as e:
            logger.error(f"Error parsing seed list: {e}")
            return False

    def process_single_project(self, project_id):
        """
        Step 4 to 7: Calls APIs sequentially and saves data.
        """
        logger.info(f"Processing Project ID: {project_id}")
        
        # Step 4: Insights
        insights_data = get_project_insights(project_id)
        self.processor.process_project_insights(project_id, insights_data)
        time.sleep(1) # Sleep to avoid Cloudflare/Rate limit
        
        # Extract lat/lng for surrounding
        lat, lng = None, None
        if insights_data:
            data = insights_data.get('data', {})
            lat = data.get('lat_cdnt')
            lng = data.get('long_cdnt')
        
        # Step 5: Price History
        history_data = get_project_price_history(project_id)
        self.processor.process_price_history(project_id, history_data)
        time.sleep(1)
        
        # Step 6: Price Chart
        chart_data = get_project_price_chart(project_id)
        self.processor.process_price_chart(project_id, chart_data)
        time.sleep(1)
        
        # Step 7: Surrounding
        surrounding_data = get_project_surrounding(project_id, lat=lat, lng=lng)
        self.processor.process_surrounding(project_id, surrounding_data)
        time.sleep(1)
        
        logger.info(f"Finished processing Project ID: {project_id}")

    def run(self):
        """
        Main loop for crawler.
        """
        start_time = time.time()
        
        if not self.init_seed_list():
            return
            
        # Optional: Limit number of projects to run for testing if needed
        # But user requested "hãy lấy tất cả thông tin" (get all), so we will run the entire queue.
        total_projects = len(self.project_queue)
        projects_processed = 0
        
        while self.project_queue:
            project_id = self.project_queue.popleft()
            
            # Step 2 & 3: Check visited
            if project_id in self.visited_projects:
                continue
                
            self.visited_projects.add(project_id)
            
            logger.info(f"Progress: {projects_processed}/{total_projects}")
            self.process_single_project(project_id)
            projects_processed += 1
            
        end_time = time.time()
        logger.info(f"Project Level Crawler Finished! Processed {projects_processed} projects in {end_time - start_time:.2f} seconds.")
