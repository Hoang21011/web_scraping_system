# Databricks notebook source
import os
import argparse
from dotenv import load_dotenv
from pyspark.sql import SparkSession    
from pyspark.sql.functions import (
    col, when, lit, lower, regexp_extract, stddev_samp, 
    coalesce, isnan, count
)
from pyspark.sql.window import Window

load_dotenv()
load_dotenv("/Volumes/workspace/default/real_estate_data/config.env", override=True)

# Khởi tạo Spark Session với đầy đủ cấu hình Iceberg cho tầng Gold
spark = SparkSession.builder \
    .appName("feature_engineering_pipeline") \
    .master("spark://spark-master:7077") \
    .config("spark.jars.packages", "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.0,org.apache.hadoop:hadoop-aws:3.3.4,org.postgresql:postgresql:42.6.0") \
    .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
    .config("spark.sql.catalog.iceberg", "org.apache.iceberg.spark.SparkCatalog") \
    .config("spark.sql.catalog.iceberg.type", "jdbc") \
    .config("spark.sql.catalog.iceberg.uri", "jdbc:postgresql://postgres:5432/iceberg_catalog") \
    .config("spark.sql.catalog.iceberg.jdbc.user", "postgres") \
    .config("spark.sql.catalog.iceberg.jdbc.password", "trust") \
    .config("spark.sql.catalog.iceberg.warehouse", "s3a://gold/") \
    .config("spark.sql.catalog.iceberg.io-impl", "org.apache.iceberg.aws.s3.S3FileIO") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
    .config("spark.hadoop.fs.s3a.access.key", os.environ.get("MINIO_ROOT_USER", "admin")) \
    .config("spark.hadoop.fs.s3a.access.secret", os.environ.get("MINIO_ROOT_PASSWORD", "12345678")) \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .getOrCreate()


def run_feature_engineering():  
    print("Bắt đầu Feature Engineering...")
    
    # 1. SQL Join & Aggregate Core Amenities
    try:
        # Tầng silver đang dùng iceberg table nên đọc trực tiếp từ catalog
        spark.table("iceberg.silver.properties").createOrReplaceTempView("silver_properties")
        spark.table("iceberg.silver.projects").createOrReplaceTempView("silver_projects")
        spark.table("iceberg.silver.project_amenities").createOrReplaceTempView("silver_project_amenities")
        spark.table("iceberg.silver.subdivisions").createOrReplaceTempView("silver_subdivisions")
        spark.table("iceberg.silver.project_prices").createOrReplaceTempView("silver_project_prices")
    except Exception as e:
        print("Cảnh báo: Chưa đủ dữ liệu ở tầng silver", e)
        return

    # Câu lệnh query Spark SQL để gom dữ liệu
    query = """
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
        FROM silver_project_amenities
        GROUP BY project_id
    )
    SELECT 
        p.*,
        proj.* EXCLUDE(id, code, name, slug, address, ward, district, district_code, province, province_code, min_selling_price, max_selling_price, min_unit_price, max_unit_price),
        sub.* EXCLUDE(id, type, name, project_id, min_selling_price, max_selling_price, min_unit_price, max_unit_price, developer_name, handover_date_from, handover_date_to, monthly_service_fee, bike_parking_monthly, car_parking_monthly, number_ele_min, number_ele_max, number_basement_min, number_basement_max, min_prop_per_floor, max_prop_per_floor, number_living_floor),
        COALESCE(a.amenity_score, 0) as amenity_score,
        COALESCE(a.core_amenity_score, 0) as core_amenity_score
    FROM silver_properties p
    LEFT JOIN (
        SELECT * FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY id ORDER BY id) as rn FROM silver_projects
        ) WHERE rn = 1
    ) proj ON p.project_id = proj.id
    LEFT JOIN (
        SELECT * FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY id ORDER BY id) as rn FROM silver_subdivisions 
        ) WHERE rn = 1
    ) sub ON p.sector_id = sub.id
    LEFT JOIN proj_amenities_agg a ON p.project_id = a.project_id
    """
    
    print("Executing SQL JOIN...")
    df = spark.sql(query)
    
    # -------------------------------------------------------------
    # SỬ DỤNG PYSPARK FUNCTIONS ĐỂ TẠO FEATURE (THAY VÌ PANDAS)
    # -------------------------------------------------------------
    
    print("Kỹ thuật Nhóm 1...")
    
    # Phân loại phòng ngủ
    df = df.withColumn("bedroom_count", 
        when(col("number_of_bedrooms").isNull() | isnan(col("number_of_bedrooms")), "Unknown")
        .when(col("number_of_bedrooms") == 0, "Studio")
        .when(col("number_of_bedrooms").isin(1, 2), "1-2PN")
        .when(col("number_of_bedrooms") == 3, "3PN")
        .otherwise("Oversized")
    )
    
    # Xếp hạng dự án
    df = df.withColumn("rank", 
        when(lower(col("rank")).like("%cao cấp%"), "Cao cấp")
        .when(lower(col("rank")).like("%trung cấp%"), "Trung cấp")
        .otherwise("Bình dân")
    )
    
    # Hướng cửa sổ (window_direction)
    df = df.withColumn("window_direction", 
        when(lower(col("directions")).like("%đông%"), "Đông")
        .when(lower(col("directions")).like("%tây%"), "Tây")
        .when(lower(col("directions")).like("%nam%"), "Nam")
        .when(lower(col("directions")).like("%bắc%"), "Bắc")
        .otherwise("Khác")
    )
    
    # Demand Code
    df = df.withColumn("is_secondary_only", 
        when(col("demand_code").like("%SECONDARY%") & ~col("demand_code").like("%PRIMARY%"), 1).otherwise(0)
    ).withColumn("has_primary", 
        when(col("demand_code").like("%PRIMARY%"), 1).otherwise(0)
    )
    
    # Bathroom per sqm (Tránh chia cho 0)
    df = df.withColumn("bathroom_per_sqm", 
        when((col("min_area").isNull()) | (col("min_area") == 0), lit(None))
        .otherwise(col("number_of_bathrooms") / col("min_area"))
    )
    
    print("Kỹ thuật Nhóm 2...")
    
    # Furniture status
    df = df.withColumn("furniture_status_encoded", 
        when(lower(col("furniture_status")) == "bàn giao thô", 0)
        .when(lower(col("furniture_status")) == "cơ bản", 1)
        .when(lower(col("furniture_status")) == "liền tường", 2)
        .when(lower(col("furniture_status")) == "đầy đủ", 3)
        .when(lower(col("furniture_status")) == "cao cấp", 4)
        .otherwise(1) # Default
    )
    
    # Giữ nguyên tên cột (Alias)
    df = df.withColumn("view_type", col("views")) \
           .withColumn("floor_bin", col("floor_number")) \
           .withColumn("infra_quality", col("infra_grade"))
    
    print("Kỹ thuật Nhóm 3 (Advanced)...")
    
    # Corner (Góc)
    df = df.withColumn("is_corner", when(lower(col("positions")).like("%góc%"), 1).otherwise(0))
    df = df.withColumn("area_discount_ratio", col("max_area") * col("is_corner"))
    
    # Lấy số từ chuỗi floor_number bằng Regex
    df = df.withColumn("floor_num", regexp_extract(col("floor_number"), r"(\d+)", 1).cast("float"))
    df = df.withColumn("is_special_low_floor", 
        when((col("floor_num") <= 10) & (col("min_unit_price") > 150000000), 1).otherwise(0)
    )
    
    # Mật độ vs Vị trí
    df = df.withColumn("density_vs_location", col("cstn_dens") * col("center_rd_dist"))
    
    # Boutique index (max_prop_per_floor / number_ele_max)
    df = df.withColumn("elev_density", 
        when((col("number_ele_max").isNull()) | (col("number_ele_max") == 0), 0)
        .otherwise(col("max_prop_per_floor") / col("number_ele_max"))
    )
    df = df.withColumn("boutique_index", 
        when(col("elev_density") > 0, 1 / col("elev_density")).otherwise(0)
    )
    
    # Cemetary Penalty
    df = df.withColumn("is_cemetery", 
        when(lower(col("views")).rlike("nghĩa trang|khu mộ"), 1).otherwise(0)
    )
    df = df.withColumn("rank_ordinal", 
        when(col("rank") == "Bình dân", 1)
        .when(col("rank") == "Trung cấp", 2)
        .when(col("rank") == "Cao cấp", 3)
        .otherwise(1)
    )
    df = df.withColumn("cemetery_penalty_interaction", col("is_cemetery") * col("rank_ordinal"))
    
    # Block price volatility (Tính std độ lệch chuẩn của min_selling_price theo sector_id)
    windowSpec = Window.partitionBy("sector_id")
    df = df.withColumn("block_price_volatility", coalesce(stddev_samp("min_selling_price").over(windowSpec), lit(0)))
    
    # Transit
    df = df.withColumn("premium_transit_flag", 
        when((lower(col("local_bus")) == "yes") | (lower(col("central_bus")) == "yes"), 1).otherwise(0)
    )
    
    # Loại BĐS
    property_type_lower = lower(col("property_type"))
    df = df.withColumn("is_shophouse", when(property_type_lower.like("%shophouse%"), 1).otherwise(0))
    df = df.withColumn("commercial_area_multiplier", col("min_area") * col("is_shophouse"))
    
    df = df.withColumn("is_villa", when(property_type_lower.rlike("biệt thự|villa"), 1).otherwise(0))
    df = df.withColumn("ultra_luxury_isolate", when((col("is_villa") == 1) & (col("min_area") > 150), 1).otherwise(0))
    
    df = df.withColumn("micro_investment_flag", when(property_type_lower.like("%officetel%"), 1).otherwise(0))
    
    print("Ghi kết quả ra Iceberg Table và Markdown...")

    # Ghi toàn bộ dữ liệu sạch xuống tầng Gold
    df.write.format("iceberg") \
        .mode("overwrite") \
        .saveAsTable("iceberg.gold.feature_table")
    
    # Rút ngẫu nhiên/hoặc 20 dòng đầu tiên biến về Pandas để in ra Markdown báo cáo
    sample_pd = df.select(
        'id', 'project_name', 'bedroom_count', 'rank', 'window_direction', 
        'area_discount_ratio', 'block_price_volatility', 'amenity_score', 'core_amenity_score'
    ).limit(20).toPandas()
    
    try:
        current_dir = os.path.dirname(__file__)
    except NameError:
        current_dir = os.getcwd()
    md_path = os.path.join(current_dir, "..", "..", "feature_engineering_output.md")
    
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write('# Feature Engineering Final Output (Sample)\n\n')
        f.write('Đây là 20 dòng mẫu từ bảng `iceberg.gold.feature_table` chứa các features đã được tổng hợp bằng PySpark.\n\n')
        f.write('| ID | Tên Dự Án | Số PN | Rank | Hướng Cửa Sổ | Tương Tác Căn Góc | Biến Động Giá (STD) | Điểm Tiện Ích | Điểm Tiện Ích Trọng Số |\n')
        f.write('|----|-----------|-------|------|--------------|-------------------|---------------------|---------------|------------------------|\n')
        for _, row in sample_pd.iterrows():
            # Xử lý format số cho dễ nhìn
            volatility = f"{row['block_price_volatility']:,.0f}" if not pd.isna(row['block_price_volatility']) else "0"
            f.write(f"| {row['id']} | {row['project_name']} | {row['bedroom_count']} | {row['rank']} | {row['window_direction']} | {row['area_discount_ratio']} | {volatility} | {row['amenity_score']} | {row['core_amenity_score']} |\n")
        
    print(f"Hoàn tất! File đã được lưu tại iceberg.gold.feature_table và sample tại {md_path}")

if __name__ == '__main__':
    run_feature_engineering()
