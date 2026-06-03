import duckdb
import os
from dotenv import load_dotenv

load_dotenv()

def create_gold_layer():
    print("Bắt đầu xử lý dữ liệu Silver -> Gold...")
    
    # Thư mục chứa dữ liệu Silver (đầu vào) và Gold (đầu ra)
    silver_dir_name = os.getenv("SILVER_DATA_DIR")
    if not silver_dir_name:
        raise ValueError("Thiếu biến môi trường SILVER_DATA_DIR")
    silver_dir = silver_dir_name if os.path.isabs(silver_dir_name) else os.path.join(os.path.dirname(__file__), "..", silver_dir_name)

    gold_dir_name = os.getenv("GOLD_DATA_DIR")
    if not gold_dir_name:
        raise ValueError("Thiếu biến môi trường GOLD_DATA_DIR")
    gold_dir = gold_dir_name if os.path.isabs(gold_dir_name) else os.path.join(os.path.dirname(__file__), "..", gold_dir_name)
    os.makedirs(gold_dir, exist_ok=True)
    
    # Sử dụng DuckDB in-memory
    conn = duckdb.connect(':memory:')
    
    # Aggregate: Tính giá trung bình, min, max theo Quận/Phường
    print("Đang tổng hợp dữ liệu Gold: Giá trung bình theo khu vực...")
    
    query = """
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
    conn.execute(f"COPY gold_price_by_ward TO '{parquet_path}' (FORMAT PARQUET);")
    
    print(f"Hoàn thành! Các file Parquet (Gold Layer) đã được lưu tại: {gold_dir}")

if __name__ == "__main__":
    create_gold_layer()
