import duckdb
import os
from dotenv import load_dotenv

# Load .env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

def export_to_duckdb():
    # Configure directories
    data_dir = os.getenv("BRONZE_DATA_DIR", "data/bronze")
    abs_data_dir = os.path.join(os.path.dirname(__file__), data_dir)
    
    # Target database file
    db_name = os.getenv("DUCKDB_PATH", "data/real_estate.duckdb")
    db_path = os.path.join(os.path.dirname(__file__), db_name)
    
    # Ensure data directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    if os.path.exists(db_path):
        os.remove(db_path)
        
    conn = duckdb.connect(db_path)
    print("Connected to DuckDB!")
    
    # Files to load
    files = {
        "properties": "properties.jsonl",
        "projects": "projects.jsonl",
        "subdivisions": "subdivisions.jsonl",
        "project_prices": "project_prices.jsonl"
    }
    
    for table_name, file_name in files.items():
        file_path = os.path.join(abs_data_dir, file_name)
        if os.path.exists(file_path):
            print(f"Loading {file_path} into table {table_name}...")
            # Use read_json_auto to infer schema and load data (ignoring minor JSON schema variations)
            try:
                # ignore_errors=true will drop objects that can't be parsed into the inferred strict schema
                # We can also use union_by_name=true if schemas vary slightly by keys
                conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM read_json_auto('{file_path}', format='newline_delimited', ignore_errors=true)")
                count = conn.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
                print(f" -> Loaded {count} rows into {table_name}.")
            except Exception as e:
                print(f" -> Error loading {table_name}: {e}")
        else:
            print(f"File {file_path} not found.")
            
    conn.close()
    print("DuckDB export completed! Database saved to:", db_path)

if __name__ == "__main__":
    export_to_duckdb()
