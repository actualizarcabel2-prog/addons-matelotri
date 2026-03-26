# -*- coding: utf-8 -*-
"""TMDb API wrapper para Matelotri Cinema."""
import json
try:
    from urllib.request import urlopen, Request
    from urllib.parse import urlencode
except ImportError:
    from urllib2 import urlopen, Request
    from urllib import urlencode

API_KEY = "f090bb54758cabf231fb605d3e3e0468"
BASE = "https://api.themoviedb.org/3"
IMG = "https://image.tmdb.org/t/p"
LANG = "es-ES"


def _get(path, params=None):
    p = {"api_key": API_KEY, "language": LANG}
    if params:
        p.update(params)
    url = "{}/{}?{}".format(BASE, path, urlencode(p))
    try:
        r = urlopen(Request(url, headers={"User-Agent": "Kodi/21"}), timeout=8)
        return json.loads(r.read().decode("utf-8"))
    except:
        return {}


def poster(path):
    return "{}/w500{}".format(IMG, path) if path else ""


def backdrop(path):
    return "{}/w1280{}".format(IMG, path) if path else ""


def popular_movies(page=1):
    return _get("movie/popular", {"page": page})

def now_playing(page=1):
    return _get("movie/now_playing", {"page": page})

def top_rated_movies(page=1):
    return _get("movie/top_rated", {"page": page})

def popular_tv(page=1):
    return _get("tv/popular", {"page": page})

def top_rated_tv(page=1):
    return _get("tv/top_rated", {"page": page})

def on_the_air(page=1):
    return _get("tv/on_the_air", {"page": page})

def search_multi(query, page=1):
    return _get("search/multi", {"query": query, "page": page})

def search_movie(query, page=1):
    return _get("search/movie", {"query": query, "page": page})

def search_tv(query, page=1):
    return _get("search/tv", {"query": query, "page": page})

def movie_details(movie_id):
    return _get("movie/{}".format(movie_id))

def tv_details(tv_id):
    return _get("tv/{}".format(tv_id), {"append_to_response": "external_ids"})

def tv_season(tv_id, season):
    return _get("tv/{}/season/{}".format(tv_id, season))

def genres_movie():
    return _get("genre/movie/list")

def genres_tv():
    return _get("genre/tv/list")

def discover_movie(genre_id=None, year=None, page=1):
    p = {"page": page, "sort_by": "popularity.desc"}
    if genre_id:
        p["with_genres"] = genre_id
    if year:
        p["primary_release_year"] = year
    return _get("discover/movie", p)

def discover_tv(genre_id=None, page=1):
    p = {"page": page, "sort_by": "popularity.desc"}
    if genre_id:
        p["with_genres"] = genre_id
    return _get("discover/tv", p)
