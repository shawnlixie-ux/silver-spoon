import kalshi_python_sync
python3 -m pip install kalshi-python-sync
from kalshi_python_sync import Configuration, KalshiClient

# 1. SETUP CONFIGURATION FIRST
# This tells Python HOW to talk to Kalshi
config = Configuration(host="https://api.elections.kalshi.com/trade-api/v2")

# Replace with your actual Key ID
config.api_key_id = "a16a7121-dc58-4637-a3c9-36f211d109eb"

# Load your Private Key file
with open("circlingdiamond45.txt", "r") as f:
    config.private_key = f.read()

# 2. INITIALIZE THE CLIENT
# Now the 'client' variable exists and can be used below
client = KalshiClient(config)

# 3. FIND THE TICKER
print("--- Searching for Maxey Tickers ---")
markets_response = client.get_markets(status="open", limit=100)

for market in markets_response.markets:
    if "Maxey" in market.title:
        print(f"Found Ticker: {market.ticker} | Title: {market.title}")

# 4. FETCH THE ORDERBOOK
# NOTE: Make sure this ticker exactly matches one found in Step 3!
target_ticker = "NBAP-26MAR17-MAXEY-25.5-PTS" 

try:
    response = client.get_market_orderbook(ticker=target_ticker)
    orderbook = response.orderbook

    print(f"\n--- Order Book for {target_ticker} ---")
    
    # Kalshi returns prices in CENTS
    print("YES Bids (Price, Quantity):")
    for level in orderbook.yes[:5]: 
        print(f"  {level[0]}c x {level[1]} contracts")

    print("\nNO Bids (Price, Quantity):")
    for level in orderbook.no[:5]:
        print(f"  {level[0]}c x {level[1]} contracts")
        
except Exception as e:
    print(f"\nError fetching orderbook: {e}")
    print("Double-check that the target_ticker is currently ACTIVE.")


