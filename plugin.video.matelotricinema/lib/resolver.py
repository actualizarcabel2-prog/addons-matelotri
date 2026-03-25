# -*- coding: utf-8 -*-
"""Resolver de enlaces gratuitos para Matelotri Cinema.
Extrae URLs reproducibles de fuentes gratuitas."""
import json
import re
try:
    from urllib.request import urlopen, Request
    from urllib.parse import quote, urlencode
except ImportError:
    from urllib2 import urlopen, Request
    from urllib import quote, urlencode

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _fetch(url, headers=None, timeout=12):
    h = headers or HEADERS.copy()
    try:
        req = Request(url, headers=h)
        return urlopen(req, timeout=timeout).read().decode("utf-8", errors="ignore")
    except:
        return ""


def _fetch_json(url, headers=None, timeout=12):
    h = headers or HEADERS.copy()
    h["Accept"] = "application/json"
    try:
        req = Request(url, headers=h)
        return json.loads(urlopen(req, timeout=timeout).read().decode("utf-8"))
    except:
        return {}


def resolve_movie(title, year=None, tmdb_id=None, imdb_id=None):
    """Busca enlaces para película. Devuelve lista de dicts."""
    links = []

    if tmdb_id:
        links.extend(_source_vidsrc(tmdb_id, "movie"))
        links.extend(_source_embedsu(tmdb_id, "movie"))
        links.extend(_source_autoembed(tmdb_id, "movie"))
        links.extend(_source_multiembed(tmdb_id, "movie"))
        links.extend(_source_nontongo(tmdb_id, "movie"))

    if imdb_id:
        links.extend(_source_vidsrc_imdb(imdb_id, "movie"))

    return links


def resolve_episode(title, season, episode, tmdb_id=None, imdb_id=None):
    """Busca enlaces para episodio."""
    links = []
    s, e = int(season), int(episode)

    if tmdb_id:
        links.extend(_source_vidsrc(tmdb_id, "tv", s, e))
        links.extend(_source_embedsu(tmdb_id, "tv", s, e))
        links.extend(_source_autoembed(tmdb_id, "tv", s, e))
        links.extend(_source_multiembed(tmdb_id, "tv", s, e))

    if imdb_id:
        links.extend(_source_vidsrc_imdb(imdb_id, "tv", s, e))

    return links


# ============================================================
# FUENTES CON EXTRACCIÓN REAL
# ============================================================

def _source_vidsrc(tmdb_id, media_type, season=None, episode=None):
    """VidSrc.icu - extrae m3u8 real."""
    links = []
    try:
        if media_type == "movie":
            url = "https://vidsrc.icu/embed/movie/{}".format(tmdb_id)
        else:
            url = "https://vidsrc.icu/embed/tv/{}/{}/{}".format(tmdb_id, season, episode)

        html = _fetch(url)
        if not html:
            return links

        # Buscar m3u8 o mp4 en el HTML
        m3u8 = re.findall(r'(https?://[^\s\'"]+\.m3u8[^\s\'"]*)', html)
        mp4 = re.findall(r'(https?://[^\s\'"]+\.mp4[^\s\'"]*)', html)

        for u in m3u8[:2]:
            links.append({
                "name": "[COLOR gold]VidSrc[/COLOR] - HLS",
                "url": u, "quality": "720p", "lang": "multi", "source": "vidsrc"
            })
        for u in mp4[:2]:
            links.append({
                "name": "[COLOR gold]VidSrc[/COLOR] - MP4",
                "url": u, "quality": "720p", "lang": "multi", "source": "vidsrc"
            })

        # Buscar iframe src para seguir
        iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I)
        for iframe_url in iframes[:3]:
            if iframe_url.startswith('//'):
                iframe_url = 'https:' + iframe_url
            sub_html = _fetch(iframe_url, {"User-Agent": HEADERS["User-Agent"],
                                            "Referer": url})
            if sub_html:
                sub_m3u8 = re.findall(r'(https?://[^\s\'"]+\.m3u8[^\s\'"]*)', sub_html)
                sub_mp4 = re.findall(r'(https?://[^\s\'"]+\.mp4[^\s\'"]*)', sub_html)
                for u in sub_m3u8[:2]:
                    links.append({
                        "name": "[COLOR gold]VidSrc[/COLOR] - Stream",
                        "url": u + "|Referer=" + quote(iframe_url),
                        "quality": "720p", "lang": "multi", "source": "vidsrc"
                    })
                for u in sub_mp4[:2]:
                    links.append({
                        "name": "[COLOR gold]VidSrc[/COLOR] - Direct",
                        "url": u + "|Referer=" + quote(iframe_url),
                        "quality": "720p", "lang": "multi", "source": "vidsrc"
                    })
    except:
        pass
    return links


def _source_vidsrc_imdb(imdb_id, media_type, season=None, episode=None):
    """VidSrc con IMDB ID."""
    links = []
    try:
        if media_type == "movie":
            url = "https://vidsrc.xyz/embed/movie/{}".format(imdb_id)
        else:
            url = "https://vidsrc.xyz/embed/tv/{}/{}-{}".format(imdb_id, season, episode)

        html = _fetch(url)
        if not html:
            return links

        m3u8 = re.findall(r'(https?://[^\s\'"]+\.m3u8[^\s\'"]*)', html)
        mp4 = re.findall(r'(https?://[^\s\'"]+\.mp4[^\s\'"]*)', html)

        for u in m3u8[:2]:
            links.append({
                "name": "[COLOR lime]VidSrc.xyz[/COLOR] - HLS",
                "url": u, "quality": "720p", "lang": "multi", "source": "vidsrc.xyz"
            })
        for u in mp4[:2]:
            links.append({
                "name": "[COLOR lime]VidSrc.xyz[/COLOR] - MP4",
                "url": u, "quality": "720p", "lang": "multi", "source": "vidsrc.xyz"
            })

        iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I)
        for iframe_url in iframes[:3]:
            if iframe_url.startswith('//'):
                iframe_url = 'https:' + iframe_url
            sub = _fetch(iframe_url, {"User-Agent": HEADERS["User-Agent"], "Referer": url})
            if sub:
                for u in re.findall(r'(https?://[^\s\'"]+\.m3u8[^\s\'"]*)', sub)[:2]:
                    links.append({
                        "name": "[COLOR lime]VidSrc.xyz[/COLOR] - Stream",
                        "url": u + "|Referer=" + quote(iframe_url),
                        "quality": "720p", "lang": "multi", "source": "vidsrc.xyz"
                    })
    except:
        pass
    return links


def _source_embedsu(tmdb_id, media_type, season=None, episode=None):
    """embed.su - extrae streams."""
    links = []
    try:
        if media_type == "movie":
            url = "https://embed.su/embed/movie/{}".format(tmdb_id)
        else:
            url = "https://embed.su/embed/tv/{}/{}/{}".format(tmdb_id, season, episode)

        html = _fetch(url)
        if not html:
            return links

        m3u8 = re.findall(r'(https?://[^\s\'"]+\.m3u8[^\s\'"]*)', html)
        for u in m3u8[:3]:
            links.append({
                "name": "[COLOR cyan]EmbedSU[/COLOR] - HLS",
                "url": u + "|Referer=" + quote(url),
                "quality": "720p", "lang": "multi", "source": "embedsu"
            })

        # Buscar JSON con sources
        json_matches = re.findall(r'"file"\s*:\s*"(https?://[^"]+)"', html)
        for u in json_matches[:3]:
            links.append({
                "name": "[COLOR cyan]EmbedSU[/COLOR] - Direct",
                "url": u + "|Referer=" + quote(url),
                "quality": "720p", "lang": "multi", "source": "embedsu"
            })
    except:
        pass
    return links


def _source_autoembed(tmdb_id, media_type, season=None, episode=None):
    """AutoEmbed.cc"""
    links = []
    try:
        if media_type == "movie":
            url = "https://player.autoembed.cc/embed/movie/{}".format(tmdb_id)
        else:
            url = "https://player.autoembed.cc/embed/tv/{}/{}/{}".format(
                tmdb_id, season, episode)

        html = _fetch(url)
        if not html:
            return links

        for u in re.findall(r'(https?://[^\s\'"]+\.m3u8[^\s\'"]*)', html)[:2]:
            links.append({
                "name": "[COLOR orange]AutoEmbed[/COLOR] - HLS",
                "url": u + "|Referer=" + quote(url),
                "quality": "720p", "lang": "multi", "source": "autoembed"
            })
        for u in re.findall(r'"file"\s*:\s*"(https?://[^"]+)"', html)[:2]:
            links.append({
                "name": "[COLOR orange]AutoEmbed[/COLOR] - Direct",
                "url": u + "|Referer=" + quote(url),
                "quality": "720p", "lang": "multi", "source": "autoembed"
            })
    except:
        pass
    return links


def _source_multiembed(tmdb_id, media_type, season=None, episode=None):
    """MultiEmbed"""
    links = []
    try:
        if media_type == "movie":
            url = "https://multiembed.mov/?video_id={}&tmdb=1".format(tmdb_id)
        else:
            url = "https://multiembed.mov/?video_id={}&tmdb=1&s={}&e={}".format(
                tmdb_id, season, episode)

        html = _fetch(url)
        if not html:
            return links

        for u in re.findall(r'(https?://[^\s\'"]+\.m3u8[^\s\'"]*)', html)[:2]:
            links.append({
                "name": "[COLOR yellow]MultiEmbed[/COLOR] - HLS",
                "url": u + "|Referer=" + quote(url),
                "quality": "720p", "lang": "multi", "source": "multiembed"
            })
        for u in re.findall(r'"file"\s*:\s*"(https?://[^"]+)"', html)[:2]:
            links.append({
                "name": "[COLOR yellow]MultiEmbed[/COLOR] - Direct",
                "url": u + "|Referer=" + quote(url),
                "quality": "720p", "lang": "multi", "source": "multiembed"
            })
    except:
        pass
    return links


def _source_nontongo(tmdb_id, media_type, season=None, episode=None):
    """NontonGo - API directa."""
    links = []
    try:
        if media_type == "movie":
            url = "https://www.nontongo.win/embed/movie/{}".format(tmdb_id)
        else:
            url = "https://www.nontongo.win/embed/tv/{}/{}/{}".format(
                tmdb_id, season, episode)

        html = _fetch(url)
        if not html:
            return links

        for u in re.findall(r'(https?://[^\s\'"]+\.m3u8[^\s\'"]*)', html)[:2]:
            links.append({
                "name": "[COLOR magenta]NontonGo[/COLOR] - HLS",
                "url": u + "|Referer=" + quote(url),
                "quality": "720p", "lang": "multi", "source": "nontongo"
            })
    except:
        pass
    return links


def filter_by_quality(links, max_quality="720p"):
    quality_order = {"SD": 0, "720p": 1, "1080p": 2, "4K": 3}
    max_val = quality_order.get(max_quality, 1)
    return [l for l in links
            if quality_order.get(l.get("quality", "SD"), 0) <= max_val]
