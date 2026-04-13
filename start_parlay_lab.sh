#!/bin/bash
echo "🏀 Starting Delta..."

lsof -ti:8080 | xargs kill -9 2>/dev/null
sleep 1

cd "/Applications/Betting Project/API Keys/circlingdiamond45 (read)"
python3 bridge.py &
BRIDGE_PID=$!
echo "✅ Bridge started (PID: $BRIDGE_PID)"
sleep 2

cd "/Applications/Betting Project"
python3 -m http.server 8080 &
SERVER_PID=$!
echo "✅ Server started (PID: $SERVER_PID)"
sleep 1

open "http://127.0.0.1:8080/Delta.html"

echo "═══════════════════════════════════════"
echo "  DELTA RUNNING"
echo "  Open: http://127.0.0.1:8080/Delta.html"
echo "  To stop: press Ctrl+C"
echo "═══════════════════════════════════════"

trap "kill $BRIDGE_PID $SERVER_PID 2>/dev/null; echo 'Stopped.'" EXIT
wait
