#!/bin/bash
# Detiene el bot auto-responder

echo "=== DETENIENDO BOT ==="

pkill -f "python3.*bot.py" 2>/dev/null
echo "Bot detenido"

sleep 1

if ps aux | grep -q "[b]ot.py"; then
    echo "AVISO: El bot todavia esta corriendo"
else
    echo "OK: Bot detenido completamente"
fi
