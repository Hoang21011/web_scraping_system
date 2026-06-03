from curl_cffi import requests
from bs4 import BeautifulSoup
import json

url = "https://onehousing.vn/ban-can-ho?loai=villa,row_house,shop_house&page=1"
res = requests.get(url, impersonate="chrome")
soup = BeautifulSoup(res.text, "html.parser")
script = soup.find("script", id="__NEXT_DATA__")
data = json.loads(script.string)

props = data.get("props", {}).get("pageProps", {})
if "fallback" in props:
    for k, val in props["fallback"].items():
        if isinstance(val, dict) and "data" in val:
            if isinstance(val["data"], dict) and "items" in val["data"]:
                print("Found items inside", k, "length:", len(val["data"]["items"]))
                if val["data"]["items"]:
                    print(json.dumps(val["data"]["items"][0])[:300])
            elif isinstance(val["data"], list):
                print("Found list in data", k)
            else:
                print("Data keys:", val["data"].keys())
