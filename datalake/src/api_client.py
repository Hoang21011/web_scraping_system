import os
from curl_cffi import requests
from logger_config import logger
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv("/Volumes/workspace/default/real_estate_data/config.env", override=True)

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://onehousing.vn/",
    "Origin": "https://onehousing.vn",
}

import argparse

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('--project-insights-api', default=os.getenv("PROJECT_INSIGHTS_API"))
parser.add_argument('--quick-filter-api', default=os.getenv("QUICK_FILTER_API"))
args, _ = parser.parse_known_args()

PROJECT_INSIGHTS_API = args.project_insights_api
if not PROJECT_INSIGHTS_API:
    raise ValueError("Thiếu cấu hình PROJECT_INSIGHTS_API (từ tham số dòng lệnh hoặc .env)")

QUICK_FILTER_API = args.quick_filter_api
if not QUICK_FILTER_API:
    raise ValueError("Thiếu cấu hình QUICK_FILTER_API (từ tham số dòng lệnh hoặc .env)")

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

def fetch_project_details(project_id):
    """
    Fetch detailed platform data: Name, Location, Amenities, and Subdivisions.
    """
    url = f"{PROJECT_INSIGHTS_API}/{project_id}"
    try:
        response = requests.get(url, headers=headers, impersonate="chrome", timeout=15)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Project Details API Error {response.status_code} for URL: {url}")
            return None
    except Exception as e:
        logger.error(f"Exception during request to {url}: {e}")
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
