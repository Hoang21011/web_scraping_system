# Databricks notebook source
# MAGIC %pip install python-dotenv duckdb beautifulsoup4 curl-cffi pandas numpy

# COMMAND ----------
import duckdb
import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv
import argparse

load_dotenv()
load_dotenv("/Volumes/workspace/default/real_estate_data/config.env", override=True)

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

def run_feature_engineering():
    print("Bắt đầu Feature Engineering...")
    
    silver_dir = SILVER_DATA_DIR
    gold_dir = GOLD_DATA_DIR
    os.makedirs(gold_dir, exist_ok=True)
    
    conn = duckdb.connect(':memory:')
    
    # 1. SQL Join & Aggregate Core Amenities
    query = f"""
    WITH proj_amenities_agg AS (
        SELECT 
            project_id,
            COUNT(DISTINCT amenity_id) as amenity_score,
            SUM(CASE 
                WHEN LOWER(amenity_name) LIKE '%xe buýt%' THEN 5
                WHEN LOWER(amenity_name) LIKE '%bệnh viện%' OR LOWER(amenity_name) LIKE '%vinmec%' THEN 5
                WHEN LOWER(amenity_name) LIKE '%trường học%' OR LOWER(amenity_name) LIKE '%vinschool%' THEN 4
                WHEN LOWER(amenity_name) LIKE '%trung tâm thương mại%' OR LOWER(amenity_name) LIKE '%vincom%' THEN 4
                WHEN LOWER(amenity_name) LIKE '%hồ%' OR LOWER(amenity_name) LIKE '%biển%' THEN 3
                WHEN LOWER(amenity_name) LIKE '%công viên%' THEN 2
                WHEN LOWER(amenity_name) LIKE '%sân chơi%' OR LOWER(amenity_name) LIKE '%thể thao%' THEN 1
                ELSE 0 
            END) as core_amenity_score
        FROM read_parquet('{os.path.join(silver_dir, "project_amenities.parquet")}')
        GROUP BY project_id
    ),
    pivoted_prices AS (
        PIVOT (
            SELECT project_id, 'price_' || year || '_' || LPAD(month::VARCHAR, 2, '0') as yyyy_mm, price_average 
            FROM read_parquet('{os.path.join(silver_dir, "project_prices.parquet")}')
        )
        ON yyyy_mm
        USING FIRST(price_average)
        GROUP BY project_id
    )
    SELECT 
        p.*,
        proj.* EXCLUDE(id, code, name, slug, address, ward, district, district_code, province, province_code, min_selling_price, max_selling_price, min_unit_price, max_unit_price),
        sub.* EXCLUDE(id, type, name, project_id, min_selling_price, max_selling_price, min_unit_price, max_unit_price, developer_name, handover_date_from, handover_date_to, monthly_service_fee, bike_parking_monthly, car_parking_monthly, number_ele_min, number_ele_max, number_basement_min, number_basement_max, min_prop_per_floor, max_prop_per_floor, number_living_floor),
        COALESCE(a.amenity_score, 0) as amenity_score,
        COALESCE(a.core_amenity_score, 0) as core_amenity_score,
        pp.* EXCLUDE (project_id)
    FROM read_parquet('{os.path.join(silver_dir, "properties.parquet")}') p
    LEFT JOIN read_parquet('{os.path.join(silver_dir, "projects.parquet")}') proj ON p.project_id = proj.id
    LEFT JOIN read_parquet('{os.path.join(silver_dir, "subdivisions.parquet")}') sub ON p.sector_id = sub.id
    LEFT JOIN proj_amenities_agg a ON p.project_id = a.project_id
    LEFT JOIN pivoted_prices pp ON p.project_id = pp.project_id
    """
    
    print("Executing SQL JOIN...")
    df = conn.execute(query).df()
    
    # 2. Nhóm 1: Feature cần chuyển đổi
    print("Kỹ thuật Nhóm 1...")
    
    def classify_bedroom(x):
        if pd.isna(x): return 'Unknown'
        if x == 0: return 'Studio'
        if x in [1, 2]: return '1-2PN'
        if x == 3: return '3PN'
        return 'Oversized'
    df['bedroom_count'] = df['number_of_bedrooms'].apply(classify_bedroom)
    
    def map_rank(x):
        x = str(x).lower()
        if 'cao cấp' in x: return 'Cao cấp'
        if 'trung cấp' in x: return 'Trung cấp'
        return 'Bình dân'
    df['rank'] = df['rank'].apply(map_rank)
    
    def map_direction(x):
        x = str(x).lower()
        if 'đông' in x: return 'Đông'
        if 'tây' in x: return 'Tây'
        if 'nam' in x: return 'Nam'
        if 'bắc' in x: return 'Bắc'
        return 'Khác'
    df['window_direction'] = df['directions'].apply(map_direction)
    
    df['is_secondary_only'] = df['demand_code'].apply(lambda x: 1 if 'SECONDARY' in str(x) and 'PRIMARY' not in str(x) else 0)
    df['has_primary'] = df['demand_code'].apply(lambda x: 1 if 'PRIMARY' in str(x) else 0)
    
    # Xử lý missing min_area tránh chia 0
    df['bathroom_per_sqm'] = df['number_of_bathrooms'] / df['min_area'].replace(0, np.nan)
    
    # 3. Nhóm 2: Feature giữ nguyên hoặc mã hoá cơ bản
    print("Kỹ thuật Nhóm 2...")
    furniture_map = {'bàn giao thô': 0, 'cơ bản': 1, 'liền tường': 2, 'đầy đủ': 3, 'cao cấp': 4}
    df['furniture_status_encoded'] = df['furniture_status'].str.lower().map(furniture_map).fillna(1)
    
    df['view_type'] = df['views']
    df['floor_bin'] = df['floor_number']
    df['infra_quality'] = df['infra_grade']
    
    # 4. Nhóm 3: Feature phái sinh (Nâng cao)
    print("Kỹ thuật Nhóm 3 (Advanced)...")
    
    df['is_corner'] = df['positions'].str.lower().str.contains('góc').fillna(False).astype(int)
    df['area_discount_ratio'] = df['max_area'] * df['is_corner']
    
    df['floor_num'] = df['floor_number'].astype(str).str.extract(r'(\d+)').astype(float)
    df['is_special_low_floor'] = ((df['floor_num'] <= 10) & (df['min_unit_price'] > 150000000)).astype(int)
    
    df['density_vs_location'] = df['cstn_dens'] * df['center_rd_dist']
    
    # Boutique index (Tránh chia 0 và NA)
    elev_density = df['max_prop_per_floor'] / df['number_ele_max'].replace(0, np.nan)
    elev_density = elev_density.fillna(0)
    df['boutique_index'] = np.where(elev_density > 0, 1 / elev_density, 0)
    
    is_cemetery = df['views'].str.lower().str.contains('nghĩa trang|khu mộ').fillna(False).astype(int)
    rank_ordinal = df['rank'].map({'Bình dân': 1, 'Trung cấp': 2, 'Cao cấp': 3}).fillna(1)
    df['cemetery_penalty_interaction'] = is_cemetery * rank_ordinal
    
    # Block price volatility (Giữ giá trị 0 nếu thiếu mẫu theo yêu cầu)
    std_by_sector = df.groupby('sector_id')['min_selling_price'].transform('std').fillna(0)
    df['block_price_volatility'] = std_by_sector
    
    df['premium_transit_flag'] = ((df['local_bus'].str.upper() == 'YES') | (df['central_bus'].str.upper() == 'YES')).astype(int)
    
    is_shophouse = df['property_type'].str.lower().str.contains('shophouse').fillna(False).astype(int)
    df['commercial_area_multiplier'] = df['min_area'] * is_shophouse
    
    is_villa = df['property_type'].str.lower().str.contains('biệt thự|villa').fillna(False).astype(int)
    df['ultra_luxury_isolate'] = ((is_villa == 1) & (df['min_area'] > 150)).astype(int)
    
    df['micro_investment_flag'] = df['property_type'].str.lower().str.contains('officetel').fillna(False).astype(int)
    
    print("Ghi kết quả ra Parquet và Markdown...")
    output_parquet = os.path.join(gold_dir, 'gold_features.parquet')
    conn.register('df_final', df)
    conn.execute(f"COPY df_final TO '{output_parquet}' (FORMAT PARQUET);")
    
    sample_df = df.head(20)[['id', 'project_name', 'bedroom_count', 'rank', 'window_direction', 'area_discount_ratio', 'block_price_volatility', 'amenity_score', 'core_amenity_score']]
    
    md_path = os.path.join(os.path.dirname(__file__), "..", "..", "feature_engineering_output.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write('# Feature Engineering Final Output (Sample)\n\n')
        f.write('Đây là 20 dòng mẫu từ bảng `gold_features.parquet` chứa các features đã được tổng hợp và thiết kế.\n\n')
        f.write('| ID | Tên Dự Án | Số PN (Phân loại) | Rank | Hướng Cửa Sổ | Tương Tác Căn Góc | Biến Động Giá (STD) | Điểm Tiện Ích | Điểm Tiện Ích Trọng Số |\n')
        f.write('|----|-----------|-------------------|------|--------------|-------------------|---------------------|---------------|------------------------|\n')
        for _, row in sample_df.iterrows():
            f.write(f"| {row['id']} | {row['project_name']} | {row['bedroom_count']} | {row['rank']} | {row['window_direction']} | {row['area_discount_ratio']} | {row['block_price_volatility']:,.0f} | {row['amenity_score']} | {row['core_amenity_score']} |\n")
        
    print(f"Hoàn tất! File đã được lưu tại {output_parquet} và sample tại {md_path}")

if __name__ == '__main__':
    run_feature_engineering()
