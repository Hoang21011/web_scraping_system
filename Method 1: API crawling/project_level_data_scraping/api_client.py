import json
import os
from dotenv import load_dotenv
from curl_cffi import requests
from logger_config import logger

# Load env variables from root folder
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

SUGGESTION_API = os.getenv("SUGGESTION_API", "https://api.onehousing.vn/onehousing-channel/v1/inventories/search/suggestion")
PROJECT_INSIGHTS_API = os.getenv("PROJECT_INSIGHTS_API", "https://api.onehousing.vn/onehousing-channel/v1/insights/projects")

def make_request(url):
    """
    Helper function to make requests using curl_cffi with impersonate.
    """
    try:
        response = requests.get(
            url,
            impersonate="chrome",
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"API Error {response.status_code} for URL: {url}")
            return None
    except Exception as e:
        logger.error(f"Exception during request to {url}: {e}")
        return None

def get_vinhomes_projects():
    """
    Step 1: Get list of Vinhomes projects.
    Returns: list of dicts (or dict containing list)
    """
    url = f"{SUGGESTION_API}?content=Vinhomes"
    return make_request(url)

def get_project_insights(project_id):
    """
    Step 4: Get general info & subdivisions
    """
    url = f"{PROJECT_INSIGHTS_API}/{project_id}"
    return make_request(url)

def get_project_price_history(project_id):
    """
    Step 5: Get price history
    Requires POST method with empty json body.
    """
    url = f"{PROJECT_INSIGHTS_API}/{project_id}/price-history"
    try:
        response = requests.post(url, json={}, impersonate="chrome", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Price History API Error {response.status_code} for URL: {url}")
            return None
    except Exception as e:
        logger.error(f"Exception during request to {url}: {e}")
        return None

def get_project_price_chart(project_id):
    """
    Step 6: Get price chart
    Requires POST method with empty json body.
    """
    url = f"{PROJECT_INSIGHTS_API}/{project_id}/price-chart"
    try:
        response = requests.post(url, json={}, impersonate="chrome", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Price Chart API Error {response.status_code} for URL: {url}")
            return None
    except Exception as e:
        logger.error(f"Exception during request to {url}: {e}")
        return None

def get_project_surrounding(project_id, lat=None, lng=None):
    """
    Step 7: Get surrounding amenities
    Use latCdnt and longCdnt if provided.
    """
    url = f"{PROJECT_INSIGHTS_API}/surrounding?page=0&size=20"
    if lat and lng:
        url += f"&latCdnt={lat}&longCdnt={lng}"
    else:
        url += f"&projectId={project_id}"
        
    return make_request(url)
