# -*- coding: utf-8 -*-
"""Resolver Matelotri Cinema v7 - urllib puro + Torrentio + AllDebrid."""
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


def _get(url, timeout=4):
    try:
        req = Request(url, headers={"User-Agent": "Kodi/21.2",
                                     "Accept": "application/json"})
        resp = urlopen(req, timeout=timeout)
        return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return {}


def _ad(endpoint, extra=""):
    return _get("{}/{}?agent={}&apikey={}{}".format(
        AD_BASE, endpoint, AD_AGENT, AD_KEY, extra), 6)


def resolve_movie(title, year=None, tmdb_id=None, imdb_id=None):
    if not imdb_id:
        return []
    magnets = _torrentio_movie(imdb_id)
    if not magnets:
        magnets = _yts(imdb_id)
    return _resolve(magnets)


def resolve_episode(title, season, episode, tmdb_id=None, imdb_id=None):
    if not imdb_id:
        return []
    magnets = _torrentio_episode(imdb_id, int(season), int(episode))
    return _resolve(magnets)


def _torrentio_movie(imdb_id):
    magnets = []
    data = _get("https://torrentio.strem.fun/stream/movie/{}.json".format(imdb_id), 5)
    for s in data.get("streams", [])[:8]:
        h = s.get("infoHash", "")
        if h:
            t = s.get("title", "")
            magnets.append({"hash": h, "quality": _q(t),
                           "size": _sz(t), "name": s.get("name", "")[:40]})
    return magnets


def _torrentio_episode(imdb_id, s, e):
    magnets = []
    data = _get("https://torrentio.strem.fun/stream/series/{}:{}:{}.json".format(
        imdb_id, s, e), 5)
    for st in data.get("streams", [])[:8]:
        h = st.get("infoHash", "")
        if h:
            t = st.get("title", "")
            magnets.append({"hash": h, "quality": _q(t),
                           "size": _sz(t), "name": st.get("name", "")[:40]})
    return magnets


def _yts(imdb_id):
    magnets = []
    data = _get("https://yts.mx/api/v2/list_movies.json?query_term={}&limit=1".format(
        imdb_id), 4)
    for m in data.get("data", {}).get("movies", [])[:1]:
        for t in m.get("torrents", []):
            h = t.get("hash", "")
            if h:
                magnets.append({"hash": h, "quality": t.get("quality", "720p"),
                               "size": t.get("size", ""), "name": m.get("title", "")})
    return magnets


def _q(text):
    t = text.lower()
    if "2160p" in t or "4k" in t:
        return "4K"
    if "1080p" in t:
        return "1080p"
    if "720p" in t:
        return "720p"
    return "SD"


def _sz(text):
    for line in text.split("\n"):
        if "GB" in line or "MB" in line:
            return line.strip()
    return ""


def _resolve(magnets):
    links = []
    for m in magnets[:4]:
        magnet = "magnet:?xt=urn:btih:{}".format(m["hash"])
        url = _ad_stream(magnet)
        if url:
            links.append({
                "name": "[COLOR gold]{} {}[/COLOR] ({})".format(
                    m["quality"], m["name"], m.get("size", "")),
                "url": url, "quality": m["quality"],
                "lang": "multi", "source": "alldebrid"})
            if len(links) >= 3:
                break
    return links


def _ad_stream(magnet):
    try:
        data = _ad("magnet/upload", "&magnets[]={}".format(quote(magnet)))
        if data.get("status") != "success":
            return None
        mags = data.get("data", {}).get("magnets", [])
        if not mags:
            return None
        mid = mags[0].get("id")
        if not mid:
            return None
        for i in range(3):
            if i > 0:
                time.sleep(1.5)
            st = _ad("magnet/status", "&id={}".format(mid))
            mg = st.get("data", {}).get("magnets", {})
            if mg.get("statusCode") == 4:
                return _video(mg)
        _ad("magnet/delete", "&id={}".format(mid))
    except Exception:
        pass
    return None


def _video(mag):
    try:
        exts = ('.mkv', '.mp4', '.avi', '.mov')
        best, bsz = None, 0
        for fl in mag.get("links", []):
            fn = fl.get("filename", "").lower()
            sz = fl.get("size", 0)
            if any(fn.endswith(e) for e in exts) and sz > bsz:
                best, bsz = fl.get("link"), sz
        if best:
            d = _ad("link/unlock", "&link={}".format(quote(best)))
            if d.get("status") == "success":
                return d.get("data", {}).get("link", "")
    except Exception:
        pass
    return None


def filter_by_quality(links, max_quality="4K"):
    order = {"SD": 0, "720p": 1, "1080p": 2, "4K": 3}
    mx = order.get(max_quality, 3)
    return [l for l in links if order.get(l.get("quality", "SD"), 0) <= mx]
