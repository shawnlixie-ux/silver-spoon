# Delta — Improvement Log

---

## Session: March 23, 2026

### Parlay Lab → Delta Rebrand

The app was fully renamed and redesigned from "Parlay Lab" to "DELTA".

**Header changes:**
- Replaced basketball emoji + "PARLAY LAB" title with Δ symbol + "DELTA" logotype
- Subtitle changed from "3-MODEL SYSTEM · KALSHI API · KELLY CRITERION" to cleaner "3-MODEL · KALSHI · KELLY"
- Bankroll input cleaned up (removed redundant $ span)
- Bridge status now shows face SVG icons: smiling face when data loaded, dizzy face when bridge offline, grinning face when bridge online

**Tab changes:**
- Removed all emojis from tabs (🟢 KALSHI → ANALYSIS, ⚡ TRADE → TRADE, etc.)
- Added TRACK tab (new — replaces no dedicated tracking UI)
- Tabs renamed: KALSHI → ANALYSIS, kept TRADE / PROPS / VALUE / KELLY / DATA / TRACK

**Visual redesign:**
- Complete CSS rewrite with new DELTA design system
- Canvas background: animated star field (twinkling), bezier path trails, shooting meteors
- DELTA title scramble animation on load
- Floating pill header + floating pill tab bar at bottom of screen
- Tubelight lamp glow effect on active tab
- All emojis replaced with custom SVG icons (fire, ice, calculator, notebook)
- Glowing card borders on LOCK items (mouse-tracking proximity glow)
- Skeleton loading states, toast notifications
- Win probability bar on game cards
- Animated counters, tooltips
- Game card smooth collapse animation
- Game filter bar (All / team pills) synced between Analysis and Props tabs
- LOCK badge shimmer animation
- localStorage persistence for bankroll, kelly fraction, model weights

---

### Model Rebuild (V3)

**Model A — Efficiency (weight: 50%)**
- Net rating blend: 70% season + 30% L10
- GTD players penalized at 40% of OUT impact (was binary)
- Back-to-back: Away B2B = +3.8% penalty, Home B2B = -1.8% (asymmetric, was flat)
- HCA now uses both teams' actual home/away records instead of flat 2.5%

**Model B — Momentum (weight: 35%)**
- Offensive heat: L10 pts vs season avg
- Trajectory signal: L5 vs L10 (improving/declining)
- L10 record weight reduced 0.65 → 0.25 (was overweighted)
- Streak capped at ±2% max
- Added venue form and opponent-adjusted form

**Model C — Vegas-First (weight: 15%)**
- When Vegas loaded: 75% Vegas (de-vigged) + 25% Pythagorean
- Fallback: Pythagorean win expectancy (pts^13.91) + margin + pace
- Removed all efficiency clash logic (was duplicating Model A)

**Weights** stored in localStorage as `delta_weights`, editable in WEIGHTS sub-tab

---

### TRACK Tab — New Feature

Three sub-tabs added under TRACK:

**TRACKER sub-tab:**
- Auto-logs all model predictions when data loads
- W/L manual override buttons on each pending game row
- CHECK RESULTS button auto-fetches ESPN scores for pending predictions
- Shows pick, model confidence %, tier badge, score when resolved
- Delete button per row
- Win/loss stats header (total W-L, win %)

**BACKTEST sub-tab:**
- Fetches last N days of ESPN completed games (configurable: 7/14/21/30/60 days)
- Runs all three models against historical outcomes using current team data
- Shows accuracy by confidence tier (LOCK / HIGH / MED / LOW)
- Shows per-model accuracy (Model A / B / C)
- Brier score + vs baseline metric
- Full game log with pick/result per game
- Note about Model C running in Pythagorean fallback during backtest

**WEIGHTS sub-tab:**
- Sliders for Model A / B / C weights (must total 100%)
- Live preview of how weight changes affect today's picks
- Apply / Reset buttons

---

### Bug Fixes This Session

**Backtest — ESPN abbreviation mismatch (root cause of 17.8% accuracy):**
- ESPN returns `GS`, `SA`, `NO`, `NY`, `WSH`, `UTAH` etc.
- Model uses `GSW`, `SAS`, `NOP`, `NYK`, `WAS`, `UTA`
- Added `ESPN_NORM` map + `norm()` function — all abbreviations normalized before team lookup
- Was causing most games to be skipped or matched to wrong teams

**Backtest — wrong game count:**
- `totalGames` was using `results.length` (all ESPN games) instead of `dayRows.length` (games model actually ran on)
- Fixed — accuracy % now divides by correct number

**Backtest — team data check (AND → OR):**
- Was using `&&` on team data check, skipping games only if BOTH teams missing
- Fixed to `||` — skips if EITHER team missing (no data = no signal)
- Added `AVG_TEAM` fallback using league averages so games still run when one team not in today's loaded data

**Backtest — requires data loaded first:**
- Added guard: shows error message if D.teams is empty when backtest runs
- Shows debug info (ESPN abbrs found vs your team keys) if 0 games match

**checkResults — always picked home team as pick:**
- `logPredictions` was hardcoding `pick: g.h` (always home team)
- Fixed: now stores `d.avg > 0.5 ? g.h : g.a` (actual model pick)

**checkResults — only checked exact prediction date:**
- Now fetches today + yesterday + all pending prediction dates
- Added `PHO`, `OKC`, `MEM`, `CLE` to ESPN abbreviation map
- Removed duplicate orphaned checkResults code block that was outside any function (syntax error)
- Now accepts games where `homeScore !== awayScore` as completed even if ESPN hasn't marked `completed: true` yet

**Startup script — path errors:**
- Fixed folder name: `API Keys` (not `API Keys & Bridge`)
- Fixed `delta_v2.html` → `Delta.html`
- Fixed bridge.py RW key path: `API Keys/orbitingrectangle12 (read : write)/`
- Script now kills port 8080 before starting, waits for bridge before opening browser

---

### Known Issues / Still To Fix

- **Backtest uses current team data as proxy** — not ideal for historical accuracy since rosters and form change. No fix without a historical stats API.
- **checkResults fuzzy matching removed** — now exact match only. If ESPN uses an abbreviation not in the map, game won't auto-resolve. Use W/L buttons as fallback.
- **Props tab oppD** — still using team average DRTG, not position-specific. NBA.com only.
- **Player list** — top 10 by ESPN order, not by minutes played.
- **Kalshi search pagination** — still only returns first page of results.

---

## Model Improvement Roadmap (carried forward)

### Model A
- [ ] Pace-adjusted ratings (true ortg/drtg per 100 possessions)
- [ ] Lineup-adjusted net rating (degraded when star is out, not flat penalty)

### Model B
- [ ] ATS L10 via The Odds API (free tier: 500 req/month)

### Model C
- [ ] Multi-season H2H (60% current / 30% last / 10% two seasons ago)
- [ ] Clutch record via `stats.nba.com` (requires user-agent spoofing)

### Props
- [ ] Position-specific opponent defense (NBA.com)
- [ ] Usage rate in deep fetch
- [ ] Sort props by edge size
- [ ] Collapsible per-game sections

### Infrastructure
- [ ] Kalshi paginated search
- [ ] Auto-ticker builder (player + game + stat → ticker format)
- [ ] Ngrok setup for remote access
