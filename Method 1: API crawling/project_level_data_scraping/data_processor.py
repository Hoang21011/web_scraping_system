import os
import json
from logger_config import logger

class DataProcessor:
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Define output files
        self.files = {
            "projects": os.path.join(self.data_dir, "projects.jsonl"),
            "project_price": os.path.join(self.data_dir, "project_price.jsonl"),
            "sectors": os.path.join(self.data_dir, "sectors.jsonl"),
            "surrounding": os.path.join(self.data_dir, "surrounding.jsonl"),
        }
        
    def _save_to_jsonl(self, table_name, data_list):
        """
        Appends a list of dicts to a specific jsonl file.
        If data_list is a single dict, converts to list.
        """
        if not data_list:
            return
            
        if isinstance(data_list, dict):
            data_list = [data_list]
            
        file_path = self.files.get(table_name)
        if not file_path:
            logger.error(f"Unknown table name: {table_name}")
            return
            
        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                for item in data_list:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Error saving to {table_name}.jsonl: {e}")

    def process_project_insights(self, project_id, insights_data):
        """
        Processes API 1 data.
        Separates into projects and sections tables.
        """
        if not insights_data:
            return
            
        try:
            # Check structure. Usually data is inside 'data' key or root
            data = insights_data.get('data', insights_data)
            
            # Extract sections if present
            sections = data.pop('insight_by_sector', []) or data.pop('subdivisions', []) or data.pop('sections', [])
            
            # Save project general info
            project_info = data.copy()
            project_info['project_id'] = project_id
            self._save_to_jsonl("projects", project_info)
            
            # Save sections
            section_records = []
            for sec in sections:
                if isinstance(sec, dict):
                    sec['project_id'] = project_id
                    section_records.append(sec)
            
            self._save_to_jsonl("sectors", section_records)
            
        except Exception as e:
            logger.error(f"Error processing project insights for {project_id}: {e}")

    def process_price_history(self, project_id, history_data):
        """
        Processes API 2 data.
        """
        if not history_data:
            return
            
        try:
            data = history_data.get('data', history_data)
            # Create a record combining project_id and the history data
            record = {
                "project_id": project_id,
                "data_type": "history",
                "price_data": data
            }
            self._save_to_jsonl("project_price", record)
        except Exception as e:
            logger.error(f"Error processing price history for {project_id}: {e}")

    def process_price_chart(self, project_id, chart_data):
        """
        Processes API 3 data.
        """
        if not chart_data:
            return
            
        try:
            data = chart_data.get('data', chart_data)
            # Create a record combining project_id and the chart data
            record = {
                "project_id": project_id,
                "data_type": "chart",
                "price_data": data
            }
            self._save_to_jsonl("project_price", record)
        except Exception as e:
            logger.error(f"Error processing price chart for {project_id}: {e}")

    def process_surrounding(self, project_id, surrounding_data):
        """
        Processes API 4 data.
        """
        if not surrounding_data:
            return
            
        try:
            data = surrounding_data.get('data', surrounding_data)
            if not data:
                logger.warning(f"No surrounding data for {project_id}")
                return
                
            # Surrounding data is usually a list of items (schools, hospitals, etc.)
            if isinstance(data, list):
                records = []
                for item in data:
                    item['project_id'] = project_id
                    records.append(item)
                self._save_to_jsonl("surrounding", records)
            else:
                record = data.copy() if isinstance(data, dict) else {"content": data}
                record['project_id'] = project_id
                self._save_to_jsonl("surrounding", record)
        except Exception as e:
            logger.error(f"Error processing surrounding for {project_id}: {e}")
