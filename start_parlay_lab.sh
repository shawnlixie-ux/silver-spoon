#!/bin/bash
echo "🏀 Starting Parlay Lab..."

# Start bridge in background
cd "/Applications/Betting Project/API Keys/circlingdiamond45 (read)"
python3 bridge.py &
BRIDGE_PID=$!
echo "✅ Bridge started (PID: $BRIDGE_PID)"

# Wait for bridge to start
sleep 2

# Start HTML server in background
cd "/Applications/Betting Project"
python3 -m http.server 8080 &
SERVER_PID=$!
echo "✅ HTML server started (PID: $SERVER_PID)"

# Wait and check bridge
sleep 1
echo "🔍 Checking bridge..."
curl -s http://127.0.0.1:5001/status

echo ""
echo "═══════════════════════════════════════"
echo "  PARLAY LAB RUNNING"
echo "  Open: http://127.0.0.1:8080/Parlay_Lab_Kalshi%20current.html"
echo "  To stop: press Ctrl+C"
echo "═══════════════════════════════════════"

# Keep script running — Ctrl+C kills everything
trap "kill $BRIDGE_PID $SERVER_PID; echo 'Stopped.'" EXIT
wait