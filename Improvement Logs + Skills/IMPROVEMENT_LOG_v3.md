# Parlay Lab — Improvement Log

## Session: March 17-18, 2026 (Session 1)

### Completed
- Fixed bridge connection (PKCS#8 key conversion, SDK upgrade to 3.5.0)
- Fixed positions/orders SDK model patches
- Built ESPN auto-fetch pipeline with parallel threading
- Added AUTO-FETCH button to DATA tab
- Added dual API key setup (read-only for data, read/write for betting)
- Built betting UI (confirmation modal, quick size buttons, cancel orders)
- Added startup script (`start_parlay_lab.sh`)
- Added direct ticker input for Kalshi markets
- Built DEEP FETCH endpoint with real player stats (szn, L5, L10, min)
- Fixed gamelog date sorting (cross-reference events_dict by eventId)
- Fixed season filter (2025-26 Regular Season only)
- Fixed traded players (filter by current team abbreviation)
- Real L10 record, win streak, scoring trend, opponent-adjusted form for teams
- Roster limited to top 10 players per team

---

## Session: March 18-19, 2026 (Session 2)

### Completed
- **Model B rebuilt** — dropped ATS (no data), added opponent-adjusted form
- **Model C rebuilt** — dropped H2H and clutch (no data), added strength of schedule and net rating matchup
- **Model A upgraded** — team-specific HCA based on actual home/away win% (fallback to 2.5% if no data)
- **Future game date picker** — Today/+1/+2/+3 day buttons in DATA tab, both fetches use selected date
- **Props player quality fixed** — sort by actual minutes played, filter 0-game players, top 8 per team
- **Props projection formula upgraded:**
  - L5 weight increased from 20% → 50% (recent form most predictive)
  - L10 weight changed from 45% → 30%
  - Season weight changed from 35% → 20%
  - Exponential decay weighting on L10 (decay=0.85, recent games weighted more)
  - B2B penalty added (-11% if player on back-to-back)
  - Minutes adjustment (only penalizes sub-28 min players, doesn't boost stars)
  - oppD multiplier softened from 0.8 → 0.4 (was too aggressive)
  - Home/away changed from flat ±0.8pts → proportional ±2.5%
  - Blowout risk tiered (>20 net gap: -10%, >12: -6%, >7: -3%)
  - Star-out usage boost (+8% if star OUT, +5% if 2 starters OUT, +3% if 1 starter OUT)
- **Pace-adjusted ortg/drtg** — now calculated per 100 possessions (ESPN raw ÷ pace × 99.2)

---

## Architecture (Current State)

### Files
| File | Purpose |
|---|---|
| `Parlay_Lab_Kalshi current.html` | Main app (~1383 lines) |
| `bridge.py` | Flask server on port 5001 |
| `thirdAPIKEY_converted.txt` | Read-only Kalshi key (PKCS#8) |
| `orbitingrectangle12_converted.txt` | Read/write Kalshi key (PKCS#8) |
| `start_parlay_lab.sh` | One-command startup script |

### Startup
```bash
"/Applications/Betting Project/start_parlay_lab.sh"
# Then open: http://127.0.0.1:8080/Parlay_Lab_Kalshi%20current.html
```

### Bridge Endpoints
| Method | Path | Purpose |
|---|---|---|
| GET | `/status` | Auth check + balance |
| GET | `/balance` | Account balance |
| GET | `/search?q=&series=&limit=` | Search markets |
| GET | `/orderbook/<ticker>` | Order book |
| GET | `/market/<ticker>` | Single market |
| GET | `/positions` | Portfolio |
| GET | `/orders` | Recent orders |
| GET | `/fetch-espn?offset=N` | Fast fetch (games/teams/rosters, N days out) |
| GET | `/fetch-espn-deep?offset=N` | Deep fetch (+ player gamelogs, N days out) |
| POST | `/place_bet` | Place order (read/write key) |
| POST | `/cancel_order` | Cancel order (read/write key) |

### Kalshi Keys
- Read-only: `5a3ad6f1-a741-42a3-8ce6-20ce32529d7a` → `thirdAPIKEY_converted.txt`
- Read/write: `e98fa333-9d9c-4402-a345-545ec5736023` → `orbitingrectangle12_converted.txt`
- Both keys need PKCS#8 conversion: `openssl pkcs8 -topk8 -nocrypt -in key.txt -out key_converted.txt`
- SDK field: `config.private_key_pem` (NOT `config.private_key`)

### SDK Patches Applied (kalshi-python-sync 3.5.0)
These files were patched to use `Optional[int]` instead of `StrictInt`:
- `models/market_position.py` — total_traded, position, market_exposure, realized_pnl, fees_paid
- `models/event_position.py` — total_cost, total_cost_shares, event_exposure, realized_pnl, fees_paid
- `models/order.py` — yes_price, no_price, fill_count, remaining_count, initial_count, taker_fees, maker_fees, taker_fill_cost, maker_fill_cost, queue_position
- `models/market.py` — yes_bid, yes_ask, no_bid, no_ask, last_price, volume, open_interest, etc.
- `models/orderbook.py` — yes, no fields
- `models/get_market_orderbook_response.py` — orderbook field
⚠️ If SDK is upgraded/reinstalled, all patches must be reapplied.

---

## Prediction Models (Current — V2.3)

### Model A — Efficiency (45%)
- Net rating diff × 0.028
- Tiered injury adjustments (star -3.5%, starter -1.5%, bench -0.5%)
- Rest/B2B adjustments
- Travel adjustments
- Altitude (DEN +3%, UTA +2%)
- Team-specific HCA based on actual home/away win% spread (fallback: flat 2.5%)

### Model B — Recent Form (30%)
- L10 record (real data from ESPN schedule)
- Scoring trend (L10 pts vs season avg)
- Win streak (real data, tiered adjustments)
- Venue split (actual home win% vs away win%)
- Opponent-adjusted form (avg net rating of last 10 opponents)
- ~~ATS L10~~ — dropped, no data source

### Model C — Matchup (25%)
- Record baseline (overall win% × 0.45)
- Strength of schedule (opp_adj_form as proxy)
- Style clash (3pt rate mismatch)
- Pace mismatch
- Net rating matchup differential
- ~~H2H~~ — dropped (2-4 game sample too small)
- ~~Clutch record~~ — dropped (no API source)

### Consensus System
- 3/3 agree + edge >10% = 🔥 LOCK
- 3/3 agree = 🟢 HIGH
- 2/3 agree = 🟡 MED
- 0-1/3 agree = 🔴 LOW

---

## Props Projection Formula (Current)

```
Base = L5 × 0.50 + L10_decay × 0.30 + Season × 0.20

Where L10_decay = exponential decay weighted average (decay=0.85)
Most recent game weighted most heavily.

Adjustments applied in order:
1. Minutes adjustment (only if player avg < 28 min: scale down to max(0.7, min/30))
2. B2B penalty (-11% if player on back-to-back)
3. oppD adjustment: × (1 + ((oD - 112.5) / 112.5) × 0.4)
4. Pace adjustment: × (game_pace / 99.2)
5. Home/away: × 1.025 (home) or × 0.975 (away)
6. Blowout risk: × 0.90 (net gap >20), × 0.94 (>12), × 0.97 (>7)
7. Star-out boost: × 1.08 (star OUT), × 1.05 (2+ starters OUT), × 1.03 (1 starter OUT)
```

---

## ESPN Data Pipeline

### Fast Fetch (/fetch-espn)
- Today's scheduled games + times
- Team stats: pace-adjusted ortg/drtg, pace, net rating, wins/losses, tpr
- Home/away records
- Top 10 roster (ESPN order)
- Injuries
- Load time: ~3-5 seconds

### Deep Fetch (/fetch-espn-deep)
- Everything in fast fetch PLUS:
- Team L10 record, win streak, scoring trend (from schedule endpoint)
- Opponent-adjusted form (avg net rating of L10 opponents)
- Player gamelogs: szn avg, L5, L10 (decay-weighted), minutes
- Top 8 players per team sorted by actual minutes played
- Filters out players with 0 games this season
- Filters out traded players' pre-trade stats
- Load time: ~10-15 seconds

### ESPN Abbreviation Map
```python
ABBR_MAP = {'NY': 'NYK', 'SA': 'SAS', 'WSH': 'WAS', 'GS': 'GSW', 'NO': 'NOP', 'UTAH': 'UTA'}
```

---

## Kalshi Notes

### Current Market Structure
- Individual player props: `KXNBA2D` prefix (replaced old `NBAP`)
- Game winners: `KXNBAGAME` (limited availability in search)
- Multi-leg parlays: `KXMVECROSSCATEGORY`, `KXMVESPORTSMULTIGAMEEXTENDED`
- Search API only returns first ~200 markets — KXNBA2D often not in first page
- Direct ticker lookup works: paste exact ticker in TRADE tab input box

### Known Kalshi Issues
- Search doesn't find KXNBA2D markets (pagination problem)
- Positions show tickers but yes/no counts are null (Kalshi API returns null)
- Orders show all fields except count/price (null from Kalshi)
- Prices often null on parlay markets (illiquid)

---

## Known Issues / Still To Fix

### High Priority
- [ ] **oppD position-specific** — currently pace-adjusted team DRTG, not position-specific. Need NBA.com or position-split data.
- [ ] **Usage rate** — biggest missing variable. ESPN has it in gamelog advanced stats. Needs to be fetched and incorporated.
- [ ] **Kalshi search pagination** — only gets first 200 markets, misses KXNBA2D

### Medium Priority
- [ ] **Props UI** — collapsible per-game sections, sort by edge size, fix input focus bug (double-digit entry)
- [ ] **Player list sort** — currently top 8 by ESPN order in fast fetch; only deep fetch sorts by minutes
- [ ] **Win/loss prediction tracker** — log predictions, auto-check results via ESPN
- [ ] **Backtest** — run models on last 30-60 days of completed games

### Lower Priority
- [ ] **Ngrok** — share app with friend in SF
- [ ] **Limit order recommendation tab** — model edge vs current Kalshi price, suggest limit prices

---

## V3 Roadmap

### Model Improvements
- [ ] **H2H** — multi-season weighted (60% current, 30% last, 10% two seasons ago)
- [ ] **Clutch record** — NBA.com `stats.nba.com/stats/teamdashboardbyclutch` (requires user-agent spoofing)
- [ ] **ATS L10** — The Odds API free tier or ESPN odds endpoint
- [ ] **Matchup-specific defender** — NBA.com player defense stats
- [ ] **Role absorption** — when star is out, who gets the usage? Lineup data from NBA.com
- [ ] **Game total context** — ESPN odds endpoint for over/under

### Props Improvements
- [ ] **Usage rate** — ESPN advanced gamelog stats (USG%)
- [ ] **Minutes projection** — trend-based (last 5 games avg vs season)
- [ ] **Rest-adjusted performance** — some players significantly better on 2+ days rest
- [ ] **Opponent pace vs this team specifically** — historical H2H pace

### Infrastructure
- [ ] **Bet tracker** — P&L history, model accuracy by tier
- [ ] **Backtest engine** — run models on historical games
- [ ] **Ngrok** — public URL for remote access
- [ ] **Pandas DataFrames** — better data analysis
- [ ] **EPM integration** — Dunks & Threes EPM for player impact

---

## Version History
| Version | Key Change |
|---|---|
| V1 | 2-model system, basic props |
| V2 | 3 models + show math |
| V2.1 | Research-calibrated weights |
| V2.2 | Backtest-proven 118 games, removed double-counting |
| V2.2+Kalshi | TRADE tab, bridge.py, Kalshi API |
| V2.3 | Bridge fixed, ESPN auto+deep fetch, betting UI, startup script |
| V2.4 | Models rebuilt (B+C), team-specific HCA, date picker, props formula upgraded, pace-adjusted ratings |
