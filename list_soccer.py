import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ["ODDS_API_KEY"]

url = f"https://api.the-odds-api.com/v4/sports?apiKey={API_KEY}"
response = requests.get(url)
sports = response.json()

# Filter to soccer only
soccer = [s for s in sports if s["group"] == "Soccer"]

print(f"Found {len(soccer)} active soccer leagues:\n")
for s in sorted(soccer, key=lambda x: x["key"]):
    print(f"{s['key']:45} {s['title']}")
