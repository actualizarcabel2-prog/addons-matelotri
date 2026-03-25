# -*- coding: utf-8 -*-
"""Resolver AllDebrid v5 - Torrentio (Stremio) + AllDebrid.
Torrentio siempre funciona, no esta bloqueado."""
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
HEADERS = {"User-Agent": "Kodi/21.2", "Accept": "application/json"}


def _get(url, timeout=5):
    try:
        return json.loads(urlopen(
            Request(url, headers=HEADERS), timeout=timeout
        ).read().decode("utf-8"))
    except:
        return {}


def _ad(endpoint, extra=""):
    return _get("{}/{}?agent={}&apikey={}{}".format(
        AD_BASE, endpoint, AD_AGENT, AD_KEY, extra), 8)


def resolve_movie(title, year=None, tmdb_id=None, imdb_id=None):
    if not imdb_id:
        return []
    magnets = _torrentio_movie(imdb_id)
    return _resolve(magnets)


def resolve_episode(title, season, episode, tmdb_id=None, imdb_id=None):
    if not imdb_id:
        return []
    s, e = int(season), int(episode)
    magnets = _torrentio_episode(imdb_id, s, e)
    return _resolve(magnets)


# ============================================================
# TORRENTIO - API de Stremio (siempre funciona)
# ============================================================

def _torrentio_movie(imdb_id):
    """Torrentio devuelve torrents ordenados por calidad."""
    magnets = []
    try:
        url = "https://torrentio.strem.fun/stream/movie/{}.json".format(imdb_id)
        data = _get(url, timeout=5)
        streams = data.get("streams", [])

        for s in streams[:8]:
            info_hash = s.get("infoHash", "")
            title = s.get("title", "")
            name = s.get("name", "")

            if not info_hash:
                continue

            quality = _detect_quality(title + " " + name)
            # Extraer tamaño del titulo
            size = ""
            for part in title.split("\n"):
                if "GB" in part or "MB" in part:
                    size = part.strip()
                    break

            magnets.append({
                "hash": info_hash,
                "quality": quality,
                "size": size,
                "name": name[:40] + " " + title.split("\n")[0][:30] if title else name[:60]
            })
    except:
        pass
    return magnets


def _torrentio_episode(imdb_id, season, episode):
    magnets = []
    try:
        url = "https://torrentio.strem.fun/stream/series/{}:{}:{}.json".format(
            imdb_id, season, episode)
        data = _get(url, timeout=5)
        streams = data.get("streams", [])

        for s in streams[:8]:
            info_hash = s.get("infoHash", "")
            title = s.get("title", "")
            name = s.get("name", "")

            if not info_hash:
                continue

            quality = _detect_quality(title + " " + name)
            size = ""
            for part in title.split("\n"):
                if "GB" in part or "MB" in part:
                    size = part.strip()
                    break

            magnets.append({
                "hash": info_hash,
                "quality": quality,
                "size": size,
                "name": name[:40] + " " + title.split("\n")[0][:30] if title else name[:60]
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
# ALLDEBRID
# ============================================================

def _resolve(magnets):
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

        # Esperar max 4.5 seg
        for i in range(3):
            if i > 0:
                time.sleep(1.5)
            status = _ad("magnet/status", "&id={}".format(mag_id))
            mag = status.get("data", {}).get("magnets", {})
            if mag.get("statusCode") == 4:
                return _extract_video(mag)

        _ad("magnet/delete", "&id={}".format(mag_id))
    except:
        pass
    return None


def _extract_video(mag):
    try:
        exts = ('.mkv', '.mp4', '.avi', '.mov')
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
