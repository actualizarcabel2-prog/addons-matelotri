# -*- coding: utf-8 -*-
"""Matelotri Cinema - Servicio de protección de marca.
Restaura iconos y branding si Palantir3 actualiza y sobreescribe."""
import os
import shutil
import xbmc
import xbmcaddon
import xbmcvfs
import hashlib
import json
import time

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo("id")
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo("path"))
ADDON_DATA = xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))

# URL base donde están nuestros assets de respaldo
ASSETS_URL = "https://raw.githubusercontent.com/actualizarcabel2-prog/addons-matelotri/main/imagenes/"

MEDIA_DIR = os.path.join(ADDON_PATH, "resources", "media")
BACKUP_DIR = os.path.join(ADDON_DATA, "brand_backup")

# Archivos a proteger
BRAND_FILES = {
    "icon.png": os.path.join(ADDON_PATH, "icon.png"),
    "peliculas.png": os.path.join(MEDIA_DIR, "peliculas.png"),
    "series.png": os.path.join(MEDIA_DIR, "series.png"),
    "dibujos.png": os.path.join(MEDIA_DIR, "dibujos.png"),
    "anime.png": os.path.join(MEDIA_DIR, "anime.png"),
    "documentales.png": os.path.join(MEDIA_DIR, "documentales.png"),
    "musica.png": os.path.join(MEDIA_DIR, "musica.png"),
    "buscar.png": os.path.join(MEDIA_DIR, "buscar.png"),
    "fav.png": os.path.join(MEDIA_DIR, "fav.png"),
    "reajustes.png": os.path.join(MEDIA_DIR, "reajustes.png"),
}


def log(msg):
    xbmc.log("[MatelotriCinema] {}".format(msg), xbmc.LOGINFO)


def md5_file(path):
    """Calcula MD5 de un archivo."""
    if not os.path.exists(path):
        return ""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def backup_brand():
    """Guarda copia de seguridad de nuestros assets."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    hashes = {}
    for name, path in BRAND_FILES.items():
        if os.path.exists(path):
            backup = os.path.join(BACKUP_DIR, name)
            shutil.copy2(path, backup)
            hashes[name] = md5_file(path)
    # Guardar hashes
    with open(os.path.join(BACKUP_DIR, "hashes.json"), "w") as f:
        json.dump(hashes, f)
    log("Backup de marca creado ({} archivos)".format(len(hashes)))


def check_and_restore():
    """Verifica si los assets fueron sobreescritos y los restaura."""
    hash_file = os.path.join(BACKUP_DIR, "hashes.json")
    if not os.path.exists(hash_file):
        backup_brand()
        return

    with open(hash_file, "r") as f:
        saved_hashes = json.load(f)

    restored = 0
    for name, path in BRAND_FILES.items():
        if name in saved_hashes:
            current_hash = md5_file(path)
            if current_hash != saved_hashes[name]:
                # Archivo cambiado - restaurar
                backup = os.path.join(BACKUP_DIR, name)
                if os.path.exists(backup):
                    shutil.copy2(backup, path)
                    restored += 1
                    log("Restaurado: {}".format(name))

    if restored > 0:
        log("{} archivos de marca restaurados".format(restored))


def ensure_addon_xml():
    """Asegura que addon.xml tiene nuestro ID y nombre."""
    addon_xml = os.path.join(ADDON_PATH, "addon.xml")
    if os.path.exists(addon_xml):
        with open(addon_xml, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        if "palantir" in content.lower():
            content = content.replace("plugin.video.palantir3", ADDON_ID)
            content = content.replace("Palantir", "Matelotri Cinema")
            with open(addon_xml, "w", encoding="utf-8") as f:
                f.write(content)
            log("addon.xml corregido")


def main():
    log("Servicio de marca iniciado")
    monitor = xbmc.Monitor()

    # Primera ejecución - backup y verificación
    time.sleep(5)
    check_and_restore()
    ensure_addon_xml()

    # Bucle principal - verificar cada 30 min
    while not monitor.abortRequested():
        if monitor.waitForAbort(1800):
            break
        check_and_restore()

    log("Servicio de marca detenido")


if __name__ == "__main__":
    main()
