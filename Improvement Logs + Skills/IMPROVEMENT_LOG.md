# Parlay Lab — Improvement Log

## Session: March 17-18, 2026

### Completed Today
- Fixed bridge connection (PKCS#8 key conversion, SDK upgrade to 3.5.0)
- Fixed positions/orders SDK model patches
- Built ESPN auto-fetch pipeline with parallel threading
- Added AUTO-FETCH button to DATA tab
- Added dual API key setup (read-only for data, read/write for betting)
- Built betting UI (confirmation modal, quick size buttons, cancel orders)
- Added startup script (`start_parlay_lab.sh`)
- Added direct ticker input for Kalshi markets

---

## Model Improvement Roadmap

### Why H2H and Clutch are currently dropped
- **H2H (Head-to-Head):** ESPN exposes season series records but the sample size is tiny (2-4 games). With only 2-4 meetings per season the signal is too noisy to be reliable. Worth adding back when we can get multi-season H2H weighted by recency.
- **Clutch record:** Win/loss in games decided by 5 pts or less. NBA.com has this data but requires scraping. ESPN doesn't expose it via API. Will add when we tackle NBA.com scraping.

### Goals — Model A (Efficiency, currently 45%)
- [ ] **Team-specific HCA** — replace flat 2.5% with actual home win% spread per team. Some teams are +8% at home (DEN, BOS), others barely +1%. Data source: ESPN home/away records (already in fetch, just not being used for HCA).
- [ ] **Lineup-adjusted net rating** — when a star is out, use a degraded net rating not just the flat injury penalty. Would need usage rate data.
- [ ] **Pace-adjusted ratings** — use true ortg/drtg per 100 possessions instead of points per game as proxy.

### Goals — Model B (Momentum, currently 30% — needs full rebuild)
Current state: Almost entirely fake (L10, streak, ATS all default to 0/5-5).

Rebuild plan:
- [ ] **Real L10 record** — fetch from ESPN schedule endpoint, count last 10 game results
- [ ] **Real win streak** — calculate from schedule, count current consecutive W or L
- [ ] **Real scoring trend** — L10 pts avg vs season avg, from schedule results
- [ ] **Opponent-adjusted form** — weight recent wins/losses by opponent net rating (win vs OKC worth more than win vs WAS). Biggest single upgrade possible.
- [ ] **Drop ATS** — no reliable free data source. Future: The Odds API (free tier) for Vegas lines.
- [ ] **ATS L10 (future)** — The Odds API or ESPN odds endpoint. Teams consistently beating the spread have real edge.

### Goals — Model C (Matchup, currently 25%)
Current state: Mixed — record baseline/pace/style real, H2H/clutch fake.

Rebuild plan:
- [ ] **Drop H2H** — too small sample size per season. Add back when multi-season H2H available.
- [ ] **Drop clutch record** — no API source. Add back when NBA.com scraping built.
- [ ] **Strength of schedule** — average net rating of last 10 opponents. Available from schedule fetch.
- [ ] **Pace-adjusted scoring diff** — pts per 100 possessions diff instead of raw pts diff.
- [ ] **Keep:** pace mismatch, style clash (3pt rate), record baseline.

### Goals — H2H (Future — V3)
- [ ] Multi-season H2H weighted by recency (current season 60%, last season 30%, 2 seasons ago 10%)
- [ ] Data source: ESPN schedule historical data or Basketball-Reference scraping

### Goals — Clutch Record (Future — V3)
- [ ] NBA.com stats API: `stats.nba.com/stats/teamdashboardbyclutch`
- [ ] Requires user-agent spoofing (NBA.com blocks bots)
- [ ] Alternative: track it ourselves from ESPN play-by-play data

### Goals — ATS / Vegas Lines (Future — V3)
- [ ] The Odds API (free tier: 500 requests/month) — `api.the-odds-api.com`
- [ ] ESPN odds endpoint: `sports.core.api.espn.com/v2/sports/basketball/leagues/nba/events/{event}/competitions/{comp}/odds`
- [ ] Would unlock ATS L10, line movement tracking, and sharp money indicators

---

## Player Props Model Roadmap

### Deep Fetch — To Build Next
- [ ] Player gamelogs → szn avg, L5, L10, minutes per game
- [ ] Usage rate per player (ESPN advanced stats)
- [ ] Pace-adjusted player stats
- [ ] Opponent position-specific defense (future — NBA.com only)
- [ ] Minutes projection model (future — based on recent minutes trend + injury status)

### Projection Formula Improvements
Current: `Base = L10 × 0.45 + Season × 0.35 + L5 × 0.20`

Proposed upgrades:
- [ ] Add usage rate adjustment — high usage player on fast team = more scoring opportunities
- [ ] Add opponent pace adjustment — playing vs high-pace team increases possessions
- [ ] Add blowout risk refinement — use actual point spread not just net rating gap
- [ ] Add position-specific opponent DRTG (when available)
- [ ] Add minutes projection — if player averaging 32 min but 28 in last 5, project 28 not 32

---

## Data Pipeline Roadmap

### Currently Working
- ESPN auto-fetch: games, team stats (ortg/drtg/pace/record), rosters, injuries
- Parallel fetching (~3-5 seconds for 8 games)

### To Build — Deep Fetch
- [ ] Player gamelogs (L5/L10/szn/min/usage) — ~130 calls, parallel, ~10-15 sec
- [ ] Team schedule last 10 (L10 record/streak/trend) — ~16 calls, parallel, fast
- [ ] Better home/away records reliability

### Future Data Sources
- [ ] The Odds API — Vegas lines, ATS tracking
- [ ] NBA.com — clutch records, position defense, lineup data
- [ ] Basketball-Reference — multi-season H2H, historical splits
- [ ] EPM (Dunks & Threes) — player impact metric for game model

---

## Kalshi Integration Notes

### Current State
- Individual player prop markets now use `KXNBA2D` prefix (changed from `NBAP`)
- Search API only returns first page of results — `KXNBA2D` markets often not in first 200
- Direct ticker lookup works via `/market/<ticker>` endpoint
- Game winner markets (`KXNBAGAME`) may also be limited in search
- All multi-leg parlay markets use `KXMVECROSSCATEGORY` / `KXMVESPORTSMULTIGAMEEXTENDED`
- Prices often null on parlay markets (illiquid)

### To Fix
- [ ] Paginated search — fetch all pages until query match found
- [ ] Auto-ticker builder — given player name + game + stat type, try common ticker formats
- [ ] Show Kalshi odds in props tab when ticker is found
