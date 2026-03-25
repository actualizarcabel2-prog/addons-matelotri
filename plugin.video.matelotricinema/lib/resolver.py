# -*- coding: utf-8 -*-
"""Resolver de enlaces - busca fuentes gratuitas."""
import json
import re
try:
    from urllib.request import urlopen, Request, quote
    from urllib.parse import urlencode
except ImportError:
    from urllib2 import urlopen, Request
    from urllib import quote, urlencode


def _fetch(url, headers=None):
    """Descarga contenido de URL."""
    if not headers:
        headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 12) Kodi/21"}
    try:
        req = Request(url, headers=headers)
        resp = urlopen(req, timeout=15)
        return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return ""


def resolve_movie(title, year=None, imdb_id=None):
    """Busca enlaces gratuitos para una película.
    
    Devuelve lista de dicts: [{name, url, quality, lang}]
    """
    links = []
    
    # Fuente 1: Búsqueda genérica
    try:
        links.extend(_search_vidsrc(title, year, "movie", imdb_id))
    except:
        pass
    
    # Fuente 2: Embedsources
    try:
        links.extend(_search_embed(title, year, "movie", imdb_id))
    except:
        pass
    
    return links


def resolve_episode(title, season, episode, imdb_id=None):
    """Busca enlaces para un episodio de serie."""
    links = []
    
    try:
        links.extend(_search_vidsrc(title, None, "tv", imdb_id,
                                     season=season, episode=episode))
    except:
        pass
    
    try:
        links.extend(_search_embed(title, None, "tv", imdb_id,
                                    season=season, episode=episode))
    except:
        pass
    
    return links


def _search_vidsrc(title, year, media_type, imdb_id=None,
                    season=None, episode=None):
    """Busca en VidSrc (fuente gratuita)."""
    links = []
    if not imdb_id:
        return links
    
    if media_type == "movie":
        url = "https://vidsrc.xyz/embed/movie/{}".format(imdb_id)
    else:
        url = "https://vidsrc.xyz/embed/tv/{}/{}-{}".format(
            imdb_id, season, episode)
    
    links.append({
        "name": "[COLOR gold]VidSrc[/COLOR] - {}".format(
            "720p" if media_type == "movie" else "SD"),
        "url": url,
        "quality": "720p",
        "lang": "multi",
        "source": "vidsrc"
    })
    return links


def _search_embed(title, year, media_type, imdb_id=None,
                   season=None, episode=None):
    """Busca en fuentes embed gratuitas."""
    links = []
    if not imdb_id:
        return links
    
    if media_type == "movie":
        url = "https://www.2embed.cc/embed/{}".format(imdb_id)
    else:
        url = "https://www.2embed.cc/embedtv/{}&s={}&e={}".format(
            imdb_id, season, episode)
    
    links.append({
        "name": "[COLOR lime]2Embed[/COLOR] - SD",
        "url": url,
        "quality": "SD",
        "lang": "multi",
        "source": "2embed"
    })
    return links


def filter_by_quality(links, max_quality="720p"):
    """Filtra enlaces según calidad máxima permitida."""
    quality_order = {"SD": 0, "720p": 1, "1080p": 2, "4K": 3}
    max_val = quality_order.get(max_quality, 1)
    return [l for l in links if quality_order.get(l.get("quality", "SD"), 0) <= max_val]
