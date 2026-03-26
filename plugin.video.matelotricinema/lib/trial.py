# -*- coding: utf-8 -*-
"""Sistema de trial 3 días para Matelotri Cinema."""
import os
import time
import xbmcvfs
import xbmcaddon

ADDON = xbmcaddon.Addon()
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))
TRIAL_FILE = os.path.join(PROFILE, "trial.dat")
TRIAL_DAYS = 3


def _first_run():
    os.makedirs(PROFILE, exist_ok=True)
    if not os.path.exists(TRIAL_FILE):
        with open(TRIAL_FILE, "w") as f:
            f.write(str(time.time()))


def _days_used():
    _first_run()
    try:
        with open(TRIAL_FILE, "r") as f:
            start = float(f.read().strip())
        return max(0, (time.time() - start) / 86400)
    except:
        return 0


def can_play():
    return _days_used() < TRIAL_DAYS


def get_max_quality():
    return "4K"


def get_status_text():
    days = _days_used()
    if days < TRIAL_DAYS:
        left = TRIAL_DAYS - int(days)
        return "[COLOR lime]Trial: {} dias restantes[/COLOR]".format(left)
    return "[COLOR red]Trial expirado[/COLOR]"


def is_premium():
    return ADDON.getSetting("is_premium") == "true"
