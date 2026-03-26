# -*- coding: utf-8 -*-
"""Matelotri Cinema - Servicio de marca + sincronización datos."""
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

# Ruta userdata de Palantir3
P3_ID = "plugin.video.palantir3"
USERDATA = xbmcvfs.translatePath("special://userdata/addon_data/")
P3_DATA = os.path.join(USERDATA, P3_ID)
MY_DATA = os.path.join(USERDATA, ADDON_ID)

MEDIA_DIR = os.path.join(ADDON_PATH, "resources", "media")
BACKUP_DIR = os.path.join(MY_DATA, "brand_backup")

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


def sync_palantir_data():
    """Copia/sincroniza datos de Palantir3 al addon Matelotri."""
    if not os.path.exists(P3_DATA):
        log("No se encontro userdata de Palantir3 en: " + P3_DATA)
        return False

    os.makedirs(MY_DATA, exist_ok=True)

    # Archivos importantes a sincronizar
    files_to_sync = [
        "settings.xml",
        "cache.db",
        "watched.db",
        "cookies.dat",
    ]

    synced = 0
    for f in files_to_sync:
        src = os.path.join(P3_DATA, f)
        dst = os.path.join(MY_DATA, f)
        if os.path.exists(src):
            # Solo copiar si es más nuevo o no existe
            if not os.path.exists(dst) or \
               os.path.getmtime(src) > os.path.getmtime(dst):
                shutil.copy2(src, dst)
                synced += 1
                log("Sincronizado: " + f)

    if synced > 0:
        log("{} archivos sincronizados desde Palantir3".format(synced))

    return True


def md5_file(path):
    if not os.path.exists(path):
        return ""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def backup_brand():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    hashes = {}
    for name, path in BRAND_FILES.items():
        if os.path.exists(path):
            shutil.copy2(path, os.path.join(BACKUP_DIR, name))
            hashes[name] = md5_file(path)
    with open(os.path.join(BACKUP_DIR, "hashes.json"), "w") as f:
        json.dump(hashes, f)
    log("Backup de marca creado")


def check_and_restore():
    hash_file = os.path.join(BACKUP_DIR, "hashes.json")
    if not os.path.exists(hash_file):
        backup_brand()
        return

    with open(hash_file, "r") as f:
        saved = json.load(f)

    restored = 0
    for name, path in BRAND_FILES.items():
        if name in saved and md5_file(path) != saved[name]:
            backup = os.path.join(BACKUP_DIR, name)
            if os.path.exists(backup):
                shutil.copy2(backup, path)
                restored += 1

    if restored:
        log("{} archivos de marca restaurados".format(restored))


def main():
    log("Servicio Matelotri Cinema iniciado")
    monitor = xbmc.Monitor()
    time.sleep(3)

    # 1. Sincronizar datos de Palantir3 (API keys, Trakt, etc.)
    sync_palantir_data()

    # 2. Proteger marca
    check_and_restore()

    # 3. Bucle: sincronizar cada 15 min
    while not monitor.abortRequested():
        if monitor.waitForAbort(900):  # 15 min
            break
        sync_palantir_data()
        check_and_restore()

    log("Servicio Matelotri Cinema detenido")


if __name__ == "__main__":
    main()
