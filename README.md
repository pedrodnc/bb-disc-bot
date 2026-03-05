# bb-disc-bot

Herramientas de automatizacion para Discord. Dos bots independientes:

1. **Auto-Responder** (`bot.py`) - Vigila un canal, detecta cuando un "dealer" publica una imagen, y responde automaticamente con un comando (ej: `!roll`). Multi-usuario, reconexion 24/7.

2. **Sender** (`sender.py`) - Envia mensajes (texto + imagenes) a multiples canales de un servidor. Modo loop, horario programado, dry-run.

> **Mejor experiencia en VPS.** Estos bots estan pensados para correr 24/7 en un VPS barato ($3-5/mes). Configuras una vez, te olvidas. En local funciona para probar, pero si quieres fiabilidad real, VPS.

---

## Por que un VPS es lo mas efectivo

| | Local (tu PC) | VPS |
|---|---|---|
| Funciona 24/7 | Solo con el PC encendido | Siempre |
| Sobrevive reinicios | No | Si (systemd) |
| Estabilidad de red | Depende de tu Wi-Fi | Nivel datacenter |
| Uso de recursos | ~15MB RAM | ~15MB RAM |
| Coste | Gratis pero poco fiable | $3-5/mes, solido |

Un VPS de $3/mes (Hetzner, Contabo, OVH, Vultr) es mas que suficiente.

---

## Inicio rapido

```bash
git clone https://github.com/pedrodnc/bb-disc-bot.git
cd bb-disc-bot
chmod +x install.sh && ./install.sh
```

---

## 1. Auto-Responder (bot.py)

Vigila un canal especifico. Cuando un usuario "dealer" publica una imagen, responde automaticamente con un comando configurable.

### Configurar

```bash
python3 ver_config.py
```

Menu interactivo donde configuras:
- **Canal** - ID del canal a vigilar
- **Comando** - Que responder (por defecto `!roll`, puedes cambiarlo a lo que quieras)
- **Dealers** - IDs de los usuarios cuyas imagenes disparan la respuesta
- **Usuarios** - Cuentas que responderan (cada una con su token). Puedes tener multiples cuentas respondiendo en paralelo

O edita directamente `bot_config.json`:

```json
{
  "canal_id": "123456789012345678",
  "comando": "!roll",
  "dealers": ["111111111111111111"],
  "usuarios": [
    {
      "nombre": "MiCuenta",
      "token": "tu_token",
      "activo": true
    }
  ]
}
```

### Ejecutar

```bash
python3 bot.py
```

El bot se conecta via WebSocket al Gateway de Discord, mantiene la conexion viva con heartbeat, y se reconecta automaticamente si se cae.

### Que puedes modificar

| Parametro | Donde | Que hace |
|-----------|-------|----------|
| `comando` | bot_config.json | Texto que se envia como respuesta (ej: `!roll`, `!join`, `!claim`) |
| `dealers` | bot_config.json | Lista de IDs cuyos mensajes con imagen disparan respuesta |
| `canal_id` | bot_config.json | Canal que vigila el bot |
| `usuarios` | bot_config.json | Lista de cuentas que responden (multi-usuario) |
| Deteccion de imagen | bot.py L140-147 | Extensiones de archivo que se consideran "imagen" |
| Reply vs mensaje normal | bot.py L75-80 | Cambia `message_reference` si quieres mensaje normal en vez de reply |

---

## 2. Sender (sender.py)

Envia mensajes a multiples canales de un servidor. Texto, imagenes, o ambos.

### Configurar

Edita `sender_config.json`:

```json
{
    "token": "tu_token",
    "server_id": "123456789012345678",
    "channels": ["111111111111111111", "222222222222222222"],
    "message": "Hola a todos!",
    "images": ["images/foto.png"],
    "loop_interval_minutes": 60,
    "delay_between_channels": 1.5,
    "schedule": {
        "enabled": true,
        "start_hour": 8,
        "end_hour": 23,
        "timezone_offset": 1
    }
}
```

### Ejecutar

```bash
# Descubrir IDs de canales
python3 sender.py --list-channels

# Probar sin enviar
python3 sender.py --dry-run

# Enviar una vez
python3 sender.py --once

# Enviar en bucle
python3 sender.py --loop

# Config alternativa
python3 sender.py -c evento.json --once

# Token por variable de entorno
DISCORD_TOKEN=xxx python3 sender.py --once
```

### Opciones del sender

| Campo | Default | Que hace |
|-------|---------|----------|
| `token` | - | Token de Discord |
| `server_id` | - | ID del servidor |
| `channels` | - | Lista de IDs de canales |
| `message` | `""` | Texto del mensaje |
| `images` | `[]` | Imagenes locales o URLs |
| `loop_interval_minutes` | `60` | Minutos entre envios en modo loop |
| `delay_between_channels` | `1.5` | Segundos entre cada canal |
| `max_retries` | `2` | Reintentos por canal |
| `schedule.enabled` | `false` | Activar horario |
| `schedule.start_hour` | `8` | Hora inicio |
| `schedule.end_hour` | `23` | Hora fin |
| `schedule.timezone_offset` | `0` | Offset UTC (ej: `1` para CET) |

---

## Como obtener tu token de Discord

1. Abre Discord en el navegador (discord.com/app)
2. Pulsa `F12` para abrir DevTools
3. Ve a la pestana **Network**
4. Haz cualquier accion en Discord
5. Haz clic en cualquier peticion a `discord.com/api`
6. Busca la cabecera `Authorization` en los headers
7. Copia ese valor

> **Nota**: Esto es un selfbot (usa tu token de usuario). Los ToS de Discord tecnicamente prohiben selfbots. Usalo bajo tu responsabilidad.

## Como obtener IDs

1. En Discord: Ajustes > Avanzado > Modo desarrollador: ON
2. Click derecho en servidor > "Copiar ID del servidor"
3. Click derecho en canal > "Copiar ID del canal"
4. Click derecho en usuario > "Copiar ID de usuario"

O usa: `python3 sender.py --list-channels`

---

## Despliegue en VPS (recomendado)

### Opcion 1: screen (rapido)

```bash
screen -S bot
source venv/bin/activate
python3 bot.py

# Ctrl+A, D para dejar en background
# screen -r bot para volver
```

### Opcion 2: systemd (mejor opcion)

```bash
# Editar con tu usuario y ruta
nano bot.service

sudo cp bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable bot
sudo systemctl start bot

# Gestion
sudo systemctl status bot
sudo journalctl -u bot -f
```

### Opcion 3: scripts incluidos

```bash
chmod +x start_bot.sh stop_bot.sh
./start_bot.sh     # Inicia en background
./stop_bot.sh      # Para el bot
tail -f logs/bot_live.log  # Ver logs
```

### Opcion 4: Docker

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bot.py bot_config.json ./
CMD ["python3", "bot.py"]
```

---

## Ejecucion local

```bash
./install.sh
python3 ver_config.py    # Configurar auto-responder
python3 bot.py           # Ejecutar
```

Funciona en local, pero si cierras la terminal se para.

---

## Estructura

```
bb-disc-bot/
  bot.py                    # Auto-responder (WebSocket Gateway)
  sender.py                 # Sender de mensajes (REST API)
  ver_config.py             # Configurador interactivo del bot
  bot_config.json.example   # Plantilla config auto-responder
  sender_config.json.example # Plantilla config sender
  start_bot.sh              # Script para iniciar bot
  stop_bot.sh               # Script para parar bot
  bot.service               # Plantilla systemd
  requirements.txt          # Dependencias
  install.sh                # Instalacion rapida
  images/                   # Imagenes locales (git-ignored)
  logs/                     # Logs (git-ignored)
```

---

## Ideas de personalizacion

- **Cambiar el trigger**: Edita `bot.py` para que responda a texto en vez de imagenes, o a embeds, o a reacciones
- **Comando dinamico**: Modifica para que responda con comandos aleatorios de una lista
- **Multiples canales**: Cambia `bot.py` para vigilar varios canales a la vez
- **Notificaciones**: Anade un webhook para que te avise cuando detecta algo
- **Tracking de puntos**: Anade logica para parsear respuestas del bot del servidor y llevar cuenta
- **Webhook sender**: Cambia `sender.py` para usar webhooks en vez de tokens de usuario
- **Embeds**: Modifica el payload del sender para enviar mensajes con formato enriquecido

---

## Licencia

MIT
