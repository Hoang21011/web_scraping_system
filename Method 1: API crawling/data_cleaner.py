from logger_config import logger
import json

def parse_vinhomes_project_ids(raw_data):
    """
    Parses the suggestion API response to extract project IDs.
    Returns a set of project IDs.
    """
    project_ids = set()
    try:
        # Handle cases where raw_data might be a string due to double-encoded JSON
        if isinstance(raw_data, str):
            raw_data = json.loads(raw_data)

        # Assuming data structure from suggestion API has a list of items
        # We need to explore the exact structure, but typically:
        # data might be a list or a dict containing lists.
        # Let's handle the case if it's a list directly or has a 'data' key.
        if isinstance(raw_data, dict) and 'data' in raw_data and 'projects' in raw_data['data']:
            items = raw_data['data']['projects']
        elif isinstance(raw_data, list):
            items = raw_data
        else:
            items = []
            
        for item in items:
            # We look for something identifying it as a project. 
            # In OneHousing suggestion API, project_id or object_code might be present.
            obj_code = item.get('object_code') or item.get('id')
            if obj_code:
                project_ids.add(obj_code)
                
        logger.info(f"Extracted {len(project_ids)} Vinhomes project IDs from suggestions.")
    except Exception as e:
        logger.error(f"Error parsing Vinhomes project IDs: {e}")
        
    return project_ids

def clean_and_filter_properties(properties_data, vinhomes_project_ids=None):
    """
    Step 3 & Step 6: Filter by project_id and remove heavy fields.
    Returns a tuple: (cleaned_properties_list, new_inventory_codes_list)
    """
    cleaned_properties = []
    new_inventory_codes = []
    
    if not properties_data:
        return cleaned_properties, new_inventory_codes
        
    try:
        # The similar properties API returns a list under data or directly as a list
        if isinstance(properties_data, dict) and 'data' in properties_data:
            items = properties_data['data']
        elif isinstance(properties_data, list):
            items = properties_data
        else:
            items = []
            
        for item in items:
            project_id = item.get('project_id')
            
            # Step 3: Filter by project_id (if vinhomes_project_ids is provided and not empty)
            if vinhomes_project_ids and project_id not in vinhomes_project_ids:
                continue
                
            # Step 6: Remove heavy fields
            keys_to_remove = [k for k in item.keys() if 'url' in k.lower() or 'gallery' in k.lower() or 'galleries' in k.lower()]
            for k in keys_to_remove:
                item.pop(k, None)
                
            # Collect cleaned data
            cleaned_properties.append(item)
            
            # Step 7: Extract new inventory codes
            # The id is usually under 'inventory_code' or 'id'
            inv_code = item.get('inventory_code') or item.get('id')
            # OneHousing API usually has 'inventory_code' like 'PUMQJ3' and 'id' like a UUID. The similar API uses inventory_code or ID? 
            # The URL uses inventory_code e.g. 7LVMFB. We need to extract inventory_code.
            if item.get('inventory_code'):
                new_inventory_codes.append(item.get('inventory_code'))
            elif item.get('id') and len(str(item.get('id'))) < 10: # Just a heuristic if inventory_code is missing
                new_inventory_codes.append(item.get('id'))
                
    except Exception as e:
        logger.error(f"Error cleaning properties: {e}")
        
    return cleaned_properties, new_inventory_codes
