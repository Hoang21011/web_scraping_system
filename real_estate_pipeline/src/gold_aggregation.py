# Databricks notebook source
# MAGIC %pip install python-dotenv duckdb beautifulsoup4 curl-cffi

# COMMAND ----------
import duckdb
import os
from dotenv import load_dotenv

load_dotenv()
load_dotenv(os.getenv("CONFIG_FILE_PATH"), override=True)

import argparse

# File này có nhiệm vụ tạo ra các dashboard display trên Databricks

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('--silver-data-dir', default=os.getenv("SILVER_DATA_DIR"))
parser.add_argument('--gold-data-dir', default=os.getenv("GOLD_DATA_DIR"))
args, _ = parser.parse_known_args()

SILVER_DATA_DIR = args.silver_data_dir
if not SILVER_DATA_DIR:
    raise ValueError("Thiếu cấu hình SILVER_DATA_DIR (từ tham số dòng lệnh hoặc .env)")

GOLD_DATA_DIR = args.gold_data_dir
if not GOLD_DATA_DIR:
    raise ValueError("Thiếu cấu hình GOLD_DATA_DIR (từ tham số dòng lệnh hoặc .env)")

def create_gold_layer():
    print("Bắt đầu xử lý dữ liệu Silver -> Gold...")
    
    # Thư mục chứa dữ liệu Silver và Gold
    silver_dir_name = SILVER_DATA_DIR
    silver_dir = silver_dir_name if os.path.isabs(silver_dir_name) else os.path.join(os.path.dirname(__file__), "..", silver_dir_name)

    gold_dir_name = GOLD_DATA_DIR
    gold_dir = gold_dir_name if os.path.isabs(gold_dir_name) else os.path.join(os.path.dirname(__file__), "..", gold_dir_name)
    os.makedirs(gold_dir, exist_ok=True)
    
    # Sử dụng DuckDB in-memory
    conn = duckdb.connect(':memory:')
    
    # Aggregate
    print("Đang tổng hợp dữ liệu Gold: Giá trung bình theo khu vực...")
    
    query = f"""
    CREATE OR REPLACE TABLE gold_price_by_ward AS
    SELECT 
        district, 
        ward,
        COUNT(id) as total_properties,
        AVG(min_selling_price) as avg_min_selling_price,
        AVG(max_selling_price) as avg_max_selling_price,
        MIN(min_selling_price) as lowest_price,
        MAX(max_selling_price) as highest_price
    FROM read_parquet('{os.path.join(silver_dir, "properties.parquet")}')
    WHERE min_selling_price IS NOT NULL
    GROUP BY district, ward
    ORDER BY total_properties DESC
    """
    conn.execute(query)
    
    # Export to Parquet
    parquet_path = os.path.join(gold_dir, 'gold_price_by_ward.parquet')
    print(f"Bảng gold_price_by_ward đã lưu.")
    
    # MARKET OVERVIEW

    print("Đang tổng hợp dữ liệu: gold_property_summary...")
    conn.execute(f"""
    CREATE OR REPLACE TABLE gold_property_summary AS
    SELECT 
        province, district, ward, property_type,
        COUNT(id) as total_supply,
        AVG((min_unit_price + max_unit_price)/2) as avg_unit_price,
        SUM(CASE WHEN urgent_sale THEN 1 ELSE 0 END) as urgent_sale_count,
        SUM(CASE WHEN sell_for_cut_losses THEN 1 ELSE 0 END) as cut_loss_count
    FROM read_parquet('{os.path.join(silver_dir, "properties.parquet")}')
    GROUP BY province, district, ward, property_type
    """)
    conn.execute(f"COPY gold_property_summary TO '{os.path.join(gold_dir, 'gold_property_summary.parquet')}' (FORMAT PARQUET);")

    print("Đang tổng hợp dữ liệu: gold_property_area_bins...")
    conn.execute(f"""
    CREATE OR REPLACE TABLE gold_property_area_bins AS
    SELECT 
        province, district,
        CASE 
            WHEN ((min_area + max_area)/2) < 50 THEN '<50m2'
            WHEN ((min_area + max_area)/2) BETWEEN 50 AND 80 THEN '50-80m2'
            ELSE '>80m2'
        END as area_bin,
        COUNT(id) as total_supply,
        AVG(min_selling_price) as avg_price
    FROM read_parquet('{os.path.join(silver_dir, "properties.parquet")}')
    WHERE min_area IS NOT NULL AND max_area IS NOT NULL
    GROUP BY province, district, area_bin
    """)
    conn.execute(f"COPY gold_property_area_bins TO '{os.path.join(gold_dir, 'gold_property_area_bins.parquet')}' (FORMAT PARQUET);")

    # PRICE TRENDS

    print("Đang tổng hợp dữ liệu: gold_price_history_monthly...")
    conn.execute(f"""
    CREATE OR REPLACE TABLE gold_price_history_monthly AS
    SELECT 
        p.district, pp.year, pp.month,
        AVG(pp.price_average) as avg_price,
        AVG(pp.percent_change) as avg_percent_change
    FROM read_parquet('{os.path.join(silver_dir, "project_prices.parquet")}') pp
    JOIN read_parquet('{os.path.join(silver_dir, "projects.parquet")}') p ON pp.project_id = p.id
    GROUP BY p.district, pp.year, pp.month
    """)
    conn.execute(f"COPY gold_price_history_monthly TO '{os.path.join(gold_dir, 'gold_price_history_monthly.parquet')}' (FORMAT PARQUET);")

    print("Đang tổng hợp dữ liệu: gold_developer_pricing...")
    conn.execute(f"""
    CREATE OR REPLACE TABLE gold_developer_pricing AS
    SELECT 
        developer_name,
        COUNT(id) as total_projects,
        AVG((min_unit_price + max_unit_price)/2) as avg_unit_price,
        MIN(handover_date_from) as min_handover_date,
        MAX(handover_date_from) as max_handover_date
    FROM read_parquet('{os.path.join(silver_dir, "projects.parquet")}')
    WHERE developer_name IS NOT NULL
    GROUP BY developer_name
    """)
    conn.execute(f"COPY gold_developer_pricing TO '{os.path.join(gold_dir, 'gold_developer_pricing.parquet')}' (FORMAT PARQUET);")

    # PROJECT OVERVIEW

    print("Đang tổng hợp dữ liệu: gold_project_quality...")
    conn.execute(f"""
    CREATE OR REPLACE TABLE gold_project_quality AS
    SELECT 
        p.id, p.name, p.district,
        COUNT(a.amenity_id) as amenity_count,
        MAX(p.cstn_dens) as cstn_dens,
        MAX(p.monthly_service_fee) as monthly_service_fee,
        MAX(p.bike_parking_monthly) as bike_parking_monthly,
        MAX(p.car_parking_monthly) as car_parking_monthly
    FROM read_parquet('{os.path.join(silver_dir, "projects.parquet")}') p
    LEFT JOIN read_parquet('{os.path.join(silver_dir, "project_amenities.parquet")}') a ON p.id = a.project_id
    GROUP BY p.id, p.name, p.district
    """)
    conn.execute(f"COPY gold_project_quality TO '{os.path.join(gold_dir, 'gold_project_quality.parquet')}' (FORMAT PARQUET);")

    print("Đang tổng hợp dữ liệu: gold_subdivision_area_boxplot...")
    conn.execute(f"""
    CREATE OR REPLACE TABLE gold_subdivision_area_boxplot AS
    SELECT 
        sector_name,
        MIN(min_area) as min_carpet_area,
        MAX(max_area) as max_carpet_area,
        MEDIAN((min_area + max_area)/2) as median_carpet_area
    FROM read_parquet('{os.path.join(silver_dir, "properties.parquet")}')
    WHERE sector_name IS NOT NULL AND min_area IS NOT NULL AND max_area IS NOT NULL
    GROUP BY sector_name
    """)
    conn.execute(f"COPY gold_subdivision_area_boxplot TO '{os.path.join(gold_dir, 'gold_subdivision_area_boxplot.parquet')}' (FORMAT PARQUET);")

    print("Đang tổng hợp dữ liệu: gold_subdivision_metrics...")
    conn.execute(f"""
    CREATE OR REPLACE TABLE gold_subdivision_metrics AS
    SELECT 
        s.id as subdivision_id, 
        s.name as subdivision_name, 
        s.project_id,
        p.name as project_name,
        p.district,
        p.province,
        (s.min_prop_per_floor + s.max_prop_per_floor)/2.0 as avg_prop_per_floor,
        (s.number_ele_min + s.number_ele_max)/2.0 as avg_ele,
        s.number_living_floor
    FROM read_parquet('{os.path.join(silver_dir, "subdivisions.parquet")}') s
    LEFT JOIN read_parquet('{os.path.join(silver_dir, "projects.parquet")}') p ON s.project_id = p.id
    """)
    conn.execute(f"COPY gold_subdivision_metrics TO '{os.path.join(gold_dir, 'gold_subdivision_metrics.parquet')}' (FORMAT PARQUET);")

    print("Đang tổng hợp dữ liệu: gold_project_handover_timeline...")
    conn.execute(f"""
    CREATE OR REPLACE TABLE gold_project_handover_timeline AS
    SELECT 
        id as project_id, 
        name as project_name, 
        district, 
        province, 
        developer_name, 
        handover_date_from
    FROM read_parquet('{os.path.join(silver_dir, "projects.parquet")}')
    WHERE handover_date_from IS NOT NULL
    ORDER BY handover_date_from ASC
    """)
    conn.execute(f"COPY gold_project_handover_timeline TO '{os.path.join(gold_dir, 'gold_project_handover_timeline.parquet')}' (FORMAT PARQUET);")

    # GEOSPACIAL

    print("Đang tổng hợp dữ liệu: gold_geo_heatmap...")
    conn.execute(f"""
    CREATE OR REPLACE TABLE gold_geo_heatmap AS
    SELECT 
        ROUND(lat, 3) as lat_bin,
        ROUND(long, 3) as long_bin,
        COUNT(id) as property_count,
        AVG(min_selling_price) as avg_price
    FROM read_parquet('{os.path.join(silver_dir, "properties.parquet")}')
    WHERE lat IS NOT NULL AND long IS NOT NULL
    GROUP BY lat_bin, long_bin
    """)
    conn.execute(f"COPY gold_geo_heatmap TO '{os.path.join(gold_dir, 'gold_geo_heatmap.parquet')}' (FORMAT PARQUET);")
    
    print(f"Hoàn thành! Các file Parquet (Gold Layer) đã được lưu tại: {gold_dir}")

if __name__ == "__main__":
    create_gold_layer()
