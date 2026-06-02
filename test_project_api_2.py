from curl_cffi import requests
import json
url = "https://api.onehousing.vn/onehousing-channel/v1/insights/projects/16a7f900-56e6-11eb-ae93-0242ac130002"
res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, impersonate="chrome").json()
data = res.get("data", {})
if "insight_by_sector" in data:
    print("insight_by_sector type:", type(data["insight_by_sector"]))
    if isinstance(data["insight_by_sector"], list) and len(data["insight_by_sector"]) > 0:
        print("First insight_by_sector keys:", data["insight_by_sector"][0].keys())
        print(json.dumps(data["insight_by_sector"][0])[:300])

print("---")
if "blocks" in data:
    print("blocks type:", type(data["blocks"]))
    if isinstance(data["blocks"], list) and len(data["blocks"]) > 0:
        print("First block keys:", data["blocks"][0].keys())
