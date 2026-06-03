import nbformat as nbf

nb = nbf.v4.new_notebook()

nb.cells = [
    nbf.v4.new_markdown_cell("# Data Exploration: Silver Layer (Parquet)\n\nThis notebook loads and explores the cleaned Parquet files from the Silver layer using `pandas` and `duckdb`."),
    nbf.v4.new_code_cell("""import pandas as pd
import duckdb
import os

# Define silver data directory
silver_dir = 'hybrid_method/data/silver'
files = ['properties.parquet', 'projects.parquet', 'subdivisions.parquet', 'project_prices.parquet', 'project_amenities.parquet']

# Function to load and preview parquet file
def preview_parquet(filename):
    path = os.path.join(silver_dir, filename)
    if os.path.exists(path):
        print(f"\\n{'='*50}\\nPreviewing: {filename}\\n{'='*50}")
        df = pd.read_parquet(path)
        print(f"Total Rows: {len(df)}")
        print(f"Total Columns: {len(df.columns)}")
        display(df.head())
        print("\\nData Types:")
        print(df.dtypes)
    else:
        print(f"File {filename} not found.")"""),
    
    nbf.v4.new_markdown_cell("## 1. Properties (Căn hộ)"),
    nbf.v4.new_code_cell("preview_parquet('properties.parquet')"),
    
    nbf.v4.new_markdown_cell("## 2. Projects (Dự án)"),
    nbf.v4.new_code_cell("preview_parquet('projects.parquet')"),
    
    nbf.v4.new_markdown_cell("## 3. Subdivisions (Phân khu)"),
    nbf.v4.new_code_cell("preview_parquet('subdivisions.parquet')"),
    
    nbf.v4.new_markdown_cell("## 4. Project Prices (Lịch sử giá - Time Series)"),
    nbf.v4.new_code_cell("preview_parquet('project_prices.parquet')"),
    
    nbf.v4.new_markdown_cell("## 5. Project Amenities (Danh sách Tiện ích của Dự án)"),
    nbf.v4.new_code_cell("preview_parquet('project_amenities.parquet')"),
    
    nbf.v4.new_markdown_cell("## 6. Truy vấn SQL với DuckDB\n\nThử chạy một câu truy vấn SQL gom nhóm trực tiếp từ các file parquet."),
    nbf.v4.new_code_cell("""# Trung bình giá căn hộ theo phường/quận
query = '''
SELECT 
    district, 
    ward, 
    COUNT(*) as total_properties,
    AVG(min_selling_price) as avg_min_price
FROM read_parquet('hybrid_method/data/silver/properties.parquet')
GROUP BY district, ward
ORDER BY avg_min_price DESC
LIMIT 10;
'''
duckdb.query(query).df()""")
]

with open('explore_silver.ipynb', 'w') as f:
    nbf.write(nb, f)

print("Notebook explore_silver.ipynb created successfully!")
