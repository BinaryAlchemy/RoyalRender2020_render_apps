#python
# -*- coding: cp1252 -*-
######################################################################
#
# Royal Render Plugin script for Rhino
# Author:  Royal Render, Paolo Acampora
# Version v8.1.00
# Copyright (c) Holger Schoenberger - Binary Alchemy
#
######################################################################

import rrSubmitRhino


def RunCommand(is_interactive):
    """
    RunCommand is called when the user enters the command name in Rhino.
    The command name is defined by the filename minus "_cmd.py"

    :param is_interactive:
    :return:  0 == success, 1 == cancel; If no value is returned, success is assumed
    """
    print "rrSubmitCameras"

    return rrSubmitRhino.submitCurrentScene(multicam=True, console=False)
