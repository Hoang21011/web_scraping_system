import os
from curl_cffi import requests
from logger_config import logger
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://onehousing.vn/",
    "Origin": "https://onehousing.vn",
}

PROJECT_INSIGHTS_API = os.getenv("PROJECT_INSIGHTS_API", "https://api.onehousing.vn/onehousing-channel/v1/insights/projects")
QUICK_FILTER_API = "https://api.onehousing.vn/onehousing-channel/v1/inventories/search/quick-filter?fetch_all=true"

def fetch_quick_filter():
    """
    Fetch projects and subdivisions from the quick filter API.
    """
    try:
        response = requests.post(QUICK_FILTER_API, json={}, headers=headers, impersonate="chrome", timeout=15)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Quick Filter API Error {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Exception during fetch_quick_filter: {e}")
        return None

def fetch_price_history(project_id):
    """
    Fetch price history for a specific project/subdivision ID.
    """
    url = f"{PROJECT_INSIGHTS_API}/{project_id}/price-history"
    try:
        response = requests.post(url, json={}, headers=headers, impersonate="chrome", timeout=15)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Price History API Error {response.status_code} for URL: {url}")
            return None
    except Exception as e:
        logger.error(f"Exception during request to {url}: {e}")
        return None

def fetch_price_chart(project_id):
    """
    Fetch price chart for a specific project/subdivision ID.
    """
    url = f"{PROJECT_INSIGHTS_API}/{project_id}/price-chart"
    try:
        response = requests.post(url, json={}, headers=headers, impersonate="chrome", timeout=15)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Price Chart API Error {response.status_code} for URL: {url}")
            return None
    except Exception as e:
        logger.error(f"Exception during request to {url}: {e}")
        return None
