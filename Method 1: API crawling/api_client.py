from curl_cffi import requests
from logger_config import logger
import os
from dotenv import load_dotenv

# Load env variables from root folder
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://onehousing.vn/",
    "Origin": "https://onehousing.vn",
}

SUGGESTION_API = os.getenv("SUGGESTION_API", "https://api.onehousing.vn/onehousing-channel/v1/inventories/search/suggestion")
SIMILAR_PROPERTIES_API = os.getenv("SIMILAR_PROPERTIES_API", "https://api.onehousing.vn/onehousing-channel/v1/inventories/properties")

def get_vinhomes_projects():
    """
    Step 2: Collect Category (Broad Scan)
    Get the list of object_code for all Vinhomes projects.
    """
    url = f"{SUGGESTION_API}?content=Vinhomes"
    try:
        response = requests.get(url, headers=headers, impersonate="chrome", timeout=10)
        if response.status_code == 200:
            data = response.json()
            # The structure might vary, let's extract all object_code if available
            # We assume it's in a list under some key. Let's inspect typical structure if needed.
            # Usually, the data is a list of dictionaries with 'object_code' or 'id'.
            # Based on standard suggestions, it's often a list or dict.
            # We will handle extraction carefully. For now, let's return the raw JSON and parse it in the crawler.
            return data
        else:
            logger.error(f"Failed to fetch Vinhomes projects. Status: {response.status_code}, Body: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Exception during get_vinhomes_projects: {e}")
        return None

def get_similar_properties(inventory_id):
    """
    Step 5: Call API & Bypass Security
    Get similar properties for a given inventory ID.
    """
    url = f"{SIMILAR_PROPERTIES_API}/{inventory_id}/similar"
    try:
        response = requests.get(url, headers=headers, impersonate="chrome", timeout=10)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 400:
            logger.warning(f"ID {inventory_id} returned 400 (not in verified listing).")
            return None
        elif response.status_code == 404:
            logger.warning(f"ID {inventory_id} returned 404. Blocked or not found.")
            return None
        else:
            logger.error(f"ID {inventory_id} returned status {response.status_code}: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Exception during get_similar_properties for ID {inventory_id}: {e}")
        return None
