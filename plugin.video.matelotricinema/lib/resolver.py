# -*- coding: utf-8 -*-
"""Resolver AllDebrid Premium para Matelotri Cinema.
Usa torrents cacheados en AllDebrid = stream instantaneo."""
import json
import time
try:
    from urllib.request import urlopen, Request
    from urllib.parse import quote, urlencode
except ImportError:
    from urllib2 import urlopen, Request
    from urllib import quote, urlencode

AD_KEY = "i5MI5R32vKVfOk3v46WA"
AD_AGENT = "matelotri"
AD_BASE = "https://api.alldebrid.com/v4"

HEADERS = {"User-Agent": "Kodi/21.2 Matelotri", "Accept": "application/json"}


def _fetch_json(url, timeout=8):
    try:
        req = Request(url, headers=HEADERS)
        return json.loads(urlopen(req, timeout=timeout).read().decode("utf-8"))
    except:
        return {}


def _ad_api(endpoint, extra=""):
    url = "{}/{}?agent={}&apikey={}{}".format(AD_BASE, endpoint, AD_AGENT, AD_KEY, extra)
    return _fetch_json(url, timeout=10)


def resolve_movie(title, year=None, tmdb_id=None, imdb_id=None):
    links = []
    magnets = []

    # YTS - peliculas
    if imdb_id:
        magnets.extend(_yts_magnets(imdb_id, title))

    # Torrent generico
    if not magnets and title:
        q = "{} {}".format(title, year) if year else title
        magnets.extend(_search_magnets(q))

    # Resolver via AllDebrid
    if magnets:
        links.extend(_resolve_magnets(magnets))

    return links


def resolve_episode(title, season, episode, tmdb_id=None, imdb_id=None):
    s, e = int(season), int(episode)
    q = "{} S{:02d}E{:02d}".format(title, s, e)
    magnets = _search_magnets(q)
    return _resolve_magnets(magnets) if magnets else []


# ============================================================
# FUENTES DE MAGNETS
# ============================================================

def _yts_magnets(imdb_id, title=""):
    magnets = []
    try:
        url = "https://yts.mx/api/v2/list_movies.json?query_term={}&limit=1".format(imdb_id)
        data = _fetch_json(url, timeout=6)
        for movie in data.get("data", {}).get("movies", [])[:1]:
            for t in movie.get("torrents", []):
                h = t.get("hash", "")
                q = t.get("quality", "720p")
                s = t.get("size", "")
                if h:
                    name = "{} [{}]".format(movie.get("title", title), q)
                    mag = "magnet:?xt=urn:btih:{}".format(h)
                    magnets.append({"magnet": mag, "quality": q, "size": s, "name": name})
    except:
        pass
    return magnets


def _search_magnets(query):
    magnets = []
    try:
        url = "https://apibay.org/q.php?q={}&cat=0".format(quote(query))
        data = _fetch_json(url, timeout=6)
        if not isinstance(data, list):
            return magnets

        for item in data[:5]:
            h = item.get("info_hash", "")
            name = item.get("name", "")
            size = int(item.get("size", 0))
            if not h or h == "0" * 40 or size < 104857600:
                continue

            q = "SD"
            nl = name.lower()
            if "2160p" in nl or "4k" in nl:
                q = "4K"
            elif "1080p" in nl:
                q = "1080p"
            elif "720p" in nl:
                q = "720p"

            mag = "magnet:?xt=urn:btih:{}".format(h)
            magnets.append({
                "magnet": mag, "quality": q,
                "size": "{:.0f} MB".format(size / 1048576),
                "name": name[:60]
            })
    except:
        pass
    return magnets


# ============================================================
# ALLDEBRID
# ============================================================

def _resolve_magnets(magnets):
    """Resuelve magnets via AllDebrid - solo cacheados (instantaneo)."""
    links = []

    for m in magnets[:4]:
        try:
            stream = _ad_instant_or_upload(m["magnet"])
            if stream:
                links.append({
                    "name": "[COLOR gold]{} {}[/COLOR] ({})".format(
                        m["quality"], m["name"], m.get("size", "")),
                    "url": stream,
                    "quality": m["quality"],
                    "lang": "multi",
                    "source": "alldebrid"
                })
        except:
            pass

    return links


def _ad_instant_or_upload(magnet):
    """Intenta cache instantaneo, si no, upload rapido."""
    # 1. Subir magnet
    try:
        extra = "&magnets[]={}".format(quote(magnet))
        data = _ad_api("magnet/upload", extra)

        if data.get("status") != "success":
            return None

        mags = data.get("data", {}).get("magnets", [])
        if not mags:
            return None

        mag_id = mags[0].get("id")
        ready = mags[0].get("ready", False)

        if not mag_id:
            return None

        # 2. Si ya esta ready (cacheado), obtener links
        if ready:
            return _get_stream_from_magnet(mag_id)

        # 3. Si no, esperar max 5 seg
        for _ in range(3):
            time.sleep(1.5)
            status = _ad_api("magnet/status", "&id={}".format(mag_id))
            mag_data = status.get("data", {}).get("magnets", {})
            if mag_data.get("statusCode") == 4:
                return _get_stream_from_magnet(mag_id)

        # 4. Borrar magnet si no estuvo listo
        _ad_api("magnet/delete", "&id={}".format(mag_id))
    except:
        pass
    return None


def _get_stream_from_magnet(mag_id):
    """Obtiene URL de stream del magnet procesado."""
    try:
        status = _ad_api("magnet/status", "&id={}".format(mag_id))
        mag = status.get("data", {}).get("magnets", {})
        file_links = mag.get("links", [])

        # Buscar video mas grande
        video_exts = ('.mkv', '.mp4', '.avi', '.mov', '.wmv')
        best_link = None
        best_size = 0

        for fl in file_links:
            fn = fl.get("filename", "").lower()
            sz = fl.get("size", 0)
            if any(fn.endswith(ext) for ext in video_exts) and sz > best_size:
                best_link = fl.get("link")
                best_size = sz

        if best_link:
            return _ad_unlock(best_link)
    except:
        pass
    return None


def _ad_unlock(link):
    """Desbloquea enlace via AllDebrid."""
    try:
        data = _ad_api("link/unlock", "&link={}".format(quote(link)))
        if data.get("status") == "success":
            return data.get("data", {}).get("link", "")
    except:
        pass
    return None


def filter_by_quality(links, max_quality="4K"):
    quality_order = {"SD": 0, "720p": 1, "1080p": 2, "4K": 3}
    max_val = quality_order.get(max_quality, 3)
    return [l for l in links
            if quality_order.get(l.get("quality", "SD"), 0) <= max_val]
