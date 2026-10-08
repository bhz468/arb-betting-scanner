import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()
KEY = os.environ["ODDSPAPI_KEY"]

# Correct base URL from the docs
url = f"https://v5.oddspapi.io/en/bookmakers?apiKey={KEY}"

print(f"Requesting: {url.replace(KEY, 'REDACTED')}")
r = requests.get(url, timeout=30)
print(f"Status: {r.status_code}\n")

if r.status_code == 200:
    books = r.json()
    print(f"{len(books)} bookmakers available on your key:\n")
    for b in books:
        slug = b.get("slug", "?")
        name = b.get("bookmakerName", "?")
        active = b.get("active", "?")
        domain = b.get("domain", "")
        print(f"  {slug:20} | {name:25} | active={active} | {domain}")
else:
    print(r.text[:500])
