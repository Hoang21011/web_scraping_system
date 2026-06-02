import time
from logger_config import logger
from data_manager import DataManager
from html_parser import fetch_html_page, extract_properties_from_html
from api_client import fetch_quick_filter, fetch_price_history, fetch_price_chart

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
        total_properties_saved += saved_count
        logger.info(f"Page {page}: Saved {saved_count} properties.")
        
        page += 1
        time.sleep(1.5) # Anti-ban sleep

    logger.info(f"HTML Crawler finished. Total properties saved: {total_properties_saved}")

def fetch_projects_and_subdivisions(data_manager):
    """
    Step 4: Fetch projects and subdivisions from quick filter API.
    Skip "thổ cư" (residential land projects).
    """
    logger.info("--- STARTING STEP 4: FETCH PROJECTS & SUBDIVISIONS ---")
    
    qf_data = fetch_quick_filter()
    if not qf_data or "data" not in qf_data:
        logger.error("Failed to fetch quick filter data.")
        return [], []
        
    data = qf_data["data"]
    raw_projects = data.get("property_projects", [])
    raw_subdivisions = data.get("property_sectors", []) # or property_blocks
    
    # Filter out "thổ cư"
    projects = [p for p in raw_projects if "thổ cư" not in str(p.get("name", "")).lower()]
    subdivisions = [s for s in raw_subdivisions if "thổ cư" not in str(s.get("name", "")).lower()]
    
    # Save them
    data_manager.append_data("projects", projects)
    data_manager.append_data("subdivisions", subdivisions)
    
    logger.info(f"Saved {len(projects)} projects and {len(subdivisions)} subdivisions.")
    
    return projects, subdivisions

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
    
    logger.info("Pipeline Execution Completed.")

if __name__ == "__main__":
    main()
