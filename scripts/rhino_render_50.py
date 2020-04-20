#python
# -*- coding: cp1252 -*-
######################################################################
#
# Royal Render Render script for Rhinoceros
# Author:  Royal Render, Paolo Acampora
# Version %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy
#
######################################################################

import clr
import datetime
import errno
import logging
import os
import sys
import tempfile
import time

import System
from xml.etree.ElementTree import ElementTree, Element, SubElement, parse
clr.AddReference("System.Xml")
import System.Xml

import rhinoscriptsyntax as rs
import rhinoscript
import Rhino


################ Logger Functions ################

def set_logger(level=logging.DEBUG):
    logger = logging.getLogger("rrRhino")

    log_file = os.path.join(tempfile.gettempdir(), "rrRhinoRender.log")

    s_handler = logging.StreamHandler()
    f_handler = logging.FileHandler(log_file)

    log_format = logging.Formatter("' %(asctime)s %(name)s %(levelname)s: %(message)s", "%H:%M:%S")
    s_handler.setFormatter(log_format)
    f_handler.setFormatter(log_format)

    handlers = logger.handlers[:]
    for handler in handlers:
        handler.close()
        logger.removeHandler(handler)

    logger.addHandler(f_handler)
    logger.addHandler(s_handler)
    logger.setLevel(level)

    logger.debug("log file: " + log_file)
    return logger


def closeHandlers(logger):
    for handler in logger.handlers:
        handler.flush()
        handler.close()


def rrRhino_logger(func):
    """Wrapper for log functions, gets the "rrRhino" logger,
    makes sure to close handlers or flush the listener after message log

    :param func: function to wrap, must accept arguments "msg" and "logger"
    :return: wrapped function
    """
    logger = logging.getLogger("rrRhino")

    def wrapper(msg):
        func(msg, logger=logger)
        closeHandlers(logger)

    return wrapper


def io_retry(func, wait_secs=0.35, num_tries=3):
    """Wrapper that re-executes given function num_tries times, waiting wait_time between tries.
    Used to avoid write error when the log file is busy, as the rrClient moves it

    :param func: function to wrap
    :param wait_secs:
    :param num_tries:
    :return: wrapped function
    """
    def wrapper(msg, logger):
        try:
            func(msg, logger)
        except IOError:
            for _ in xrange(num_tries):
                time.sleep(wait_secs)
                try:
                    func(msg, logger)
                except IOError:
                    continue
                else:
                    break

    return wrapper


def rrRhino_exit(func):
    """Add exit command to the wrapped func"""
    def wrapper(*args, **kwargs):
        func(*args, **kwargs)
        Rhino.RhinoApp.Exit()

    return wrapper


@rrRhino_logger
@io_retry
def logMessage(msg, logger=None):
    logger.info(msg)


@rrRhino_logger
@io_retry
def logMessageWarn(msg, logger=None):
    logger.warning(msg)


@rrRhino_logger
@io_retry
def logMessageDebug(msg, logger=None):
    logger.debug(msg)

@rrRhino_exit
@rrRhino_logger
@io_retry
def logMessageError(msg, logger=None):
    logger.error(msg)
    logger.error("Error reported, aborting render script")


################ Utilities ################

def createFullDirs(filename):
    if not os.path.exists(os.path.dirname(filename)):
        try:
            os.makedirs(os.path.dirname(filename))
        except OSError as exc: # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise


def getTotalFrames():
    """Return the duration in frames of the animation for the current View"""
    # tries to set an outrageously high frame number,
    # parses the "Number must be Smaller than x" reply message
    if Rhino.ApplicationSettings.AppearanceSettings.LanguageIdentifier != 1033:  # U.S. English
        print "warning: Animation properties only available with U.S. English locales"
        return 0

    rs.Command('_ViewFirstFrame')
    if rs.CommandHistory()[-42:-1] == "Unable to find viewport to play animation":
        # printed out when we are in a different camera or a new file
        return 0

    rs.Command('_-ViewFrameNumber 9999999999999999 !', 1)
    if rs.CommandHistory()[-26:-1] == "There is no frame to view":
        # printed out when there have never been animated views
        return 0

    out_msg = "Number must be"
    out_idx = rs.CommandHistory().rfind(out_msg)
    return rs.CommandHistory()[out_idx + len(out_msg):].split()[2]


################ Rendering ################

class RhinoRenderManager(object):
    """Render Output Settings
    """

    padding = 4
    img_file = ""

    def __init__(self, total_frames=0):
        self.totalFrames = total_frames if total_frames > 0 else getTotalFrames()
        logMessage("Initialized Render Manager - Rhino")

    def renderFrame(self, fr, save_rhino_render=False):
        logMessage("Rendering Frame #" + str(fr) + " ...")

        rs.Command('_Render')
        if save_rhino_render:
            if self.padding > 0:
                fname, fext = os.path.splitext(self.img_file)
                outpath = "{0}.{2:0{1}}{3}".format(fname, self.padding, fr, fext)
            else:
                outpath = self.img_file

            createFullDirs(outpath)

            kso_tcp.writeRenderPlaceholder(outpath)
            success = rs.Command('_-SaveRenderWindowAs "{0}" _Enter'.format(outpath))
            if success:
                logMessage("\t saved: " + outpath)
            else:
                logMessageWarn("error saving " + outpath)

            rs.Command('_-CloseRenderWindow')

    def renderFrames(self, FrStart, FrEnd, FrStep, save_rhino_render=False):
        if FrStart == 0:
            # "ViewFrameNumber" command will not let you set 1st (0)
            rs.Command('_ViewFirstFrame')
            self.renderFrame(0, save_rhino_render)
            if FrEnd < FrStart:
                logMessageError("First Frame higher than Last Frame (start: {0} - end: {1})".format(FrStart, FrEnd))
                return

            FrStart += 1

        for fr in xrange(FrStart, FrEnd, FrStep):
            rs.Command('_-ViewFrameNumber {0} _Enter'.format(fr))
            self.renderFrame(fr, save_rhino_render)

        if FrEnd == self.totalFrames:
            rs.Command('_ViewLastFrame')
        else:
            rs.Command('_-ViewFrameNumber {0} _Enter'.format(FrEnd))

        self.renderFrame(FrEnd, save_rhino_render)

    def setImageFile(self, filename):
        self.img_file = filename


class VRayVersionError(Exception):
    """Raised with VRay-Next versions lacking Render routines"""
    pass


class VRayLegacyVersion(Exception):
    """Raised with VRay version using previous API"""
    pass


class VRayNotFoundError(Exception):
    """Raised when VRay Script Object is not found"""
    pass


class VRayLegacyRenderManager(RhinoRenderManager):
    """Render Output Settings for older VRay versions ( version < 4)
    
    Contains the output settings for VRay. Some settings (e.g. frames) cannot be
    accessed via scripting. In order to set those we need to export the whole
    section to a vropt xml file and load it through VRay.LoadVisopt
    """
    def __init__(self, total_frames=0):
        """Get the xml document of VRay options left at their default values"""
        super(VRayLegacyRenderManager, self).__init__(total_frames=total_frames)

        self.__VRay = rs.GetPlugInObject("V-Ray for Rhino")



        self.__xmlTree = System.Xml.XmlDocument()

        # export VRay options and load xml document
        tmpSettings = tempfile.NamedTemporaryFile(delete=False, suffix=".vropt")
        tmpSettings.close()

        self.__VRay.SaveVisopt(tmpSettings.name)
        self.__xmlTree.Load(tmpSettings.name)

        vray_ver = self.__xmlTree.SelectSingleNode("//vropt/Asset/plugin/vrayplugin")
        self.vray_ver = int(vray_ver.GetAttributeNode("version").Value)

        if self.vray_ver > 9:
            self.padding = self.__VRay.Scene().Plugin("/SettingsOutput").Param("anim_frame_padding").Value()

        os.unlink(tmpSettings.name)
        logMessage("Initialized Render Manager - VRay {0}".format(self.vray_ver))

    def setDoFrameRange(self, do_range):
        if self.vray_ver < 8:
            render_range = self.__xmlTree.SelectSingleNode("//vropt/Asset/plugin/vrayplugin/parameters/parameter[@name='render_frame_range']/value")
            render_range.InnerText = str(int(do_range))
        elif self.vray_ver > 9:
            self.__VRay.Scene().Plugin("/SettingsOutput").Param("animation_time_segment").Value = int(do_range)
        else:
            logMessageWarn("Frame range not supported with VRay version {0}, please update".format(self.vray_ver))

    def setFrameRange(self, seqStart, seqEnd, seqStep=1):
        assert seqEnd >= seqStart
        
        if self.vray_ver < 8:
            # Fill frames list with frames between seqStart, seqEnd
            vop_frames = self.__xmlTree.SelectSingleNode("//vropt/Asset/plugin/vrayplugin/parameters/parameter[@name='frames']")
            frame_list = vop_frames.SelectSingleNode("value/list")
            vop_frames.SetAttribute('listType', "integer")
            frame_list.RemoveAll()
            
            for i in xrange(seqStart, seqEnd + 1, seqStep):
                fr = self.__xmlTree.CreateElement(None, "entry", None)
                fr.InnerText = str(i)
                frame_list.AppendChild(fr)
        elif self.vray_ver > 9:
            if seqStep != 1:
                logMessageWarn("Frame Step different from 1, not available with VRay " + self.vray_ver)

            self.__VRay.Scene().Plugin("/SettingsOutput").Param("frame_range_start").Value = seqStart
            self.__VRay.Scene().Plugin("/SettingsOutput").Param("frame_range_end").Value = seqEnd
        else:
            if seqStep != 1:
                logMessageWarn("Frame Step different from 1, not available with VRay " + self.vray_ver)

            fr_start = self.__xmlTree.SelectSingleNode("//vropt/Asset/plugin/vrayplugin/parameters/parameter[@name='frame_range_start']/value")
            fr_end = self.__xmlTree.SelectSingleNode("//vropt/Asset/plugin/vrayplugin/parameters/parameter[@name='frame_range_end']/value") 

            fr_start.InnerText = str(seqStart)
            fr_end.InnerText = str(seqEnd)

    def setImageFile(self, filename):
        super(VRayLegacyRenderManager, self).setImageFile(filename)

        img_path = os.path.normpath(filename).replace("\\", "/")  # safer with unix paths
        if self.vray_ver < 10:
            img_file = self.__xmlTree.SelectSingleNode("//vropt/Asset/plugin/vrayplugin/parameters/parameter[@name='img_file']/value")
            img_file.InnerText = img_path
        else:
            self.__VRay.Scene().Plugin("/SettingsOutput").Param("img_file").Value = img_path

    def setSaveRender(self, is_save):
        if self.vray_ver < 10:
            save_render = self.__xmlTree.SelectSingleNode("//vropt/Asset/plugin/vrayplugin/parameters/parameter[@name='save_render']/value")
            save_render.InnerText = str(int(is_save))
        else:
            self.__VRay.Scene().Plugin("/SettingsOutput").Param("save_render").Value = bool(is_save)

    def renderFrame(self, fr, save_rhino_render=False):
        """Invoked by super().renderFrames, not needed anymore since VRay 10"""
        self.setFrameRange(fr, fr)

        if self.vray_ver < 10:
            self.UpdateVisopt()
            super(VRayLegacyRenderManager, self).renderFrame(fr, save_rhino_render)
        else:
            logMessage("Rendering Frame #" + str(fr) + " ...")
            fname, fext = os.path.splitext(self.img_file)
            outpath = "{0}.{2:0{1}}{3}".format(fname, self.padding, fr, fext)
            kso_tcp.writeRenderPlaceholder(outpath)
            rs.Command('_Render')

    def renderFrames(self, FrStart, FrEnd, FrStep, save_rhino_render=False, full_range=True):
        if self.vray_ver < 10:
            super(VRayLegacyRenderManager, self).renderFrames(FrStart, FrEnd, FrStep, save_rhino_render=save_rhino_render)
            return

        if full_range and FrStep == 1:
            logMessage("Rendering Frames #{0}->#{1}...".format(FrStart, FrEnd))
            self.setFrameRange(FrStart, FrEnd)
            rs.Command('_Render')
        else:
            for fr in xrange(FrStart, FrEnd, FrStep):
                self.renderFrame(fr, save_rhino_render)

    def setDoAnimation(self, do_anim):
        if self.vray_ver < 10:
            do_animation = self.__xmlTree.SelectSingleNode("//vropt/Asset/plugin/vrayplugin/parameters/parameter[@name='do_animation']/value")
            do_animation.InnerText = str(int(do_anim))
        else:
            self.__VRay.Scene().Plugin("/SettingsOutput").Param("do_animation").Value = bool(do_anim)

    def setNeedFrameNumber(self, is_need):
        need_frame = self.__xmlTree.SelectSingleNode("//vropt/Asset/plugin/vrayplugin/parameters/parameter[@name='img_file_needFrameNumber']/value")
        need_frame.InnerText = str(int(is_need))

    def WriteVisopt(self, voptfile):
        """Save object settings to a .vropt file"""
        self.__xmlTree.Save(voptfile)

    def SaveVisopt(self, voptfile):
        """Save VRay options to a .visopt file"""
        self.__VRay.SaveVisopt(voptfile)

    def LoadVisopt(self, voptfile):
        """Set VRay options from a .vropt/.vsopt file"""
        self.__VRay.LoadVisopt(voptfile)

    def UpdateVisopt(self):
        """Save and Reload all options"""
        if self.vray_ver > 10:
            logMessageWarn("Export of Vray Options is not needed with VRay ", + self.vray_ver)

        tmpSettings = tempfile.NamedTemporaryFile(delete=False, suffix=".vropt")
        tmpSettings.close()
        self.WriteVisopt(tmpSettings.name)
        self.LoadVisopt(tmpSettings.name)
        os.unlink(tmpSettings.name)

        self.SetBatchRenderOn(True)  # batch mode can be lost on reload

    def SetBatchRenderOn(self, is_on):
        """Wait for VRay rendering before resuming the script"""
        self.__VRay.SetBatchRenderOn(is_on)

    def indent(self, elem, level=0):
        """Format an xml tree with nice indentation
        (from infix.se (Filip Solomonsson))
        """
        i = "\n" + level * ' '
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + " "
            for e in elem:
                self.indent(e, level + 1)
                if not e.tail or not e.tail.strip():
                    e.tail = i + " "
            if not e.tail or not e.tail.strip():
                e.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
        return True


class VRayRenderManager(RhinoRenderManager):
    """Render Output Settings for VRay Next (version > 4)

    Contains the output settings for VRay. Some settings (e.g. frames) cannot be
    accessed via scripting. In order to set those we need to export the whole
    section to a vropt xml file and load it through VRay.LoadVisopt
    """

    def __init__(self, total_frames=0):
        super(VRayRenderManager, self).__init__(total_frames=total_frames)

        self.__VRay = rs.GetPlugInObject("V-Ray for Rhino")
        if not self.__VRay:
            msg = "'V-Ray for Rhino' doesn't return any script object, please check your VRay install," \
                  " and that the Rhino executable set in rrConfig matches the proper platform (32/64 bit)"
            logMessageError(msg)
            raise VRayNotFoundError(msg)

        try:
            self._vray_scene = self.__VRay.Scene()
        except AttributeError:
            # needs to use old rendermanager
            raise VRayLegacyVersion()

        if hasattr(self.__VRay, "SaveVisopt"):
            raise VRayLegacyVersion()

        self.render_mode = 0  # production
        self.render_engine = 0 # defaulted to CPU, set later
        self.render_timeout = -1  # modal execution

        self._setRenderEngine()
        logMessage("Initialized Render Manager - VRay Next")

    def _setRenderEngine(self):
        """Set vray render engine according to scene settings"""
        param = self._vray_scene.Plugin("/RTEngine").Param("render_mode")
        if param.Value() == -1:
            self.render_engine = 0
            return
        if param.Value() == 104:  # CUDA
            self.render_engine = 1
        if param.Value() == 107:  # RTX
            self.render_engine = 2

    def setDoFrameRange(self, do_range):
        self.__VRay.SetSceneValue("/SettingsOutput", "animation_time_segment", do_range)

    def setFrameRange(self, seqStart, seqEnd, seqStep=1):
        self.__VRay.SetSceneValue("/SettingsOutput", "frame_range_start", seqStart)
        self.__VRay.SetSceneValue("/SettingsOutput", "frame_range_end", seqEnd)

        if seqStep != 1:
            logMessageWarn("Frame Step different from 1, not available with VRay " + self.vray_ver)

    def setImageFile(self, filename):
        img_path = os.path.normpath(filename).replace("\\", "/")  # safer with unix paths
        self.__VRay.SetSceneValue("/SettingsOutput", "img_file", img_path)

    def setSaveRender(self, is_save):
        self.__VRay.SetSceneValue("/SettingsOutput", "save_render", is_save)

    def renderFrame(self, fr, save_rhino_render=False):
        """Invoked by super().renderFrames, not needed anymore since VRay 10"""
        self.setFrameRange(fr, fr)

        logMessage("Rendering Frame #" + str(fr) + " ...")
        fname, fext = os.path.splitext(self.img_file)
        outpath = "{0}.{2:0{1}}{3}".format(fname, self.padding, fr, fext)
        kso_tcp.writeRenderPlaceholder(outpath)

        try:
            self.__VRay.Render(self.render_mode, self.render_engine, self.render_timeout)
        except AttributeError as e:
            msg = 'Vray plugin lacks "Render()" function, please update'
            logMessageError(msg)
            raise VRayVersionError(msg)

    def renderFrames(self, FrStart, FrEnd, FrStep, save_rhino_render=False, full_range=True):
        if full_range and FrStep == 1:
            logMessage("Rendering Frames #{0}->#{1}...".format(FrStart, FrEnd))
            self.setFrameRange(FrStart, FrEnd)
            self.__VRay.Render(self.render_mode, self.render_engine, self.render_timeout)
        else:
            for fr in xrange(FrStart, FrEnd, FrStep):
                self.renderFrame(fr, save_rhino_render)

    def setDoAnimation(self, do_anim):
        self.__VRay.SetSceneValue("/SettingsOutput", "do_animation", do_anim)

    def setNeedFrameNumber(self, is_need):
        self.__VRay.SetSceneValue("/SettingsOutput", "img_file_needFrameNumber", is_need)


def init_rhino():
    """
    """
    logMessage("Initializing Rhino Session - Royal Render %rrVersion%")

    img_file = rs.GetString("Image File")
    img_ext = rs.GetString("Image Extension")

    seqStart = rs.GetInteger("Sequence Start", number=0, minimum=0)
    seqEnd = rs.GetInteger("Sequence End", number=0, minimum=0)
    seqStep = rs.GetInteger("Sequence Step", number=1, minimum=1)
    renderer = rs.GetString("RendererName")
    pymodpath = rs.GetString("PyModPath")
    is_single = rs.GetInteger("IsSingle", number=0, minimum=0)
    avFrameTimeSec = rs.GetInteger("AvFrameTimeSec", number=0, minimum=-1)

    max_frames = int(getTotalFrames())
    if max_frames < seqEnd:
        logMessageWarn("Frame range larger than animation, setting last frame to " + str(max_frames))
        seqEnd = max_frames

    logMessage("Append python search path with '" + pymodpath + "'")
    sys.path.append(pymodpath)
    global kso_tcp
    import kso_tcp

    # make sure we are not duplicating "."
    img_file = img_file.rstrip(".")
    img_ext = img_ext.lstrip(".")
    img_full = img_file if is_single else "{0}.{1}".format(img_file, img_ext)

    current_rnd = rhinoscript.application.DefaultRenderer()
    if renderer.lower() == "rhino":
        if  current_rnd != "Rhino Render":
            rs.Command('_-SetCurrentRenderPlugin "Rhino Render" _Enter', 0)

        rmanager = RhinoRenderManager(total_frames=max_frames)
        rmanager.setImageFile(img_full)
        save_rhino_render = True
    elif renderer.lower() == "vray":
        if current_rnd != "V-Ray for Rhino":
            rs.Command('_-SetCurrentRenderPlugin "V-Ray for Rhino" _Enter', 0)

        use_frnum = 0 if is_single else 1

        save_rhino_render = False
        try:
            rmanager = VRayRenderManager(total_frames=max_frames)
            vray_legacy = False
        except VRayLegacyVersion:  # TODO: make specific exception
            rmanager = VRayLegacyRenderManager(total_frames=max_frames)
            vray_legacy = True

            if rmanager.vray_ver == 9:
                save_rhino_render = True

        rmanager.setDoFrameRange(1)
        rmanager.setSaveRender(not save_rhino_render)
        rmanager.setDoAnimation(use_frnum)
        rmanager.setImageFile(img_full)

        if vray_legacy:
            rmanager.setNeedFrameNumber(use_frnum)
            if rmanager.vray_ver < 10:
                rmanager.UpdateVisopt()

            rmanager.SetBatchRenderOn(True)

    if is_single:
        rmanager.padding = 0

    rmanager.renderFrames(seqStart, seqEnd, seqStep, save_rhino_render=save_rhino_render)


if __name__=="__main__":
    set_logger(logging.INFO)
    init_rhino()
    rs.DocumentModified(False)
    closeHandlers(logging.getLogger("rrRhino"))
    Rhino.RhinoApp.Exit()
