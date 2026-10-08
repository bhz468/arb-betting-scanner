import os
import requests
from dotenv import load_dotenv

load_dotenv()
KEY = os.environ["ODDSPAPI_KEY"]

tests = [
    ("v5 bookmakers", f"https://v5.oddspapi.io/en/bookmakers?apiKey={KEY}"),
    ("v5 fixtures/odds/main", f"https://v5.oddspapi.io/en/fixtures/odds/main?apiKey={KEY}&tournamentId=17&bookmakers=1xbet,stake"),
    ("v4 bookmakers", f"https://api.oddspapi.io/v4/bookmakers?sportId=10&apiKey={KEY}"),
    ("v4 fixtures", f"https://api.oddspapi.io/v4/fixtures?sportId=10&tournamentId=17&apiKey={KEY}"),
]

for label, url in tests:
    try:
        r = requests.get(url, timeout=20)
        print(f"[{r.status_code}] {label}")
        if r.status_code != 200:
            print(f"       {r.text[:150]}")
        else:
            print(f"       OK ({len(r.text)} bytes)")
    except Exception as e:
        print(f"[ERR] {label}: {e}")
