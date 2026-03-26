# -*- coding: utf-8 -*-
"""Sistema de trial 3 dias para Matelotri Cinema."""
import os
import time


def _get_profile():
    try:
        import xbmcvfs
        import xbmcaddon
        addon = xbmcaddon.Addon()
        return xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    except Exception:
        try:
            import xbmc
            import xbmcaddon
            addon = xbmcaddon.Addon()
            return xbmc.translatePath(addon.getAddonInfo("profile"))
        except Exception:
            return ""


def _trial_file():
    profile = _get_profile()
    if not profile:
        return ""
    try:
        os.makedirs(profile, exist_ok=True)
    except Exception:
        pass
    return os.path.join(profile, "trial.dat")


def _days_used():
    tf = _trial_file()
    if not tf:
        return 0
    if not os.path.exists(tf):
        try:
            with open(tf, "w") as f:
                f.write(str(time.time()))
        except Exception:
            pass
        return 0
    try:
        with open(tf, "r") as f:
            start = float(f.read().strip())
        return max(0, (time.time() - start) / 86400)
    except Exception:
        return 0


def can_play():
    return _days_used() < 3


def get_max_quality():
    return "4K"


def get_status_text():
    days = _days_used()
    if days < 3:
        left = 3 - int(days)
        return "[COLOR lime]Trial: {} dias[/COLOR]".format(left)
    return "[COLOR red]Trial expirado[/COLOR]"


def is_premium():
    try:
        import xbmcaddon
        return xbmcaddon.Addon().getSetting("is_premium") == "true"
    except Exception:
        return False
