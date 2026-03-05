#!/bin/bash
# Inicia el bot auto-responder en background

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== INICIANDO BOT ==="

# Detener instancias previas
pkill -f "python3.*bot.py" 2>/dev/null
sleep 2

source venv/bin/activate
python3 -u bot.py > logs/bot_live.log 2>&1 &
BOT_PID=$!

sleep 3

if ps -p $BOT_PID > /dev/null 2>&1; then
    echo ""
    echo "Bot iniciado (PID: $BOT_PID)"
    echo ""
    echo "Logs:     tail -f logs/bot_live.log"
    echo "Parar:    ./stop_bot.sh"
    echo ""
    tail -10 logs/bot_live.log
else
    echo "ERROR: El bot no se inicio"
    cat logs/bot_live.log
    exit 1
fi
