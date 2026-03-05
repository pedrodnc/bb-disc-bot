#!/usr/bin/env python3
"""
bb-disc-bot - Sender
====================
Envia mensajes (texto + imagenes) a multiples canales de un servidor
de Discord. Configurable via config.json.

Uso:
  python3 sender.py                      # Envia una vez
  python3 sender.py --loop               # Envia en bucle (VPS)
  python3 sender.py --dry-run            # Simula sin enviar
  python3 sender.py --list-channels      # Lista canales del server
  python3 sender.py -c evento.json       # Config alternativa
"""

import json
import os
import sys
import asyncio
import aiohttp
import logging
import argparse
import mimetypes
from datetime import datetime, timezone, timedelta
from pathlib import Path


# ===================================================================
# LOGGING
# ===================================================================

os.makedirs("logs", exist_ok=True)

file_handler = logging.FileHandler(
    f"logs/sender_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
    encoding="utf-8"
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", datefmt="%H:%M:%S"))

logger = logging.getLogger("sender")
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.addHandler(console_handler)


# ===================================================================
# CONFIG
# ===================================================================

DEFAULT_CONFIG = {
    "token": "",
    "server_id": "",
    "channels": [],
    "message": "",
    "images": [],
    "mode": "once",
    "loop_interval_minutes": 60,
    "delay_between_channels": 1.5,
    "max_retries": 2,
    "schedule": {
        "enabled": False,
        "start_hour": 8,
        "end_hour": 23,
        "timezone_offset": 0
    }
}


def load_config(config_path):
    if not config_path.exists():
        with open(config_path, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
        logger.error(f"{config_path} creado con valores por defecto. Editalo y vuelve a ejecutar.")
        sys.exit(1)

    with open(config_path, "r") as f:
        cfg = json.load(f)

    for key, val in DEFAULT_CONFIG.items():
        if key not in cfg:
            cfg[key] = val
    return cfg


def validate_config(cfg):
    errors = []
    if not cfg.get("token"):
        errors.append("'token' esta vacio")
    if not cfg.get("server_id"):
        errors.append("'server_id' esta vacio")
    if not cfg.get("channels"):
        errors.append("'channels' esta vacio (lista de IDs de canales)")
    if not cfg.get("message") and not cfg.get("images"):
        errors.append("Necesitas al menos 'message' o 'images'")
    if errors:
        logger.error("Errores en config:")
        for e in errors:
            logger.error(f"  - {e}")
        sys.exit(1)


# ===================================================================
# SENDER
# ===================================================================

class MessageSender:
    API_BASE = "https://discord.com/api/v10"

    def __init__(self, cfg):
        self.cfg = cfg
        self.token = cfg["token"]
        self.server_id = cfg["server_id"]
        self.channels = cfg["channels"]
        self.message = cfg.get("message", "")
        self.images = cfg.get("images", [])
        self.delay = cfg.get("delay_between_channels", 1.5)
        self.max_retries = cfg.get("max_retries", 2)
        self.dry_run = False
        self.session = None
        self.sent = 0
        self.failed = 0

        self.base_headers = {
            "Authorization": self.token,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    async def verify_token(self):
        url = f"{self.API_BASE}/users/@me"
        headers = {**self.base_headers, "Content-Type": "application/json"}
        try:
            async with self.session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    user = await resp.json()
                    name = user.get("global_name") or user.get("username", "?")
                    logger.info(f"  Usuario: {name} ({user.get('id', '?')})")
                    return True
                elif resp.status == 401:
                    logger.error("Token invalido o expirado")
                    return False
                else:
                    logger.error(f"Error verificando token: HTTP {resp.status}")
                    return False
        except Exception as e:
            logger.error(f"Error de conexion: {e}")
            return False

    async def get_channel_name(self, channel_id):
        url = f"{self.API_BASE}/channels/{channel_id}"
        headers = {**self.base_headers, "Content-Type": "application/json"}
        try:
            async with self.session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("name", channel_id)
        except Exception:
            pass
        return str(channel_id)

    async def list_server_channels(self):
        url = f"{self.API_BASE}/guilds/{self.server_id}/channels"
        headers = {**self.base_headers, "Content-Type": "application/json"}
        try:
            async with self.session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    channels = await resp.json()
                    text_channels = [c for c in channels if c.get("type") in (0, 5)]
                    text_channels.sort(key=lambda c: c.get("position", 0))
                    return text_channels
                else:
                    logger.error(f"Error listando canales: HTTP {resp.status}")
                    return []
        except Exception as e:
            logger.error(f"Error: {e}")
            return []

    async def load_image(self, image_path):
        if image_path.startswith("http://") or image_path.startswith("https://"):
            try:
                async with self.session.get(image_path) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        ct = resp.headers.get("Content-Type", "image/png")
                        name = image_path.split("/")[-1].split("?")[0]
                        if not name or "." not in name:
                            ext = ct.split("/")[-1].split(";")[0]
                            name = f"image.{ext}"
                        return name, data, ct
                    else:
                        logger.error(f"  Error descargando imagen {image_path}: HTTP {resp.status}")
                        return None
            except Exception as e:
                logger.error(f"  Error descargando imagen {image_path}: {e}")
                return None

        p = Path(image_path)
        if not p.exists():
            p = Path("images") / image_path
        if not p.exists():
            logger.error(f"  Imagen no encontrada: {image_path}")
            return None
        ct = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
        return p.name, p.read_bytes(), ct

    async def send_to_channel(self, channel_id, attempt=1):
        if self.dry_run:
            ch_name = await self.get_channel_name(channel_id)
            logger.info(f"  [DRY-RUN] #{ch_name} ({channel_id})")
            self.sent += 1
            return True

        url = f"{self.API_BASE}/channels/{channel_id}/messages"
        image_data_list = []
        for img_path in self.images:
            result = await self.load_image(img_path)
            if result:
                image_data_list.append(result)

        try:
            if image_data_list:
                data = aiohttp.FormData()
                payload_json = {}
                if self.message:
                    payload_json["content"] = self.message
                data.add_field("payload_json", json.dumps(payload_json), content_type="application/json")
                for i, (filename, file_bytes, content_type) in enumerate(image_data_list):
                    data.add_field(f"files[{i}]", file_bytes, filename=filename, content_type=content_type)
                async with self.session.post(url, data=data, headers=self.base_headers) as resp:
                    return await self._handle_response(resp, channel_id, attempt)
            else:
                headers = {**self.base_headers, "Content-Type": "application/json"}
                payload = {"content": self.message}
                async with self.session.post(url, json=payload, headers=headers) as resp:
                    return await self._handle_response(resp, channel_id, attempt)
        except Exception as e:
            if attempt < self.max_retries:
                logger.warning(f"  Error en {channel_id}: {e}, reintento {attempt}/{self.max_retries}")
                await asyncio.sleep(1)
                return await self.send_to_channel(channel_id, attempt + 1)
            self.failed += 1
            logger.error(f"  Error enviando a {channel_id}: {e}")
            return False

    async def _handle_response(self, resp, channel_id, attempt):
        if resp.status == 200:
            self.sent += 1
            ch_name = await self.get_channel_name(channel_id)
            img_info = f" + {len(self.images)} img" if self.images else ""
            logger.info(f"  [{self.sent}] #{ch_name}{img_info}")
            return True
        elif resp.status == 429:
            data = await resp.json()
            wait = data.get("retry_after", 2)
            logger.warning(f"  Rate limit en {channel_id} -- esperando {wait:.1f}s")
            await asyncio.sleep(wait)
            return await self.send_to_channel(channel_id, attempt)
        elif resp.status == 403:
            self.failed += 1
            logger.error(f"  Sin permisos: {channel_id}")
            return False
        elif resp.status == 404:
            self.failed += 1
            logger.error(f"  Canal no encontrado: {channel_id}")
            return False
        else:
            if attempt < self.max_retries:
                logger.warning(f"  Error {resp.status} en {channel_id}, reintento {attempt}/{self.max_retries}")
                await asyncio.sleep(1)
                return await self.send_to_channel(channel_id, attempt + 1)
            self.failed += 1
            text = await resp.text()
            logger.error(f"  Error {resp.status} en {channel_id}: {text[:200]}")
            return False

    def is_within_schedule(self):
        sched = self.cfg.get("schedule", {})
        if not sched.get("enabled", False):
            return True
        offset = sched.get("timezone_offset", 0)
        tz = timezone(timedelta(hours=offset))
        now = datetime.now(tz)
        start = sched.get("start_hour", 0)
        end = sched.get("end_hour", 23)
        if start <= now.hour <= end:
            return True
        logger.debug(f"Fuera de horario ({now.hour}:00, permitido {start}:00-{end}:59)")
        return False

    async def send_once(self):
        self.sent = 0
        self.failed = 0
        if not self.is_within_schedule():
            logger.info("Fuera de horario, saltando envio")
            return
        logger.info(f"\nEnviando a {len(self.channels)} canales...")
        for channel_id in self.channels:
            await self.send_to_channel(str(channel_id))
            await asyncio.sleep(self.delay)
        logger.info(f"Resultado: {self.sent} enviados, {self.failed} fallidos")

    async def run(self, mode="once"):
        self.session = aiohttp.ClientSession()
        msg_preview = self.message[:50] + ("..." if len(self.message) > 50 else "")
        logger.info("=" * 55)
        logger.info("  bb-disc-bot - Sender")
        logger.info("=" * 55)
        if not await self.verify_token():
            await self.session.close()
            return
        logger.info(f"  Server:   {self.server_id}")
        logger.info(f"  Canales:  {len(self.channels)}")
        if self.message:
            logger.info(f"  Mensaje:  \"{msg_preview}\"")
        if self.images:
            logger.info(f"  Imagenes: {len(self.images)}")
        logger.info(f"  Modo:     {mode}")
        logger.info(f"  Delay:    {self.delay}s")
        if self.dry_run:
            logger.info("  ** DRY-RUN: no se enviara nada **")
        sched = self.cfg.get("schedule", {})
        if sched.get("enabled"):
            offset = sched.get("timezone_offset", 0)
            logger.info(f"  Horario:  {sched['start_hour']}:00 - {sched['end_hour']}:59 (UTC{offset:+d})")
        logger.info("=" * 55)
        try:
            if mode == "loop":
                interval = self.cfg.get("loop_interval_minutes", 60)
                logger.info(f"Modo loop: cada {interval} minutos")
                while True:
                    await self.send_once()
                    logger.info(f"Esperando {interval} minutos...")
                    await asyncio.sleep(interval * 60)
            else:
                await self.send_once()
        finally:
            await self.session.close()

    async def run_list_channels(self):
        self.session = aiohttp.ClientSession()
        logger.info("=" * 55)
        logger.info("  Listando canales del servidor")
        logger.info("=" * 55)
        if not await self.verify_token():
            await self.session.close()
            return
        channels = await self.list_server_channels()
        if channels:
            logger.info(f"\n  {len(channels)} canales de texto:\n")
            for ch in channels:
                ch_id = ch["id"]
                ch_name = ch.get("name", "?")
                ch_type = "anuncio" if ch.get("type") == 5 else "texto"
                marker = " <--" if ch_id in [str(c) for c in self.channels] else ""
                logger.info(f"  #{ch_name:<30} {ch_id}  ({ch_type}){marker}")
            logger.info(f"\n  Canales marcados con '<--' estan en tu config.json")
        else:
            logger.info("No se pudieron obtener canales")
        await self.session.close()


# ===================================================================
# CLI
# ===================================================================

def main():
    parser = argparse.ArgumentParser(description="bb-disc-bot - Sender de mensajes a Discord")
    parser.add_argument("--once", action="store_true", help="Envia una vez y sale (default)")
    parser.add_argument("--loop", action="store_true", help="Envia en bucle segun intervalo")
    parser.add_argument("--dry-run", action="store_true", help="Simula sin enviar")
    parser.add_argument("--list-channels", action="store_true", help="Lista canales del server")
    parser.add_argument("--message", "-m", type=str, help="Override del mensaje")
    parser.add_argument("--token", "-t", type=str, help="Override del token")
    parser.add_argument("--config", "-c", type=str, default="sender_config.json", help="Ruta al config")
    args = parser.parse_args()

    config_path = Path(args.config)
    cfg = load_config(config_path)

    env_token = os.environ.get("DISCORD_TOKEN")
    if env_token:
        cfg["token"] = env_token
    if args.token:
        cfg["token"] = args.token
    if args.message:
        cfg["message"] = args.message
    if not args.list_channels:
        validate_config(cfg)

    bot = MessageSender(cfg)
    bot.dry_run = args.dry_run

    try:
        if args.list_channels:
            asyncio.run(bot.run_list_channels())
        elif args.loop:
            asyncio.run(bot.run(mode="loop"))
        else:
            asyncio.run(bot.run(mode="once"))
    except KeyboardInterrupt:
        logger.info(f"\nCancelado. Enviados: {bot.sent}, Fallidos: {bot.failed}")


if __name__ == "__main__":
    main()
