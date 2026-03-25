# -*- coding: utf-8 -*-
"""TMDb API wrapper para Matelotri Cinema."""
import json
try:
    from urllib.request import urlopen, Request, quote
except ImportError:
    from urllib2 import urlopen, Request
    from urllib import quote

# TMDb API v3 - registrar en themoviedb.org para key propia
API_KEY = "a7cde1e0e3ae1ee3fea0688c82e557b5"
BASE = "https://api.themoviedb.org/3"
IMG = "https://image.tmdb.org/t/p/"


def _get(path, params=None, lang="es-ES"):
    """Petición GET a TMDb."""
    url = BASE + path + "?api_key=" + API_KEY + "&language=" + lang
    if params:
        for k, v in params.items():
            url += "&{}={}".format(k, quote(str(v)))
    try:
        req = Request(url, headers={"User-Agent": "Kodi/21"})
        resp = urlopen(req, timeout=15)
        return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"results": [], "error": str(e)}


def popular_movies(page=1, lang="es-ES"):
    return _get("/movie/popular", {"page": page}, lang)


def now_playing(page=1, lang="es-ES"):
    return _get("/movie/now_playing", {"page": page}, lang)


def top_rated_movies(page=1, lang="es-ES"):
    return _get("/movie/top_rated", {"page": page}, lang)


def popular_tv(page=1, lang="es-ES"):
    return _get("/tv/popular", {"page": page}, lang)


def top_rated_tv(page=1, lang="es-ES"):
    return _get("/tv/top_rated", {"page": page}, lang)


def on_the_air(page=1, lang="es-ES"):
    return _get("/tv/on_the_air", {"page": page}, lang)


def search_multi(query, page=1, lang="es-ES"):
    return _get("/search/multi", {"query": query, "page": page}, lang)


def search_movie(query, page=1, lang="es-ES"):
    return _get("/search/movie", {"query": query, "page": page}, lang)


def search_tv(query, page=1, lang="es-ES"):
    return _get("/search/tv", {"query": query, "page": page}, lang)


def movie_details(movie_id, lang="es-ES"):
    return _get("/movie/{}".format(movie_id), lang=lang)


def tv_details(tv_id, lang="es-ES"):
    return _get("/tv/{}".format(tv_id), lang=lang)


def tv_season(tv_id, season, lang="es-ES"):
    return _get("/tv/{}/season/{}".format(tv_id, season), lang=lang)


def genres_movie(lang="es-ES"):
    return _get("/genre/movie/list", lang=lang)


def genres_tv(lang="es-ES"):
    return _get("/genre/tv/list", lang=lang)


def discover_movie(genre_id=None, year=None, page=1, lang="es-ES"):
    params = {"page": page, "sort_by": "popularity.desc"}
    if genre_id:
        params["with_genres"] = genre_id
    if year:
        params["primary_release_year"] = year
    return _get("/discover/movie", params, lang)


def discover_tv(genre_id=None, year=None, page=1, lang="es-ES"):
    params = {"page": page, "sort_by": "popularity.desc"}
    if genre_id:
        params["with_genres"] = genre_id
    if year:
        params["first_air_date_year"] = year
    return _get("/discover/tv", params, lang)


def poster(path, size="w500"):
    if path:
        return IMG + size + path
    return ""


def backdrop(path, size="w1280"):
    if path:
        return IMG + size + path
    return ""
