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
    keys = list(props["fallback"].keys())
    print("Fallback keys:")
    for k in keys:
        print(" ->", k)
        val = props["fallback"][k]
        if isinstance(val, dict):
            print("    Contains data, keys:", val.keys())
            if "data" in val:
                print("    Data items count:", len(val["data"]))
                if val["data"]:
                    print("    First item:", json.dumps(val["data"][0])[:200])

