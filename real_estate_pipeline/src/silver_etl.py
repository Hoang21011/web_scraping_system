# Databricks notebook source
# MAGIC %pip install python-dotenv duckdb beautifulsoup4 curl-cffi

# COMMAND ----------
import duckdb
import os
from dotenv import load_dotenv

load_dotenv()
load_dotenv("/Volumes/workspace/default/real_estate_data/config.env", override=True)

import argparse

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('--silver-data-dir', default=os.getenv("SILVER_DATA_DIR"))
parser.add_argument('--bronze-data-dir', default=os.getenv("BRONZE_DATA_DIR"))
args, _ = parser.parse_known_args()

SILVER_DATA_DIR = args.silver_data_dir
if not SILVER_DATA_DIR:
    raise ValueError("Thiếu cấu hình SILVER_DATA_DIR (từ tham số dòng lệnh hoặc .env)")

BRONZE_DATA_DIR = args.bronze_data_dir
if not BRONZE_DATA_DIR:
    raise ValueError("Thiếu cấu hình BRONZE_DATA_DIR (từ tham số dòng lệnh hoặc .env)")

def create_silver_layer():
    silver_dir_name = SILVER_DATA_DIR
    silver_dir = silver_dir_name if os.path.isabs(silver_dir_name) else os.path.join(os.path.dirname(__file__), "..", silver_dir_name)
    os.makedirs(silver_dir, exist_ok=True)
    
    bronze_dir_name = BRONZE_DATA_DIR
    bronze_dir = bronze_dir_name if os.path.isabs(bronze_dir_name) else os.path.join(os.path.dirname(__file__), "..", bronze_dir_name)
    
    # Sử dụng DuckDB in-memory engine thay vì file vật lý
    conn = duckdb.connect(':memory:')
    
    print("Bắt đầu xử lý dữ liệu Bronze -> Silver...")
    
    # ---------------------------------------------------------
    # 1. Bảng silver_properties
    # ---------------------------------------------------------
    print("Đang xử lý silver_properties...")
    query_properties = f"""
    CREATE OR REPLACE TABLE silver_properties AS
    SELECT 
        id::VARCHAR as id, project_id::VARCHAR as project_id, block_id::VARCHAR as block_id, sector_id::VARCHAR as sector_id, project_name, block_name, sector_name,
        province_code, district_code, province, district, ward_code, ward, inventory_code,
        array_to_string(directions, ', ') as directions,
        array_to_string(property_type, ', ') as property_type,
        property_group, property_code,
        geolocation.lat_cdnt::DOUBLE as lat,
        geolocation.long_cdnt::DOUBLE as long,
        number_of_bedrooms, number_of_bedrooms_displays, classify,
        min_selling_price::BIGINT as min_selling_price,
        max_selling_price::BIGINT as max_selling_price,
        min_unit_price::BIGINT as min_unit_price,
        max_unit_price::BIGINT as max_unit_price,
        min_area::DOUBLE as min_area,
        max_area::DOUBLE as max_area,
        array_to_string(views, ', ') as views,
        is_liked, good_price, urgent_sale,
        property_furnitures.furniture_status as furniture_status,
        status,
        array_to_string(facade_directions, ', ') as facade_directions,
        available_for_sale_status,
        view_count.count::INT as view_count,
        floor_number,
        array_to_string(positions, ', ') as positions,
        sell_for_cut_losses,
        strftime(to_timestamp(last_modified_date::BIGINT / 1000), '%d-%m-%Y') as last_modified_date,
        number_of_bathrooms[1] as number_of_bathrooms
    FROM read_json_auto('{os.path.join(bronze_dir, "properties*.jsonl")}');
    """
    
    conn.execute(query_properties)
    
    # Chuyển dữ liệu sang Pandas DataFrame để thực hiện Preprocessing chuyên sâu
    import pandas as pd
    df_properties = conn.execute("SELECT * FROM silver_properties").df()
    
    # ---------------------------------------------------------
    # DATA PREPROCESSING & CLEANING (PANDAS)
    # ---------------------------------------------------------
    print("Đang thực hiện Data Preprocessing cho properties...")
    
    # 5. Handling Missing Values: Loại bỏ các hàng thiếu giá hoặc diện tích
    df_properties = df_properties.dropna(subset=['min_selling_price', 'min_area', 'views'])
    
    # 1. Text Standardization: Xóa khoảng trắng và viết hoa chữ cái đầu (chỉ với project_name)
    df_properties['project_name'] = df_properties['project_name'].str.strip().str.title()
    
    # 2. Data Cleaning (Sửa lỗi chính tả trên toàn bộ DataFrame)
    df_properties = df_properties.replace('High-quanlity', 'High-quality', regex=True)
    df_properties = df_properties.replace('High-Quanlity', 'High-Quality', regex=True)
    
    # 3. Categorical Binning & View Cleaning
    import re
    import unicodedata
    def clean_and_categorize_view(v):
        if pd.isna(v) or str(v).strip() == '':
            return 'Không Xác Định'
            
        # Ép về chữ thường, chuẩn hóa Unicode (NFC) và xóa khoảng trắng trước khi thay thế
        v = unicodedata.normalize('NFC', str(v))
        v = v.lower().strip()
        
        # Sửa lỗi chữ sai dấu cứng
        v = v.replace('nôi khu', 'nội khu')
        v = v.replace('nộii khu', 'nội khu')
        
        # Với phần ngoại khu, lấy nội dung trong ngoặc, bỏ chữ "ngoại khu"
        # VD: "ngoại khu (hồ bơi)" -> "hồ bơi"
        v = re.sub(r'ngoại khu\s*\((.*?)\)', r'\1', v)
        
        # Gộp các giá trị lặp Nghĩa trang / Khu mộ
        if 'nghĩa trang' in v or 'khu mộ' in v:
            return 'Nghĩa Trang / Khu Mộ'
            
        # Kiểm tra chuỗi vô nghĩa, đơn lẻ (VD: "k", "k, k", ký tự rác)
        # Bỏ qua các ký tự không phải chữ số và xem độ dài
        v_clean = re.sub(r'[^\w]', '', v)
        if len(v_clean) <= 1 or v_clean.strip('k') == '':
            return 'Khác'
            
        # Gom nhóm danh mục (Categorical Binning) - Ưu tiên các view giá trị cao
        if 'hồ' in v: return 'Hồ'
        if 'công viên' in v: return 'Công Viên'
        if 'thành phố' in v: return 'Thành Phố'
        if 'trường học' in v: return 'Trường Học'
        if 'nội khu' in v: return 'Nội Khu'
        
        # Loại bỏ các giá trị bị lặp do nối chuỗi (VD: "đất trống, đất trống" -> "đất trống")
        items = [x.strip() for x in v.split(',')]
        seen = set()
        unique_items = []
        for item in items:
            if item and item not in seen:
                seen.add(item)
                unique_items.append(item)
        v = ', '.join(unique_items)
        
        # Cuối cùng mới .title() lại để tránh lỗi ký tự đặc biệt như I/I
        return v.title()
        
    df_properties['views'] = df_properties['views'].apply(clean_and_categorize_view)
    
    # Đưa lại vào DuckDB và xuất ra Parquet
    conn.register('df_properties_cleaned', df_properties)
    conn.execute(f"COPY df_properties_cleaned TO '{os.path.join(silver_dir, 'properties.parquet')}' (FORMAT PARQUET);")

    
    # ---------------------------------------------------------
    # 2. Bảng silver_projects
    # ---------------------------------------------------------
    print("Đang xử lý silver_projects...")
    query_projects = f"""
    CREATE OR REPLACE TABLE silver_projects AS
    SELECT
        id::VARCHAR as id, code, name, slug, address, ward, district, district_code, province, province_code,
        center_rd_dist::DOUBLE as center_rd_dist,
        min_selling_price::BIGINT as min_selling_price,
        max_selling_price::BIGINT as max_selling_price,
        min_unit_price::BIGINT as min_unit_price,
        max_unit_price::BIGINT as max_unit_price,
        blocks::INT as blocks,
        cstn_dens::DOUBLE as cstn_dens,
        swim_dens, local_bus, central_bus, developer_name, rank, handover_date,
        try_cast(handover_date_from as DATE) as handover_date_from,
        try_cast(construction_start_date_from as DATE) as construction_start_date_from,
        number_living_floor::DOUBLE as number_living_floor,
        number_ele[1]::DOUBLE as number_ele_min,
        number_ele[2]::DOUBLE as number_ele_max,
        number_basement[1]::DOUBLE as number_basement_min,
        number_basement[2]::DOUBLE as number_basement_max,
        min_prop_per_floor::INT as min_prop_per_floor,
        max_prop_per_floor::INT as max_prop_per_floor,
        green_dens::DOUBLE as green_dens, trans_grade, infra_grade, school_grade,
        array_to_string(demand_code, ', ') as demand_code,
        description, population::INT as population, population_density::DOUBLE as population_density,
        lat_cdnt::DOUBLE as lat, long_cdnt::DOUBLE as long,
        array_to_string(channel_code, ', ') as channel_code,
        monthly_service_fee[1]::DOUBLE as monthly_service_fee,
        bike_parking_monthly[1]::DOUBLE as bike_parking_monthly,
        car_parking_monthly[1]::DOUBLE as car_parking_monthly,
        sort_index::INT as sort_index,
        total_area::DOUBLE as total_area,
        insight_type, selling_property_count::INT as selling_property_count, has_price
    FROM read_json_auto('{os.path.join(bronze_dir, "projects*.jsonl")}');
    """
    conn.execute(query_projects)
    conn.execute(f"COPY silver_projects TO '{os.path.join(silver_dir, 'projects.parquet')}' (FORMAT PARQUET);")

    # Tách bảng chiều tiện ích của dự án
    print("Đang xử lý silver_project_amenities...")
    query_proj_amenities = f"""
    CREATE OR REPLACE TABLE silver_project_amenities AS
    SELECT 
        id::VARCHAR as project_id,
        COALESCE(a.id::VARCHAR, q.id::VARCHAR) as amenity_id,
        COALESCE(a.name, q.name) as amenity_name,
        q.code as amenity_code
    FROM read_json_auto('{os.path.join(bronze_dir, "projects*.jsonl")}'), 
    UNNEST(quality_indexes) AS t(q)
    LEFT JOIN UNNEST(q.attributes) AS t2(a) ON true
    WHERE q.parent_type = 'PROJECT';
    """
    conn.execute(query_proj_amenities)
    conn.execute(f"COPY silver_project_amenities TO '{os.path.join(silver_dir, 'project_amenities.parquet')}' (FORMAT PARQUET);")

    # ---------------------------------------------------------
    # 3. Bảng silver_subdivisions
    # ---------------------------------------------------------
    print("Đang xử lý silver_subdivisions...")
    query_subdivisions = f"""
    CREATE OR REPLACE TABLE silver_subdivisions AS
    SELECT
        type, sector_id::VARCHAR as id, sector_name as name, project_id::VARCHAR as project_id,
        min_selling_price::BIGINT as min_selling_price,
        max_selling_price::BIGINT as max_selling_price,
        min_unit_price::BIGINT as min_unit_price,
        max_unit_price::BIGINT as max_unit_price,
        developer_name, 
        try_cast(handover_date_from as DATE) as handover_date_from,
        try_cast(handover_date_to as DATE) as handover_date_to,
        monthly_service_fee[1]::DOUBLE as monthly_service_fee,
        bike_parking_monthly[1]::DOUBLE as bike_parking_monthly,
        car_parking_monthly[1]::DOUBLE as car_parking_monthly,
        number_ele[1]::DOUBLE as number_ele_min,
        number_ele[2]::DOUBLE as number_ele_max,
        number_basement[1]::DOUBLE as number_basement_min,
        number_basement[2]::DOUBLE as number_basement_max,
        min_prop_per_floor::INT as min_prop_per_floor,
        max_prop_per_floor::INT as max_prop_per_floor,
        number_living_floor::DOUBLE as number_living_floor
    FROM read_json_auto('{os.path.join(bronze_dir, "subdivisions*.jsonl")}');
    """
    conn.execute(query_subdivisions)
    conn.execute(f"COPY silver_subdivisions TO '{os.path.join(silver_dir, 'subdivisions.parquet')}' (FORMAT PARQUET);")

    # ---------------------------------------------------------
    # 4. Bảng silver_project_prices (Chuẩn hóa Time Series)
    # ---------------------------------------------------------
    print("Đang xử lý silver_project_prices (Time Series)...")
    query_prices = f"""
    CREATE OR REPLACE TABLE silver_project_prices AS
    SELECT 
        project_id::VARCHAR as project_id,
        pc.unit::INT as month,
        pc.year::INT as year,
        pc.price_average::DOUBLE as price_average,
        pc.percent::DOUBLE as percent_change
    FROM read_json_auto('{os.path.join(bronze_dir, "project_prices*.jsonl")}'), UNNEST(price_history.value) AS t(pc)
    ORDER BY project_id, year ASC, month ASC;
    """
    conn.execute(query_prices)
    conn.execute(f"COPY silver_project_prices TO '{os.path.join(silver_dir, 'project_prices.parquet')}' (FORMAT PARQUET);")
    
    print(f"Hoàn thành! Các file Parquet (Silver Layer) đã được lưu tại: {silver_dir}")
    conn.close()

if __name__ == "__main__":
    create_silver_layer()
