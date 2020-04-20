#python
# -*- coding: cp1252 -*-
######################################################################
#
# Royal Render Render script for VRed
# Author:  Royal Render, Paolo Acampora
# Version v8.1.00
# Copyright (c) Holger Schoenberger - Binary Alchemy
#
######################################################################


import datetime
import os
import sys

import vrCamera
import vrRenderLayerModule
import vrOSGWidget
import vrController
import vrRenderSettings
import vrScenegraph
import vrVariants
import vrVariantSets
import vrVredUi

from PySide2 import QtWidgets


def logMessageGen(lvl, msg):
    if len(lvl) == 0:
        return datetime.datetime.now().strftime("' %H:%M.%S") + " rrVRed      : " + str(msg)

    return datetime.datetime.now().strftime("' %H:%M.%S") + " rrVRed - " + str(lvl) + ": " + str(msg)


def logMessage(msg):
    vrController.vrLogInfo(logMessageGen("", msg))


def logMessageDebug(msg):
    vrController.vrLogInfo("DGB", msg)


def logMessageSET(msg):
    vrController.vrLogInfo("SET", msg)


def flushLog():
    sys.stdout.flush()
    sys.stderr.flush()


def logMessageError(msg):
    vrController.vrLogE("ERR", str(msg) + "\n\n")
    logMessage("\nError reported, aborting render script\n")
    vrController.terminateVred()


def pyModPath(modpath):
    sys.path.append(modpath)
    global kso_tcp
    import kso_tcp


def vredMainWindow(id):
    """Return a wrapper to the main window

    :param id: window pointer
    """
    from shiboken2 import wrapInstance
    return wrapInstance(id, QtWidgets.QMainWindow)


def stereoActions():
    """Return stereo related menu entries.
    We are triggering the menu items to activate Stereo rendering

    :return: (stereo_off, stereo_l, stereo_r)
    """
    mw = vredMainWindow(vrVredUi.getMainWindow())
    menu_actions = mw.menuBar().actions()

    stereo_off = None
    stereo_l = None
    stereo_r = None
    for menu_action in menu_actions:
        if menu_action.text() == "Visualization":
            menu = menu_action.menu()
            for ac in menu.actions():
                if ac.text() == "Stereo":

                    for stereo_ac in ac.menu().actions():
                        if stereo_ac.text() == "Disabled":
                            stereo_off = stereo_ac
                        if stereo_ac.text() == "Left Eye":
                            stereo_l = stereo_ac
                        if stereo_ac.text() == "Right Eye":
                            stereo_r = stereo_ac

            break

    return stereo_off, stereo_l, stereo_r


def renderFrames(FrStart, FrEnd, FrStep,
                 img_fname=None, camera=None,
                 layer=None, single=False,
                 channel=None):
    logMessage("Application started")
    vrOSGWidget.enableRender(False)
    vrRenderSettings.setRenderUseClipRange(False)
    vrRenderSettings.setRenderFrameStep(1)

    if img_fname:

        if "<ImageStereo" in img_fname:
            # we have to use the menu entries
            stereo_off, stereo_l, stereo_r = stereoActions()
            if not stereo_off:
                logMessageError("stereo entries not found")
            if "<ImageStereoL>" in img_fname:
                img_fname = img_fname.replace("<ImageStereoL>", "Left")
                stereo_l.trigger()
            else:
                img_fname = img_fname.replace("<ImageStereoR>", "Right")
                stereo_r.trigger()

        filename, fileext = os.path.splitext(img_fname)
        filename = filename.replace("-<Channel>", "")
        if layer:
            filename = filename.replace("<Layer>", layer)

        if not single:
            filename = filename.rstrip("-")
        vrRenderSettings.setRenderFilename(filename + fileext)
    else:
        filename, fileext = os.path.splitext(vrRenderSettings.getRenderFilename())

    if camera:
        cam_node = vrScenegraph.findNode(camera)
        if cam_node.isValid():
            vrOSGWidget.setViewportCamera(-1, cam_node)

    if layer:
        if layer in vrVariantSets.getVariantSets():
            vrVariants.selectVariantSet(layer)
        else:  # try render layers
            vrOSGWidget.enableRaytracing(True)
            vrRenderLayerModule.resetRenderLayers()
            vrRenderLayerModule.activateRenderLayer(layer)

    if channel:
        vrOSGWidget.enableRaytracing(True)

    for fr in xrange(FrStart, FrEnd + 1,FrStep):
        logMessage("Rendering Frame #{0} ...".format(fr))
        fr_fname = '{0}-{1:05}{2}'.format(filename, fr, fileext)
        logMessage("placeholder " + fr_fname)
        kso_tcp.writeRenderPlaceholder(fr_fname)

        vrRenderSettings.setRenderStartFrame(fr)
        vrRenderSettings.setRenderStopFrame(fr)
        vrRenderSettings.startRenderToFile(True)

    vrController.terminateVred()
