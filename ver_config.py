#!/usr/bin/env python3
"""
Configurador interactivo del bot auto-responder.
Ejecutar: python3 ver_config.py
"""

import os
import json
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "bot_config.json"

DEFAULT_CONFIG = {
    "canal_id": "",
    "comando": "!roll",
    "dealers": [],
    "usuarios": []
}


def cargar():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()


def guardar(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print("\n[OK] Guardado")


def limpiar():
    os.system('clear' if os.name != 'nt' else 'cls')


def mostrar(config):
    limpiar()
    print("=" * 55)
    print("       CONFIGURACION - AUTO RESPONDER")
    print("=" * 55)

    print(f"\n[1] CANAL:   {config.get('canal_id') or '(vacio)'}")
    print(f"[2] COMANDO: {config.get('comando', '!roll')}")

    dealers = config.get('dealers', [])
    print(f"\n[3] DEALERS ({len(dealers)}):")
    for i, d in enumerate(dealers, 1):
        print(f"    {i}. {d}")
    if not dealers:
        print("    (ninguno)")

    usuarios = config.get('usuarios', [])
    print(f"\n[4] USUARIOS ({len(usuarios)}):")
    for i, u in enumerate(usuarios, 1):
        nombre = u.get('nombre', 'Sin nombre')
        tiene_token = "con token" if u.get('token') else "SIN TOKEN"
        estado = "ON" if u.get('activo', True) else "OFF"
        print(f"    {i}. [{estado}] {nombre} ({tiene_token})")
    if not usuarios:
        print("    (ninguno)")

    print("\n" + "=" * 55)


def menu_dealers(config):
    dealers = config.get('dealers', [])
    print("\nDEALERS actuales:")
    for i, d in enumerate(dealers, 1):
        print(f"  {i}. {d}")

    print("\n  a - Anadir")
    print("  e - Eliminar")
    print("  Enter - Volver")

    op = input("\n> ").strip().lower()

    if op == 'a':
        nuevo = input("ID del dealer: ").strip()
        if nuevo and nuevo not in dealers:
            dealers.append(nuevo)
            config['dealers'] = dealers
            guardar(config)
    elif op == 'e' and dealers:
        try:
            idx = int(input("Numero a eliminar: ")) - 1
            if 0 <= idx < len(dealers):
                dealers.pop(idx)
                config['dealers'] = dealers
                guardar(config)
        except ValueError:
            pass


def menu_usuarios(config):
    usuarios = config.get('usuarios', [])
    print("\nUSUARIOS actuales:")
    for i, u in enumerate(usuarios, 1):
        estado = "ON" if u.get('activo', True) else "OFF"
        print(f"  {i}. [{estado}] {u.get('nombre', '?')}")

    print("\n  a - Anadir usuario")
    print("  t - Cambiar token")
    print("  x - Activar/Desactivar")
    print("  e - Eliminar")
    print("  Enter - Volver")

    op = input("\n> ").strip().lower()

    if op == 'a':
        nombre = input("Nombre del usuario: ").strip()
        if nombre:
            print("\nPara obtener el token:")
            print("1. Abre Discord en navegador (discord.com/app)")
            print("2. F12 > Network > cualquier peticion a discord.com/api")
            print("3. Copia la cabecera 'Authorization'")
            token = input("\nToken: ").strip()
            usuarios.append({'nombre': nombre, 'token': token, 'activo': True})
            config['usuarios'] = usuarios
            guardar(config)

    elif op == 't' and usuarios:
        try:
            idx = int(input("Numero de usuario: ")) - 1
            if 0 <= idx < len(usuarios):
                token = input("Nuevo token: ").strip()
                if token:
                    usuarios[idx]['token'] = token
                    config['usuarios'] = usuarios
                    guardar(config)
        except ValueError:
            pass

    elif op == 'x' and usuarios:
        try:
            idx = int(input("Numero de usuario: ")) - 1
            if 0 <= idx < len(usuarios):
                usuarios[idx]['activo'] = not usuarios[idx].get('activo', True)
                config['usuarios'] = usuarios
                guardar(config)
        except ValueError:
            pass

    elif op == 'e' and usuarios:
        try:
            idx = int(input("Numero a eliminar: ")) - 1
            if 0 <= idx < len(usuarios):
                usuarios.pop(idx)
                config['usuarios'] = usuarios
                guardar(config)
        except ValueError:
            pass


def main():
    config = cargar()

    while True:
        mostrar(config)
        print("\nElige que cambiar:")
        print("  1 - Canal")
        print("  2 - Comando")
        print("  3 - Dealers")
        print("  4 - Usuarios")
        print("  0 - Salir")

        op = input("\n> ").strip()

        if op == '0':
            print("\nAdios!")
            break
        elif op == '1':
            nuevo = input(f"Nuevo canal (actual: {config.get('canal_id', 'ninguno')}): ").strip()
            if nuevo:
                config['canal_id'] = nuevo
                guardar(config)
        elif op == '2':
            nuevo = input(f"Nuevo comando (actual: {config.get('comando', '!roll')}): ").strip()
            if nuevo:
                config['comando'] = nuevo
                guardar(config)
        elif op == '3':
            menu_dealers(config)
        elif op == '4':
            menu_usuarios(config)

        if op not in ['3', '4']:
            input("\nEnter para continuar...")


if __name__ == '__main__':
    main()
