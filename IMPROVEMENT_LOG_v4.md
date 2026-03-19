# Parlay Lab — Improvement Log v4

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
- Model B rebuilt — dropped ATS, added opponent-adjusted form
- Model C rebuilt — dropped H2H and clutch, added SOS and net rating matchup
- Model A upgraded — team-specific HCA (fallback to 2.5%)
- Future game date picker (Today/+1/+2/+3 days)
- Props player quality fixed — sort by minutes, filter 0-game players, top 8 per team
- Props projection formula upgraded:
  - L5 50%, L10 30%, Season 20%
  - Exponential decay on L10 (decay=0.85)
  - B2B penalty (-11%)
  - Minutes adjustment (sub-28min players only)
  - oppD multiplier softened (0.8→0.4)
  - Home/away proportional (±2.5%)
  - Tiered blowout risk
  - Star-out usage boost
- Pace-adjusted ortg/drtg (per 100 possessions)

---

### Completed
- Vegas odds via Odds API — fetch moneyline odds, convert to implied probability, show VEGAS % column on game cards
- Team logos added to Kalshi tab game headers and Props tab player cards + game headers
- Props confidence % — STRONG/LEAN/NEUTRAL badges now show % over/under line with glow effect on STRONG
- Collapsible game cards on both Kalshi tab and Props tab
- Props line input fix — onchange instead of oninput, no more focus loss on multi-digit entry
- Manual injury input UI — autocomplete player search, OUT/GTD/PLAY status, Star/Starter tier, instant model update
- Model B fixes — venue split now uses real home/away data (was defaulting to 57/43%), stronger streak penalties (up to ±6% for 10+ game streaks), L10 weight increased 0.50→0.65
- Fixed home/away record parsing — ESPN uses "Home"/"Road" not "home"/"road" (case sensitive bug)
- Props formula upgraded — L5 50%, decay-weighted L10 30%, season 20%, B2B penalty, tiered blowout, star-out boost, proportional home/away, softer oppD multiplier, minutes adjustment
- Pace-adjusted ortg/drtg (per 100 possessions)
- Usage rate via avgEstimatedPossessions from ESPN advanced stats
- Exponential decay L10 weighting (decay=0.85) in bridge.py
- Injury impact by PPG tier (25+/18-25/12-18/6-12/<6) instead of flat star/starter/bench
- Future game date picker (Today/+1/+2/+3 days)
- GitHub repo set up (silver-spoon)

### Known Issues
- BallDontLie injuries endpoint requires paid tier — manual input is current workaround
- NBA.com and ESPN injury APIs unreliable/blocked
- Vegas gap still exists (~10-15%) due to missing injury info and matchup-specific data we don't have
- nba_api installed but only has scoreboard/boxscore/playbyplay/odds — no injury endpoint

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
# Open: http://127.0.0.1:8080/Parlay_Lab_Kalshi%20current.html
```

### Bridge Port: 5001
### Kalshi Keys
- Read-only: `5a3ad6f1-a741-42a3-8ce6-20ce32529d7a` → `thirdAPIKEY_converted.txt`
- Read/write: `e98fa333-9d9c-4402-a345-545ec5736023` → `orbitingrectangle12_converted.txt`
- Key conversion: `openssl pkcs8 -topk8 -nocrypt -in key.txt -out key_converted.txt`
- SDK field: `config.private_key_pem`

### SDK Patches (kalshi-python-sync 3.5.0)
Patched to Optional[int]: market_position, event_position, order, market, orderbook, get_market_orderbook_response
⚠️ Must reapply if SDK upgraded/reinstalled

---

## Prediction Models (V2.4 — Current)

### Model A — Efficiency (45%)
- Net rating diff × 0.028
- Tiered injury adjustments (star -3.5%, starter -1.5%, bench -0.5%)
- Rest/B2B, travel, altitude (DEN +3%, UTA +2%)
- Team-specific HCA from actual home/away win% spread

### Model B — Recent Form (30%)
- L10 record (real ESPN schedule data)
- Scoring trend (L10 pts vs season avg)
- Win streak (tiered)
- Venue split (actual home/away win%)
- Opponent-adjusted form (avg net rating of L10 opponents)

### Model C — Matchup (25%)
- Record baseline (win% × 0.45)
- Strength of schedule (opp_adj_form)
- Style clash (3pt rate mismatch)
- Pace mismatch
- Net rating matchup diff

### Consensus: LOCK/HIGH/MED/LOW tiers

---

## Props Projection Formula (V2.4)
```
Base = L5×0.50 + L10_decay×0.30 + Season×0.20
L10_decay = exponential decay weighted (decay=0.85)

Adjustments:
1. Minutes (sub-28min: scale down)
2. B2B penalty (-11%)
3. oppD: × (1 + ((oD-112.5)/112.5) × 0.4)
4. Pace: × (game_pace/99.2)
5. Home/away: ×1.025 / ×0.975
6. Blowout: ×0.90/>20, ×0.94/>12, ×0.97/>7
7. Star-out boost: ×1.08/×1.05/×1.03
```

---

## ESPN Data Pipeline

### Fast Fetch (/fetch-espn?offset=N)
Games, team stats (pace-adjusted), rosters (top 10), injuries — ~3-5s

### Deep Fetch (/fetch-espn-deep?offset=N)
Everything above + player gamelogs (szn/L5/L10_decay/min) + team L10/streak/trend/opp_adj_form
Top 8 per team by actual minutes, filters 0-game players, current team only for traded players — ~10-15s

---

## Kalshi Notes
- Individual props: `KXNBA2D` prefix
- Game winners: `KXNBAGAME`
- Parlays: `KXMVECROSSCATEGORY`, `KXMVESPORTSMULTIGAMEEXTENDED`
- Search only returns first ~200 markets — KXNBA2D often missed
- Direct ticker input works in TRADE tab

---

## IMMEDIATE GOALS (Next 1-3 Sessions)

### 1. Usage Rate [ ]
- **What:** % of team possessions a player uses when on floor
- **Why:** Single biggest missing variable. 18pts on 22% usage ≠ 18pts on 30% usage
- **Source:** ESPN advanced stats endpoint (separate from standard gamelog)
- **How to use:** Multiply base projection by usage ratio vs league avg (league avg ~20%)
- **Status:** ESPN gamelog labels don't include USG% — need to check advanced endpoint

### 2. Props Confidence Score [ ]
- **What:** Tier each prop projection (STRONG/LEAN/NEUTRAL) with visual indicator
- **Why:** 5pts over line is very different from 0.3pts over
- **How:** |projection - line| / line × 100 = confidence %, then tier it
- Currently shows OVER/UNDER but no confidence level on the difference

### 3. Props UI Improvements [ ]
- Collapsible per-game sections (currently one long scroll)
- Sort by edge size (biggest projection vs line gap first)
- Fix double-digit input focus bug (have to click again after first digit)
- Show confidence tier badge per player

### 4. Auto-Refresh / Status Update [ ]
- Refresh button that re-fetches injury status mid-day
- Live injury updates without full re-fetch
- Alert when a key player is newly listed as OUT/GTD

### 5. Kalshi Search Pagination [ ]
- Paginate through all market pages to find KXNBA2D props
- Auto-ticker builder: player name + game + stat → try common ticker formats

### 6. Smarter Injury Impact [ ]
- Tier injured player impact by their actual scoring avg, not just starter/bench
- If injured player averages 25+pts, treat as star-level impact regardless of label
- Currently all starters get same -1.5% regardless of who they are

---

## MEDIUM TERM GOALS (Next Month)

### 7. Win/Loss Prediction Tracker [ ]
- Log each game's predictions when data loads
- Auto-check results via ESPN scores
- Running record by confidence tier (LOCK: X/Y, HIGH: X/Y, etc.)
- Model accuracy over time dashboard

### 8. Backtest Engine [ ]
- Run models on last 30-60 days of completed games
- Use current stats (approximate — late season stats stable)
- Get real accuracy numbers by confidence tier
- Find optimal model A/B/C weights via regression

### 9. Limit Order Recommendation Tab [ ]
- Pull current Kalshi prices for tonight's games
- Compare to model probability
- Suggest: "Place limit YES at 58¢ — model says 65%, worth waiting for"
- One-click to load ticker into TRADE tab
- Kelly sizing at recommended price

### 10. Correlated Props Warning [ ]
- Flag when two bets are correlated (Jokic over + Denver win)
- Show correlation risk level
- Suggest bet sizing adjustment

### 11. Game Total Projection [ ]
- Project combined score for each game
- Useful for pace-dependent prop decisions
- Formula: (hT.ortg + aT.ortg) / 2 × pace_factor

### 12. Ngrok / Remote Access [ ]
- One command to share app with friend
- `ngrok http 8080` → public URL
- Friend can view and analyze without running bridge

### 13. Bankroll Management [ ]
- Full Kelly bankroll tracker
- Session P&L
- Drawdown warnings (stop betting if down X%)
- Running ROI

### 14. Multi-Game Parlay Builder [ ]
- Since Kalshi is mostly parlays, find best combinations
- Take top 3-5 model picks, show parlay probability
- Calculate expected value of parlay vs single bets

---

## LONG TERM / V3 GOALS

### 15. NBA.com Integration [ ]
- Clutch records (stats.nba.com/stats/teamdashboardbyclutch)
- Position-specific opponent defense
- Lineup data (who plays with who)
- Requires user-agent spoofing to avoid blocks

### 16. Vegas Lines / Odds API [ ]
- The Odds API (free tier: 500 req/month)
- ATS L10 tracking
- Line movement alerts
- Sharp money indicators

### 17. H2H Multi-Season [ ]
- Weight current season 60%, last 30%, two seasons ago 10%
- ESPN schedule historical data

### 18. Machine Learning Layer [ ]
- Train on backtest data to optimize A/B/C weights
- Replace hardcoded 45/30/25 with data-driven weights
- Retrain monthly as season progresses

### 19. Live In-Game Props [ ]
- During a game, project final stats based on current pace + time remaining
- "Jokic has 18pts with 8 min left in 3rd — projected finish: 28pts"
- Kalshi has live markets

### 20. Monte Carlo Simulation [ ]
- Run 1000 simulated games, show probability distribution
- "Jokic scores 25+ with 67% probability"
- More useful than single point projection

### 21. Opponent-Specific Player Projections [ ]
- How does this player historically perform vs this specific team
- Multi-season weighted
- More predictive than general team DRTG

### 22. Discord/Slack Alerts [ ]
- Push notification when model finds 15%+ edge
- Injury alert when key player newly OUT
- Morning summary of today's best plays

### 23. Season-Long Dashboard [ ]
- Track model accuracy week by week
- Which teams model is best/worst at predicting
- Which confidence tiers are actually profitable
- Visual charts of performance over time

### 24. EPM Integration [ ]
- Dunks & Threes EPM (free, updated regularly)
- Better player impact metric than +/- or PER
- Use for game model and lineup impact estimates

### 25. Travel Fatigue Model [ ]
- Timezone changes (EST→PST more impactful than PST→EST)
- Coast-to-coast on short rest
- Number of road games in last 7 days
- More granular than just "traveled: true"

### 26. Minute Projection Model [ ]
- Predict actual minutes tonight based on:
  - Recent minutes trend
  - Injury status of teammates
  - Game script prediction (blowout = reduced minutes)
  - Coach tendencies

### 27. Shot Quality vs Volume [ ]
- True shooting % over L10 (efficiency metric)
- Consistent efficient scorer vs high-variance volume scorer
- Affects projection confidence level

### 28. Bet Correlation Matrix [ ]
- Show correlation between all current bets
- Portfolio-level risk management
- Kelly adjustment for correlated positions

---

## HOW TO IMPROVE PREDICTIONS — KEY INSIGHTS

### Game Model
1. **Net rating source** — ESPN's numbers drift from NBA.com's official ratings. NBA.com integration (V3) would improve baseline accuracy.
2. **Same-day lineup changes** — model doesn't fully reflect late injury news. Auto-refresh helps.
3. **Model weights are hardcoded** — backtest will tell us optimal weights. After 200 games, run regression.
4. **Season progress factor** — HCA weakens late in season for playoff teams. Could add.

### Props Model
1. **Usage rate** — single biggest missing variable. Next to implement.
2. **Minutes projection** — we use L10 avg but tonight's minutes depend on rotation decisions.
3. **Shot quality** — efficient vs volume scorer affects consistency.
4. **Position-specific pace** — a slow team might play fast against guard-heavy offense.
5. **Teammate absence asymmetry** — PG out → SG gets ball-handling boost. PF out → C gets post opportunities. We treat all absences equally.

---

## Version History
| Version | Key Change |
|---|---|
| V1 | 2-model system, basic props |
| V2 | 3 models + show math |
| V2.1 | Research-calibrated weights |
| V2.2 | Backtest-proven 118 games |
| V2.2+Kalshi | TRADE tab, bridge.py, Kalshi API |
| V2.3 | Bridge fixed, ESPN fetches, betting UI, startup script |
| V2.4 | Models rebuilt, HCA, date picker, props formula v2, pace-adjusted ratings |
