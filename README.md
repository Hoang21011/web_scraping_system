# 🏗️ Real Estate Data Lakehouse (Medallion Architecture)

Đây là một hệ thống Data Lakehouse hoàn chỉnh được xây dựng để thu thập (crawl), xử lý, kiểm định chất lượng và lưu trữ dữ liệu Bất động sản. Dự án áp dụng chuẩn kiến trúc **Medallion (Bronze -> Silver -> Gold)** và được tự động hóa hoàn toàn từ đầu tới cuối.

## 🌟 Kiến trúc & Công nghệ (Tech Stack)

Hệ thống được thiết kế theo tư duy hiện đại, tách biệt hoàn toàn giữa việc lưu trữ (Storage) và tính toán (Compute), tận dụng tối đa các công nghệ mã nguồn mở hàng đầu:

*   **Lưu trữ (Storage):** [MinIO](https://min.io/) (S3-compatible Object Storage) thay thế cho HDFS/AWS S3.
*   **Định dạng bảng (Table Format):** [Apache Iceberg](https://iceberg.apache.org/) mang đến khả năng Time-travel, ACID transaction trực tiếp trên Data Lake.
*   **Xử lý dữ liệu (Compute Engine):** [Apache Spark](https://spark.apache.org/) (PySpark) đóng vai trò là "Cỗ máy cày" xử lý lượng lớn dữ liệu cho các bước ETL.
*   **Truy vấn (Query Engine):** [Trino](https://trino.io/) giúp truy vấn SQL siêu tốc trực tiếp trên các file Parquet của Iceberg.
*   **Sổ hộ khẩu (Catalog):** **PostgreSQL** đóng vai trò là JDBC Catalog duy nhất, quản lý metadata cho toàn bộ Iceberg.
*   **Điều phối (Orchestration):** [Apache Airflow](https://airflow.apache.org/) quản lý lập lịch, theo dõi và điều phối toàn bộ các luồng Data Pipelines.
*   **Kiểm định chất lượng (Data Quality):** [Great Expectations](https://greatexpectations.io/) (v1.0+) chốt chặn, kiểm tra rác trước khi đẩy dữ liệu vào báo cáo.
*   **Message Broker (Event Streaming):** **Apache Kafka** & **Zookeeper**.
*   **Cơ sở hạ tầng:** Toàn bộ được đóng gói bằng **Docker Compose**.

---

## 🗺️ Luồng xử lý dữ liệu (Data Flow)

Dự án áp dụng chặt chẽ kiến trúc **Medallion**:

1.  **🟤 Tầng Bronze (Raw Data):** 
    *   Mã nguồn `main.py` thực hiện Crawl dữ liệu thô.
    *   Dữ liệu được đẩy qua Kafka và ghi thẳng xuống bucket `bronze` trên MinIO dưới dạng file JSON/HTML gốc.
2.  **⚪ Tầng Silver (Cleansed Data):** 
    *   Script `silver_etl.py` (PySpark) đọc dữ liệu từ Bronze, làm sạch, ép kiểu dữ liệu (Schema enforcement) và lưu dưới định dạng Apache Iceberg vào bucket `silver`.
    *   **Data Quality Gate:** Script `gx_checkpoint.py` (Great Expectations) sẽ quét bảng Silver. Nếu phát hiện rác (ví dụ: `id` bị Null, `price` bị âm), luồng ETL sẽ lập tức dừng lại và báo còi (Discord/Email Alert).
3.  **🟡 Tầng Gold (Feature / Aggregation Data):** 
    *   Nếu dữ liệu sạch, script `feature_engineering.py` (PySpark) sẽ được chạy để tạo các đặc trưng (Features) phục vụ cho Machine Learning hoặc tính toán Aggregation cho các Dashboard Báo cáo, lưu vào bảng Iceberg tại bucket `gold`.

---

## 🤖 Tự động hóa bằng Airflow (DAGs)

Hệ thống được tự động hóa bằng 3 luồng DAGs trong thư mục `dags/`:

*   **`dag_etl_pipeline.py` (Daily):** Luồng chính kích hoạt tuần tự: `Crawl` -> `Silver ETL` -> `GX Quality Check` -> `Gold ETL`.
*   **`iceberg_maintenance.py` (Monthly):** Dọn dẹp rác (Orphan files) và xóa các Snapshot cũ (Expire Snapshots) của Iceberg để giải phóng dung lượng ổ cứng MinIO.
*   **`dag_bronze_compaction.py` (Monthly):** Gom nén hàng nghìn file JSON nhỏ xíu sinh ra từ quá trình Streaming thành các file nén `.tar.gz` để lưu trữ dài hạn (Archive) giúp MinIO không bị quá tải.

---

## 🚀 Hướng dẫn khởi chạy (How to run)

### 1. Khởi động hạ tầng Docker
Yêu cầu máy tính đã cài đặt Docker và Docker Compose. Tại thư mục gốc của dự án, chạy lệnh:
```bash
docker-compose up -d
```
Lệnh này sẽ khởi động toàn bộ Cluster bao gồm: MinIO, Postgres, Kafka, Zookeeper, Spark Master/Worker, Trino, và Airflow.

### 2. Truy cập các giao diện quản trị (UI)
*   **MinIO (Storage):** `http://localhost:9001` (Quản lý các file vật lý).
*   **Airflow (Orchestration):** `http://localhost:8080` (hoặc `8081` tùy config) -> Bật (Toggle) các DAGs để hệ thống tự động chạy.
*   **Spark UI (Giám sát Job):** `http://localhost:8080` (Của Spark Master).

### 3. Truy vấn dữ liệu (Querying)
Sử dụng các công cụ SQL (như DBeaver, DataGrip) để kết nối vào **Trino** tại cổng `8080` (không cần username/password đặc biệt).
Sau đó bạn có thể truy vấn dữ liệu Lakehouse y như thao tác với Database truyền thống:
```sql
-- Xem dữ liệu bảng Silver
SELECT * FROM iceberg.silver.properties LIMIT 10;

-- Xem dữ liệu bảng Gold
SELECT * FROM iceberg.gold.feature_table LIMIT 10;
```

---

## 📂 Cấu trúc thư mục (Folder Structure)

```text
web_scraping_system/
├── dags/                       # Nơi chứa các file DAGs của Airflow
│   ├── dag_etl_pipeline.py     
│   ├── dag_bronze_compaction.py
│   ├── iceberg_maintenance.py
│   └── maintenance_script.py
├── datalake/                   # Mã nguồn PySpark chính (ETL)
│   └── src/
│       ├── main.py             # Script crawl dữ liệu
│       ├── silver_etl.py       # Transform Raw -> Silver
│       └── feature_engineering.py # Transform Silver -> Gold
├── gx/                         # Cấu hình Great Expectations (Data Quality)
│   ├── gx_checkpoint.py        # Script khai báo luật & check data
│   └── ...                     
├── trino/                      # Cấu hình Trino
│   └── catalog/
│       └── iceberg.properties
├── docker-compose.yml          # Cấu hình toàn bộ hạ tầng
├── .env                        # File chứa các biến môi trường bảo mật
├── requirements.txt            # Thư viện Python
└── README.md                   # Bạn đang đọc nó đây!
```
