import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()
KEY = os.environ["ODDSPAPI_KEY"]

url = "https://v5.oddspapi.io/en/bookmakers"
r = requests.get(url, params={"apiKey": KEY}, timeout=30)
print(f"Status: {r.status_code}")

if r.status_code == 200:
    data = r.json()
    books = data if isinstance(data, list) else data.get("bookmakers", data.get("data", []))
    print(f"\n{len(books)} bookmakers available on your key:\n")
    for b in books:
        slug = b.get("slug", b.get("bookmaker", "?"))
        name = b.get("bookmakerName", b.get("name", ""))
        active = b.get("active", True)
        print(f"  {slug:20} | {name:25} | active={active}")
else:
    print(r.text[:500])
