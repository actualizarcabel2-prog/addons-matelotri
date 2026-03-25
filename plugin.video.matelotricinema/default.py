# -*- coding: utf-8 -*-
"""Matelotri Cinema - Addon principal para Kodi 21.2 Omega."""
import sys
import os
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc

try:
    from urllib.parse import parse_qsl, urlencode, quote_plus
except ImportError:
    from urlparse import parse_qsl
    from urllib import urlencode, quote_plus

# Paths
ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo("id")
ADDON_PATH = ADDON.getAddonInfo("path")
MEDIA = os.path.join(ADDON_PATH, "resources", "media")
HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]

# Importar módulos propios
sys.path.insert(0, os.path.join(ADDON_PATH, "lib"))
from tmdb import (popular_movies, now_playing, top_rated_movies,
                  popular_tv, top_rated_tv, on_the_air,
                  search_multi, search_movie, search_tv,
                  movie_details, tv_details, tv_season,
                  genres_movie, genres_tv,
                  discover_movie, discover_tv,
                  poster, backdrop)
from trial import can_play, get_max_quality, get_status_text, is_premium
from resolver import resolve_movie, resolve_episode, filter_by_quality


def build_url(params):
    return BASE_URL + "?" + urlencode(params)


def icon(name):
    return os.path.join(MEDIA, name)


def add_dir(label, action, params=None, icon_name="", plot="",
            is_folder=True, fanart_img=""):
    url_params = {"action": action}
    if params:
        url_params.update(params)
    url = build_url(url_params)

    li = xbmcgui.ListItem(label)
    art = {}
    if icon_name:
        art["icon"] = icon(icon_name)
        art["thumb"] = icon(icon_name)
    if fanart_img:
        art["fanart"] = fanart_img
    else:
        art["fanart"] = os.path.join(ADDON_PATH, "fanart.png")
    li.setArt(art)

    if plot:
        li.setInfo("video", {"plot": plot})

    xbmcplugin.addDirectoryItem(HANDLE, url, li, is_folder)


def add_movie_item(movie):
    """Añade un item de película."""
    title = movie.get("title", "Sin título")
    year = movie.get("release_date", "")[:4]
    label = "{} ({})".format(title, year) if year else title
    overview = movie.get("overview", "")
    movie_id = movie.get("id", 0)
    poster_url = poster(movie.get("poster_path"))
    fanart_url = backdrop(movie.get("backdrop_path"))

    url = build_url({
        "action": "play_movie",
        "movie_id": movie_id,
        "title": title,
        "year": year
    })

    li = xbmcgui.ListItem(label)
    li.setInfo("video", {
        "title": title,
        "year": int(year) if year else 0,
        "plot": overview,
        "mediatype": "movie"
    })
    li.setArt({
        "poster": poster_url,
        "thumb": poster_url,
        "fanart": fanart_url or os.path.join(ADDON_PATH, "fanart.png"),
        "icon": poster_url
    })
    li.setProperty("IsPlayable", "true")
    xbmcplugin.addDirectoryItem(HANDLE, url, li, False)


def add_tv_item(show):
    """Añade un item de serie."""
    title = show.get("name", "Sin título")
    year = show.get("first_air_date", "")[:4]
    label = "{} ({})".format(title, year) if year else title
    overview = show.get("overview", "")
    tv_id = show.get("id", 0)
    poster_url = poster(show.get("poster_path"))
    fanart_url = backdrop(show.get("backdrop_path"))

    url = build_url({
        "action": "tv_seasons",
        "tv_id": tv_id,
        "title": title
    })

    li = xbmcgui.ListItem(label)
    li.setInfo("video", {
        "title": title,
        "year": int(year) if year else 0,
        "plot": overview,
        "mediatype": "tvshow"
    })
    li.setArt({
        "poster": poster_url,
        "thumb": poster_url,
        "fanart": fanart_url or os.path.join(ADDON_PATH, "fanart.png"),
        "icon": poster_url
    })
    xbmcplugin.addDirectoryItem(HANDLE, url, li, True)


# ============================================================
# MENÚ PRINCIPAL
# ============================================================
def main_menu():
    status = get_status_text()
    add_dir("[COLOR gold]═══ MATELOTRI CINEMA ═══[/COLOR]  {}".format(status),
            "noop", icon_name="", plot="Tu cine en casa")
    add_dir("[COLOR gold]Películas[/COLOR]", "peliculas", icon_name="peliculas.png")
    add_dir("[COLOR gold]Series[/COLOR]", "series", icon_name="series.png")
    add_dir("[COLOR gold]Dibujos[/COLOR]", "dibujos", icon_name="dibujos.png")
    add_dir("[COLOR gold]Anime[/COLOR]", "anime", icon_name="anime.png")
    add_dir("[COLOR gold]Documentales[/COLOR]", "documentales", icon_name="documentales.png")
    add_dir("[COLOR gold]Música[/COLOR]", "musica", icon_name="musica.png")
    add_dir("[COLOR gold]Buscar[/COLOR]", "buscar", icon_name="buscar.png")
    add_dir("[COLOR gold]Favoritos[/COLOR]", "favoritos", icon_name="favoritos.png")
    add_dir("[COLOR gold]Ajustes[/COLOR]", "ajustes", icon_name="ajustes.png",
            is_folder=False)
    xbmcplugin.endOfDirectory(HANDLE)


# ============================================================
# SUBMENÚS POR CATEGORÍA
# ============================================================
def menu_peliculas():
    add_dir("[COLOR gold]★ Populares[/COLOR]", "movie_list",
            {"cat": "popular"}, "peliculas.png")
    add_dir("[COLOR gold]★ Estrenos[/COLOR]", "movie_list",
            {"cat": "now_playing"}, "peliculas.png")
    add_dir("[COLOR gold]★ Mejor valoradas[/COLOR]", "movie_list",
            {"cat": "top_rated"}, "peliculas.png")
    add_dir("[COLOR gold]★ Por género[/COLOR]", "movie_genres",
            icon_name="peliculas.png")
    add_dir("[COLOR gold]★ Por año[/COLOR]", "movie_years",
            icon_name="peliculas.png")
    xbmcplugin.endOfDirectory(HANDLE)


def menu_series():
    add_dir("[COLOR gold]★ Populares[/COLOR]", "tv_list",
            {"cat": "popular"}, "series.png")
    add_dir("[COLOR gold]★ En emisión[/COLOR]", "tv_list",
            {"cat": "on_the_air"}, "series.png")
    add_dir("[COLOR gold]★ Mejor valoradas[/COLOR]", "tv_list",
            {"cat": "top_rated"}, "series.png")
    add_dir("[COLOR gold]★ Por género[/COLOR]", "tv_genres",
            icon_name="series.png")
    xbmcplugin.endOfDirectory(HANDLE)


def menu_dibujos():
    add_dir("[COLOR gold]★ Películas animadas[/COLOR]", "movie_list",
            {"cat": "discover", "genre": "16"}, "dibujos.png")
    add_dir("[COLOR gold]★ Series animadas[/COLOR]", "tv_list",
            {"cat": "discover", "genre": "16"}, "dibujos.png")
    xbmcplugin.endOfDirectory(HANDLE)


def menu_anime():
    # Anime = Animation (16) con origen JP
    add_dir("[COLOR gold]★ Anime - Series[/COLOR]", "tv_list",
            {"cat": "discover", "genre": "16"}, "anime.png")
    add_dir("[COLOR gold]★ Anime - Películas[/COLOR]", "movie_list",
            {"cat": "discover", "genre": "16"}, "anime.png")
    xbmcplugin.endOfDirectory(HANDLE)


def menu_documentales():
    add_dir("[COLOR gold]★ Documentales - Películas[/COLOR]", "movie_list",
            {"cat": "discover", "genre": "99"}, "documentales.png")
    add_dir("[COLOR gold]★ Documentales - Series[/COLOR]", "tv_list",
            {"cat": "discover", "genre": "99"}, "documentales.png")
    xbmcplugin.endOfDirectory(HANDLE)


def menu_musica():
    add_dir("[COLOR gold]★ Películas musicales[/COLOR]", "movie_list",
            {"cat": "discover", "genre": "10402"}, "musica.png")
    xbmcplugin.endOfDirectory(HANDLE)


# ============================================================
# LISTADOS
# ============================================================
def list_movies(params):
    cat = params.get("cat", "popular")
    page = int(params.get("page", "1"))
    genre = params.get("genre", "")
    year = params.get("year", "")

    if cat == "popular":
        data = popular_movies(page)
    elif cat == "now_playing":
        data = now_playing(page)
    elif cat == "top_rated":
        data = top_rated_movies(page)
    elif cat == "discover":
        data = discover_movie(genre_id=genre, year=year, page=page)
    else:
        data = popular_movies(page)

    for movie in data.get("results", []):
        add_movie_item(movie)

    # Paginación
    total = data.get("total_pages", 1)
    if page < total:
        add_dir("[COLOR gold]» Siguiente página ({}/{})[/COLOR]".format(
            page + 1, total), "movie_list",
            {"cat": cat, "page": page + 1, "genre": genre, "year": year})

    xbmcplugin.setContent(HANDLE, "movies")
    xbmcplugin.endOfDirectory(HANDLE)


def list_tv(params):
    cat = params.get("cat", "popular")
    page = int(params.get("page", "1"))
    genre = params.get("genre", "")

    if cat == "popular":
        data = popular_tv(page)
    elif cat == "on_the_air":
        data = on_the_air(page)
    elif cat == "top_rated":
        data = top_rated_tv(page)
    elif cat == "discover":
        data = discover_tv(genre_id=genre, page=page)
    else:
        data = popular_tv(page)

    for show in data.get("results", []):
        add_tv_item(show)

    total = data.get("total_pages", 1)
    if page < total:
        add_dir("[COLOR gold]» Siguiente página ({}/{})[/COLOR]".format(
            page + 1, total), "tv_list",
            {"cat": cat, "page": page + 1, "genre": genre})

    xbmcplugin.setContent(HANDLE, "tvshows")
    xbmcplugin.endOfDirectory(HANDLE)


# ============================================================
# GÉNEROS Y AÑOS
# ============================================================
def list_movie_genres():
    data = genres_movie()
    for g in data.get("genres", []):
        add_dir("[COLOR gold]{}[/COLOR]".format(g["name"]),
                "movie_list", {"cat": "discover", "genre": g["id"]},
                "peliculas.png")
    xbmcplugin.endOfDirectory(HANDLE)


def list_tv_genres():
    data = genres_tv()
    for g in data.get("genres", []):
        add_dir("[COLOR gold]{}[/COLOR]".format(g["name"]),
                "tv_list", {"cat": "discover", "genre": g["id"]},
                "series.png")
    xbmcplugin.endOfDirectory(HANDLE)


def list_movie_years():
    import datetime
    current_year = datetime.datetime.now().year
    for y in range(current_year, 1990, -1):
        add_dir("[COLOR gold]{}[/COLOR]".format(y),
                "movie_list", {"cat": "discover", "year": y},
                "peliculas.png")
    xbmcplugin.endOfDirectory(HANDLE)


# ============================================================
# TEMPORADAS Y EPISODIOS
# ============================================================
def list_seasons(params):
    tv_id = params.get("tv_id", "")
    title = params.get("title", "")
    data = tv_details(tv_id)

    for s in data.get("seasons", []):
        snum = s.get("season_number", 0)
        if snum == 0:
            continue
        label = "Temporada {}".format(snum)
        ep_count = s.get("episode_count", 0)
        poster_url = poster(s.get("poster_path"))

        url = build_url({
            "action": "tv_episodes",
            "tv_id": tv_id,
            "season": snum,
            "title": title
        })
        li = xbmcgui.ListItem("[COLOR gold]{}[/COLOR] ({} eps)".format(
            label, ep_count))
        li.setArt({
            "poster": poster_url,
            "thumb": poster_url,
            "fanart": backdrop(data.get("backdrop_path")) or
                      os.path.join(ADDON_PATH, "fanart.png")
        })
        li.setInfo("video", {"plot": s.get("overview", "")})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, True)

    xbmcplugin.setContent(HANDLE, "seasons")
    xbmcplugin.endOfDirectory(HANDLE)


def list_episodes(params):
    tv_id = params.get("tv_id", "")
    season = int(params.get("season", "1"))
    title = params.get("title", "")
    data = tv_season(tv_id, season)

    for ep in data.get("episodes", []):
        epnum = ep.get("episode_number", 0)
        ep_title = ep.get("name", "Episodio {}".format(epnum))
        label = "{}x{:02d} - {}".format(season, epnum, ep_title)

        url = build_url({
            "action": "play_episode",
            "tv_id": tv_id,
            "season": season,
            "episode": epnum,
            "title": title
        })
        li = xbmcgui.ListItem("[COLOR gold]{}[/COLOR]".format(label))
        still = ep.get("still_path")
        li.setArt({
            "thumb": poster(still) if still else "",
            "fanart": backdrop(data.get("poster_path")) or
                      os.path.join(ADDON_PATH, "fanart.png")
        })
        li.setInfo("video", {
            "plot": ep.get("overview", ""),
            "mediatype": "episode",
            "season": season,
            "episode": epnum
        })
        li.setProperty("IsPlayable", "true")
        xbmcplugin.addDirectoryItem(HANDLE, url, li, False)

    xbmcplugin.setContent(HANDLE, "episodes")
    xbmcplugin.endOfDirectory(HANDLE)


# ============================================================
# BUSCAR
# ============================================================
def do_search():
    kb = xbmc.Keyboard("", "[COLOR gold]Matelotri Cinema - Buscar[/COLOR]")
    kb.doModal()
    if not kb.isConfirmed():
        return
    query = kb.getText().strip()
    if not query:
        return

    data = search_multi(query)
    for item in data.get("results", []):
        mt = item.get("media_type", "")
        if mt == "movie":
            add_movie_item(item)
        elif mt == "tv":
            add_tv_item(item)

    xbmcplugin.endOfDirectory(HANDLE)


# ============================================================
# REPRODUCIR
# ============================================================
def play_movie(params):
    if not can_play():
        xbmcgui.Dialog().ok(
            "[COLOR gold]Matelotri Cinema[/COLOR]",
            "[COLOR red]Tu prueba gratuita de 3 días ha expirado.[/COLOR]\n\n"
            "Contacta para obtener Premium con AllDebrid\n"
            "y disfruta en 1080p/4K sin límites.")
        return

    title = params.get("title", "")
    year = params.get("year", "")
    movie_id = params.get("movie_id", "")

    # Obtener IMDB ID
    details = movie_details(movie_id)
    imdb_id = details.get("imdb_id", "")

    pDialog = xbmcgui.DialogProgress()
    pDialog.create("[COLOR gold]Matelotri Cinema[/COLOR]",
                   "Buscando enlaces para: {}...".format(title))
    pDialog.update(30)

    links = resolve_movie(title, year, tmdb_id=movie_id, imdb_id=imdb_id)
    max_q = get_max_quality()
    links = filter_by_quality(links, max_q)

    pDialog.update(80)
    pDialog.close()

    if not links:
        xbmcgui.Dialog().ok(
            "[COLOR gold]Matelotri Cinema[/COLOR]",
            "No se encontraron enlaces disponibles para:\n{}".format(title))
        return

    if len(links) == 1 or ADDON.getSetting("autoplay") == "true":
        _play(links[0]["url"], title)
    else:
        names = [l["name"] for l in links]
        idx = xbmcgui.Dialog().select(
            "[COLOR gold]Seleccionar enlace[/COLOR]", names)
        if idx >= 0:
            _play(links[idx]["url"], title)


def play_episode(params):
    if not can_play():
        xbmcgui.Dialog().ok(
            "[COLOR gold]Matelotri Cinema[/COLOR]",
            "[COLOR red]Tu prueba gratuita de 3 días ha expirado.[/COLOR]")
        return

    title = params.get("title", "")
    season = params.get("season", "1")
    episode = params.get("episode", "1")
    tv_id = params.get("tv_id", "")

    details = tv_details(tv_id)
    # TMDb no tiene IMDB ID directamente para TV, usar el ID
    imdb_id = details.get("external_ids", {}).get("imdb_id", "")
    if not imdb_id:
        imdb_id = "tv_{}".format(tv_id)

    pDialog = xbmcgui.DialogProgress()
    pDialog.create("[COLOR gold]Matelotri Cinema[/COLOR]",
                   "Buscando: {} S{:02d}E{:02d}...".format(
                       title, int(season), int(episode)))
    pDialog.update(30)

    links = resolve_episode(title, season, episode, tmdb_id=tv_id, imdb_id=imdb_id)
    max_q = get_max_quality()
    links = filter_by_quality(links, max_q)

    pDialog.update(80)
    pDialog.close()

    if not links:
        xbmcgui.Dialog().ok(
            "[COLOR gold]Matelotri Cinema[/COLOR]",
            "No se encontraron enlaces.")
        return

    if len(links) == 1 or ADDON.getSetting("autoplay") == "true":
        _play(links[0]["url"], title)
    else:
        names = [l["name"] for l in links]
        idx = xbmcgui.Dialog().select(
            "[COLOR gold]Seleccionar enlace[/COLOR]", names)
        if idx >= 0:
            _play(links[idx]["url"], title)


def _play(url, title):
    """Reproduce un enlace."""
    li = xbmcgui.ListItem(path=url)
    li.setInfo("video", {"title": title})
    xbmcplugin.setResolvedUrl(HANDLE, True, li)


# ============================================================
# ROUTER
# ============================================================
def router(paramstring):
    params = dict(parse_qsl(paramstring))
    action = params.get("action", "")

    if not action:
        main_menu()
    elif action == "peliculas":
        menu_peliculas()
    elif action == "series":
        menu_series()
    elif action == "dibujos":
        menu_dibujos()
    elif action == "anime":
        menu_anime()
    elif action == "documentales":
        menu_documentales()
    elif action == "musica":
        menu_musica()
    elif action == "movie_list":
        list_movies(params)
    elif action == "tv_list":
        list_tv(params)
    elif action == "movie_genres":
        list_movie_genres()
    elif action == "tv_genres":
        list_tv_genres()
    elif action == "movie_years":
        list_movie_years()
    elif action == "tv_seasons":
        list_seasons(params)
    elif action == "tv_episodes":
        list_episodes(params)
    elif action == "buscar":
        do_search()
    elif action == "favoritos":
        xbmcgui.Dialog().ok("[COLOR gold]Matelotri Cinema[/COLOR]",
                            "Próximamente...")
    elif action == "ajustes":
        ADDON.openSettings()
    elif action == "play_movie":
        play_movie(params)
    elif action == "play_episode":
        play_episode(params)
    elif action == "noop":
        pass


if __name__ == "__main__":
    router(sys.argv[2][1:])
