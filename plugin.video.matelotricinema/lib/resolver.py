# -*- coding: utf-8 -*-
"""Resolver de enlaces gratuitos para Matelotri Cinema."""
import json
import re
try:
    from urllib.request import urlopen, Request, quote
    from urllib.parse import urlencode
except ImportError:
    from urllib2 import urlopen, Request
    from urllib import quote, urlencode

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Accept": "*/*",
    "Referer": "https://vidsrc.xyz/"
}


def _fetch(url, headers=None, timeout=15):
    """Descarga contenido de URL."""
    if not headers:
        headers = HEADERS.copy()
    try:
        req = Request(url, headers=headers)
        resp = urlopen(req, timeout=timeout)
        return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return ""


def resolve_movie(title, year=None, tmdb_id=None, imdb_id=None):
    """Busca enlaces gratuitos para una película.
    
    Devuelve lista: [{name, url, quality, lang, source}]
    """
    links = []

    # Fuente 1: VidSrc.xyz (con TMDb ID)
    if tmdb_id:
        try:
            vidsrc_links = _resolve_vidsrc_movie(tmdb_id)
            links.extend(vidsrc_links)
        except:
            pass

    # Fuente 2: 2Embed (con IMDb ID)
    if imdb_id:
        try:
            embed_links = _resolve_2embed_movie(imdb_id)
            links.extend(embed_links)
        except:
            pass

    # Fuente 3: AutoEmbed (con TMDb ID)
    if tmdb_id:
        try:
            auto_links = _resolve_autoembed_movie(tmdb_id)
            links.extend(auto_links)
        except:
            pass

    # Fuente 4: MoviesAPI (con TMDb ID)
    if tmdb_id:
        try:
            mapi_links = _resolve_moviesapi_movie(tmdb_id)
            links.extend(mapi_links)
        except:
            pass

    # Fuente 5: SuperEmbed
    if imdb_id:
        try:
            se_links = _resolve_superembed(imdb_id, "movie")
            links.extend(se_links)
        except:
            pass

    return links


def resolve_episode(title, season, episode, tmdb_id=None, imdb_id=None):
    """Busca enlaces para un episodio de serie."""
    links = []
    s = int(season)
    e = int(episode)

    if tmdb_id:
        try:
            links.extend(_resolve_vidsrc_tv(tmdb_id, s, e))
        except:
            pass

    if imdb_id:
        try:
            links.extend(_resolve_2embed_tv(imdb_id, s, e))
        except:
            pass

    if tmdb_id:
        try:
            links.extend(_resolve_autoembed_tv(tmdb_id, s, e))
        except:
            pass

    if tmdb_id:
        try:
            links.extend(_resolve_moviesapi_tv(tmdb_id, s, e))
        except:
            pass

    return links


# ============================================================
# FUENTES
# ============================================================

def _resolve_vidsrc_movie(tmdb_id):
    """VidSrc.xyz - fuente gratuita fiable."""
    links = []
    url = "https://vidsrc.xyz/embed/movie/{}".format(tmdb_id)
    links.append({
        "name": "[COLOR gold]VidSrc[/COLOR] - HD",
        "url": url,
        "quality": "720p",
        "lang": "multi",
        "source": "vidsrc"
    })
    # VidSrc alternativo
    url2 = "https://vidsrc.in/embed/movie/{}".format(tmdb_id)
    links.append({
        "name": "[COLOR gold]VidSrc.in[/COLOR] - HD",
        "url": url2,
        "quality": "720p",
        "lang": "multi",
        "source": "vidsrc.in"
    })
    return links


def _resolve_vidsrc_tv(tmdb_id, season, episode):
    links = []
    url = "https://vidsrc.xyz/embed/tv/{}/{}/{}".format(tmdb_id, season, episode)
    links.append({
        "name": "[COLOR gold]VidSrc[/COLOR] - S{:02d}E{:02d}".format(season, episode),
        "url": url,
        "quality": "720p",
        "lang": "multi",
        "source": "vidsrc"
    })
    url2 = "https://vidsrc.in/embed/tv/{}/{}/{}".format(tmdb_id, season, episode)
    links.append({
        "name": "[COLOR gold]VidSrc.in[/COLOR] - S{:02d}E{:02d}".format(season, episode),
        "url": url2,
        "quality": "720p",
        "lang": "multi",
        "source": "vidsrc.in"
    })
    return links


def _resolve_2embed_movie(imdb_id):
    links = []
    url = "https://www.2embed.cc/embed/{}".format(imdb_id)
    links.append({
        "name": "[COLOR lime]2Embed[/COLOR] - HD",
        "url": url,
        "quality": "720p",
        "lang": "multi",
        "source": "2embed"
    })
    return links


def _resolve_2embed_tv(imdb_id, season, episode):
    links = []
    url = "https://www.2embed.cc/embedtv/{}&s={}&e={}".format(imdb_id, season, episode)
    links.append({
        "name": "[COLOR lime]2Embed[/COLOR] - S{:02d}E{:02d}".format(season, episode),
        "url": url,
        "quality": "720p",
        "lang": "multi",
        "source": "2embed"
    })
    return links


def _resolve_autoembed_movie(tmdb_id):
    links = []
    url = "https://player.autoembed.cc/embed/movie/{}".format(tmdb_id)
    links.append({
        "name": "[COLOR cyan]AutoEmbed[/COLOR] - HD",
        "url": url,
        "quality": "720p",
        "lang": "multi",
        "source": "autoembed"
    })
    return links


def _resolve_autoembed_tv(tmdb_id, season, episode):
    links = []
    url = "https://player.autoembed.cc/embed/tv/{}/{}/{}".format(tmdb_id, season, episode)
    links.append({
        "name": "[COLOR cyan]AutoEmbed[/COLOR] - S{:02d}E{:02d}".format(season, episode),
        "url": url,
        "quality": "720p",
        "lang": "multi",
        "source": "autoembed"
    })
    return links


def _resolve_moviesapi_movie(tmdb_id):
    links = []
    url = "https://moviesapi.club/movie/{}".format(tmdb_id)
    links.append({
        "name": "[COLOR orange]MoviesAPI[/COLOR] - HD",
        "url": url,
        "quality": "720p",
        "lang": "multi",
        "source": "moviesapi"
    })
    return links


def _resolve_moviesapi_tv(tmdb_id, season, episode):
    links = []
    url = "https://moviesapi.club/tv/{}-{}-{}".format(tmdb_id, season, episode)
    links.append({
        "name": "[COLOR orange]MoviesAPI[/COLOR] - S{:02d}E{:02d}".format(season, episode),
        "url": url,
        "quality": "720p",
        "lang": "multi",
        "source": "moviesapi"
    })
    return links


def _resolve_superembed(imdb_id, media_type):
    links = []
    url = "https://multiembed.mov/?video_id={}&tmdb=1".format(imdb_id)
    links.append({
        "name": "[COLOR yellow]SuperEmbed[/COLOR] - HD",
        "url": url,
        "quality": "720p",
        "lang": "multi",
        "source": "superembed"
    })
    return links


def filter_by_quality(links, max_quality="720p"):
    """Filtra enlaces según calidad máxima."""
    quality_order = {"SD": 0, "720p": 1, "1080p": 2, "4K": 3}
    max_val = quality_order.get(max_quality, 1)
    return [l for l in links
            if quality_order.get(l.get("quality", "SD"), 0) <= max_val]
