# -*- coding: utf-8 -*-
"""Sistema de trial gratuito - 3 días."""
import os
import time

ADDON_DATA = None


def _get_trial_file():
    global ADDON_DATA
    if not ADDON_DATA:
        import xbmcvfs
        import xbmcaddon
        ADDON_DATA = xbmcvfs.translatePath(
            xbmcaddon.Addon().getAddonInfo("profile"))
    if not os.path.exists(ADDON_DATA):
        os.makedirs(ADDON_DATA)
    return os.path.join(ADDON_DATA, "trial.dat")


def get_trial_start():
    """Devuelve timestamp de inicio del trial."""
    path = _get_trial_file()
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return float(f.read().strip())
        except:
            pass
    # Primera vez - iniciar trial
    ts = time.time()
    with open(path, "w") as f:
        f.write(str(ts))
    return ts


def days_remaining():
    """Días restantes del trial (3 días)."""
    start = get_trial_start()
    elapsed = time.time() - start
    remaining = 3.0 - (elapsed / 86400.0)
    return max(0, remaining)


def is_trial_active():
    """True si quedan días de trial."""
    return days_remaining() > 0


def is_premium():
    """True si tiene key de AllDebrid configurada."""
    try:
        import xbmcaddon
        addon = xbmcaddon.Addon()
        return (addon.getSetting("is_premium") == "true" and
                len(addon.getSetting("alldebrid_key")) > 5)
    except:
        return False


def can_play():
    """True si puede reproducir (trial activo o premium)."""
    return is_premium() or is_trial_active()


def get_max_quality():
    """Devuelve calidad máxima permitida."""
    if is_premium():
        return "4K"
    return "720p"  # Gratis = SD/720p


def get_status_text():
    """Texto de estado para mostrar."""
    if is_premium():
        return "[COLOR gold]★ PREMIUM[/COLOR]"
    days = days_remaining()
    if days > 0:
        return "[COLOR lime]Prueba: {:.0f}d {:.0f}h[/COLOR]".format(
            int(days), (days % 1) * 24)
    return "[COLOR red]Prueba expirada[/COLOR]"
