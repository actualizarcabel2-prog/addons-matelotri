# -*- coding: utf-8 -*-
"""Matelotri Cinema — Kodi Addon v3.0
Conecta al servidor Matelotri para catálogos y streams.
"""
import sys
import os
import json

try:
    from urllib.request import urlopen, Request
    from urllib.parse import urlencode, quote_plus, parse_qs
except ImportError:
    from urllib2 import urlopen, Request
    from urllib import urlencode, quote_plus
    from urlparse import parse_qs

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]

# Auto-descubrimiento del servidor via GitHub Pages
CONFIG_URL = "https://raw.githubusercontent.com/actualizarcabel2-prog/addons-matelotri/main/matelotri-config.json"

def _get_server():
    """Obtiene URL del servidor desde GitHub (auto-actualizable)."""
    try:
        req = Request(CONFIG_URL, headers={"User-Agent": "Kodi/21.2"})
        resp = urlopen(req, timeout=5)
        cfg = json.loads(resp.read().decode("utf-8"))
        if cfg.get("maintenance"):
            xbmcgui.Dialog().ok("Matelotri Cinema", cfg.get("message", "En mantenimiento"))
            return None, None
        return cfg.get("server", ""), cfg.get("access_key", "cabel1n3")
    except Exception:
        # Fallback a settings locales
        return (ADDON.getSetting("server_url") or "http://192.168.1.100:7000",
                ADDON.getSetting("access_key") or "cabel1n3")

SERVER, ACCESS_KEY = _get_server()
API = "{}/{}".format(SERVER.rstrip("/"), ACCESS_KEY) if SERVER else ""

MEDIA_PATH = os.path.join(ADDON.getAddonInfo("path"), "resources", "media")


def get_icon(name):
    p = os.path.join(MEDIA_PATH, name + ".png")
    return p if os.path.exists(p) else ""


def api_get(endpoint):
    """Llama al servidor Matelotri."""
    url = "{}/{}".format(API, endpoint)
    try:
        req = Request(url, headers={"User-Agent": "Kodi/21.2"})
        resp = urlopen(req, timeout=12)
        return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        xbmcgui.Dialog().notification("Matelotri Cinema",
                                      "Error de conexión", xbmcgui.NOTIFICATION_ERROR, 3000)
        return {}


def main_menu():
    """Menú principal."""
    items = [
        ("🎬 Películas Populares", "catalog/movie/matelotri-populares.json", "peliculas"),
        ("🆕 Estrenos", "catalog/movie/matelotri-estrenos.json", "peliculas"),
        ("⭐ Mejor Valoradas", "catalog/movie/matelotri-top.json", "peliculas"),
        ("📺 Series Populares", "catalog/series/matelotri-series.json", "series"),
        ("🔍 Buscar Película", "search_movie", "buscar"),
        ("🔍 Buscar Serie", "search_series", "buscar"),
        ("⚙️ Ajustes", "settings", "ajustes"),
    ]
    for title, action, icon in items:
        li = xbmcgui.ListItem(title)
        li.setArt({"icon": get_icon(icon), "thumb": get_icon(icon)})
        url = "{}?action={}".format(BASE_URL, action)
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    xbmcplugin.endOfDirectory(HANDLE)


def list_catalog(endpoint):
    """Lista películas o series desde el servidor."""
    data = api_get(endpoint)
    metas = data.get("metas", [])
    if not metas:
        xbmcgui.Dialog().notification("Matelotri Cinema", "Sin resultados", xbmcgui.NOTIFICATION_INFO)
        return

    content_type = "movies" if "/movie/" in endpoint else "tvshows"
    media_type = "movie" if "/movie/" in endpoint else "tvshow"
    xbmcplugin.setContent(HANDLE, content_type)

    for item in metas:
        li = xbmcgui.ListItem(item.get("name", ""))
        li.setInfo("video", {
            "title": item.get("name", ""),
            "year": int(item.get("year", 0)) if item.get("year") else None,
            "plot": item.get("description", ""),
            "rating": float(item.get("imdbRating", 0)) if item.get("imdbRating") else None,
            "mediatype": media_type
        })
        li.setArt({
            "poster": item.get("poster", ""),
            "fanart": item.get("background", ""),
            "thumb": item.get("poster", ""),
            "banner": item.get("background", "")
        })
        imdb_id = item.get("id", "")
        stream_type = "movie" if media_type == "movie" else "series"
        url = "{}?action=streams&type={}&id={}".format(BASE_URL, stream_type, imdb_id)
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)

    xbmcplugin.endOfDirectory(HANDLE)


def search(content_type):
    """Búsqueda."""
    kb = xbmc.Keyboard("", "Buscar en Matelotri Cinema")
    kb.doModal()
    if not kb.isConfirmed() or not kb.getText():
        return
    query = kb.getText()
    if content_type == "movie":
        endpoint = "catalog/movie/matelotri-buscar/search={}.json".format(quote_plus(query))
    else:
        endpoint = "catalog/series/matelotri-buscar-series/search={}.json".format(quote_plus(query))
    list_catalog(endpoint)


def show_streams(stream_type, imdb_id):
    """Muestra enlaces disponibles."""
    dialog = xbmcgui.DialogProgress()
    dialog.create("Matelotri Cinema", "Buscando enlaces...")
    dialog.update(30)

    data = api_get("stream/{}/{}.json".format(stream_type, imdb_id))
    streams = data.get("streams", [])

    dialog.update(80)
    dialog.close()

    if not streams:
        xbmcgui.Dialog().ok("Matelotri Cinema", "No se encontraron enlaces")
        return

    # Filtrar streams con URL directa
    playable = []
    for s in streams:
        url = s.get("url", "")
        title = s.get("title", s.get("name", "Enlace"))
        if url:
            playable.append({"title": title, "url": url})

    if not playable:
        # Si no hay URLs directas, mostrar info
        names = [s.get("title", s.get("name", ""))[:60] for s in streams[:20]]
        xbmcgui.Dialog().select("Enlaces encontrados ({})".format(len(streams)), names)
        return

    # Selector de calidad
    titles = [p["title"][:70] for p in playable[:15]]
    idx = xbmcgui.Dialog().select(
        "Elige calidad ({} enlaces)".format(len(playable)), titles)

    if idx >= 0:
        play_url(playable[idx]["url"], playable[idx]["title"])


def play_url(url, title=""):
    """Reproduce URL directa."""
    li = xbmcgui.ListItem(title)
    li.setPath(url)
    li.setInfo("video", {"title": title})
    xbmcplugin.setResolvedUrl(HANDLE, True, li)


def router():
    """Router principal."""
    # xbmc already imported at top level
    params = parse_qs(sys.argv[2].lstrip("?"))

    action = params.get("action", [None])[0]

    if action is None:
        main_menu()
    elif action == "settings":
        ADDON.openSettings()
    elif action == "search_movie":
        search("movie")
    elif action == "search_series":
        search("series")
    elif action == "streams":
        show_streams(params["type"][0], params["id"][0])
    elif action.startswith("catalog/"):
        list_catalog(action)
    else:
        main_menu()


if __name__ == "__main__":
    # xbmc already imported at top level
    router()
