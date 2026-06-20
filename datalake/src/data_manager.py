import os
import json
from logger_config import logger
from dotenv import load_dotenv

# Load .env relative to this file
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv("/Volumes/workspace/default/real_estate_data/config.env", override=True)

import argparse

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('--bronze-data-dir', default=os.getenv("BRONZE_DATA_DIR"))
args, _ = parser.parse_known_args()

BRONZE_DATA_DIR = args.bronze_data_dir
if not BRONZE_DATA_DIR:
    raise ValueError("Thiếu cấu hình BRONZE_DATA_DIR (từ tham số dòng lệnh hoặc .env)")

class DataManager:
    def __init__(self, data_dir=None):
        if data_dir is None:
            data_dir = BRONZE_DATA_DIR
        self.data_dir = data_dir if os.path.isabs(data_dir) else os.path.join(os.path.dirname(__file__), "..", data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        
        import time
        self.run_id = time.strftime("%Y%m%d_%H%M%S")
        self.file_handles = {}
        
        self.files = {
            "properties": os.path.join(self.data_dir, f"properties_{self.run_id}.jsonl"),
            "projects": os.path.join(self.data_dir, f"projects_{self.run_id}.jsonl"),
            "subdivisions": os.path.join(self.data_dir, f"subdivisions_{self.run_id}.jsonl"),
            "project_prices": os.path.join(self.data_dir, f"project_prices_{self.run_id}.jsonl")
        }
        
        self.visited_projects = self._load_visited_projects()

    def _load_visited_projects(self):
        visited = set()
        import glob
        pattern = os.path.join(self.data_dir, "project_prices*.jsonl")
        for price_file in glob.glob(pattern):
            if os.path.exists(price_file):
                try:
                    with open(price_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            try:
                                data = json.loads(line)
                                if 'project_id' in data:
                                    visited.add(data['project_id'])
                            except json.JSONDecodeError:
                                pass
                except Exception as e:
                    logger.error(f"Error reading {price_file}: {e}")
        return visited

    def _get_handle(self, file_key):
        if file_key not in self.file_handles:
            self.file_handles[file_key] = open(self.files[file_key], 'w', encoding='utf-8')
        return self.file_handles[file_key]

    def is_project_visited(self, project_id):
        return project_id in self.visited_projects

    def mark_project_visited(self, project_id):
        self.visited_projects.add(project_id)

    def append_data(self, file_key, data_list):
        """
        Append a list of dictionary items to the specified jsonl file.
        Uses a long-lived file handle in 'w' mode to avoid Databricks 'Illegal seek' append errors.
        """
        if not data_list:
            return 0
            
        if file_key not in self.files:
            logger.error(f"Invalid file key: {file_key}")
            return 0
            
        try:
            f = self._get_handle(file_key)
            for item in data_list:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
            f.flush()
            return len(data_list)
        except Exception as e:
            logger.error(f"Error appending data to {file_key}: {e}")
            return 0

    def append_single(self, file_key, item):
        self.append_data(file_key, [item])

    def close(self):
        for f in self.file_handles.values():
            try:
                f.close()
            except Exception:
                pass
