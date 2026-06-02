import os
import json
from curl_cffi import requests
from logger_config import logger
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

# The user can define the API endpoint in .env. By default we use the one they pointed out.
SEARCH_API_URL = os.getenv("SEARCH_API_URL", "https://api.onehousing.vn/onehousing-channel/v1/inventories/search/top-search")

def search_properties(page=0, size=20, extra_payload=None):
    """
    Search properties using Pagination.
    We don't know if the correct API is GET or POST, so we'll allow config or default to GET with query params.
    """
    try:
        # Defaulting to GET for the top-search API the user provided
        # If the API requires POST, user can switch this to requests.post(..., json=payload)
        
        # Build query params
        params = {
            "page": page,
            "size": size
        }
        if extra_payload:
            params.update(extra_payload)
            
        logger.info(f"Fetching page {page} with size {size}...")
        response = requests.get(
            SEARCH_API_URL, 
            params=params,
            headers=headers, 
            impersonate="chrome", 
            timeout=15
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Search API Error {response.status_code}: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Exception during search_properties: {e}")
        return None
