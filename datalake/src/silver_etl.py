# Databricks notebook source
import os
from dotenv import load_dotenv
from pyspark.sql import SparkSession

load_dotenv()
load_dotenv("/Volumes/workspace/default/real_estate_data/config.env", override=True)

# Khởi tạo Spark Session tích hợp Iceberg
spark = SparkSession.builder \
    .appName("silver_etl_pyspark") \
    .master("spark://spark-master:7077") \
    .config("spark.jars.packages", "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.0,org.apache.hadoop:hadoop-aws:3.3.4,org.postgresql:postgresql:42.6.0") \
    .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
    .config("spark.sql.catalog.iceberg", "org.apache.iceberg.spark.SparkCatalog") \
    .config("spark.sql.catalog.iceberg.type", "jdbc") \
    .config("spark.sql.catalog.iceberg.uri", "jdbc:postgresql://postgres:5432/iceberg_catalog") \
    .config("spark.sql.catalog.iceberg.jdbc.user", "postgres") \
    .config("spark.sql.catalog.iceberg.jdbc.password", "trust") \
    .config("spark.sql.catalog.iceberg.warehouse", "s3a://silver/") \
    .config("spark.sql.catalog.iceberg.io-impl", "org.apache.iceberg.aws.s3.S3FileIO") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
    .config("spark.hadoop.fs.s3a.access.key", os.environ.get("MINIO_ROOT_USER", "admin")) \
    .config("spark.hadoop.fs.s3a.access.secret", os.environ.get("MINIO_ROOT_PASSWORD", "12345678")) \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .getOrCreate()

def create_silver_layer():
    print("Bắt đầu xử lý dữ liệu Bronze -> Silver bằng PySpark...")

    # Đọc RAW JSON từ Bronze MinIO. Hàm read.json của Spark sẽ TỰ ĐỘNG INFER SCHEMA!
    try:
        spark.read.json("s3a://bronze/raw_properties").createOrReplaceTempView("bronze_properties")
        spark.read.json("s3a://bronze/raw_projects").createOrReplaceTempView("bronze_projects")
        spark.read.json("s3a://bronze/raw_subdivisions").createOrReplaceTempView("bronze_subdivisions")
        spark.read.json("s3a://bronze/raw_pricing").createOrReplaceTempView("bronze_pricing")
    except Exception as e:
        print("Cảnh báo: Chưa có đủ dữ liệu ở bucket bronze trên MinIO.", e)
        return

    # ---------------------------------------------------------
    # 1. Bảng silver_properties
    # ---------------------------------------------------------
    print("Đang xử lý silver_properties...")
    query_properties = """
    SELECT 
        CAST(id AS STRING) as id, CAST(project_id AS STRING) as project_id, CAST(block_id AS STRING) as block_id, CAST(sector_id AS STRING) as sector_id, project_name, block_name, sector_name,
        province_code, district_code, province, district, ward_code, ward, inventory_code,
        array_join(directions, ', ') as directions,
        array_join(property_type, ', ') as property_type,
        property_group, property_code,
        CAST(geolocation.lat_cdnt AS DOUBLE) as lat,
        CAST(geolocation.long_cdnt AS DOUBLE) as long,
        number_of_bedrooms, number_of_bedrooms_displays, classify,
        CAST(min_selling_price AS BIGINT) as min_selling_price,
        CAST(max_selling_price AS BIGINT) as max_selling_price,
        CAST(min_unit_price AS BIGINT) as min_unit_price,
        CAST(max_unit_price AS BIGINT) as max_unit_price,
        CAST(min_area AS DOUBLE) as min_area,
        CAST(max_area AS DOUBLE) as max_area,
        array_join(views, ', ') as views,
        is_liked, good_price, urgent_sale,
        property_furnitures.furniture_status as furniture_status,
        status,
        array_join(facade_directions, ', ') as facade_directions,
        available_for_sale_status,
        CAST(view_count.count AS INT) as view_count,
        floor_number,
        array_join(positions, ', ') as positions,
        sell_for_cut_losses,
        timestamp_seconds(CAST(last_modified_date AS BIGINT) / 1000) as last_modified_date,
        element_at(number_of_bathrooms, 1) as number_of_bathrooms
    FROM bronze_properties
    """
    df_silver_properties = spark.sql(query_properties)
    df_silver_properties.write.format("iceberg").mode("overwrite").saveAsTable("iceberg.silver.properties")
    
    # ---------------------------------------------------------
    # 2. Bảng silver_projects
    # ---------------------------------------------------------
    print("Đang xử lý silver_projects...")
    query_projects = """
    SELECT
        CAST(id AS STRING) as id, code, name, slug, address, ward, district, district_code, province, province_code,
        CAST(center_rd_dist AS DOUBLE) as center_rd_dist,
        CAST(min_selling_price AS BIGINT) as min_selling_price,
        CAST(max_selling_price AS BIGINT) as max_selling_price,
        CAST(min_unit_price AS BIGINT) as min_unit_price,
        CAST(max_unit_price AS BIGINT) as max_unit_price,
        CAST(blocks AS INT) as blocks,
        CAST(cstn_dens AS DOUBLE) as cstn_dens,
        swim_dens, local_bus, central_bus, developer_name, rank, handover_date,
        CAST(handover_date_from AS DATE) as handover_date_from,
        CAST(construction_start_date_from AS DATE) as construction_start_date_from,
        CAST(number_living_floor AS DOUBLE) as number_living_floor,
        CAST(element_at(number_ele, 1) AS DOUBLE) as number_ele_min,
        CAST(element_at(number_ele, 2) AS DOUBLE) as number_ele_max,
        CAST(element_at(number_basement, 1) AS DOUBLE) as number_basement_min,
        CAST(element_at(number_basement, 2) AS DOUBLE) as number_basement_max,
        CAST(min_prop_per_floor AS INT) as min_prop_per_floor,
        CAST(max_prop_per_floor AS INT) as max_prop_per_floor,
        CAST(green_dens AS DOUBLE) as green_dens, trans_grade, infra_grade, school_grade,
        array_join(demand_code, ', ') as demand_code,
        description, CAST(population AS INT) as population, CAST(population_density AS DOUBLE) as population_density,
        CAST(lat_cdnt AS DOUBLE) as lat, CAST(long_cdnt AS DOUBLE) as long,
        array_join(channel_code, ', ') as channel_code,
        CAST(element_at(monthly_service_fee, 1) AS DOUBLE) as monthly_service_fee,
        CAST(element_at(bike_parking_monthly, 1) AS DOUBLE) as bike_parking_monthly,
        CAST(element_at(car_parking_monthly, 1) AS DOUBLE) as car_parking_monthly,
        CAST(sort_index AS INT) as sort_index,
        CAST(total_area AS DOUBLE) as total_area,
        insight_type, CAST(selling_property_count AS INT) as selling_property_count, has_price
    FROM bronze_projects
    """
    df_silver_projects = spark.sql(query_projects)
    df_silver_projects.write.format("iceberg").mode("overwrite").saveAsTable("iceberg.silver.projects")

    # Tách bảng chiều tiện ích của dự án
    print("Đang xử lý silver_project_amenities...")
    query_proj_amenities = """
    SELECT 
        CAST(id AS STRING) as project_id,
        CAST(q.id AS BIGINT) as amenity_id,
        q.name as amenity_name,
        q.code as amenity_code
    FROM bronze_projects LATERAL VIEW explode(quality_indexes) t AS q
    WHERE q.parent_type = 'PROJECT'
    """
    df_silver_proj_amenities = spark.sql(query_proj_amenities)
    df_silver_proj_amenities.write.format("iceberg").mode("overwrite").saveAsTable("iceberg.silver.project_amenities")

    # ---------------------------------------------------------
    # 3. Bảng silver_subdivisions
    # ---------------------------------------------------------
    print("Đang xử lý silver_subdivisions...")
    query_subdivisions = """
    SELECT
        type, CAST(sector_id AS STRING) as id, sector_name as name, CAST(project_id AS STRING) as project_id,
        CAST(min_selling_price AS BIGINT) as min_selling_price,
        CAST(max_selling_price AS BIGINT) as max_selling_price,
        CAST(min_unit_price AS BIGINT) as min_unit_price,
        CAST(max_unit_price AS BIGINT) as max_unit_price,
        developer_name, 
        CAST(handover_date_from AS DATE) as handover_date_from,
        CAST(handover_date_to AS DATE) as handover_date_to,
        CAST(element_at(monthly_service_fee, 1) AS DOUBLE) as monthly_service_fee,
        CAST(element_at(bike_parking_monthly, 1) AS DOUBLE) as bike_parking_monthly,
        CAST(element_at(car_parking_monthly, 1) AS DOUBLE) as car_parking_monthly,
        CAST(element_at(number_ele, 1) AS DOUBLE) as number_ele_min,
        CAST(element_at(number_ele, 2) AS DOUBLE) as number_ele_max,
        CAST(element_at(number_basement, 1) AS DOUBLE) as number_basement_min,
        CAST(element_at(number_basement, 2) AS DOUBLE) as number_basement_max,
        CAST(min_prop_per_floor AS INT) as min_prop_per_floor,
        CAST(max_prop_per_floor AS INT) as max_prop_per_floor,
        CAST(number_living_floor AS DOUBLE) as number_living_floor
    FROM bronze_subdivisions
    """
    df_silver_subdivisions = spark.sql(query_subdivisions)
    df_silver_subdivisions.write.format("iceberg").mode("overwrite").saveAsTable("iceberg.silver.subdivisions")
    
    # ---------------------------------------------------------
    # 4. Bảng silver_project_prices (Chuẩn hóa Time Series)
    # ---------------------------------------------------------
    print("Đang xử lý silver_project_prices (Time Series)...")
    # Phải check data schema thực tế của giá để bung mảng (UNNEST) cho chuẩn, dùng explode thay vì unnest
    query_prices = """
    SELECT 
        CAST(project_id AS STRING) as project_id,
        CAST(pc.unit AS INT) as month,
        CAST(pc.year AS INT) as year,
        CAST(pc.price_average AS DOUBLE) as price_average,
        CAST(pc.percent AS DOUBLE) as percent_change
    FROM bronze_pricing LATERAL VIEW explode(price_history.value) t AS pc
    """
    df_silver_pricing = spark.sql(query_prices)
    df_silver_pricing.write.format("iceberg").mode("overwrite").saveAsTable("iceberg.silver.project_prices")
    
    print("Hoàn thành! Các bảng Iceberg (Silver Layer) đã được lưu thành công!")

if __name__ == "__main__":
    create_silver_layer()
