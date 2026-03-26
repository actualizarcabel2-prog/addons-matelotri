# -*- coding: utf-8 -*-
"""Matelotri Cinema — Kodi Addon v3.0
Conecta al servidor Matelotri para catálogos y streams.
"""
import sys
import os
import json

try:
    from urllib.request import urlopen, Request
    from urllib.parse import quote_plus, parse_qs
except ImportError:
    from urllib2 import urlopen, Request
    from urllib import quote_plus
    from urlparse import parse_qs

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

try:
    import xbmcvfs
    translatePath = xbmcvfs.translatePath
except AttributeError:
    translatePath = xbmc.translatePath

ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]
PROFILE = translatePath(ADDON.getAddonInfo("profile"))

# Auto-descubrimiento del servidor via GitHub Pages
CONFIG_URL = "https://raw.githubusercontent.com/actualizarcabel2-prog/addons-matelotri/main/matelotri-config.json"


def _load_auth():
    """Carga la contraseña guardada."""
    auth_file = os.path.join(PROFILE, "auth.json")
    if os.path.exists(auth_file):
        try:
            with open(auth_file, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_auth(data):
    """Guarda contraseña para no volver a pedirla."""
    if not os.path.exists(PROFILE):
        os.makedirs(PROFILE)
    auth_file = os.path.join(PROFILE, "auth.json")
    with open(auth_file, "w") as f:
        json.dump(data, f)


def _get_server():
    """Obtiene URL del servidor desde GitHub (auto-actualizable)."""
    try:
        req = Request(CONFIG_URL, headers={"User-Agent": "Kodi/21.2"})
        resp = urlopen(req, timeout=5)
        cfg = json.loads(resp.read().decode("utf-8"))
        if cfg.get("maintenance"):
            xbmcgui.Dialog().ok("Matelotri Cinema", cfg.get("message", "En mantenimiento"))
            return None, None
        return cfg.get("server", ""), cfg.get("access_key", "")
    except Exception:
        return (ADDON.getSetting("server_url") or "http://209.38.230.244:7000",
                ADDON.getSetting("access_key") or "cabel1n3")


def _check_password():
    """Verifica contraseña. La pide una vez y la guarda para siempre."""
    auth = _load_auth()
    if auth.get("verified"):
        return True

    # Pedir contraseña
    dialog = xbmcgui.Dialog()
    password = dialog.input("🔑 Introduce la contraseña de Matelotri Cinema",
                            type=xbmcgui.INPUT_ALPHANUM,
                            option=xbmcgui.ALPHANUM_HIDE_INPUT)
    if not password:
        dialog.ok("Matelotri Cinema", "Se necesita contraseña para acceder.")
        return False

    # Verificar contra el servidor
    server, expected_key = _get_server()
    if not server:
        return False

    if password == expected_key:
        # Pedir nombre y teléfono
        nombre = dialog.input("👤 Tu nombre (para tu cuenta)")
        if not nombre:
            nombre = "Cliente"
        telefono = dialog.input("📱 Tu teléfono (para soporte)")

        _save_auth({"verified": True, "key": password, "name": nombre, "phone": telefono})

        # Enviar datos al servidor para el dashboard
        try:
            reg_url = "{}/{}/manifest.json".format(server, password)
            req = Request(reg_url, headers={"User-Agent": "Kodi/21.2",
                                            "X-Client-Name": nombre,
                                            "X-Client-Phone": telefono})
            urlopen(req, timeout=5)
        except Exception:
            pass

        dialog.ok("Matelotri Cinema", "✅ ¡Bienvenido {}!\n30 días de prueba gratis.".format(nombre))
        return True
    else:
        dialog.ok("Matelotri Cinema", "❌ Contraseña incorrecta.")
        return False


MEDIA_PATH = os.path.join(ADDON.getAddonInfo("path"), "resources", "media")


def get_icon(name):
    p = os.path.join(MEDIA_PATH, name + ".png")
    return p if os.path.exists(p) else ""


def api_get(endpoint):
    """Llama al servidor Matelotri."""
    auth = _load_auth()
    server, _ = _get_server()
    key = auth.get("key", "cabel1n3")
    url = "{}/{}/{}".format(server.rstrip("/"), key, endpoint)
    try:
        req = Request(url, headers={"User-Agent": "Kodi/21.2"})
        resp = urlopen(req, timeout=12)
        return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        xbmcgui.Dialog().notification("Matelotri Cinema",
                                      "Error de conexión", xbmcgui.NOTIFICATION_ERROR, 3000)
        return {}


def main_menu():
    """Menú principal completo."""
    items = [
        # --- PELÍCULAS ---
        ("🎬 Películas Populares", "catalog/movie/matelotri-populares.json", "peliculas"),
        ("🆕 Estrenos", "catalog/movie/matelotri-estrenos.json", "peliculas"),
        ("⭐ Mejor Valoradas", "catalog/movie/matelotri-top.json", "peliculas"),
        ("🔥 Tendencias", "catalog/movie/matelotri-trending.json", "peliculas"),
        # --- GÉNEROS PELÍCULAS ---
        ("💥 Acción", "catalog/movie/matelotri-accion.json", "peliculas"),
        ("😂 Comedia", "catalog/movie/matelotri-comedia.json", "peliculas"),
        ("🎭 Drama", "catalog/movie/matelotri-drama.json", "peliculas"),
        ("👻 Terror", "catalog/movie/matelotri-terror.json", "peliculas"),
        ("🚀 Ciencia Ficción", "catalog/movie/matelotri-ciencia-ficcion.json", "peliculas"),
        ("🎨 Animación", "catalog/movie/matelotri-animacion.json", "peliculas"),
        ("📖 Documentales", "catalog/movie/matelotri-documentales.json", "documentales"),
        ("🔪 Thriller", "catalog/movie/matelotri-thriller.json", "peliculas"),
        ("❤️ Romance", "catalog/movie/matelotri-romance.json", "peliculas"),
        ("🗺️ Aventura", "catalog/movie/matelotri-aventura.json", "peliculas"),
        ("👨‍👩‍👧 Familia", "catalog/movie/matelotri-familia.json", "dibujos"),
        ("⚔️ Guerra", "catalog/movie/matelotri-guerra.json", "peliculas"),
        ("🔫 Crimen", "catalog/movie/matelotri-crimen.json", "peliculas"),
        ("🧙 Fantasía", "catalog/movie/matelotri-fantasia.json", "peliculas"),
        # --- SERIES ---
        ("📺 Series Populares", "catalog/series/matelotri-series.json", "series"),
        ("🏆 Series Top", "catalog/series/matelotri-series-top.json", "series"),
        ("📡 En Emisión", "catalog/series/matelotri-series-hoy.json", "series"),
        ("🎌 Anime", "catalog/series/matelotri-series-anime.json", "anime"),
        ("🎓 Docs Series", "catalog/series/matelotri-series-doc.json", "documentales"),
        ("🎭 Series Drama", "catalog/series/matelotri-series-drama.json", "series"),
        ("🕵️ Series Crimen", "catalog/series/matelotri-series-crimen.json", "series"),
        # --- PLATAFORMAS PELÍCULAS ---
        ("🔴 Netflix Películas", "catalog/movie/matelotri-netflix.json", "peliculas"),
        ("🔵 Amazon Películas", "catalog/movie/matelotri-amazon.json", "peliculas"),
        ("🏰 Disney+ Películas", "catalog/movie/matelotri-disney.json", "peliculas"),
        ("💜 HBO Max Películas", "catalog/movie/matelotri-hbo.json", "peliculas"),
        ("🍎 Apple TV+ Películas", "catalog/movie/matelotri-apple.json", "peliculas"),
        # --- PLATAFORMAS SERIES ---
        ("🔴 Netflix Series", "catalog/series/matelotri-netflix-series.json", "series"),
        ("🔵 Amazon Series", "catalog/series/matelotri-amazon-series.json", "series"),
        ("🏰 Disney+ Series", "catalog/series/matelotri-disney-series.json", "series"),
        ("💜 HBO Series", "catalog/series/matelotri-hbo-series.json", "series"),
        ("🍎 Apple TV+ Series", "catalog/series/matelotri-apple-series.json", "series"),
        # --- HERRAMIENTAS ---
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
    """Muestra enlaces disponibles via servidor VPS."""
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

    playable = []
    for s in streams:
        url = s.get("url", "")
        title = s.get("title", s.get("name", "Enlace"))
        if url:
            playable.append({"title": title, "url": url})

    if not playable:
        names = [s.get("title", s.get("name", ""))[:60] for s in streams[:20]]
        xbmcgui.Dialog().select("Enlaces encontrados ({})".format(len(streams)), names)
        return

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
    params = parse_qs(sys.argv[2].lstrip("?"))
    action = params.get("action", [None])[0]

    # Verificar contraseña (solo la primera vez)
    if not _check_password():
        return

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
    router()
