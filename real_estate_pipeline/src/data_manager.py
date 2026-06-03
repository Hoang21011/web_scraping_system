import os
import json
from logger_config import logger
from dotenv import load_dotenv

# Load .env relative to this file
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

class DataManager:
    def __init__(self, data_dir=None):
        if data_dir is None:
            data_dir = os.getenv("BRONZE_DATA_DIR", "/Volumes/main/default/real_estate_data/bronze")
        self.data_dir = os.path.join(os.path.dirname(__file__), data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.files = {
            "properties": os.path.join(self.data_dir, "properties.jsonl"),
            "projects": os.path.join(self.data_dir, "projects.jsonl"),
            "subdivisions": os.path.join(self.data_dir, "subdivisions.jsonl"),
            "project_prices": os.path.join(self.data_dir, "project_prices.jsonl")
        }
        
        self.visited_projects = self._load_visited_projects()

    def _load_visited_projects(self):
        visited = set()
        price_file = self.files["project_prices"]
        if os.path.exists(price_file):
            with open(price_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        # We track project/subdivision visits by their unique ID
                        if 'project_id' in data:
                            visited.add(data['project_id'])
                    except json.JSONDecodeError:
                        pass
        return visited

    def is_project_visited(self, project_id):
        return project_id in self.visited_projects

    def mark_project_visited(self, project_id):
        self.visited_projects.add(project_id)

    def append_data(self, file_key, data_list):
        """
        Append a list of dictionary items to the specified jsonl file.
        """
        if not data_list:
            return 0
            
        file_path = self.files.get(file_key)
        if not file_path:
            logger.error(f"Invalid file key: {file_key}")
            return 0
            
        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                for item in data_list:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
            return len(data_list)
        except Exception as e:
            logger.error(f"Error appending data to {file_key}: {e}")
            return 0

    def append_single(self, file_key, item):
        self.append_data(file_key, [item])
