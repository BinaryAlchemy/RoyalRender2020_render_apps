# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy

import os
import sys
import logging
logger = logging.getLogger("HtoRR")

try:
    import hou
except ImportError:
    pass


def open_save_hip():
    logger.debug("Checking if save is required")
    if not hou.hipFile.hasUnsavedChanges():
        return True

    e = hou.ui.displayMessage("Save the current hip file?",
                              buttons=("Yes", "No", "Cancel"))

    if e == 0:
        saveMode= hou.getPreference("autoSaveIncrement")
        if saveMode=="2":
            hou.hipFile.saveAndBackup()
        elif saveMode=="1":
            hou.hipFile.saveAndIncrementFileName()
        else:
            hou.hipFile.save()
        return True

    if e == 1:
        return True

    elif e == 2:
        return False


def get_rr_root():
    """Return Path to Royal Render Root.

    Raises:
        EnvironmentError: Variable "RR_ROOT" not set

    Returns:
        string -- Path to Royal Render Root

    """
    if 'RR_ROOT' in os.environ:
        return os.environ['RR_ROOT'].strip("\r")
    else:
        raise EnvironmentError('Variable "RR_ROOT" not set')


def get_os_sring():
    if ((sys.platform.lower() == "win32") or
            (sys.platform.lower() == "win64")):
        return "win"
    elif (sys.platform.lower() == "darwin"):
        return "osx"
    else:
        return "lx"
