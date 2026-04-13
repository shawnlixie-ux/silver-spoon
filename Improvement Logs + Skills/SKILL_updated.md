---
name: parlay-lab
description: Context and architecture for the Parlay Lab NBA betting analysis app. Use this skill whenever the user mentions Parlay Lab, parlay lab, their NBA betting app, Kalshi integration, player props, Kelly criterion betting, bridge.py, or any work on their sports prediction models. Also trigger when they mention updating game data, model calibration, backtest results, ESPN API endpoints, or Kalshi API trading. This skill contains the full project architecture, model specs, API references, user preferences, known issues, and roadmap — always read it before making any changes.
---

# Parlay Lab — Project Skill

## What Is Parlay Lab
A single-page HTML app for NBA game prediction and Kalshi betting. It runs a 3-model prediction system, calculates Kelly criterion bet sizing, projects player props, and integrates with the Kalshi prediction market API via a local Python bridge server.

## User Preferences
- **ALWAYS confirm before making code changes.** Do not modify HTML, Python, or any project files without explicit approval.
- User is learning Python/APIs — explain concepts when introducing new patterns
- Keep the existing JetBrains Mono dark theme aesthetic
- User wants to be able to bet NO on player props (can't do this on Kalshi website)

---

## Architecture

```
┌─────────────────────┐     localhost:5000     ┌─────────────┐     HTTPS      ┌───────────┐
│  Parlay_Lab.html    │ ◄──────────────────► │  bridge.py  │ ◄────────────► │ Kalshi API│
│  (browser)          │     fetch() calls     │  (Flask)    │  kalshi-python │           │
└─────────────────────┘                       └─────────────┘    -sync SDK   └───────────┘
                                                      │
                                                      │ HTTP
                                                      ▼
                                              ┌───────────────┐
                                              │  ESPN APIs    │
                                              │ (auto-fetch)  │
                                              └───────────────┘
```

### Files
| File | Purpose |
|---|---|
| `Parlay_Lab_Kalshi current.html` | Main app — all UI, models, and rendering (single file, ~1200 lines) |
| `bridge.py` | Flask server — proxies between HTML frontend and Kalshi API + ESPN auto-fetch |
| `thirdAPIKEY.txt` | Kalshi RSA private key (original format, DO NOT EDIT) |
| `thirdAPIKEY_converted.txt` | Kalshi PKCS#8 converted key (used by bridge.py) |

### How to Start the App (Full Startup Sequence)
```
Terminal 1 — Bridge:
cd "/Applications/Betting Project/API Keys/circlingdiamond45 (read)"
python3 bridge.py

Terminal 2 — HTML Server:
cd "/Applications/Betting Project"
python3 -m http.server 8080

Terminal 3 — Test bridge (optional):
curl http://127.0.0.1:5000/status

Browser:
http://localhost:8080/Parlay_Lab_Kalshi%20current.html
```

### Bridge Endpoints
| Method | Path | Purpose |
|---|---|---|
| GET | `/status` | Auth check + balance |
| GET | `/balance` | Account balance (cents) |
| GET | `/search?q=&series=&limit=` | Search open markets |
| GET | `/orderbook/<ticker>` | Order book depth |
| GET | `/market/<ticker>` | Single market details |
| GET | `/positions` | Current portfolio |
| GET | `/orders?status=` | Recent orders |
| GET | `/fetch-espn` | Auto-fetch tonight's ESPN data (games, teams, rosters, injuries) |
| POST | `/place_bet` | Place limit order (body: ticker, side, price, count) |
| POST | `/cancel_order` | Cancel order (body: order_id) |

### Kalshi Auth
- SDK: `kalshi-python-sync` version 3.5.0
- Host: `https://api.elections.kalshi.com/trade-api/v2`
- API Key ID: `5a3ad6f1-a741-42a3-8ce6-20ce32529d7a`
- Private key file: `thirdAPIKEY_converted.txt` (PKCS#8 format)
- Config field: `config.private_key_pem` (NOT `config.private_key` — this changed in SDK 3.5.0)
- Current key is **READ ONLY** — no order placement until user switches to read/write key

### Key Conversion Process (Required Every Time Kalshi Gives a New Key)
Kalshi always generates keys in RSA format. The SDK requires PKCS#8. Every new key must be converted:
```bash
cd "/Applications/Betting Project/API Keys/circlingdiamond45 (read)"
openssl pkcs8 -topk8 -nocrypt -in "newkey.txt" -out "newkey_converted.txt"
```
Then update bridge.py to point to the converted file and use `config.private_key_pem`.

### Kalshi Ticker Format (NBA Player Props)
```
NBAP-{DDMMMYY}-{LASTNAME}-{LINE}-{STAT}
Example: NBAP-26MAR17-MAXEY-25.5-PTS
```

### ESPN Abbreviation Map (ESPN → App)
ESPN uses different abbreviations for some teams. bridge.py handles this:
```python
ABBR_MAP = {
    'NY': 'NYK', 'SA': 'SAS', 'WSH': 'WAS', 'GS': 'GSW',
    'NO': 'NOP', 'UTAH': 'UTA'
}
```

### SDK Model Patches Applied (March 2026)
The kalshi-python-sync 3.5.0 SDK has strict integer validation that rejects None values from Kalshi's API. These fields were patched in the installed SDK to use `Optional[int]`:

**File: kalshi_python_sync/models/market_position.py**
- `total_traded`, `position`, `market_exposure`, `realized_pnl`, `fees_paid`

**File: kalshi_python_sync/models/event_position.py**
- `total_cost`, `total_cost_shares`, `event_exposure`, `realized_pnl`, `fees_paid`

**File: kalshi_python_sync/models/order.py**
- `yes_price`, `no_price`, `fill_count`, `remaining_count`, `initial_count`, `taker_fees`, `maker_fees`, `taker_fill_cost`, `maker_fill_cost`, `queue_position`

⚠️ If the SDK is ever upgraded or reinstalled, these patches will need to be reapplied.

---

## App Tabs
1. **🟢 KALSHI** — Game cards with 3-model analysis, Kalshi price inputs, edge calculation, Kelly sizing
2. **⚡ TRADE** — Search Kalshi markets, view orderbooks, place orders, view positions/orders
3. **🎯 PROPS** — Player prop projections vs Kalshi lines, "Fetch Kalshi Lines" auto-matches, "BET NO" shortcut
4. **💎 VALUE** — All teams ranked by model win probability
5. **📐 KELLY** — Kelly criterion bet sizing aggregated across all games
6. **📡 DATA** — AUTO-FETCH ESPN button + manual JSON paste loader

---

## ESPN Auto-Fetch Pipeline

### What It Fetches Automatically
- Tonight's scheduled games and tip-off times (ET)
- Team stats: ortg (pts for), drtg (pts against), pace, net rating, wins/losses, tpr (3pt%)
- Home/away records
- Rosters with injury status (PLAY/GTD/OUT)
- Injury reports per team

### What Still Needs Manual Input
- Kalshi prices (kH, kA) — use "FETCH KALSHI LINES" button in PROPS tab
- H2H records — ESPN doesn't expose easily
- Rest days / travel — calculate manually
- L5/L10 player stats — ESPN roster endpoint doesn't return these (future roadmap)
- Season averages (szn) — future roadmap

### ESPN API Used
- Site API: `https://site.api.espn.com/apis/site/v2/sports/basketball/nba`
- Core API: `https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba`
- Parallel fetching with `ThreadPoolExecutor(max_workers=16)` — runs all teams simultaneously
- Load time: ~3-5 seconds for 8 games (16 teams)

### Known ESPN Issues
- Some teams occasionally timeout on the core API stats endpoint (MIL, OKC, WAS seen on 3/17/26) — falls back to league average defaults
- L10 wins/losses not available from ESPN — defaults to 5/5
- Home/away wins/losses sometimes return 0 if record endpoint times out

---

## Prediction Models (V2.2 — Backtest-Proven)

### Model A — Efficiency (weight: 45%)
Core: Net rating diff × 0.028 (proven best single predictor)
Adds: tiered injuries, B2B fatigue (ProbWin-calibrated), altitude (DEN +3%, UTA +2%), travel, HCA +2.5%

### Model B — Momentum (weight: 30%)
L10 record × 0.50, scoring trend, win streaks (SHAP: #1 momentum factor, 4+ streak = strong), venue split, ATS L10

### Model C — Matchup (weight: 25%)
Season H2H × 0.10 (small sample), style clash (3pt mismatch), clutch record (games within 5pts), pace mismatch, record baseline × 0.45

### Consensus System
- 3/3 agree + edge >10% = 🔥 LOCK
- 3/3 agree = 🟢 HIGH
- 2/3 agree = 🟡 MED
- 0-1/3 agree = 🔴 LOW

### Injury Tiers
```json
{"p":"Name","s":"OUT","star":true}      // All-Star → -3.5%
{"p":"Name","s":"OUT","starter":true}    // Starter → -1.5%
{"p":"Name","s":"OUT","starter":false}   // Bench → -0.5%
```

### Props Projection
Base = L10 × 0.45 + Season × 0.35 + L5 × 0.20
Adjustments: opponent DRTG, pace, home/away ±0.8, blowout risk (-6% if net gap >12)

### Backtest Results (118 games, March 2026)
| Confidence Tier | Record | Accuracy |
|---|---|---|
| 20%+ edge | 25/26 | 96.2% |
| 15-20% | 22/23 | 95.7% |
| 10-15% | 19/21 | 90.5% |
| 5-10% | 25/28 | 89.3% |
| 0-5% | 31/50 | 62.0% — SKIP |

Accuracy ceiling: research says 68-72%, best ML gets ~65%, our target is 62-66%.

---

## JSON Data Format
```json
{
  "date": "Mar 17, 2026",
  "games": [
    {"id":"g1", "h":"ATL", "a":"ORL", "t":"7:00 PM",
     "hp":58, "ap":42, "kH":58, "kA":42,
     "h2h":[2,1], "hRest":1, "aRest":0,
     "hTravel":false, "aTravel":true}
  ],
  "teams": {
    "ATL": {"ortg":115.2, "drtg":114.1, "pace":101.9,
            "w":36, "l":31, "net":1.1,
            "l10w":7, "l10l":3, "hw":22, "hl":12, "aw":14, "al":19,
            "streak":3, "ptsFor":115.5, "ptsAg":114.1,
            "l10ptsFor":118.2, "tpr":0.38, "atsl10":6,
            "closew":12, "closel":8}
  },
  "players": [
    {"name":"Trae Young", "team":"ATL", "opp":"ORL",
     "pos":"PG", "szn":25.8, "l5":28.2, "l10":27.1,
     "min":35.7, "line":26.5, "status":"PLAY",
     "note":"L5: 30,25,28,31,27"}
  ],
  "injuries": {
    "ATL": [{"p":"Bogdan Bogdanovic", "s":"OUT", "starter":true}]
  }
}
```

---

## ESPN API Reference

### Site API (user-friendly)
Base: `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/`
- `scoreboard` — live scores
- `scoreboard?dates=YYYYMMDD` — specific date
- `standings` — league standings (NOTE: returns almost empty as of March 2026, use core API instead)
- `teams/{id}/roster` — team roster (no stats, just names/positions/injury status)
- `teams/{id}/injuries` — injury report
- `teams/{id}/schedule` — team schedule

### Core API (detailed data)
Base: `https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/`
- `seasons/2026/types/2/teams/{id}/statistics` — full team stats (ortg, drtg, pace, etc.)
- `seasons/2026/types/2/teams/{id}/record` — wins/losses, home/away splits, pts for/against

---

## Known Issues
1. **L5/L10 player stats** — ESPN roster endpoint doesn't return these. Auto-fetch sets all to 0. User must manually add or build deep fetch.
2. **Season averages (szn, min)** — same issue, set to 0 by auto-fetch. Future roadmap item.
3. **Occasional ESPN timeouts** — some teams fall back to league averages. Usually resolves on retry.
4. **Read-only API key** — can't place orders until user switches to read/write key
5. **Player prop matching** — matches on last name only, could fail with common last names
6. **H2H records** — not auto-fetched, defaults to [1,1]
7. **Rest days / travel** — not auto-fetched, defaults to 1/False

## V3 Roadmap (Not Yet Built)
- Deep fetch mode: L5/L10 and season averages via player gamelog API (~10-15 sec load)
- Bet tracker with P&L history
- Correlation warnings for same-game bets
- Auto-sort props by edge size
- Referee assignment tendencies
- Player vs specific team historical performance
- Usage rate WITH vs WITHOUT teammates
- Bankroll drawdown protection
- Minutes projection model
- Pandas DataFrames for data analysis / candlestick data

---

## Version History
| Version | Key Change |
|---|---|
| V1 | 2-model system (efficiency + record), basic props |
| V2 | 3 models + show math toggle |
| V2.1 | Research-calibrated weights (FiveThirtyEight, ProbWin, SHAP) |
| V2.2 | Backtest-proven on 118 games, removed ORTG/DRTG double-counting |
| V2.2+Kalshi | Added TRADE tab, bridge.py, full Kalshi API integration |
| V2.3 | Fixed bridge connection (key format PKCS#8, file path, SDK upgrade to 3.5.0), fixed positions/orders SDK model patches, added ESPN auto-fetch pipeline with parallel threading, added AUTO-FETCH button to DATA tab |
