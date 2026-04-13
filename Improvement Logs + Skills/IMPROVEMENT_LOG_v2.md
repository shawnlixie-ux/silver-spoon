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
- Built DEEP FETCH endpoint with real player stats (szn, L5, L10, min)
- Fixed gamelog date sorting (cross-reference events_dict by eventId)
- Fixed season filter (2025-26 Regular Season only, no last season bleedthrough)
- Fixed traded players (filter by current team abbreviation)
- Real L10 record, win streak, scoring trend, opponent-adjusted form for teams
- Roster limited to top 10 players per team

### Known Issues / Still To Fix
- **oppD in props tab** — currently showing team average DRTG, not position-specific defense. Still incorrect for individual player matchups. Need NBA.com or position-split data.
- **Minutes** — L10 average minutes is close but off by ~0.5 vs ESPN. Acceptable for now.
- **Stats accuracy** — off by 0.1-0.2 on some players due to rounding differences vs ESPN. Acceptable.
- **Player list** — currently top 10 by ESPN order. Should eventually sort by actual minutes played.

---

## Model Improvement Roadmap

### Why H2H and Clutch are currently dropped
- **H2H:** ESPN season series has 2-4 game sample — too small to be reliable. Worth adding when multi-season H2H is available.
- **Clutch record:** Win/loss in games decided by 5 pts. NBA.com has this (`stats.nba.com/stats/teamdashboardbyclutch`) but requires user-agent spoofing. Add in V3.

### Goals — Model A (Efficiency, currently 45%)
- [ ] **Team-specific HCA** — replace flat 2.5% with actual home win% spread per team. Data available from ESPN home/away records already fetched.
- [ ] **Lineup-adjusted net rating** — degraded net rating when star is out, not just flat penalty.
- [ ] **Pace-adjusted ratings** — true ortg/drtg per 100 possessions (ESPN has `paceFactor` and `possessions`).

### Goals — Model B (Momentum, currently 30% — needs rebuild)
Current state: L10, streak, ATS all defaulted. Now have real L10/streak data from deep fetch.

Rebuild plan:
- [x] **Real L10 record** — fetched from ESPN schedule ✅
- [x] **Real win streak** — calculated from schedule ✅
- [x] **Real scoring trend** — L10 pts vs season avg ✅
- [x] **Opponent-adjusted form** — avg net rating of last 10 opponents ✅
- [ ] **Wire these into Model B** — currently fetched but not used in model yet
- [ ] **Drop ATS** — no reliable free data source
- [ ] **ATS L10 (future)** — The Odds API or ESPN odds endpoint

### Goals — Model C (Matchup, currently 25%)
- [ ] **Drop H2H** — small sample, add back with multi-season data later
- [ ] **Drop clutch** — no API source, add back with NBA.com scraping
- [ ] **Strength of schedule** — avg net rating of last 10 opponents (already calculated in opp_adj_form)
- [ ] **Pace-adjusted scoring diff** — pts per 100 possessions diff
- [ ] **Keep:** pace mismatch, style clash, record baseline

### Goals — H2H (Future V3)
- [ ] Multi-season H2H weighted by recency (60% current, 30% last, 10% two seasons ago)
- [ ] ESPN schedule historical data

### Goals — Clutch Record (Future V3)
- [ ] `stats.nba.com/stats/teamdashboardbyclutch` — requires user-agent spoofing
- [ ] Alternative: track from ESPN play-by-play data

### Goals — ATS / Vegas Lines (Future V3)
- [ ] The Odds API (free tier: 500 req/month) — `api.the-odds-api.com`
- [ ] ESPN odds: `sports.core.api.espn.com/v2/.../events/{event}/competitions/{comp}/odds`

---

## Player Props Model Roadmap

### Deep Fetch — Completed
- [x] Player gamelogs → szn avg, L5, L10, minutes per game
- [x] Correct season filtering (2025-26 only)
- [x] Traded player handling (current team only)
- [x] Date-sorted games for accurate L5/L10

### Still To Build
- [ ] **oppD fix** — position-specific opponent defense (NBA.com only)
- [ ] **Usage rate** — ESPN has it in advanced stats, need to add to gamelog fetch
- [ ] **Minutes projection** — based on recent minutes trend + injury status
- [ ] **Prop UI improvements** — collapsible per-game sections, sort by edge size

### oppD Issue
Current: using team average DRTG as opponent defense proxy
Problem: a PG vs a good PG-defending team ≠ team avg DRTG
Fix options:
- NBA.com positional defense stats (requires scraping)
- Manual override in JSON for key matchups
- Use opponent DRTG rank as a proxy (better than raw number)

---

## Data Pipeline Status

### Currently Working
- ESPN auto-fetch: games, team stats, rosters (top 10), injuries (~3-5s)
- ESPN deep fetch: all above + player gamelogs + team L10/streak/trend (~10-15s)
- Parallel fetching with ThreadPoolExecutor

### To Build
- [ ] Player sorting by minutes (not ESPN roster order)
- [ ] Usage rate in deep fetch
- [ ] Collapsible game groups in props tab

---

## Kalshi Integration Notes

### Current State
- Individual player prop markets use `KXNBA2D` prefix (changed from `NBAP`)
- Search API only returns first page — `KXNBA2D` markets often not in first 200
- Direct ticker lookup works via `/market/<ticker>` and direct input box
- Parlay markets: `KXMVECROSSCATEGORY` / `KXMVESPORTSMULTIGAMEEXTENDED`
- Prices often null on parlay markets (illiquid)
- Read-only key: `5a3ad6f1-a741-42a3-8ce6-20ce32529d7a` (thirdAPIKEY_converted.txt)
- Read/write key: `e98fa333-9d9c-4402-a345-545ec5736023` (orbitingrectangle12_converted.txt)

### To Fix
- [ ] Paginated search — fetch all pages until query match found
- [ ] Auto-ticker builder — given player + game + stat, try common ticker formats

---

## Next Session Priorities
1. Wire real L10/streak/opp_adj_form data into Model B
2. Rebuild Model B and C with real data
3. Fix oppD (position-specific or better proxy)
4. Props tab UI — collapsible per game, sort by edge, fix input focus bug
5. Ngrok setup for friend in SF to access
