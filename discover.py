import os
import requests
from dotenv import load_dotenv

load_dotenv()
KEY = os.environ["ODDSPAPI_KEY"]
BASE = "https://api.oddspapi.io/v4"

# 1) List all sports
print("=" * 60)
print("SPORTS")
print("=" * 60)
r = requests.get(f"{BASE}/sports", params={"apiKey": KEY}, timeout=30)
sports = r.json()
for s in sports:
    print(f"  sportId={s.get('sportId'):5} {s.get('sportName')}")

# 2) List soccer tournaments (sportId=10)
print()
print("=" * 60)
print("SOCCER TOURNAMENTS (filtered)")
print("=" * 60)
r = requests.get(f"{BASE}/tournaments", params={"sportId": 10, "apiKey": KEY}, timeout=30)
tournaments = r.json()
print(f"Total tournaments: {len(tournaments)}\n")

keywords = ["premier league", "ligue 1", "la liga", "serie a", "bundesliga",
            "eredivisie", "champions league", "europa league", "conference league",
            "botola", "morocco"]
for t in tournaments:
    name = (t.get("tournamentName") or t.get("name") or "").lower()
    if any(k in name for k in keywords):
        tid = t.get("tournamentId") or t.get("id")
        print(f"  id={tid:8} {t.get('tournamentName') or t.get('name')}")
