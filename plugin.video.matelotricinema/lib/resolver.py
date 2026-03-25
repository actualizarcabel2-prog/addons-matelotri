# -*- coding: utf-8 -*-
"""Resolver AllDebrid Premium para Matelotri Cinema.
Usa YTS/torrents -> AllDebrid -> stream directo."""
import json
import re
import time
try:
    from urllib.request import urlopen, Request
    from urllib.parse import quote, urlencode
except ImportError:
    from urllib2 import urlopen, Request
    from urllib import quote, urlencode

# AllDebrid API key premium
AD_KEY = "i5MI5R32vKVfOk3v46WA"
AD_AGENT = "matelotri"
AD_BASE = "https://api.alldebrid.com/v4"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 12) Kodi/21.2",
    "Accept": "application/json"
}


def _fetch_json(url, timeout=12):
    try:
        req = Request(url, headers=HEADERS)
        return json.loads(urlopen(req, timeout=timeout).read().decode("utf-8"))
    except:
        return {}


def _ad_api(endpoint, params=None):
    """Llamada a AllDebrid API."""
    url = "{}/{}?agent={}&apikey={}".format(AD_BASE, endpoint, AD_AGENT, AD_KEY)
    if params:
        for k, v in params.items():
            url += "&{}={}".format(k, quote(str(v)))
    return _fetch_json(url)


def resolve_movie(title, year=None, tmdb_id=None, imdb_id=None):
    """Busca y resuelve enlaces premium para película."""
    links = []

    # Fuente 1: YTS (torrents de películas)
    if imdb_id:
        links.extend(_yts_movie(imdb_id, title))

    # Fuente 2: 1337x via torrent API
    if title:
        search = "{} {}".format(title, year) if year else title
        links.extend(_torrent_search(search, "movie"))

    return links


def resolve_episode(title, season, episode, tmdb_id=None, imdb_id=None):
    """Busca y resuelve enlaces premium para episodio."""
    s, e = int(season), int(episode)
    search = "{} S{:02d}E{:02d}".format(title, s, e)
    return _torrent_search(search, "tv")


# ============================================================
# FUENTES DE TORRENTS
# ============================================================

def _yts_movie(imdb_id, title=""):
    """YTS.mx API - películas en torrent."""
    links = []
    try:
        url = "https://yts.mx/api/v2/list_movies.json?query_term={}".format(imdb_id)
        data = _fetch_json(url)
        movies = data.get("data", {}).get("movies", [])

        for movie in movies[:1]:  # Solo primera coincidencia
            for torrent in movie.get("torrents", []):
                quality = torrent.get("quality", "720p")
                hash_val = torrent.get("hash", "")
                size = torrent.get("size", "")

                if not hash_val:
                    continue

                # Crear magnet
                name = quote("{} ({}) [{}]".format(
                    movie.get("title", title), movie.get("year", ""), quality))
                magnet = "magnet:?xt=urn:btih:{}&dn={}".format(hash_val, name)

                # Resolver via AllDebrid
                stream_url = _alldebrid_magnet(magnet)
                if stream_url:
                    links.append({
                        "name": "[COLOR gold]YTS {}[/COLOR] - {} ({})".format(
                            quality, movie.get("title", ""), size),
                        "url": stream_url,
                        "quality": quality,
                        "lang": "multi",
                        "source": "yts"
                    })
    except:
        pass
    return links


def _torrent_search(query, media_type):
    """Busca torrents y resuelve via AllDebrid."""
    links = []
    try:
        # Usar API de búsqueda de torrents
        url = "https://apibay.org/q.php?q={}&cat=0".format(quote(query))
        data = _fetch_json(url)

        if not isinstance(data, list):
            return links

        count = 0
        for item in data:
            if count >= 3:
                break
            name = item.get("name", "")
            info_hash = item.get("info_hash", "")
            size = int(item.get("size", 0))

            if not info_hash or info_hash == "0000000000000000000000000000000000000000":
                continue

            size_mb = size / 1048576
            if size_mb < 100:  # Ignorar archivos muy pequeños
                continue

            quality = "SD"
            name_lower = name.lower()
            if "2160p" in name_lower or "4k" in name_lower:
                quality = "4K"
            elif "1080p" in name_lower:
                quality = "1080p"
            elif "720p" in name_lower:
                quality = "720p"

            magnet = "magnet:?xt=urn:btih:{}&dn={}".format(
                info_hash, quote(name))

            stream_url = _alldebrid_magnet(magnet)
            if stream_url:
                links.append({
                    "name": "[COLOR gold]{} {}[/COLOR] ({:.0f} MB)".format(
                        quality, name[:50], size_mb),
                    "url": stream_url,
                    "quality": quality,
                    "lang": "multi",
                    "source": "torrent"
                })
                count += 1
    except:
        pass
    return links


# ============================================================
# ALLDEBRID RESOLVER
# ============================================================

def _alldebrid_magnet(magnet):
    """Sube magnet a AllDebrid y obtiene enlace directo."""
    try:
        # 1. Subir magnet
        url = "{}/magnet/upload?agent={}&apikey={}&magnets[]={}".format(
            AD_BASE, AD_AGENT, AD_KEY, quote(magnet))
        data = _fetch_json(url, timeout=15)

        if data.get("status") != "success":
            return None

        magnets = data.get("data", {}).get("magnets", [])
        if not magnets:
            return None

        magnet_id = magnets[0].get("id")
        if not magnet_id:
            return None

        # 2. Esperar a que esté listo (max 10 seg)
        for _ in range(5):
            status = _ad_api("magnet/status", {"id": magnet_id})
            mag_data = status.get("data", {}).get("magnets", {})

            if mag_data.get("statusCode") == 4:  # Ready
                # 3. Buscar archivo de video más grande
                links = mag_data.get("links", [])
                video_link = _find_video_link(links)
                if video_link:
                    # 4. Desbloquear enlace
                    return _alldebrid_unlock(video_link)
                break
            elif mag_data.get("statusCode") == 1:  # En cola
                time.sleep(2)
            else:
                time.sleep(2)

    except:
        pass
    return None


def _find_video_link(links):
    """Encuentra el archivo de video más grande en los links."""
    video_exts = ('.mkv', '.mp4', '.avi', '.mov', '.wmv')
    best = None
    best_size = 0

    for link in links:
        filename = link.get("filename", "").lower()
        size = link.get("size", 0)

        if any(filename.endswith(ext) for ext in video_exts):
            if size > best_size:
                best = link.get("link")
                best_size = size

    return best


def _alldebrid_unlock(link):
    """Desbloquea un enlace via AllDebrid."""
    try:
        data = _ad_api("link/unlock", {"link": link})
        if data.get("status") == "success":
            return data.get("data", {}).get("link", "")
    except:
        pass
    return None


def filter_by_quality(links, max_quality="720p"):
    quality_order = {"SD": 0, "720p": 1, "1080p": 2, "4K": 3}
    max_val = quality_order.get(max_quality, 1)
    return [l for l in links
            if quality_order.get(l.get("quality", "SD"), 0) <= max_val]
