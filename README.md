# Arbitrage Betting Scanner

A Python bot that scans football odds across multiple bookmakers, detects
arbitrage opportunities, and sends alerts via Telegram.

## What It Does

- Fetches pre-match 1X2 odds from [OddsPapi](https://oddspapi.io) for 10 football
  leagues (Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Eredivisie,
  Champions League, Europa League, Conference League, Botola Pro D1).
- Filters to a configurable time window (default: next 24 hours).
- Detects arbitrage when `1/odds_home + 1/odds_draw + 1/odds_away < 1.0`.
- Calculates the optimal stake split for a given bankroll.
- Sends formatted alerts to a Telegram chat.

## Why It Exists

Built as a learning project to practice:
- Multi-source API integration with rate limiting
- Concurrent data fetching (`ThreadPoolExecutor`)
- Domain modeling (normalizing market IDs, bookmaker slugs)
- Automated alerting pipelines

**Note on scope:** bookmaker coverage is filtered to platforms accessible
from Morocco, which excludes most regulated EU/UK books. See the
"Limitations" section below.

## Architecture

