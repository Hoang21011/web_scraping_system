import json
import os

def profile_file(filepath):
    print(f"\n{'='*50}\nProfiling: {os.path.basename(filepath)}\n{'='*50}")
    if not os.path.exists(filepath):
        print("File not found!")
        return
        
    records = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= 10:  # just load first 10 for structure
                break
            try:
                records.append(json.loads(line))
            except:
                pass
                
    if not records:
        print("No valid JSON lines found.")
        return
        
    # Analyze keys of the first record
    first = records[0]
    print(f"Number of keys: {len(first.keys())}")
    print("Keys and Types (first record):")
    for k, v in first.items():
        type_str = type(v).__name__
        if isinstance(v, list) and len(v) > 0:
            type_str += f"[{type(v[0]).__name__}]"
        print(f"  - {k}: {type_str}")

def main():
    base_dir = "hybrid_method/data/bronze"
    files = ["properties.jsonl", "projects.jsonl", "subdivisions.jsonl", "project_prices.jsonl"]
    for f in files:
        profile_file(os.path.join(base_dir, f))

if __name__ == "__main__":
    main()
