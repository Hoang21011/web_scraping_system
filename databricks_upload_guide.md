# Hướng dẫn chi tiết: Đưa Code và Data lên Databricks

Để tiếp tục phân tích dữ liệu ở tầng Silver/Gold hoặc huấn luyện AI trên Databricks, bạn cần đưa **Code** (các file Python, Notebook) và **Data** (toàn bộ cấu trúc thư mục tầng Bronze và Silver) lên môi trường này.

Dưới đây là 2 cách (từ dễ bằng giao diện đến chuyên nghiệp bằng dòng lệnh) để thực hiện:

---

## 🟢 CÁCH 1: Dùng Giao Diện (Dễ nhất, phù hợp làm tay)

### Bước 1: Upload Code (Kết nối GitHub)
Cách tốt nhất để đưa code lên Databricks là đồng bộ hóa với Git. Vì bạn đã push code lên nhánh `main` trên GitHub, bạn chỉ cần kéo nó về Databricks:
1. Đăng nhập vào Databricks Workspace.
2. Ở thanh công cụ bên trái, chọn **Workspace**.
3. Bấm vào nút **Create** (dấu cộng) ở góc trên bên phải > Chọn **Git folder** (hoặc **Repo** ở bản cũ).
4. Dán đường link repo GitHub của bạn vào (`https://github.com/Hoang21011/web_scraping_system.git`).
5. Bấm **Create Repo**. Toàn bộ code của bạn sẽ có mặt trên Databricks và bạn có thể cập nhật (`pull`) bất cứ lúc nào.

### Bước 2: Upload Data (Lưu vào Unity Catalog Volumes)
Cách hiện đại và an toàn nhất trên Databricks là dùng Unity Catalog Volumes thay vì DBFS cũ:
1. Trên thanh công cụ bên trái, chọn **Catalog** (biểu tượng hình trụ cơ sở dữ liệu).
2. Chọn Catalog của bạn. Nếu đây là tài khoản mới, bạn thường sẽ thấy sẵn catalog tên là **`main`**, **`workspace`**, hoặc **`hive_metastore`**. Hãy bấm chọn nó.
3. Sau khi chọn Catalog, hệ thống sẽ yêu cầu chọn Schema (Database). Bạn hãy chọn schema **`default`** có sẵn.
4. Bấm **Create** (ở góc phải) > **Volume**.
5. Đặt tên Volume là `real_estate_data` và bấm Create.
5. Mở Volume vừa tạo, bấm **Create directory** (hoặc tạo thư mục) để tạo 2 thư mục con tên là `bronze` và `silver` (nhằm giữ nguyên kiến trúc Medallion).
6. Mở thư mục `bronze`, chọn **Upload to this volume** và kéo thả các file `.jsonl` từ máy bạn (thư mục `hybrid_method/data/bronze/`) vào.
7. Mở thư mục `silver`, lặp lại thao tác kéo thả cho các file `.parquet` từ thư mục `hybrid_method/data/silver/`.
   
*(Đường dẫn data của bạn sẽ có dạng: `/Volumes/main/default/real_estate_data/silver/properties.parquet`)*

---

## 🔴 CÁCH 2: Dùng Databricks CLI (Chuyên nghiệp, tự động hóa)

Nếu dữ liệu của bạn sinh ra liên tục mỗi ngày, việc kéo thả bằng tay sẽ mất thời gian. Hãy dùng Databricks CLI.

### Bước 1: Cài đặt và cấu hình Databricks CLI
Mở Terminal trên máy tính Mac của bạn và chạy lệnh:
```bash
brew tap databricks/tap
brew install databricks
```
Sau đó, xác thực với tài khoản Databricks:
```bash
databricks configure --token
```
*(Bạn cần tạo một Personal Access Token trong phần User Settings trên giao diện Databricks và dán vào đây)*

### Bước 2: Upload Data tự động bằng CLI
Mở Terminal tại thư mục gốc của project, bạn có thể đẩy toàn bộ thư mục dữ liệu (cả Bronze và Silver) lên DBFS bằng các lệnh sau:
```bash
# Upload dữ liệu Bronze (JSONL)
databricks fs cp -r hybrid_method/data/bronze/ dbfs:/FileStore/real_estate_data/bronze/

# Upload dữ liệu Silver (Parquet)
databricks fs cp -r hybrid_method/data/silver/ dbfs:/FileStore/real_estate_data/silver/
```
*(Lưu ý: Nếu sử dụng Unity Catalog Volume ở Cách 1, hãy thay đường dẫn đích thành dạng `/Volumes/main/default/real_estate_data/bronze/`)*

### Bước 3: Upload Code tự động (Tùy chọn)
Nếu không dùng Git, bạn cũng có thể copy code lên Workspace:
```bash
databricks workspace import_dir ./hybrid_method /Users/your_email@domain.com/hybrid_method
```

---

## 🚀 Đọc dữ liệu trên Databricks Notebook

Sau khi đã có code và data, bạn tạo một Notebook mới trên Databricks và dùng **PySpark** để đọc dữ liệu với tốc độ cao.

```python
# Đọc dữ liệu thô từ tầng Bronze (JSONL)
df_bronze = spark.read.json("/Volumes/main/default/real_estate_data/bronze/properties.jsonl")
display(df_bronze.limit(5))

# Đọc dữ liệu sạch từ tầng Silver (Parquet)
df_silver = spark.read.parquet("/Volumes/main/default/real_estate_data/silver/properties.parquet")
display(df_silver.limit(5))

# Tạo Temp View để dùng thẳng SQL trên dữ liệu Silver
df_silver.createOrReplaceTempView("silver_properties")
```

Bây giờ bạn có thể mở 1 cell mới, chọn ngôn ngữ `%sql` và truy vấn y hệt như đang dùng DuckDB:
```sql
%sql
SELECT district, ward, COUNT(*) as total
FROM silver_properties
GROUP BY district, ward
ORDER BY total DESC;
```

---

## 👥 Phân quyền: Thêm người dùng (Share Workspace & Data)

Nếu bạn muốn mời một người khác (ví dụ qua Gmail) vào cùng làm việc trên Databricks, bạn cần cấp 3 loại quyền: Quyền vào Workspace, Quyền xem Code, và Quyền đọc Data.

### Bước 1: Thêm tài khoản vào Workspace (Admin)
1. Ở góc trên cùng bên phải màn hình Databricks, bấm vào tên tài khoản của bạn > Chọn **Admin Console** (hoặc Settings > Identity and access management).
2. Chọn mục **Users** > Bấm nút **Add User**.
3. Nhập địa chỉ Gmail của người đó và bấm **Send Invite**. 
*(Người đó sẽ nhận được email mời tạo tài khoản/đăng nhập vào Databricks)*.

### Bước 2: Cấp quyền truy cập Code (Workspace/Git Folder)
Người dùng mới vào sẽ không tự động thấy code của bạn. Bạn phải chia sẻ thư mục Code cho họ:
1. Trở lại trang **Workspace** ở thanh bên trái.
2. Tìm đến thư mục Git/Repo chứa code của bạn (ví dụ `web_scraping_system`).
3. Bấm chuột phải vào thư mục (hoặc dấu 3 chấm) > Chọn **Share** (hoặc Permissions).
4. Ở ô tìm kiếm, nhập Gmail của người đó > Chọn quyền **Can Run** hoặc **Can Edit** > Bấm **Add**.

### Bước 3: Cấp quyền truy cập Data (Unity Catalog Volume)
Đây là bước quan trọng nhất vì Unity Catalog bảo mật dữ liệu rất chặt chẽ:
1. Vào mục **Catalog** ở thanh bên trái.
2. Tìm đến Volume chứa dữ liệu của bạn: `main` > `default` > `real_estate_data`.
3. Bấm vào tên Volume `real_estate_data`. Nhìn sang góc phải trên cùng, bấm nút **Permissions**.
4. Bấm **Grant**. Nhập Gmail của người đó vào ô tìm kiếm.
5. Đánh dấu chọn quyền **READ VOLUME** (nếu chỉ muốn họ đọc dữ liệu) hoặc **WRITE VOLUME** (nếu muốn họ được tải thêm dữ liệu lên).
6. Bấm **Grant** để lưu lại.

Lúc này, người đồng nghiệp của bạn có thể đăng nhập vào, mở Notebook và chạy đúng đoạn code `spark.read.parquet(...)` như trên mà không gặp lỗi phân quyền (Access Denied).
