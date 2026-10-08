import os
import sys
import signal
import asyncio
import logging
import requests
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from telegram import Bot
from telegram.constants import ParseMode

load_dotenv()

API_KEY = os.environ["ODDSPAPI_KEY"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

BASE = "https://api.oddspapi.io/v4"

# ============================================================
# CONFIG
# ============================================================

TOURNAMENTS = {
    17:    "Premier League",
    8:     "La Liga",
    23:    "Serie A",
    35:    "Bundesliga",
    34:    "Ligue 1",
    37:    "Eredivisie",
    7:     "Champions League",
    679:   "Europa League",
    34480: "Conference League",
    937:   "Botola Pro D1",
}

MY_BOOKMAKERS = [
    "1xbet", "stake", "bcgame", "duelbits",
    "22bet", "melbet", "betwinner",
]

HOURS_AHEAD = 72          # look 72h out (more chance of catching arbs)
TOTAL_STAKE = 100.0
MIN_MARGIN = 0.015
MIN_LEG_STAKE = 5.0
MAX_WORKERS = 8           # parallel odds fetches
MARKET_ID = 101           # 1X2 full-time
OUT_HOME, OUT_DRAW, OUT_AWAY = 101, 102, 103

# ============================================================

SEEN_FILE = "seen_arbs.txt"
LOG_FILE = os.path.expanduser("~/Desktop/arbt_betting/scanner.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

_interrupted = False


def _sigint(signum, frame):
    global _interrupted
    _interrupted = True
    log.warning("\nInterrupted — will stop after current league.")


def load_seen():
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE) as f:
        return set(line.strip() for line in f)


def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        for item in seen:
            f.write(item + "\n")


# ============================================================
# FETCH
# ============================================================

def get_fixtures(tournament_id):
    url = f"{BASE}/fixtures"
    params = {"apiKey": API_KEY, "sportId": 10, "tournamentId": tournament_id}
    try:
        r = requests.get(url, params=params, timeout=30)
        if r.status_code != 200:
            log.warning(f"    fixtures HTTP {r.status_code}: {r.text[:150]}")
            return []
        return r.json()
    except Exception as e:
        log.warning(f"    fixtures error: {e}")
        return []


def get_odds(fixture_id):
    url = f"{BASE}/odds"
    params = {
        "apiKey": API_KEY,
        "fixtureId": fixture_id,
        "bookmakers": ",".join(MY_BOOKMAKERS),
    }
    try:
        r = requests.get(url, params=params, timeout=30)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


# ============================================================
# PARSE
# ============================================================

def parse_1x2(odds_data):
    """
    From /odds response, extract:
      {bookmaker: {"1": price, "X": price, "2": price}}
    Only books with all 3 outcomes priced and active.
    """
    result = {}
    bookmaker_odds = odds_data.get("bookmakerOdds", {})

    for bookmaker, book in bookmaker_odds.items():
        if bookmaker not in MY_BOOKMAKERS:
            continue
        markets = book.get("markets", {})
        m = markets.get(str(MARKET_ID))
        if not m:
            continue
        outcomes = m.get("outcomes", {})

        prices = {}
        for outcome_key, target in [
            (str(OUT_HOME), "1"),
            (str(OUT_DRAW), "X"),
            (str(OUT_AWAY), "2"),
        ]:
            o = outcomes.get(outcome_key)
            if not o:
                break
            players = o.get("players", {})
            p0 = players.get("0", {})
            if not p0.get("active", False):
                break
            price = p0.get("price")
            if price is None or price <= 1.0:
                break
            prices[target] = float(price)

        if len(prices) == 3:
            result[bookmaker] = prices

    return result


def find_arbs(fixtures_with_odds):
    arbs = []
    for fixture, book_odds in fixtures_with_odds:
        if len(book_odds) < 2:
            continue

        best = {}
        for book, prices in book_odds.items():
            for outcome, price in prices.items():
                if outcome not in best or price > best[outcome]["price"]:
                    best[outcome] = {"price": price, "book": book}

        if len(best) < 3:
            continue

        inv_sum = sum(1 / v["price"] for v in best.values())
        if inv_sum >= 1.0:
            continue

        margin = 1 - inv_sum
        if margin < MIN_MARGIN:
            continue

        legs = []
        skip = False
        for side, data in best.items():
            stake = TOTAL_STAKE * (1 / data["price"]) / inv_sum
            if stake < MIN_LEG_STAKE:
                skip = True
                break
            legs.append({
                "side": side,
                "odds": data["price"],
                "book": data["book"],
                "stake": round(stake, 2),
            })
        if skip:
            continue

        order = {"1": 0, "X": 1, "2": 2}
        legs.sort(key=lambda l: order.get(l["side"], 99))

        home = fixture.get("participant1Name", "?")
        away = fixture.get("participant2Name", "?")
        start = fixture.get("trueStartTime") or fixture.get("startTime", "")
        books_used = sorted({l["book"] for l in legs})

        arbs.append({
            "id": f"{fixture['fixtureId']}|{','.join(books_used)}",
            "event": f"{home} vs {away}",
            "league": fixture.get("tournamentName", ""),
            "start": start,
            "margin": margin,
            "legs": legs,
            "books": books_used,
        })

    return arbs


# ============================================================
# TELEGRAM
# ============================================================

async def send_telegram(arb):
    bot = Bot(token=BOT_TOKEN)
    side_name = {"1": "Home", "X": "Draw", "2": "Away"}
    lines = [
        "🚨 *ARBITRAGE FOUND* 🚨",
        "",
        f"*{arb['event']}*",
        f"🏆 {arb['league']}",
        f"⏰ {arb['start']}",
        f"💰 Margin: *{arb['margin']:.2%}*",
        "",
        f"*Stakes (total {TOTAL_STAKE:.0f}):*",
    ]
    for leg in arb["legs"]:
        lines.append(
            f"  • {side_name.get(leg['side'], leg['side'])} @ {leg['odds']} "
            f"on *{leg['book']}* → {leg['stake']}"
        )
    await bot.send_message(
        chat_id=CHAT_ID,
        text="\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )


# ============================================================
# MAIN SCAN
# ============================================================

def scan():
    signal.signal(signal.SIGINT, _sigint)

    cutoff = datetime.now(timezone.utc) + timedelta(hours=HOURS_AHEAD)
    log.info(f"Scanning {len(TOURNAMENTS)} leagues via OddsPapi v4")
    log.info(f"Bookmakers: {', '.join(MY_BOOKMAKERS)}")
    log.info(f"Window: now → {cutoff.isoformat()}\n")

    all_arbs = []
    total_in_window = 0
    total_with_odds = 0

    for tid, tname in TOURNAMENTS.items():
        if _interrupted:
            break

        fixtures = get_fixtures(tid)
        if not fixtures:
            log.info(f"  {tname:22} 0 fixtures")
            continue

        # Filter to time window
        in_window = []
        for fx in fixtures:
            ts = fx.get("trueStartTime") or fx.get("startTime")
            if not ts:
                continue
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                continue
            if dt <= cutoff:
                in_window.append(fx)

        log.info(f"  {tname:22} {len(fixtures):4} total → {len(in_window):3} in window")
        total_in_window += len(in_window)

        if not in_window:
            continue

        # Fetch odds in parallel
        results = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(get_odds, fx["fixtureId"]): fx for fx in in_window}
            for fut in as_completed(futures):
                if _interrupted:
                    break
                fx = futures[fut]
                data = fut.result()
                if not data:
                    continue
                parsed = parse_1x2(data)
                if len(parsed) >= 2:
                    results.append((fx, parsed))

        total_with_odds += len(results)
        arbs = find_arbs(results)
        all_arbs.extend(arbs)
        log.info(f"    → {len(results)} with odds, {len(arbs)} arbs")

    log.info(
        f"\nDone: {total_in_window} in window, "
        f"{total_with_odds} with odds, {len(all_arbs)} arbs"
    )

    seen = load_seen()
    new_arbs = [a for a in all_arbs if a["id"] not in seen]

    if not new_arbs:
        log.info("No new arbs.")
        return

    log.info(f"\n{len(new_arbs)} NEW arb(s):\n")
    for arb in new_arbs:
        log.info(f"  {arb['event']} | {arb['margin']:.2%}")
        log.info(f"    books: {', '.join(arb['books'])}")
        for leg in arb["legs"]:
            log.info(f"    {leg['side']:3} @ {leg['odds']:6} on {leg['book']:12} → {leg['stake']}")
        try:
            asyncio.run(send_telegram(arb))
            seen.add(arb["id"])
        except Exception as e:
            log.warning(f"    Telegram failed: {e}")
        log.info("")

    save_seen(seen)
    log.info("Scan complete.")


if __name__ == "__main__":
    scan()
