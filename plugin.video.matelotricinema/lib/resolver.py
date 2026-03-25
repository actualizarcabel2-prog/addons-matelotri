# -*- coding: utf-8 -*-
"""Resolver AllDebrid para Matelotri Cinema v4.
Multiples fuentes de torrents + AllDebrid premium."""
import json
import time
try:
    from urllib.request import urlopen, Request
    from urllib.parse import quote
except ImportError:
    from urllib2 import urlopen, Request
    from urllib import quote

AD_KEY = "i5MI5R32vKVfOk3v46WA"
AD_AGENT = "matelotri"
AD_BASE = "https://api.alldebrid.com/v4"
HEADERS = {"User-Agent": "Kodi/21.2 Matelotri", "Accept": "application/json"}


def _get(url, timeout=8):
    try:
        return json.loads(urlopen(
            Request(url, headers=HEADERS), timeout=timeout
        ).read().decode("utf-8"))
    except:
        return {}


def _ad(endpoint, extra=""):
    return _get("{}/{}?agent={}&apikey={}{}".format(
        AD_BASE, endpoint, AD_AGENT, AD_KEY, extra), timeout=10)


# ============================================================
# RESOLVER PRINCIPAL
# ============================================================

def resolve_movie(title, year=None, tmdb_id=None, imdb_id=None):
    magnets = []
    # Fuente 1: YTS
    if imdb_id:
        magnets.extend(_yts(imdb_id))
    # Fuente 2: EZTV / 1337x via Torrent Galaxy
    if not magnets:
        q = "{} {}".format(title, year) if year else title
        magnets.extend(_tgx(q))
    # Fuente 3: PirateBay
    if not magnets:
        q = "{} {}".format(title, year) if year else title
        magnets.extend(_tpb(q))
    # Fuente 4: RARBG cached en AllDebrid
    if not magnets and imdb_id:
        magnets.extend(_tpb(imdb_id))

    return _resolve(magnets)


def resolve_episode(title, season, episode, tmdb_id=None, imdb_id=None):
    s, e = int(season), int(episode)
    q = "{} S{:02d}E{:02d}".format(title, s, e)
    magnets = _tgx(q)
    if not magnets:
        magnets = _tpb(q)
    if not magnets:
        magnets = _eztv(imdb_id, s, e) if imdb_id else []
    return _resolve(magnets)


# ============================================================
# FUENTES DE MAGNETS
# ============================================================

def _yts(imdb_id):
    magnets = []
    try:
        data = _get("https://yts.mx/api/v2/list_movies.json?query_term={}&limit=1".format(imdb_id), 6)
        for m in data.get("data", {}).get("movies", [])[:1]:
            for t in m.get("torrents", []):
                h = t.get("hash", "")
                if h:
                    magnets.append({
                        "hash": h,
                        "quality": t.get("quality", "720p"),
                        "size": t.get("size", ""),
                        "name": m.get("title", "")
                    })
    except:
        pass
    return magnets


def _tpb(query):
    magnets = []
    try:
        data = _get("https://apibay.org/q.php?q={}&cat=0".format(quote(query)), 6)
        if not isinstance(data, list):
            return magnets
        for item in data[:6]:
            h = item.get("info_hash", "")
            name = item.get("name", "")
            size = int(item.get("size", 0))
            if not h or h == "0" * 40 or size < 50000000:
                continue
            magnets.append({
                "hash": h,
                "quality": _detect_quality(name),
                "size": "{:.0f}MB".format(size / 1048576),
                "name": name[:60]
            })
    except:
        pass
    return magnets


def _tgx(query):
    """Torrent Galaxy API."""
    magnets = []
    try:
        data = _get("https://torrentgalaxy.to/get-posts/keywords:{}".format(quote(query)), 6)
        # TGX devuelve HTML, buscar hashes
        # Alternativa: usar torrents.csv
    except:
        pass
    return magnets


def _eztv(imdb_id, season, episode):
    """EZTV para series."""
    magnets = []
    try:
        # EZTV API
        imdb_num = imdb_id.replace("tt", "")
        data = _get("https://eztv.re/api/get-torrents?imdb_id={}&limit=20".format(imdb_num), 6)
        for t in data.get("torrents", []):
            if t.get("season") == season and t.get("episode") == episode:
                h = t.get("hash", "")
                if h:
                    magnets.append({
                        "hash": h,
                        "quality": _detect_quality(t.get("title", "")),
                        "size": "{:.0f}MB".format(t.get("size_bytes", 0) / 1048576),
                        "name": t.get("title", "")[:60]
                    })
    except:
        pass
    return magnets


def _detect_quality(name):
    n = name.lower()
    if "2160p" in n or "4k" in n:
        return "4K"
    if "1080p" in n:
        return "1080p"
    if "720p" in n:
        return "720p"
    return "SD"


# ============================================================
# ALLDEBRID RESOLVER
# ============================================================

def _resolve(magnets):
    """Resuelve magnets via AllDebrid."""
    links = []
    for m in magnets[:5]:
        try:
            magnet = "magnet:?xt=urn:btih:{}".format(m["hash"])
            stream = _ad_resolve(magnet)
            if stream:
                links.append({
                    "name": "[COLOR gold]{} {}[/COLOR] ({})".format(
                        m["quality"], m["name"], m.get("size", "")),
                    "url": stream,
                    "quality": m["quality"],
                    "lang": "multi",
                    "source": "alldebrid"
                })
                if len(links) >= 3:
                    break
        except:
            pass
    return links


def _ad_resolve(magnet):
    """Upload magnet y obtener stream."""
    try:
        data = _ad("magnet/upload", "&magnets[]={}".format(quote(magnet)))
        if data.get("status") != "success":
            return None

        mags = data.get("data", {}).get("magnets", [])
        if not mags:
            return None

        mag_id = mags[0].get("id")
        if not mag_id:
            return None

        # Esperar (max 6 seg)
        for i in range(4):
            if i > 0:
                time.sleep(1.5)
            status = _ad("magnet/status", "&id={}".format(mag_id))
            mag = status.get("data", {}).get("magnets", {})
            if mag.get("statusCode") == 4:  # Ready
                return _extract_video(mag)

        # No listo - borrar
        _ad("magnet/delete", "&id={}".format(mag_id))
    except:
        pass
    return None


def _extract_video(mag):
    """Extrae URL de video del magnet procesado."""
    try:
        exts = ('.mkv', '.mp4', '.avi', '.mov', '.wmv')
        best, best_size = None, 0

        for fl in mag.get("links", []):
            fn = fl.get("filename", "").lower()
            sz = fl.get("size", 0)
            if any(fn.endswith(e) for e in exts) and sz > best_size:
                best = fl.get("link")
                best_size = sz

        if best:
            data = _ad("link/unlock", "&link={}".format(quote(best)))
            if data.get("status") == "success":
                return data.get("data", {}).get("link", "")
    except:
        pass
    return None


def filter_by_quality(links, max_quality="4K"):
    order = {"SD": 0, "720p": 1, "1080p": 2, "4K": 3}
    mx = order.get(max_quality, 3)
    return [l for l in links if order.get(l.get("quality", "SD"), 0) <= mx]
