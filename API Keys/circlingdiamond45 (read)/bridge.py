"""
PARLAY LAB — KALSHI BRIDGE SERVER
Flask middleware that sits between the HTML frontend and Kalshi's API.
Run this locally: python bridge.py
Frontend talks to http://127.0.0.1:5001

Endpoints:
  GET  /status         — Check if bridge is alive + authenticated
  GET  /balance        — Get account balance
  GET  /search?q=...   — Search open markets by keyword
  GET  /orderbook/<ticker> — Get orderbook for a specific ticker
  GET  /positions      — Get current portfolio positions
  GET  /orders         — Get recent orders
  GET  /market/<ticker> — Single market details
  POST /place_bet      — Place a limit order (NO side by default)
  POST /cancel_order   — Cancel an open order
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import os
from kalshi_python_sync import Configuration, KalshiClient

app = Flask(__name__)
CORS(app)



# ─── AUTHENTICATION ───────────────────────────────────
# On Railway: set KALSHI_KEY_ID and KALSHI_PRIVATE_KEY env vars.
# Locally: falls back to reading the key files as before.
import sys

def _load_pem(env_var_name, fallback_file):
    raw = os.environ.get(env_var_name, '').strip()
    print(f"[bridge] {env_var_name}: {'SET (len={})'.format(len(raw)) if raw else 'NOT SET or empty'}", file=sys.stderr)
    if raw:
        pem = raw.replace('\\n', '\n')
        if '\n' not in pem and ' ' in pem:
            print(f"[bridge] {env_var_name}: detected spaces instead of newlines — auto-fixing", file=sys.stderr)
            pem = pem.replace('-----BEGIN PRIVATE KEY----- ', '-----BEGIN PRIVATE KEY-----\n')
            pem = pem.replace(' -----END PRIVATE KEY-----', '\n-----END PRIVATE KEY-----')
            parts = pem.split('\n')
            fixed_lines = []
            for part in parts:
                if part.startswith('-----') or not part:
                    fixed_lines.append(part)
                else:
                    b64 = part.replace(' ', '')
                    fixed_lines.extend([b64[i:i+64] for i in range(0, len(b64), 64)])
            pem = '\n'.join(fixed_lines) + '\n'
        return pem
    if os.path.exists(fallback_file):
        print(f"[bridge] {env_var_name}: falling back to file {fallback_file}", file=sys.stderr)
        with open(fallback_file, "r") as f:
            return f.read()
    print(f"[bridge] FATAL: {env_var_name} not set and file '{fallback_file}' not found.", file=sys.stderr)
    print(f"[bridge] Available KALSHI_* vars: {[k for k in os.environ if 'KALSHI' in k]}", file=sys.stderr)
    sys.exit(1)

config = Configuration(host="https://api.elections.kalshi.com/trade-api/v2")
config.api_key_id = os.environ.get('KALSHI_KEY_ID', '5a3ad6f1-a741-42a3-8ce6-20ce32529d7a')
config.private_key_pem = _load_pem('KALSHI_PRIVATE_KEY', 'thirdAPIKEY_converted.txt')
client = KalshiClient(config)

# ─── READ/WRITE CLIENT (for placing/cancelling orders only) ───────────────
# On Railway: set KALSHI_RW_KEY_ID and KALSHI_RW_PRIVATE_KEY env vars.
RW_KEY_DIR = "/Applications/Betting Project/API Keys/orbitingrectangle12 (read : write)"
rw_config = Configuration(host="https://api.elections.kalshi.com/trade-api/v2")
rw_config.api_key_id = os.environ.get('KALSHI_RW_KEY_ID', 'e98fa333-9d9c-4402-a345-545ec5736023')
rw_config.private_key_pem = _load_pem('KALSHI_RW_PRIVATE_KEY', os.path.join(RW_KEY_DIR, 'orbitingrectangle12_converted.txt'))
rw_client = KalshiClient(rw_config)

ODDS_API_KEY = '4e95ed44b922d40231f0bf295268a7de'
BALLDONTLIE_API_KEY = 'c1462bb4-5409-4ce9-bf02-4c345f5e3a6a'

ODDS_TEAM_MAP = {
    'Atlanta Hawks': 'ATL', 'Boston Celtics': 'BOS', 'Brooklyn Nets': 'BKN',
    'Charlotte Hornets': 'CHA', 'Chicago Bulls': 'CHI', 'Cleveland Cavaliers': 'CLE',
    'Dallas Mavericks': 'DAL', 'Denver Nuggets': 'DEN', 'Detroit Pistons': 'DET',
    'Golden State Warriors': 'GSW', 'Houston Rockets': 'HOU', 'Indiana Pacers': 'IND',
    'Los Angeles Clippers': 'LAC', 'Los Angeles Lakers': 'LAL', 'Memphis Grizzlies': 'MEM',
    'Miami Heat': 'MIA', 'Milwaukee Bucks': 'MIL', 'Minnesota Timberwolves': 'MIN',
    'New Orleans Pelicans': 'NOP', 'New York Knicks': 'NYK', 'Oklahoma City Thunder': 'OKC',
    'Orlando Magic': 'ORL', 'Philadelphia 76ers': 'PHI', 'Phoenix Suns': 'PHX',
    'Portland Trail Blazers': 'POR', 'Sacramento Kings': 'SAC', 'San Antonio Spurs': 'SAS',
    'Toronto Raptors': 'TOR', 'Utah Jazz': 'UTA', 'Washington Wizards': 'WAS'
}

@app.route('/status', methods=['GET'])
def status():
    try:
        bal = client.get_balance()
        return jsonify({"status": "connected", "balance": bal.balance, "auth": True})
    except Exception as e:
        return jsonify({"status": "error", "auth": False, "message": str(e)}), 500


@app.route('/balance', methods=['GET'])
def get_balance():
    try:
        bal = client.get_balance()
        return jsonify({"balance": bal.balance, "payout": getattr(bal, 'payout', 0)})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/search', methods=['GET'])
def search_markets():
    import requests as req
    from kalshi_python_sync.auth import KalshiAuth
    query = request.args.get('q', '')
    limit = int(request.args.get('limit', 200))
    series = request.args.get('series', '')
    try:
        auth = KalshiAuth(config.api_key_id, config.private_key_pem)

        # Base params — always filter to open markets only
        base_params = {"limit": 200, "status": "open"}
        if series:
            # series_ticker filters server-side (works for exact series IDs)
            base_params["series_ticker"] = series

        url = 'https://api.elections.kalshi.com/trade-api/v2/markets'

        def fetch_page(cursor=None):
            p = dict(base_params)
            if cursor:
                p["cursor"] = cursor
            h = auth.create_auth_headers('GET', '/trade-api/v2/markets')
            h['Content-Type'] = 'application/json'
            return req.get(url, headers=h, params=p).json()

        # For keyword searches, paginate up to 5 pages (1000 markets) so we
        # don't miss NBA markets that sit beyond the first 200 results.
        # For no-keyword calls (just series filter) one page is enough.
        markets_raw = []
        data = fetch_page()
        markets_raw.extend(data.get('markets', []))

        if query:
            cursor = data.get('cursor')
            for _ in range(4):          # up to 4 more pages = 1000 markets total
                if not cursor:
                    break
                data = fetch_page(cursor)
                batch = data.get('markets', [])
                markets_raw.extend(batch)
                cursor = data.get('cursor') if batch else None

        # Client-side text filter (only when a query term is given)
        if query:
            q_lower = query.lower()
            markets_raw = [m for m in markets_raw if
                q_lower in m.get('ticker', '').lower() or
                q_lower in m.get('title', '').lower()]

        results = []
        for m in markets_raw[:limit]:   # honour the caller's requested limit
            results.append({
                "ticker": m.get('ticker', ''),
                "title": m.get('title', ''),
                "subtitle": m.get('subtitle', ''),
                "yes_bid": m.get('yes_bid'),
                "yes_ask": m.get('yes_ask'),
                "no_bid": m.get('no_bid'),
                "no_ask": m.get('no_ask'),
                "last_price": m.get('last_price'),
                "volume": m.get('volume') or 0,
                "open_interest": m.get('open_interest') or 0,
                "status": m.get('status', ''),
                "close_time": m.get('close_time', ''),
            })
        return jsonify({"count": len(results), "markets": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/debug-search', methods=['GET'])
def debug_search():
    """Hit /debug-search?q=nba in your browser to see raw Kalshi ticker names.
    Helps identify the correct series prefix (KXNBA2D, NBAP, etc.)"""
    import requests as req
    from kalshi_python_sync.auth import KalshiAuth
    query = request.args.get('q', 'nba').lower()
    try:
        auth = KalshiAuth(config.api_key_id, config.private_key_pem)
        url = 'https://api.elections.kalshi.com/trade-api/v2/markets'
        h = auth.create_auth_headers('GET', '/trade-api/v2/markets')
        h['Content-Type'] = 'application/json'
        r = req.get(url, headers=h, params={"limit": 200, "status": "open"}).json()
        all_markets = r.get('markets', [])
        matches = [
            {"ticker": m.get('ticker'), "title": m.get('title'), "status": m.get('status')}
            for m in all_markets
            if query in m.get('ticker', '').lower() or query in m.get('title', '').lower()
        ]
        # Also return the first 5 raw tickers so you can see the naming pattern
        sample = [m.get('ticker') for m in all_markets[:10]]
        return jsonify({
            "query": query,
            "total_open_markets_page1": len(all_markets),
            "matches": matches,
            "sample_tickers_first_10": sample,
            "cursor": r.get('cursor')
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/orderbook/<ticker>', methods=['GET'])
def get_orderbook(ticker):
    depth = int(request.args.get('depth', 10))
    try:
        response = client.get_market_orderbook(ticker=ticker)
        ob = response.orderbook
        if ob is None:
            return jsonify({"ticker": ticker, "yes": [], "no": [], "note": "No orderbook available for this market"})
        return jsonify({
            "ticker": ticker,
            "yes": [{"price": level[0], "qty": level[1]} for level in (ob.yes or [])[:depth]],
            "no": [{"price": level[0], "qty": level[1]} for level in (ob.no or [])[:depth]],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/place_bet', methods=['POST'])
def place_bet():
    data = request.json
    order_id = str(uuid.uuid4())
    side = data.get('side', 'no')
    action = data.get('action', 'buy')
    order_type = data.get('type', 'limit')
    try:
        params = {
            "ticker": data['ticker'], "action": action,
            "side": side, "count": int(data['count']),
            "type": order_type, "client_order_id": order_id,
        }
        if order_type == "limit":
            if side == "no":
                params["no_price"] = int(data['price'])
            else:
                params["yes_price"] = int(data['price'])
        response = rw_client.create_order(**params)
        return jsonify({"status": "success", "order_id": response.order.order_id, "client_order_id": order_id})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route('/cancel_order', methods=['POST'])
def cancel_order():
    data = request.json
    try:
        rw_client.cancel_order(order_id=data['order_id'])
        return jsonify({"status": "cancelled", "order_id": data['order_id']})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route('/positions', methods=['GET'])
def get_positions():
    try:
        response = client.get_positions(limit=200)
        positions = []
        for p in response.market_positions:
            positions.append({
                "ticker": p.ticker,
                "yes_count": p.position if (p.position or 0) > 0 else 0,
                "no_count": abs(p.position) if (p.position or 0) < 0 else 0,
                "avg_yes_price": p.market_exposure or 0,
                "avg_no_price": p.market_exposure or 0,
                "realized_pnl": p.realized_pnl or 0,
            })
        return jsonify({"count": len(positions), "positions": positions})
    except Exception as e:
        return jsonify({"count": 0, "positions": [], "warning": str(e)})


@app.route('/orders', methods=['GET'])
def get_orders():
    status_filter = request.args.get('status', '')
    try:
        params = {"limit": 50}
        if status_filter:
            params["status"] = status_filter
        response = client.get_orders(**params)
        orders = []
        for o in response.orders:
            orders.append({
                "order_id": o.order_id, "ticker": o.ticker,
                "side": o.side, "action": o.action,
                "type": o.type, "count": o.initial_count or 0,
                "price": getattr(o, 'yes_price', None) or getattr(o, 'no_price', None) or 0,
                "status": o.status, "created_time": getattr(o, 'created_time', ''),
            })
        return jsonify({"count": len(orders), "orders": orders})
    except Exception as e:
        return jsonify({"count": 0, "orders": [], "warning": str(e)})

@app.route('/market/<ticker>', methods=['GET'])
def get_market(ticker):
    try:
        response = client.get_market(ticker=ticker)
        m = response.market
        return jsonify({
            "ticker": m.ticker, "title": m.title,
            "subtitle": getattr(m, 'subtitle', ''),
            "status": m.status,
            "yes_bid": getattr(m, 'yes_bid', None),
            "yes_ask": getattr(m, 'yes_ask', None),
            "no_bid": getattr(m, 'no_bid', None),
            "no_ask": getattr(m, 'no_ask', None),
            "last_price": getattr(m, 'last_price', None),
            "volume": getattr(m, 'volume', 0),
            "open_interest": getattr(m, 'open_interest', 0),
            "close_time": getattr(m, 'close_time', ''),
            "result": getattr(m, 'result', ''),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    
@app.route('/fetch-espn', methods=['GET'])
def fetch_espn():
    import requests as req
    from datetime import datetime, date
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import pytz

    ESPN = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba'
    CORE = 'https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba'
    from datetime import timedelta
    offset = int(request.args.get('offset', 0))
    today = (datetime.now() + timedelta(days=offset)).strftime('%Y%m%d')

    ABBR_MAP = {
        'NY': 'NYK', 'SA': 'SAS', 'WSH': 'WAS', 'GS': 'GSW',
        'NO': 'NOP', 'UTAH': 'UTA'
    }
    def fix_abbr(a):
        return ABBR_MAP.get(a, a)

    try:
        # ─── STEP 1: Today's scheduled games ───
        sb = req.get(f'{ESPN}/scoreboard?dates={today}', timeout=5).json()
        events = sb.get('events', [])
        scheduled = events  # include pre, in, and post (all games today)
        if not scheduled:
            return jsonify({"error": "No games found for today — try offset=1 for tomorrow"}), 404

        # ─── STEP 2: Build team ID map ───
        team_ids = {}
        for event in scheduled:
            for comp in event.get('competitions', []):
                for competitor in comp.get('competitors', []):
                    t = competitor.get('team', {})
                    raw = t.get('abbreviation', '')
                    abbr = fix_abbr(raw)
                    team_ids[abbr] = {'id': t.get('id', ''), 'raw': raw}

        # ─── STEP 3: Build games array ───
        games = []
        for i, event in enumerate(scheduled):
            comp = event['competitions'][0]
            competitors = comp['competitors']
            home = next((c for c in competitors if c['homeAway'] == 'home'), competitors[0])
            away = next((c for c in competitors if c['homeAway'] == 'away'), competitors[1])
            h_abbr = fix_abbr(home['team']['abbreviation'])
            a_abbr = fix_abbr(away['team']['abbreviation'])
            state = event['status']['type']['state']
            completed = comp['status']['type'].get('completed', False)
            try:
                dt = datetime.fromisoformat(event.get('date', '').replace('Z', '+00:00'))
                dt_et = dt.astimezone(pytz.timezone('America/New_York'))
                game_time = dt_et.strftime('%-I:%M %p')
            except:
                game_time = ''
            game = {
                "id": f"g{i+1}",
                "h": h_abbr, "a": a_abbr,
                "t": game_time,
                "state": state,
                "completed": completed,
                "hp": 50, "ap": 50,
                "kH": 50, "kA": 50,
                "h2h": [1, 1],
                "hRest": 1, "aRest": 1,
                "hTravel": False, "aTravel": False
            }
            if state in ('in', 'post'):
                try:
                    game["hScore"] = int(home.get('score', 0) or 0)
                    game["aScore"] = int(away.get('score', 0) or 0)
                    if state == 'in':
                        period = comp['status'].get('period', 1)
                        clock = comp['status'].get('displayClock', '')
                        game["liveStatus"] = f"Q{period} {clock}".strip()
                except:
                    pass
            games.append(game)

        # ─── STEP 4: Fetch team stats + record + roster + injuries in parallel ───
        def fetch_team_data(abbr, info):
            tid = info['id']
            result = {'abbr': abbr, 'stats': None, 'roster': [], 'injuries': []}

            # Find opponent
            opp = ''
            for g in games:
                if g['h'] == abbr: opp = g['a']
                elif g['a'] == abbr: opp = g['h']

            try:
                # Stats + record in parallel
                with ThreadPoolExecutor(max_workers=4) as inner:
                    f_stats = inner.submit(req.get, f'{CORE}/seasons/2026/types/2/teams/{tid}/statistics', timeout=5)
                    f_rec = inner.submit(req.get, f'{CORE}/seasons/2026/types/2/teams/{tid}/record', timeout=5)
                    f_roster = inner.submit(req.get, f'{ESPN}/teams/{tid}/roster', timeout=5)
                    f_inj = inner.submit(req.get, f'{ESPN}/teams/{tid}/injuries', timeout=5)

                    stats_data = f_stats.result().json()
                    rec_data = f_rec.result().json()
                    roster_data = f_roster.result().json()
                    inj_data = f_inj.result().json()

                # Parse stats
                stats = {}
                for cat in stats_data.get('splits', {}).get('categories', []):
                    for s in cat.get('stats', []):
                        stats[s['name']] = s.get('perGameValue', s.get('value', 0)) or 0

                # Parse record
                items = rec_data.get('items', [])
                overall = next((i for i in items if i.get('name') == 'overall'), {})
                home_rec = next((i for i in items if i.get('name', '').lower() == 'home'), {})
                away_rec = next((i for i in items if i.get('name', '').lower() == 'road'), {})
                def rec_stat(item, name):
                    return next((s['value'] for s in item.get('stats', []) if s['name'] == name), 0) or 0
                
                # Debug: check what stat names are available in home_rec
                home_stat_names = [s['name'] for s in home_rec.get('stats', [])]
                summary = overall.get('summary', '0-0')
                w, l = (int(x) for x in summary.split('-')) if '-' in summary else (0, 0)

                pts_for = round(float(stats.get('avgPoints', stats.get('avgPointsFor', 113.5))), 1)
                pts_ag = round(float(rec_stat(overall, 'avgPointsAgainst') or 112.5), 1)
                pace_val = round(float(stats.get('paceFactor', 99.2)), 1)
                ortg_adj = round((pts_for / pace_val) * 99.2, 1) if pace_val > 0 else pts_for
                drtg_adj = round((pts_ag / pace_val) * 99.2, 1) if pace_val > 0 else pts_ag

                result['stats'] = {
                    "ortg": ortg_adj, "drtg": drtg_adj,
                    "pace": round(float(stats.get('paceFactor', 99.2)), 1),
                    "w": w, "l": l,
                    "net": round(pts_for - pts_ag, 1),
                    "l10w": 5, "l10l": 5,
                    "hw": int(rec_stat(home_rec, 'wins')),
                    "hl": int(rec_stat(home_rec, 'losses')),
                    "aw": int(rec_stat(away_rec, 'wins')),
                    "al": int(rec_stat(away_rec, 'losses')),
                    "streak": 0,
                    "ptsFor": pts_for, "ptsAg": pts_ag,
                    "l10ptsFor": pts_for,
                    "tpr": round(float(stats.get('threePointPct', 0.36)), 3),
                    "atsl10": 5, "closew": 5, "closel": 5
                }

                # Parse roster — first 10 players (ESPN returns starters first)
                athletes = roster_data.get('athletes', [])
                for athlete in athletes[:15]:
                    status_type = athlete.get('status', {}).get('type', 'active')
                    if status_type == 'injured': inj_status = 'OUT'
                    elif status_type == 'questionable': inj_status = 'GTD'
                    else: inj_status = 'PLAY'
                    result['roster'].append({
                        'id': athlete.get('id', ''),
                        'name': athlete.get('displayName', ''),
                        'team': abbr, 'opp': opp,
                        'pos': athlete.get('position', {}).get('abbreviation', ''),
                        'szn': 0.0, 'l5': 0.0, 'l10': 0.0,
                        'min': 0.0, 'line': 0.0,
                        'status': inj_status, 'note': ''
                    })

                # Parse injuries
                for item in inj_data.get('injuries', []):
                    athlete = item.get('athlete', {})
                    result['injuries'].append({
                        "p": athlete.get('displayName', ''),
                        "s": item.get('status', 'Out').upper(),
                        "starter": True
                    })

            except Exception as e:
                result['stats'] = {
                    "ortg": 113.5, "drtg": 112.5, "pace": 99.2,
                    "w": 0, "l": 0, "net": 0.0,
                    "l10w": 5, "l10l": 5, "hw": 0, "hl": 0,
                    "aw": 0, "al": 0, "streak": 0,
                    "ptsFor": 113.5, "ptsAg": 112.5, "l10ptsFor": 113.5,
                    "tpr": 0.36, "atsl10": 5, "closew": 5, "closel": 5
                }

            return result

        # Run all teams in parallel
        teams_out = {}
        players_out = []
        injuries = {}

        with ThreadPoolExecutor(max_workers=16) as executor:
            futures = {executor.submit(fetch_team_data, abbr, info): abbr 
                      for abbr, info in team_ids.items()}
            for future in as_completed(futures):
                data = future.result()
                abbr = data['abbr']
                if data['stats']:
                    teams_out[abbr] = data['stats']
                players_out.extend(data['roster'])
                injuries[abbr] = data['injuries']

        result = {
            "date": (date.today() + timedelta(days=offset)).strftime('%b %-d, %Y'),
            "games": games,
            "teams": teams_out,
            "players": players_out,
            "injuries": injuries
        }
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/fetch-espn-deep', methods=['GET'])
def fetch_espn_deep():
    import requests as req
    from datetime import datetime, date
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import pytz

    ESPN = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba'
    CORE = 'https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba'
    from datetime import timedelta
    offset = int(request.args.get('offset', 0))
    today = (datetime.now() + timedelta(days=offset)).strftime('%Y%m%d')

    ABBR_MAP = {
        'NY': 'NYK', 'SA': 'SAS', 'WSH': 'WAS', 'GS': 'GSW',
        'NO': 'NOP', 'UTAH': 'UTA'
    }
    def fix_abbr(a):
        return ABBR_MAP.get(a, a)

    try:
        # ─── STEP 1: Today's scheduled games ───
        sb = req.get(f'{ESPN}/scoreboard?dates={today}', timeout=5).json()
        events = sb.get('events', [])
        scheduled = events  # include pre, in, and post (all games today)
        if not scheduled:
            return jsonify({"error": "No games found for today — try offset=1 for tomorrow"}), 404

        # ─── STEP 2: Build team ID map ───
        team_ids = {}
        for event in scheduled:
            for comp in event.get('competitions', []):
                for competitor in comp.get('competitors', []):
                    t = competitor.get('team', {})
                    raw = t.get('abbreviation', '')
                    abbr = fix_abbr(raw)
                    team_ids[abbr] = {'id': t.get('id', ''), 'raw': raw}

        # ─── STEP 3: Build games array ───
        games = []
        for i, event in enumerate(scheduled):
            comp = event['competitions'][0]
            competitors = comp['competitors']
            home = next((c for c in competitors if c['homeAway'] == 'home'), competitors[0])
            away = next((c for c in competitors if c['homeAway'] == 'away'), competitors[1])
            h_abbr = fix_abbr(home['team']['abbreviation'])
            a_abbr = fix_abbr(away['team']['abbreviation'])
            state = event['status']['type']['state']
            completed = comp['status']['type'].get('completed', False)
            try:
                dt = datetime.fromisoformat(event.get('date', '').replace('Z', '+00:00'))
                dt_et = dt.astimezone(pytz.timezone('America/New_York'))
                game_time = dt_et.strftime('%-I:%M %p')
            except:
                game_time = ''
            game = {
                "id": f"g{i+1}",
                "h": h_abbr, "a": a_abbr,
                "t": game_time,
                "state": state,
                "completed": completed,
                "hp": 50, "ap": 50,
                "kH": 50, "kA": 50,
                "h2h": [1, 1],
                "hRest": 1, "aRest": 1,
                "hTravel": False, "aTravel": False
            }
            if state in ('in', 'post'):
                try:
                    game["hScore"] = int(home.get('score', 0) or 0)
                    game["aScore"] = int(away.get('score', 0) or 0)
                    if state == 'in':
                        period = comp['status'].get('period', 1)
                        clock = comp['status'].get('displayClock', '')
                        game["liveStatus"] = f"Q{period} {clock}".strip()
                except:
                    pass
            games.append(game)

        # ─── STEP 4: Deep fetch per team ───
        def fetch_team_deep(abbr, info):
            tid = info['id']
            result = {
                'abbr': abbr,
                'stats': None,
                'schedule_stats': None,
                'roster': [],
                'injuries': []
            }

            # Find opponent
            opp = ''
            for g in games:
                if g['h'] == abbr: opp = g['a']
                elif g['a'] == abbr: opp = g['h']

            try:
                with ThreadPoolExecutor(max_workers=5) as inner:
                    f_stats = inner.submit(req.get, f'{CORE}/seasons/2026/types/2/teams/{tid}/statistics', timeout=6)
                    f_rec = inner.submit(req.get, f'{CORE}/seasons/2026/types/2/teams/{tid}/record', timeout=6)
                    f_roster = inner.submit(req.get, f'{ESPN}/teams/{tid}/roster', timeout=6)
                    f_inj = inner.submit(req.get, f'{ESPN}/teams/{tid}/injuries', timeout=6)
                    f_sched = inner.submit(req.get, f'{ESPN}/teams/{tid}/schedule', timeout=8)

                    stats_data = f_stats.result().json()
                    rec_data = f_rec.result().json()
                    roster_data = f_roster.result().json()
                    inj_data = f_inj.result().json()
                    sched_data = f_sched.result().json()

                # ── Parse team stats ──
                stats = {}
                for cat in stats_data.get('splits', {}).get('categories', []):
                    for s in cat.get('stats', []):
                        stats[s['name']] = s.get('perGameValue', s.get('value', 0)) or 0

                # ── Parse record ──
                items = rec_data.get('items', [])
                overall = next((i for i in items if i.get('name') == 'overall'), {})
                home_rec = next((i for i in items if i.get('name', '').lower() == 'home'), {})
                away_rec = next((i for i in items if i.get('name', '').lower() == 'road'), {})
                def rec_stat(item, name):
                    return next((s['value'] for s in item.get('stats', []) if s['name'] == name), 0) or 0
                summary = overall.get('summary', '0-0')
                w, l = (int(x) for x in summary.split('-')) if '-' in summary else (0, 0)

                pts_for = round(float(stats.get('avgPoints', 113.5)), 1)
                pts_ag = round(float(rec_stat(overall, 'avgPointsAgainst') or 112.5), 1)

                # ── Parse schedule for L10/streak/trend ──
                all_games = []
                for event in sched_data.get('events', []):
                    comp = event.get('competitions', [{}])[0]
                    comps = comp.get('competitors', [])
                    if len(comps) != 2: continue
                    
                    # Find this team and opponent
                    my_comp = next((c for c in comps if fix_abbr(c['team'].get('abbreviation','')) == abbr), None)
                    opp_comp = next((c for c in comps if fix_abbr(c['team'].get('abbreviation','')) != abbr), None)
                    
                    if not my_comp or not opp_comp: continue
                    if my_comp.get('winner') is None: continue  # skip future games
                    
                    my_score = my_comp.get('score', {})
                    opp_abbr_raw = opp_comp['team'].get('abbreviation', '')
                    opp_abbr = fix_abbr(opp_abbr_raw)
                    
                    if isinstance(my_score, dict):
                        pts = my_score.get('value', 0) or 0
                    else:
                        pts = 0
                    
                    all_games.append({
                        'won': my_comp.get('winner', False),
                        'pts': pts,
                        'opp': opp_abbr,
                        'date': event.get('date', '')
                    })

                # Sort by date, get last 10 completed
                completed = [g for g in all_games if g['pts'] > 0]
                completed.sort(key=lambda x: x['date'])
                last10 = completed[-10:] if len(completed) >= 10 else completed

                l10w = sum(1 for g in last10 if g['won'])
                l10l = len(last10) - l10w
                l10pts = round(sum(g['pts'] for g in last10) / len(last10), 1) if last10 else pts_for

                # Win streak
                streak = 0
                for g in reversed(completed):
                    if streak == 0:
                        streak = 1 if g['won'] else -1
                    elif streak > 0 and g['won']:
                        streak += 1
                    elif streak < 0 and not g['won']:
                        streak -= 1
                    else:
                        break

                # Opponent-adjusted form — average net rating of last 10 opponents
                # We'll store opp abbreviations and look up their net ratings after
                l10_opps = [g['opp'] for g in last10]
                # 3-in-4 check — count games in last 4 days
                from datetime import datetime, timedelta
                now = datetime.utcnow()
                recent_games = [g for g in completed if g['date'] and 
                    (now - datetime.fromisoformat(g['date'].replace('Z','+00:00').replace('+00:00',''))).days <= 4]
                games_in_last4 = len(recent_games)
                
                result['schedule_stats'] = {
                    'l10w': l10w, 'l10l': l10l,
                    'l10ptsFor': l10pts,
                    'streak': streak,
                    'l10_opps': l10_opps
                }

                pace_val = round(float(stats.get('paceFactor', 99.2)), 1)
                # Pace-adjust ortg/drtg to per-100-possessions
                ortg_adj = round((pts_for / pace_val) * 99.2, 1) if pace_val > 0 else pts_for
                drtg_adj = round((pts_ag / pace_val) * 99.2, 1) if pace_val > 0 else pts_ag
                result['stats'] = {
                    "ortg": ortg_adj,
                    "drtg": drtg_adj,
                    "pace": round(float(stats.get('paceFactor', 99.2)), 1),
                    "w": w, "l": l,
                    "net": round(pts_for - pts_ag, 1),
                    "l10w": l10w, "l10l": l10l,
                    "hw": int(rec_stat(home_rec, 'wins')),
                    "hl": int(rec_stat(home_rec, 'losses')),
                    "aw": int(rec_stat(away_rec, 'wins')),
                    "al": int(rec_stat(away_rec, 'losses')),
                    "streak": streak,
                    "ptsFor": pts_for, "ptsAg": pts_ag,
                    "l10ptsFor": l10pts,
                    "tpr": round(float(stats.get('threePointPct', 0.36)), 3),
                    "atsl10": 5, "closew": 5, "closel": 5
                }

                # Parse roster — first 10 players (ESPN returns starters first)
                athletes = roster_data.get('athletes', [])
                for athlete in athletes[:15]:
                    status_type = athlete.get('status', {}).get('type', 'active')
                    if status_type == 'injured': inj_status = 'OUT'
                    elif status_type == 'questionable': inj_status = 'GTD'
                    else: inj_status = 'PLAY'
                    result['roster'].append({
                        'id': athlete.get('id', ''),
                        'name': athlete.get('displayName', ''),
                        'team': abbr, 'opp': opp,
                        'pos': athlete.get('position', {}).get('abbreviation', ''),
                        'szn': 0.0, 'l5': 0.0, 'l10': 0.0,
                        'min': 0.0, 'line': 0.0,
                        'status': inj_status, 'note': ''
                    })

                # ── Parse injuries ──
                for item in inj_data.get('injuries', []):
                    athlete = item.get('athlete', {})
                    result['injuries'].append({
                        'p': athlete.get('displayName', ''),
                        's': item.get('status', 'Out').upper(),
                        'starter': True
                    })

            except Exception as e:
                result['stats'] = {
                    "ortg": 113.5, "drtg": 112.5, "pace": 99.2,
                    "w": 0, "l": 0, "net": 0.0,
                    "l10w": 5, "l10l": 5, "hw": 0, "hl": 0,
                    "aw": 0, "al": 0, "streak": 0,
                    "ptsFor": 113.5, "ptsAg": 112.5, "l10ptsFor": 113.5,
                    "tpr": 0.36, "atsl10": 5, "closew": 5, "closel": 5
                }
            return result

        # ─── STEP 5: Run all teams in parallel ───
        teams_out = {}
        players_raw = []
        injuries = {}
        schedule_stats = {}

        with ThreadPoolExecutor(max_workers=16) as executor:
            futures = {executor.submit(fetch_team_deep, abbr, info): abbr
                      for abbr, info in team_ids.items()}
            for future in as_completed(futures):
                data = future.result()
                abbr = data['abbr']
                if data['stats']:
                    teams_out[abbr] = data['stats']
                if data['schedule_stats']:
                    schedule_stats[abbr] = data['schedule_stats']
                players_raw.extend(data['roster'])
                injuries[abbr] = data['injuries']

        # ─── STEP 6: Opponent-adjusted form ───
        for abbr, ss in schedule_stats.items():
            opp_nets = []
            for opp_abbr in ss.get('l10_opps', []):
                opp_net = teams_out.get(opp_abbr, {}).get('net', 0)
                opp_nets.append(opp_net)
            avg_opp_net = round(sum(opp_nets) / len(opp_nets), 1) if opp_nets else 0
            if abbr in teams_out:
                teams_out[abbr]['opp_adj_form'] = avg_opp_net

        # ─── STEP 7: Player gamelogs ───
        def fetch_player_gamelog(player):
            pid = player.get('id', '')
            if not pid:
                return player
            ABBR_REMAP = {'GS': 'GSW', 'SA': 'SAS', 'NY': 'NYK', 'WSH': 'WAS', 'NO': 'NOP', 'UTAH': 'UTA'}
            try:
                # Fetch gamelog and advanced stats in parallel
                with ThreadPoolExecutor(max_workers=2) as pinner:
                    f_log = pinner.submit(req.get,
                        f'https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{pid}/gamelog',
                        timeout=10)
                    f_adv = pinner.submit(req.get,
                        f'https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/seasons/2026/types/2/athletes/{pid}/statistics',
                        timeout=10)
                    data = f_log.result().json()
                    adv_data = f_adv.result().json()

                # Extract usage rate from advanced stats
                for cat in adv_data.get('splits', {}).get('categories', []):
                    for s in cat.get('stats', []):
                        if s.get('name') == 'avgEstimatedPossessions':
                            val = s.get('value', 0) or 0
                            if val > 0:
                                player['usg'] = round(float(val), 1)

                labels = data.get('labels', [])
                pts_idx = labels.index('PTS') if 'PTS' in labels else None
                min_idx = labels.index('MIN') if 'MIN' in labels else None
                events_dict = data.get('events', {})
                current_team = player.get('team', '')

                all_game_stats = []
                for season_type in data.get('seasonTypes', []):
                    if '2025-26 Regular Season' != season_type.get('displayName', ''):
                        continue
                    for cat in season_type.get('categories', []):
                        for event in cat.get('events', []):
                            stats = event.get('stats', [])
                            event_id = event.get('eventId', '')
                            event_info = events_dict.get(event_id, {})
                            game_date = event_info.get('gameDate', '')
                            event_team = event_info.get('team', {}).get('abbreviation', '')
                            norm_event = ABBR_REMAP.get(event_team, event_team)
                            norm_current = ABBR_REMAP.get(current_team, current_team)
                            if current_team and event_team and norm_event != norm_current:
                                continue
                            norm_event = ABBR_MAP.get(event_team, event_team)
                            norm_current = ABBR_MAP.get(current_team, current_team)
                            if current_team and event_team and norm_event != norm_current and event_team != current_team:
                                continue
                            pts_val = None
                            min_val = None
                            if pts_idx is not None and pts_idx < len(stats):
                                try: pts_val = float(stats[pts_idx])
                                except: pass
                            if min_idx is not None and min_idx < len(stats):
                                try: min_val = float(str(stats[min_idx]).split(':')[0])
                                except: pass
                            if pts_val is not None:
                                all_game_stats.append({'date': game_date, 'pts': pts_val, 'min': min_val or 0})

                all_game_stats.sort(key=lambda x: x['date'])
                game_pts = [g['pts'] for g in all_game_stats]
                game_min = [g['min'] for g in all_game_stats if g['min'] > 0]

                if game_pts:
                    szn = round(sum(game_pts) / len(game_pts), 1)
                    l10_games = game_pts[-10:] if len(game_pts) >= 10 else game_pts
                    l5_games = game_pts[-5:] if len(game_pts) >= 5 else game_pts

                    # Exponential decay weighted L10 — recent games weighted more
                    # decay=0.85 means each game back is worth 85% of the next one
                    decay = 0.85
                    weights = [decay ** i for i in range(len(l10_games) - 1, -1, -1)]
                    l10_weighted = round(
                        sum(p * w for p, w in zip(l10_games, weights)) / sum(weights), 1
                    )

                    player['szn'] = szn
                    player['l10'] = l10_weighted  # now decay-weighted
                    player['l5'] = round(sum(l5_games) / len(l5_games), 1)
                    player['note'] = f"L5: {','.join(str(int(p)) for p in game_pts[-5:])}"

                if game_min:
                    recent_min = game_min[-10:] if len(game_min) >= 10 else game_min
                    player['min'] = round(sum(recent_min) / len(recent_min), 1)

            except Exception as e:
                pass
            return player

# Only fetch gamelogs for non-injured players (skip DNP/OUT)
        active_players = [p for p in players_raw if p.get('status') != 'OUT']
        inactive_players = [p for p in players_raw if p.get('status') == 'OUT']

        with ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(fetch_player_gamelog, p) for p in active_players]
            players_with_stats = [f.result() for f in futures]

        # Sort by impact score (PPG × minutes), filter out pure DNP players
        # Keep players with either szn stats OR minutes played
        players_with_stats = [p for p in players_with_stats if p.get('szn', 0) > 0 or p.get('min', 0) > 10]
        players_with_stats.sort(key=lambda x: x.get('szn', 0) * x.get('min', 0), reverse=True)

        # Take top 8 per team
        team_counts = {}
        top_players = []
        for p in players_with_stats:
            team = p.get('team', '')
            if team_counts.get(team, 0) < 8:
                top_players.append(p)
                team_counts[team] = team_counts.get(team, 0) + 1

        all_players = top_players + inactive_players

        result = {
            "date": (date.today() + timedelta(days=offset)).strftime('%b %-d, %Y'),
            "games": games,
            "teams": teams_out,
            "players": all_players,
            "injuries": injuries
        }
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/debug-roster/<abbr>', methods=['GET'])
def debug_roster(abbr):
    import requests as req
    ESPN = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba'
    ABBR_TO_ID = {
        'GSW': '9', 'NYK': '18', 'ATL': '1', 'BOS': '2', 'BKN': '17',
        'CHA': '30', 'CHI': '4', 'CLE': '5', 'DAL': '6', 'DEN': '7',
        'DET': '8', 'HOU': '10', 'IND': '11', 'LAC': '12', 'LAL': '13',
        'MEM': '29', 'MIA': '14', 'MIL': '15', 'MIN': '16', 'NOP': '3',
        'OKC': '25', 'ORL': '19', 'PHI': '20', 'PHX': '21', 'POR': '22',
        'SAC': '23', 'SAS': '24', 'TOR': '28', 'UTA': '26', 'WAS': '27'
    }
    tid = ABBR_TO_ID.get(abbr, '')
    if not tid:
        return jsonify({'error': 'unknown team'})
    r = req.get(f'{ESPN}/teams/{tid}/roster', timeout=6).json()
    athletes = r.get('athletes', [])
    return jsonify({
        'total': len(athletes),
        'players': [{'id': a.get('id'), 'name': a.get('displayName'), 'status': a.get('status',{}).get('type','active')} for a in athletes[:15]]
    })


@app.route('/odds', methods=['GET'])
def get_odds():
    import requests as req
    try:
        # Fetch NBA odds + injury data
        r = req.get(
            'https://api.the-odds-api.com/v4/sports/basketball_nba/odds',
            params={
                'apiKey': ODDS_API_KEY,
                'regions': 'us',
                'markets': 'h2h',
                'oddsFormat': 'american',
                'dateFormat': 'iso'
            },
            timeout=8
        )
        data = r.json()
        
        games = []
        for game in data:
            home = game.get('home_team', '')
            away = game.get('away_team', '')
            commence = game.get('commence_time', '')
            
            # Extract best available odds
            home_odds, away_odds = None, None
            for bookie in game.get('bookmakers', []):
                for market in bookie.get('markets', []):
                    if market.get('key') == 'h2h':
                        for outcome in market.get('outcomes', []):
                            if outcome['name'] == home and home_odds is None:
                                home_odds = outcome.get('price')
                            elif outcome['name'] == away and away_odds is None:
                                away_odds = outcome.get('price')
                if home_odds and away_odds:
                    break

            def to_prob(odds):
                if odds is None: return None
                if odds < 0: return round(abs(odds) / (abs(odds) + 100) * 100, 1)
                return round(100 / (odds + 100) * 100, 1)

            games.append({
                'home': home,
                'away': away,
                'hAbbr': ODDS_TEAM_MAP.get(home, ''),
                'aAbbr': ODDS_TEAM_MAP.get(away, ''),
                'commence': game.get('commence_time', ''),
                'home_odds': home_odds,
                'away_odds': away_odds,
                'home_prob': to_prob(home_odds),
                'away_prob': to_prob(away_odds)
            })

        # Fetch injuries
        inj_r = req.get(
            'https://api.the-odds-api.com/v4/sports/basketball_nba/participants',
            params={'apiKey': ODDS_API_KEY},
            timeout=8
        )
        inj_data = inj_r.json() if inj_r.status_code == 200 else []
        injuries = inj_data if isinstance(inj_data, list) else []

        return jsonify({
            'games': games,
            'injuries': injuries,
            'requests_remaining': r.headers.get('x-requests-remaining', '?')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/injuries', methods=['GET'])
def get_injuries():
    import requests as req
    try:
        injuries_out = {}
        cursor = None
        
        while True:
            params = {'per_page': 100}
            if cursor:
                params['cursor'] = cursor
            
            r = req.get(
                'https://api.balldontlie.io/v1/player_injuries',
                headers={'Authorization': BALLDONTLIE_API_KEY},
                params=params,
                timeout=8
            )
            data = r.json()
            
            for item in data.get('data', []):
                player = item.get('player', {})
                team = player.get('team', {})
                abbr = team.get('abbreviation', '') if isinstance(team, dict) else ''
                name = f"{player.get('first_name','')} {player.get('last_name','')}".strip()
                status = item.get('status', 'Out')
                
                if not abbr or not name:
                    continue
                    
                if abbr not in injuries_out:
                    injuries_out[abbr] = []
                
                injuries_out[abbr].append({
                    'p': name,
                    's': status.upper(),
                    'starter': True
                })
            
            # Check for next page
            meta = data.get('meta', {})
            next_cursor = meta.get('next_cursor')
            if not next_cursor:
                break
            cursor = next_cursor
        
        return jsonify({'injuries': injuries_out})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/nba-markets', methods=['GET'])
def nba_markets():
    """Pull live NBA markets across game/spread/total/series series_tickers and
    normalize them so the Delta TRADE tab can join model picks to live tickers
    by `AWAY_HOME_PICK` key."""
    import re
    import requests as req
    from kalshi_python_sync.auth import KalshiAuth

    SERIES_TO_FETCH = ['KXNBAGAME', 'KXNBASPREAD', 'KXNBATOTAL', 'KXNBASERIES']
    auth = KalshiAuth(config.api_key_id, config.private_key_pem)

    all_markets = {s: [] for s in SERIES_TO_FETCH}
    try:
        for series in SERIES_TO_FETCH:
            cursor = None
            for _ in range(3):  # up to 600 markets per series
                params = {'series_ticker': series, 'status': 'open', 'limit': 200}
                if cursor:
                    params['cursor'] = cursor
                h = auth.create_auth_headers('GET', '/trade-api/v2/markets')
                h['Content-Type'] = 'application/json'
                r = req.get('https://api.elections.kalshi.com/trade-api/v2/markets',
                            headers=h, params=params, timeout=8)
                d = r.json()
                batch = d.get('markets', [])
                all_markets[series].extend(batch)
                cursor = d.get('cursor') if batch else None
                if not cursor:
                    break

        # KXNBAGAME-26APR26BOSPHI-PHI  →  yy=26 mmm=APR dd=26 away=BOS home=PHI pick=PHI
        moneylines = {}
        game_re = re.compile(r'^KXNBAGAME-(\d{2}[A-Z]{3}\d{2})([A-Z]{3})([A-Z]{3})-([A-Z]{3})$')
        for m in all_markets['KXNBAGAME']:
            t = m.get('ticker', '')
            mt = game_re.match(t)
            if not mt:
                continue
            datestr, away, home, pick = mt.groups()
            key = f"{away}_{home}_{pick}"
            existing = moneylines.get(key)
            if existing and (existing.get('close_time') or '') <= (m.get('close_time') or ''):
                continue
            moneylines[key] = {
                'ticker': t,
                'title': m.get('title', ''),
                'date_token': datestr,
                'away': away, 'home': home, 'pick': pick,
                'yes_bid': m.get('yes_bid'), 'yes_ask': m.get('yes_ask'),
                'no_bid': m.get('no_bid'), 'no_ask': m.get('no_ask'),
                'volume': m.get('volume') or 0,
                'open_interest': m.get('open_interest') or 0,
                'close_time': m.get('close_time', ''),
                'status': m.get('status', ''),
            }

        # KXNBASERIES-26PHIBOSR1-PHI  →  yy=26 away=PHI home=BOS round=1 pick=PHI
        series_winners = {}
        series_re = re.compile(r'^KXNBASERIES-(\d{2})([A-Z]{3})([A-Z]{3})R(\d)-([A-Z]{3})$')
        for m in all_markets['KXNBASERIES']:
            t = m.get('ticker', '')
            mt = series_re.match(t)
            if not mt:
                continue
            yy, away, home, rnd, pick = mt.groups()
            series_winners[f"{away}_{home}_R{rnd}_{pick}"] = {
                'ticker': t,
                'title': m.get('title', ''),
                'away': away, 'home': home, 'round': int(rnd), 'pick': pick,
                'yes_bid': m.get('yes_bid'), 'yes_ask': m.get('yes_ask'),
                'no_bid': m.get('no_bid'), 'no_ask': m.get('no_ask'),
                'volume': m.get('volume') or 0,
            }

        return jsonify({
            'moneylines': moneylines,
            'series': series_winners,
            'counts': {s: len(v) for s, v in all_markets.items()},
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("═══════════════════════════════════════════════")
    print("  PARLAY LAB — KALSHI BRIDGE SERVER")
    print("  http://127.0.0.1:5001")
    print("═══════════════════════════════════════════════")
    print("  GET  /status  /balance  /search?q=")
    print("  GET  /orderbook/<tkr>  /positions  /orders")
    print("  POST /place_bet  /cancel_order")
    print("═══════════════════════════════════════════════")
    app.run(host='127.0.0.1', port=5001, debug=True)
