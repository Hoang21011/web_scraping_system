import json
import os
from bs4 import BeautifulSoup
from curl_cffi import requests
from logger_config import logger
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(os.getenv("CONFIG_FILE_PATH"), override=True)
import argparse

# File này dùng để tải html của trang web về

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('--html-scrape-url-template', default=os.getenv("HTML_SCRAPE_URL_TEMPLATE"))
args, _ = parser.parse_known_args()

HTML_SCRAPE_URL_TEMPLATE = args.html_scrape_url_template
if not HTML_SCRAPE_URL_TEMPLATE:
    raise ValueError("Thiếu cấu hình HTML_SCRAPE_URL_TEMPLATE (từ tham số dòng lệnh hoặc .env)")

def fetch_html_page(page_number):
    # Fetch the HTML content for a specific page.
    url = HTML_SCRAPE_URL_TEMPLATE.format(page_number)
    try:
        response = requests.get(url, impersonate="chrome", timeout=15)
        if response.status_code == 200:
            return response.text
        else:
            logger.error(f"Failed to fetch page {page_number}. Status: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Exception fetching page {page_number}: {e}")
        return None

def extract_properties_from_html(html_content):
    # Parse the HTML, find __NEXT_DATA__, and extract properties.
    # Removes large image/video arrays to save space.
    if not html_content:
        return []
    soup = BeautifulSoup(html_content, "html.parser")
    script_tag = soup.find("script", id="__NEXT_DATA__")
    if not script_tag:
        logger.warning("No __NEXT_DATA__ found in the HTML.")
        return []
    try:
        data = json.loads(script_tag.string)
        props = data.get("props", {}).get("pageProps", {})
        properties = []
        
        # In our research, properties were stored inside props['fallback'] values which are lists containing dicts
        if "fallback" in props:
            for k, val in props["fallback"].items():
                if isinstance(val, dict) and "data" in val:
                    # Sometimes data is a list of property objects
                    if isinstance(val["data"], list):
                        properties.extend(val["data"])
                    # Sometimes it's dict with 'items'
                    elif isinstance(val["data"], dict) and "items" in val["data"]:
                        properties.extend(val["data"]["items"])
        # Clean the properties
        cleaned_properties = []
        for prop in properties:
            # We don't filter by Vinhomes anymore based on user feedback.
            # Just remove large media arrays
            for key in ['urls', 'galleries', 'image_urls', 'images']:
                if key in prop:
                    del prop[key]
            cleaned_properties.append(prop)
            
        return cleaned_properties
    except Exception as e:
        logger.error(f"Error parsing __NEXT_DATA__: {e}")
        return []


