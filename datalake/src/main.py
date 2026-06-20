# Databricks notebook source
# MAGIC %pip install python-dotenv duckdb beautifulsoup4 curl-cffi

# COMMAND ----------
import time
from logger_config import logger
from data_manager import DataManager
from html_parser import fetch_html_page, extract_properties_from_html
from api_client import fetch_quick_filter, fetch_project_details, fetch_price_history, fetch_price_chart

import json
from kafka import KafkaProducer

# BÌNH LUẬN SỬA LỖI: Dùng bootstrap_servers (có s), port 29092 (vì file chạy ngoài docker), encode utf-8
producer = KafkaProducer(
    bootstrap_servers=['localhost:29092'], 
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def scrape_properties(data_manager):
    """
    Step 2 & 3: Scrape properties from HTML pages via Pagination
    """
    page = 1
    total_properties_saved = 0
    
    logger.info("--- STARTING STEP 2 & 3: HTML PAGINATION CRAWLER ---")
    while True:
        logger.info(f"Fetching HTML page {page}...")
        html = fetch_html_page(page)
        
        if not html:
            logger.info(f"Page {page} returned nothing. Stopping HTML crawler.")
            break
            
        properties = extract_properties_from_html(html)
        
        if not properties:
            logger.info(f"No properties found on page {page}. End of pages.")
            break
            
        saved_count = data_manager.append_data("properties", properties)
        
        # BÌNH LUẬN SỬA LỖI: Gửi data vào topic_properties, gọi hàm flush() có ngoặc
        producer.send("topic_properties", properties)
        producer.flush()
        
        total_properties_saved += saved_count
        logger.info(f"Page {page}: Saved {saved_count} properties.")
        
        page += 1
        time.sleep(1.5) # Anti-ban sleep

    logger.info(f"HTML Crawler finished. Total properties saved: {total_properties_saved}")

def fetch_projects_and_subdivisions(data_manager):
    """
    Step 4: Fetch detailed projects and subdivisions.
    We get the list of project IDs from quick-filter, skip "thổ cư",
    then call the detailed insight API to get full locations, amenities, and sectors.
    """
    logger.info("--- STARTING STEP 4: FETCH DETAILED PROJECTS & SUBDIVISIONS ---")
    
    qf_data = fetch_quick_filter()
    if not qf_data or "data" not in qf_data:
        logger.error("Failed to fetch quick filter data.")
        return [], []
        
    data = qf_data["data"]
    raw_projects = data.get("property_projects", [])
    
    # Filter out "thổ cư" (residential land)
    valid_projects = [p for p in raw_projects if "thổ cư" not in str(p.get("name", "")).lower()]
    
    detailed_projects = []
    all_subdivisions = []
    
    for base_proj in valid_projects:
        pid = base_proj.get("id")
        if not pid: continue
        
        logger.info(f"Fetching details for Project: {base_proj.get('name')} ({pid})")
        proj_detail_resp = fetch_project_details(pid)
        
        if not proj_detail_resp or "data" not in proj_detail_resp:
            # Fallback to basic info if API fails
            detailed_projects.append(base_proj)
            continue
            
        proj_data = proj_detail_resp["data"]
        
        # 1. Save detailed project
        # We can extract just what we need, or save the whole object
        # Since it contains lots of great info (amenities, location, etc.), we save it all.
        detailed_projects.append(proj_data)
        
        # 2. Extract subdivisions (sectors)
        sectors = proj_data.get("insight_by_sector", [])
        for sector in sectors:
            sector["project_id"] = pid  # Attach foreign key relationship
            all_subdivisions.append(sector)
            
        time.sleep(1.5) # Anti-ban
    
    # Save to disk
    data_manager.append_data("projects", detailed_projects)
    data_manager.append_data("subdivisions", all_subdivisions)
    
    # BÌNH LUẬN SỬA LỖI: Gửi data vào đúng topic, không gửi string rỗng gây lỗi
    producer.send("topic_projects", detailed_projects)
    producer.flush()
    producer.send("topic_subdivisions", all_subdivisions)
    producer.flush()
    
    logger.info(f"Saved {len(detailed_projects)} detailed projects and {len(all_subdivisions)} subdivisions.")
    
    return detailed_projects, all_subdivisions

def fetch_project_pricing(data_manager, projects, subdivisions):
    """
    Step 5: Fetch Price History and Price Chart for projects & subdivisions.
    """
    logger.info("--- STARTING STEP 5: FETCH PROJECT PRICING ---")
    
    # Collect all IDs (projects and subdivisions)
    target_ids = []
    
    for p in projects:
        if "id" in p: target_ids.append(p["id"])
        elif "object_code" in p: target_ids.append(p["object_code"])
        
    for s in subdivisions:
        if "id" in s: target_ids.append(s["id"])
        elif "object_code" in s: target_ids.append(s["object_code"])
        elif "sector_id" in s: target_ids.append(s["sector_id"])
        
    target_ids = list(set(target_ids)) # Deduplicate locally
    
    for pid in target_ids:
        if not pid:
            continue
            
        if data_manager.is_project_visited(pid):
            logger.info(f"Pricing for {pid} already fetched. Skipping.")
            continue
            
        logger.info(f"Fetching pricing for project/subdivision ID: {pid}")
        
        history = fetch_price_history(pid)
        chart = fetch_price_chart(pid)
        
        price_entity = {
            "project_id": pid,
            "price_history": history.get("data", {}) if history else None,
            "price_chart": chart.get("data", {}) if chart else None
        }
        
        data_manager.append_single("project_prices", price_entity)
        
        # BÌNH LUẬN SỬA LỖI: Đẩy cục giá vào topic riêng
        producer.send("topic_project_pricing", price_entity)
        producer.flush()
        
        data_manager.mark_project_visited(pid)
        
        time.sleep(1.5) # Anti-ban sleep

def main():
    logger.info("Starting Hybrid Method Web Scraping System")
    
    data_manager = DataManager()
    
    # Step 2 & 3
    scrape_properties(data_manager)
    
    # Step 4
    projects, subdivisions = fetch_projects_and_subdivisions(data_manager)
    
    # Step 5
    fetch_project_pricing(data_manager, projects, subdivisions)
    
    data_manager.close()
    logger.info("Pipeline Execution Completed.")

if __name__ == "__main__":
    main()
