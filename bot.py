#!/usr/bin/env python3
"""
bb-disc-bot - Auto-Responder
=============================
Se conecta al Gateway de Discord via WebSocket, vigila un canal
y responde automaticamente cuando un "dealer" publica una imagen.

Soporta multiples usuarios (cada uno con su token).
Reconexion automatica 24/7.

Configuracion: bot_config.json (usar ver_config.py para editar)
"""

import json
import asyncio
import aiohttp
from aiohttp import WSMsgType
from pathlib import Path

import ssl
ssl._create_default_https_context = ssl._create_unverified_context

CONFIG_FILE = Path(__file__).parent / "bot_config.json"
GATEWAY_URL = "wss://gateway.discord.gg/?v=10&encoding=json"

DEFAULT_CONFIG = {
    "canal_id": "",
    "comando": "!roll",
    "dealers": [],
    "usuarios": []
}


def cargar_config():
    """Carga configuracion desde JSON"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()


def guardar_config(config):
    """Guarda configuracion en JSON"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


class Usuario:
    """Bot para un usuario individual"""

    def __init__(self, nombre, token, canal_id, dealer_ids, comando):
        self.nombre = nombre
        self.token = token
        self.canal_id = int(canal_id) if canal_id else 0
        self.dealer_ids = [int(d) for d in dealer_ids if d]
        self.comando = comando
        self.mi_id = None
        self.respondidos = set()
        self.headers = {
            "Authorization": token,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    def log(self, msg):
        print(f"[{self.nombre}] {msg}")

    async def responder(self, channel_id, message_id):
        """Envia reply al mensaje"""
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        payload = {
            "content": self.comando,
            "message_reference": {"message_id": str(message_id)}
        }

        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json=payload, ssl=ssl_ctx) as resp:
                if resp.status == 200:
                    self.log(f"Respondido: {self.comando}")
                    return True
                else:
                    text = await resp.text()
                    self.log(f"Error {resp.status}: {text[:80]}")
                    return False

    async def heartbeat(self, ws, intervalo, seq):
        """Mantiene conexion viva"""
        while True:
            await asyncio.sleep(intervalo / 1000)
            try:
                await ws.send_json({"op": 1, "d": seq[0]})
            except Exception:
                break

    async def ejecutar(self):
        """Loop principal del bot"""
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        seq = [None]

        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(GATEWAY_URL, ssl=ssl_ctx) as ws:
                self.log("Conectando...")

                # Recibir HELLO
                msg = await ws.receive()
                if msg.type != WSMsgType.TEXT:
                    self.log("Error de conexion")
                    return

                data = json.loads(msg.data)
                intervalo = data['d']['heartbeat_interval']

                # Heartbeat en background
                hb = asyncio.create_task(self.heartbeat(ws, intervalo, seq))

                # Identificarse
                await ws.send_json({
                    "op": 2,
                    "d": {
                        "token": self.token,
                        "properties": {"os": "windows", "browser": "chrome", "device": ""},
                        "presence": {"status": "online", "afk": False}
                    }
                })

                # Loop de eventos
                while True:
                    msg = await ws.receive()

                    if msg.type == WSMsgType.TEXT:
                        try:
                            data = json.loads(msg.data)
                        except Exception:
                            continue

                        if data.get('s'):
                            seq[0] = data['s']

                        evento = data.get('t')

                        if evento == 'READY':
                            user = data['d']['user']
                            self.mi_id = int(user['id'])
                            self.log(f"Conectado como: {user['username']}")
                            continue

                        if evento != 'MESSAGE_CREATE':
                            continue

                        msg_data = data['d']
                        canal = int(msg_data['channel_id'])
                        autor = int(msg_data['author']['id'])

                        # Ignorar propios mensajes
                        if self.mi_id and autor == self.mi_id:
                            continue

                        # Solo el canal configurado
                        if canal != self.canal_id:
                            continue

                        # Solo dealers
                        if autor not in self.dealer_ids:
                            continue

                        # Verificar que tiene imagen
                        attachments = msg_data.get('attachments', [])
                        tiene_imagen = False
                        for att in attachments:
                            fname = att.get('filename', '').lower()
                            ctype = att.get('content_type', '')
                            if any(fname.endswith(ext) for ext in ('.png', '.jpg', '.jpeg', '.gif', '.webp')) or 'image' in ctype:
                                tiene_imagen = True
                                break

                        if not tiene_imagen:
                            continue

                        msg_id = msg_data['id']

                        # Control de duplicados
                        if msg_id in self.respondidos:
                            continue

                        autor_nombre = msg_data['author'].get('username', '?')
                        self.log(f"IMAGEN de {autor_nombre} detectada!")

                        self.respondidos.add(msg_id)
                        await self.responder(canal, msg_id)

                    elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                        self.log("Desconectado")
                        break

                hb.cancel()


async def ejecutar_todos(config):
    """Ejecuta todos los usuarios habilitados"""
    usuarios = config.get('usuarios', [])
    activos = [u for u in usuarios if u.get('activo', True) and u.get('token')]

    if not activos:
        print("\n[ERROR] No hay usuarios activos con token")
        print("Ejecuta: python3 ver_config.py")
        return

    canal = config.get('canal_id', '')
    dealers = config.get('dealers', [])
    comando = config.get('comando', '!roll')

    if not canal:
        print("[ERROR] No hay canal configurado")
        return

    if not dealers:
        print("[ERROR] No hay dealers configurados")
        return

    print("=" * 55)
    print("       AUTO-RESPONDER - MULTI USUARIO")
    print("=" * 55)
    print(f"Canal: {canal}")
    print(f"Comando: {comando}")
    print(f"Dealers: {len(dealers)}")
    print(f"Usuarios: {len(activos)}")
    print("=" * 55 + "\n")

    bots = [
        Usuario(u['nombre'], u['token'], canal, dealers, comando)
        for u in activos
    ]

    await asyncio.gather(*[b.ejecutar() for b in bots], return_exceptions=True)


async def main_loop():
    """Loop con reconexion automatica"""
    while True:
        try:
            config = cargar_config()
            await ejecutar_todos(config)
        except Exception as e:
            print(f"[ERROR] {e}")

        print("\n[...] Reconectando en 5s...")
        await asyncio.sleep(5)


if __name__ == '__main__':
    print("Iniciando bot...")
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("\nBot detenido")
