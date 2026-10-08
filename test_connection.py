import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ["ODDS_API_KEY"]

url = f"https://api.the-odds-api.com/v4/sports?apiKey={API_KEY}"
response = requests.get(url)

if response.status_code == 200:
    sports = response.json()
    print(f"✅ Key works! Found {len(sports)} in-season sports.")
    for s in sports[:8]:
        print(f"  - {s['key']}: {s['title']}")
    print(f"Requests remaining: {response.headers.get('x-requests-remaining')}")
    print(f"Requests used: {response.headers.get('x-requests-used')}")
else:
    print(f"❌ Error {response.status_code}: {response.text}")
