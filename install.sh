#!/bin/bash
echo "======================================="
echo " bb-disc-bot - Setup"
echo "======================================="

if ! command -v python3 &> /dev/null; then
    echo "Instalando Python..."
    sudo apt update && sudo apt install -y python3 python3-pip python3-venv
fi

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

mkdir -p images logs

# Crear configs si no existen
if [ ! -f bot_config.json ]; then
    cp bot_config.json.example bot_config.json
    echo "  bot_config.json creado."
fi
if [ ! -f sender_config.json ]; then
    cp sender_config.json.example sender_config.json
    echo "  sender_config.json creado."
fi

echo ""
echo "======================================="
echo " Instalado!"
echo ""
echo " AUTO-RESPONDER (vigila canal y responde):"
echo "   python3 ver_config.py     # Configurar"
echo "   python3 bot.py            # Ejecutar"
echo ""
echo " SENDER (envia a multiples canales):"
echo "   nano sender_config.json   # Configurar"
echo "   python3 sender.py --once  # Enviar una vez"
echo "   python3 sender.py --loop  # Enviar en bucle"
echo ""
echo " Ver README.md para mas opciones."
echo "======================================="
