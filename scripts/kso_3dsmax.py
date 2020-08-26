# Render script for 3dsmax
#  %rrVersion%
#  Copyright (c)  Holger Schoenberger - Binary Alchemy

import datetime
import errno
import logging
import os
import shutil
import sys
import time

import ConfigParser
import MaxPlus


USE_DEFAULT_PRINT = False
USE_LOGGER = True
PRINT_DEBUG = False
ELEMENT_FILENAME_ChangedOnce = False  # True if render element filenames have been set at render time
PREV_FPADDING = -1  # digits added to render element filenames during previous renders
GLOBAL_ARG = None  # required for KSO rendering


################ Logger Functions ################

def flushLog():
    global USE_LOGGER
    if USE_LOGGER:
        sys.stdout.flush()
        sys.stderr.flush()
    else:
        logger = logging.getLogger("rrMax")
        for handler in logger.handlers:
            handler.flush()


def closeHandlers(logger):
    for handler in logger.handlers:
        handler.flush()
        handler.close()


def setLogger(log_level=20, log_name="rrMax", log_file=None, log_to_stream=False):
    logger = logging.getLogger(log_name)
    logger.setLevel(log_level)
    log_format = logging.Formatter("' %(asctime)s %(name)s %(levelname)s: %(message)s", "%H:%M:%S")

    OUTFILE_LEVEL_NUM = logging.INFO + 2
    SET_LEVEL_NUM = logging.INFO + 1

    logging.addLevelName(SET_LEVEL_NUM, "SET")
    logging.addLevelName(OUTFILE_LEVEL_NUM, "FILE")

    def logSet(self, message, *args, **kws):
        if self.isEnabledFor(SET_LEVEL_NUM):
            self._log(SET_LEVEL_NUM, message, args, **kws)

    def logFILE(self, message, *args, **kws):
        if self.isEnabledFor(OUTFILE_LEVEL_NUM):
            self._log(OUTFILE_LEVEL_NUM, message, args, **kws)

    logging.Logger.set = logSet
    logging.Logger.outfile = logFILE

    handlers = logger.handlers[:]
    for handler in handlers:
        handler.close()
        logger.removeHandler(handler)

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(log_format)
        file_handler.setLevel(log_level)

        logger.addHandler(file_handler)

    if log_to_stream:
        str_handler = logging.StreamHandler()
        str_handler.setFormatter(log_format)
        logger.addHandler(str_handler)


def rrMax_exit(func):
    """Add exit command to the wrapped func"""
    def wrapper(*args, **kwargs):
        func(*args, **kwargs)
        sys.exit()

    return wrapper


def rrMax_logger(func):
    """Wrapper for log functions, gets the "rrMax" logger,
    makes sure to close handlers or flush the listener after message log

    :param func: function to wrap, must accept arguments "msg" and "logger"
    :return: wrapped function
    """
    logger = logging.getLogger("rrMax")

    def wrapper(msg):
        func(msg, logger=logger)
        if USE_LOGGER:
            MaxPlus.Core.EvalMAXScript("flushLog()")
        else:
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

        if USE_LOGGER:
            func(msg, logger)
            return

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


@rrMax_logger
@io_retry
def logMessage(msg, logger=None):
    logger.info(msg)


@rrMax_logger
@io_retry
def logMessageSET(msg, logger=None):
    logger.set(msg)


@rrMax_logger
@io_retry
def logMessageWarn(msg, logger=None):
    logger.warning(msg)


@rrMax_logger
@io_retry
def logMessageDebug(msg, logger=None):
    logger.debug(msg)


@rrMax_logger
@io_retry
def logMessageFile(msg, logger=None):
    logger.outfile(msg)


@rrMax_exit
@rrMax_logger
@io_retry
def logMessageError(msg, logger=None):
    logger.error(msg)
    logger.error("Error reported, aborting render script")


################ Argument Parsing ################

def argValid(arg_value):
    return ((arg_value != None) and (len(str(arg_value)) > 0))


class ArgParser:
    def getParam(self, argFindName, isBool=False):
        argFindName = argFindName.lower()
        try:
            argValue = self.config.get('Max', argFindName)
        except ConfigParser.NoOptionError:
            return ""
        if argValue == None:
            return ""
        argValue = argValue.strip()
        if argValue.startswith("*"):
            return ""
        if argValue.lower() == "true":
            argValue = True
        elif argValue.lower() == "false":
            argValue = False
        elif (isBool):
            if argValue.lower() == "1":
                argValue = True
            elif argValue.lower() == "0":
                argValue = False
        logMessage("Flag  " + argFindName.ljust(15) + ": '" + str(argValue) + "'")
        return argValue

    def readArguments(self):
        self.config = ConfigParser.RawConfigParser()
        configFilename = os.path.join(os.environ['TEMP'], "kso_3dsmax.ini")
        logMessage("configFilename: " + configFilename)
        self.config.read(configFilename)

        self.SName = self.getParam("Scene")
        self.RendererMode = self.getParam("RendererMode")
        self.Renderer = self.getParam("Renderer")
        self.KSOMode = self.getParam("KSOMode")
        self.KSOPort = self.getParam("KSOPort")
        self.RPMPass = self.getParam("RPMPass")
        self.StateSet = self.getParam("StateSet")
        self.FName = self.getParam("FName")
        self.FNameVar = self.getParam("FNameVar")
        self.FExt = self.getParam("FExt")
        self.FPadding = self.getParam("FPadding")
        self.FNameChannelAdd = self.getParam("FNameChannelAdd")
        self.FrStart = self.getParam("SeqStart")
        self.FrEnd = self.getParam("SeqEnd")
        self.FrStep = self.getParam("SeqStep")
        self.FrOffset = self.getParam("SeqOffset")
        self.Camera = self.getParam("Camera")
        self.ResX = self.getParam("ResX")
        self.ResY = self.getParam("ResY")
        self.IgnoreError = self.getParam("IgnoreErr", True)
        self.RegionX1 = self.getParam("RegionX1")
        self.RegionX2 = self.getParam("RegionX2")
        self.RegionY1 = self.getParam("RegionY1")
        self.RegionY2 = self.getParam("RegionY2")
        self.RenderThreads = self.getParam("RenderThreads")
        self.PyModPath = self.getParam("PyModPath")
        self.logFile = self.getParam("LogFile")
        self.ElementsFolder = self.getParam("ElementsFolder")
        self.VRayMemLimit = self.getParam("VRayMemLimit")
        self.VRayMemLimitPercent = self.getParam("VRayMemLimitPercent")
        self.ClientTotalMemory = self.getParam("ClientTotalMemory")
        self.GBuffer = self.getParam("GBuffer", True)
        self.AutoElementFileName = self.getParam("AutoElementFileName", True)
        self.AdditionalCommandlineParam = self.getParam("AdditionalCommandlineParam")
        self.MaxBatchMode = self.getParam("MaxBatchMode", True)
        self.noFrameLoop = self.getParam("noFrameLoop", True)
        self.avFrameTime = self.getParam("avFrameTime")
        self.hdrFrameBuffer = self.getParam("hdrFrameBuffer", True)
        self.limitTime = self.getParam("limitTime")
        self.limitNoise = self.getParam("limitNoise")
        self.multiExr = self.getParam("multiExr")
        self.showVfb = self.getParam("showVfb")



def checkCreateFolder(filedir, verbose):
    if not os.path.exists(filedir):
        if verbose:
            logMessage("creating folder '%s'" % filedir)
        try:
            os.makedirs(filedir)  # throws errno.EEXIST if dir is just being created by others
        except OSError as e:
            logMessage("Error: Unable to create folder '%s'" % filedir)
            if e.errno != errno.EEXIST:
                raise


class StateSetManager:
    """Provide python access to State Sets via dotnet"""

    # base command: actual commands are appended to this string to access StateSets
    _dotAccess = '''
    dotState = dotNetObject "Autodesk.Max.StateSets.Plugin"
    stateSets = dotState.Instance
    masterState = stateSets.EntityManager.RootEntity.MasterStateSet
    numStates = masterState.Children.Count
    states = masterState.Children
    '''

    def getNumStates(self):
        return MaxPlus.Core.EvalMAXScript(self._dotAccess + ";numStates").Get()

    def getStateSets(self):
        state_sets = []
        for i in xrange(0, self.getNumStates()):
            state_name = MaxPlus.Core.EvalMAXScript("{0};states.Item[{1}].Name".format(self._dotAccess, i)).Get()
            state_sets.append(state_name)

        return state_sets

    def getStateOutPattern(self):
        pattern = MaxPlus.Core.EvalMAXScript(
            self._dotAccess + ";masterState.RenderOutputFilePattern").Get()
        return pattern

    def getCurrentState(self):
        return MaxPlus.Core.EvalMAXScript(self._dotAccess + ";masterState.CurrentState.Name").Get()

    def setCurrentState(self, state_name):
        if not state_name:
            MaxPlus.Core.EvalMAXScript(self._dotAccess + ";masterState.CurrentState=null")
            return True

        num_states = self.getNumStates()

        for i in xrange(0, num_states):
            st_name = MaxPlus.Core.EvalMAXScript(
                "{0};states.Item[{1}].Name".format(self._dotAccess, i)).Get()
            if st_name == state_name:
                MaxPlus.Core.EvalMAXScript("""{0};stateSet=states.Item[{1}];
                masterState.CurrentState = #(stateSet)""".format(self._dotAccess, i))
                return True

        return False

    def renderStateSet(self, state_name):
        """Render a State Set without activating it.
        Note: This function is not used in this render script"""

        num_states = self.getNumStates()

        for i in xrange(0, num_states):
            st_name = MaxPlus.Core.EvalMAXScript(
                "{0};states.Item[{1}].Name".format(self._dotAccess, i)).Get()
            if st_name == state_name:
                MaxPlus.Core.EvalMAXScript(
                    """{0};stateSet=states.Item[{1}];
                    stateSet.Render #(stateSet)""".format(self._dotAccess, i))
                return True

        return False


def applyOutput_default(arg, frameNr, verbose):
    """Sets the render path for main output and elements according to the job settings
    stored in arg and the given frame number. Returns the render path for the main pass

    :param arg: the ArgParser used for the current task
    :param frameNr: frame number to render, use empty string ("") when rendering an interval
    :param verbose: print out full output if True
    :return: main render path
    """
    #logMessageDebug("applyOutput_default "+str(frameNr)+"  "+str(verbose));
    render = MaxPlus.RenderSettings

    #outFile = render.GetOutputFile()
    #logMessageDebug("applyOutput_default - "+outFile)

    if arg.StateSetFilename != "":  # StateSets can set different extension
        _, tmp_ext = os.path.splitext(arg.StateSetFilename)
    else:
        _, tmp_ext = os.path.splitext(render.GetOutputFile())

    if len(tmp_ext) == 0:
        tmp_ext = arg.FExt

    # note: The render output will be set with frame number 00000,
    # but these settings have to be overwritten before each frame with the right frame number
    FPadding = max(arg.FPadding, len(str(frameNr))) if frameNr != "" else 0
    mainFileName = arg.FName + str(frameNr).zfill(FPadding) + tmp_ext

    logMessageDebug("applyOutput_default - " + mainFileName)
    if verbose:
        logMessageSET("main output to '" + arg.FName + tmp_ext + "'")

    render.SetOutputFile(arg.FName + tmp_ext)
    filedir = os.path.dirname(arg.FName)
    checkCreateFolder(filedir, True)
    render.SetSaveFile(True)

    if verbose:
        #logMessageDebug("applyOutput_default - arg.ElementsFolder "+str(arg.ElementsFolder))
        #logMessageDebug("applyOutput_default - arg.renderChannels "+str(arg.renderChannels))
        #logMessageDebug("applyOutput_default - arg.FNameVar "+str(arg.FNameVar))
        #logMessageDebug("applyOutput_default - GetElementsActive() "+str(MaxPlus.Core.EvalMAXScript("(maxOps.GetCurRenderElementMgr()).GetElementsActive()").Get()))
        logMessageDebug("applyOutput_default - AutoElementFileName is set to  "+str(arg.AutoElementFileName))

    if (arg.renderChannels and argValid(arg.FNameVar)
        and MaxPlus.Core.EvalMAXScript("(maxOps.GetCurRenderElementMgr()).GetElementsActive()").Get()):

        global ELEMENT_FILENAME_ChangedOnce
        global PREV_FPADDING
        #logMessageDebug("applyOutput_default - elements")
        nrOfElements = MaxPlus.Core.EvalMAXScript("(maxOps.GetCurRenderElementMgr()).NumRenderElements()").Get()
        if verbose:
            logMessage("Elements found: " + str(nrOfElements))

        for elemNr in xrange(0, nrOfElements):
            elem_cmd_base = "(maxOps.GetCurRenderElementMgr()).GetRenderElement {0}".format(elemNr)

            elem_class = MaxPlus.Core.EvalMAXScript("classof ({0}) as string".format(elem_cmd_base)).Get()

            if elem_class == "Missing_Render_Element_Plug_in":
                logMessageWarn(u"skipping element {0}: Missing Plugin".format(elemNr))
                continue

            elemName = MaxPlus.Core.EvalMAXScript("({0}).elementName".format(elem_cmd_base)).Get()
            elemName = elemName.replace(" ", "_")
            elemEnabled = MaxPlus.Core.EvalMAXScript("({0}).enabled".format(elem_cmd_base)).Get()

            if verbose:
                logMessageDebug(u"applyOutput_default - elemName: {0}   Enabled: {1}".format(elemName, elemEnabled))

            if not elemEnabled:
                continue

            if (MaxPlus.Core.EvalMAXScript("(( (maxOps.GetCurRenderElementMgr()).GetRenderElementFileName " + str(
                    elemNr) + ")==undefined)").Get()):
                if verbose:
                    logMessageDebug("applyOutput_default - No element filename set in scene file")
                fileout = ""
                tmp_ext = ""
                tempFileName = ""
            else:
                fVal = MaxPlus.Core.EvalMAXScript(
                    "(maxOps.GetCurRenderElementMgr()).GetRenderElementFileName " + str(elemNr))
                fileout = fVal.Get()
                if not ELEMENT_FILENAME_ChangedOnce and verbose:
                    logMessageDebug(u"element filename (saved in scene file) was set to " + fileout)
                tempFileName, tmp_ext = os.path.splitext(fileout)
                if (ELEMENT_FILENAME_ChangedOnce and (len(tempFileName) > PREV_FPADDING)):
                    for _ in xrange(0, PREV_FPADDING):
                        # remove the frame number we have added previously
                        if tempFileName[-1].isdigit():
                            tempFileName = tempFileName[:-1]
                        else:
                            break
            if len(tmp_ext) == 0:
                tmp_ext = arg.FExt

            if arg.AutoElementFileName or (len(tempFileName) == 0):
                fileout = arg.FNameVar + str(frameNr).zfill(FPadding) + tmp_ext
                logMessageDebug("AutoElementFileName: " + str(fileout))
            else:
                fileout = tempFileName + str(frameNr).zfill(FPadding) + tmp_ext
                logMessageDebug("scene element filename: " + str(fileout))

            fileout = fileout.replace("<Channel>", elemName)
            fileout = fileout.replace("<Layer>", arg.StateSetFilename)
            fileout = fileout.replace("<layer>", arg.StateSetFilename)
            fileout = fileout.replace("[Layer]", arg.StateSetFilename)
            fileout = fileout.replace("[layer]", arg.StateSetFilename)
            if verbose:
                logMessageSET("element %20s output to '%s'" % (elemName, fileout))
            fileout = os.path.normpath(fileout)
            filedir = os.path.dirname(fileout)
            fileout = fileout.replace("\\", "\\\\")
            logMessageDebug("applyOutput_default -  " + fileout)
            MaxPlus.Core.EvalMAXScript(
                u'(maxOps.GetCurRenderElementMgr()).SetRenderElementFilename {0} "{1}"'.format(elemNr, fileout))

            checkCreateFolder(filedir, verbose)

        ELEMENT_FILENAME_ChangedOnce = True
        PREV_FPADDING = FPadding

    logMessageDebug("applyOutput_default - exit " + mainFileName)
    return mainFileName


def applyRendererOptions_default(arg):
    logMessage("Rendering with Max Default Scanline")
    applyOutput_default(arg, 0, True)


def getVraySettingsContainer():
    current_renderer = MaxPlus.RenderSettings.GetCurrent(createRendererIfItDoesntExist=False)
    class_name = current_renderer.GetClassName().lower()

    assert any(name in class_name for name in ("vray", "v-ray"))

    vray_settings = "renderers.current"
    if 'gpu' in class_name:
        vray_settings += ".V_Ray_settings"

    return vray_settings


def moveOutput_VRay_sub(arg, frameNr, verbose, fNameVar_Rendered, elemName, vray_ext):
    fileout_Rendered = fNameVar_Rendered + str(frameNr).zfill(arg.FPadding) + vray_ext
    fileout_Should = arg.FNameVar + str(frameNr).zfill(arg.FPadding) + vray_ext
    fileout_Rendered = fileout_Rendered.replace("<Channel>", elemName)
    fileout_Should = fileout_Should.replace("<Channel>", elemName)

    if not os.path.isfile(fileout_Rendered):
        logMessageWarn("Element file to be moved to subfolder not found: " + fileout_Rendered)
        return False
    if verbose:
        logMessage("Moving element '" + fileout_Rendered + "' => '" + fileout_Should + "'")
    shutil.move(fileout_Rendered, fileout_Should)
    return True


def applyOutput_VRay(arg, frameNr, verbose):
    logMessageDebug("applyOutput_VRay " + str(frameNr) + "  " + str(verbose))
    # note: The render output will be set with frame number 0000, but these settings have to be overwritten before each frame with the right frame number
    if arg.RendererMode == "GIPrePass":
        return arg.FName + str(frameNr).zfill(arg.FPadding) + arg.FExt

    render = MaxPlus.RenderSettings
    if (not arg.vraySeperateRenderChannels) and (render.GetSaveFile() or (not arg.vrayRawFile)):
        return applyOutput_default(arg, frameNr, verbose)

    mainFileName = ""

    if render.GetSaveFile():
        logMessageDebug("applyOutput_VRay - render.GetSaveFile()")

        # get the extension of the main output
        _, temp_ext = os.path.splitext(render.GetOutputFile())
        if len(temp_ext) == 0:
            temp_ext = arg.FExt

        mainFileName = arg.FName + str(frameNr).zfill(arg.FPadding) + temp_ext

        if verbose:
            logMessageSET("main output to '" + arg.FName + temp_ext + "'")

        render.SetOutputFile(arg.FName + temp_ext)
        filedir = os.path.dirname(arg.FName)
        checkCreateFolder(filedir, True)

    vray_ext = arg.FExt
    vray_settings = getVraySettingsContainer()

    if arg.vraySeperateRenderChannels:
        logMessageDebug("applyOutput_VRay - vraySeperateRenderChannels")

        outputSet = not MaxPlus.Core.EvalMAXScript("({0}.output_splitfilename==undefined)".format(vray_settings)).Get()
        if outputSet:
            fVal = MaxPlus.Core.EvalMAXScript("{0}.output_splitfilename".format(vray_settings))
            _, vray_ext = os.path.splitext(fVal.Get())

        if len(vray_ext) == 0:
            vray_ext = arg.FExt  # FIXME: redundant?

        fileout = arg.FName + vray_ext
        if verbose:
            logMessageSET("VRay render channel output to " + fileout)

        filedir = os.path.dirname(fileout)
        fileout = os.path.normpath(fileout)
        fileout = fileout.replace("\\", "\\\\")
        MaxPlus.Core.EvalMAXScript('{0}.output_splitfilename="{1}"'.format(vray_settings, fileout))
        checkCreateFolder(filedir, verbose)
        if ((not render.GetSaveFile())
            and (MaxPlus.Core.EvalMAXScript("{0}.output_splitRGB".format(vray_settings)).Get())):
            mainFileName = arg.FNameVar + str(frameNr).zfill(arg.FPadding) + arg.FExt
            mainFileName = mainFileName.replace("<Channel>", "RGB_color")

    if arg.vrayRawFile:
        logMessageDebug("applyOutput_VRay - output_saveRawFile")
        fileout = arg.FName + arg.FExt
        fileout = os.path.normpath(fileout)
        fileout = fileout.replace("\\", "\\\\")
        MaxPlus.Core.EvalMAXScript('{0}.output_rawFileName="{1}"'.format(vray_settings, fileout))

        mainFileName = arg.FName + str(frameNr).zfill(arg.FPadding) + arg.FExt

    # it is not required to set the filename for VRay buffers IF output_splitfilename is enabled
    # but in case that is Disabled or there is a 3dsmax buffer, we need to set it

    elementsActive = MaxPlus.Core.EvalMAXScript("(maxOps.GetCurRenderElementMgr()).GetElementsActive()").Get()
    seperateElementFiles = argValid(arg.FNameVar) and elementsActive

    if (not render.GetSaveFile()) and (not arg.vraySeperateRenderChannels):
        seperateElementFiles = False
    if ((not arg.vrayFramebuffer) and MaxPlus.Core.EvalMAXScript("{0}.output_on".format(vray_settings)).Get()):
        seperateElementFiles = False

    if seperateElementFiles and arg.ElementsFolder:
        logMessageDebug("applyOutput_VRay - Elements")
        if (arg.vraySeperateRenderChannels
            and (MaxPlus.Core.EvalMAXScript("{0}.output_splitRGB".format(vray_settings)).Get())):

            fileout = arg.FNameVar + str(frameNr).zfill(arg.FPadding) + vray_ext

            fileout = fileout.replace("<Channel>", "RGB_color")
            filedir = os.path.dirname(fileout)

            if verbose:
                logMessageSET('element {0:>20} output to "{1}"'.format("RGB_color", fileout))
            checkCreateFolder(filedir, verbose)
        if (arg.vraySeperateRenderChannels and (
                MaxPlus.Core.EvalMAXScript("{0}.output_splitAlpha".format(vray_settings)).Get())):

            fileout = arg.FNameVar + str(frameNr).zfill(arg.FPadding) + vray_ext
            fileout = fileout.replace("<Channel>", "Alpha")
            filedir = os.path.dirname(fileout)

            if verbose:
                logMessageSET("element %20s output to '%s'" % ("Alpha", fileout))
            checkCreateFolder(filedir, verbose)

        nrOfElements = MaxPlus.Core.EvalMAXScript("(maxOps.GetCurRenderElementMgr()).NumRenderElements()").Get()
        if verbose:
            logMessage("elements found: " + str(nrOfElements))
        for elemNr in xrange(0, nrOfElements):
            elemName = MaxPlus.Core.EvalMAXScript(
                "((maxOps.GetCurRenderElementMgr()).GetRenderElement " + str(elemNr) + ").elementName").Get()

            elemName = elemName.replace(" ", "_")
            if arg.vraySeperateRenderChannels:
                fileout = arg.FNameVar + str(frameNr).zfill(arg.FPadding) + vray_ext
            else:
                if (MaxPlus.Core.EvalMAXScript("(( (maxOps.GetCurRenderElementMgr()).GetRenderElementFileName " + str(
                        elemNr) + ")==undefined)").Get()):
                    fileout = ""
                else:
                    fVal = MaxPlus.Core.EvalMAXScript(
                        "(maxOps.GetCurRenderElementMgr()).GetRenderElementFileName " + str(elemNr))
                    fileout = fVal.Get()
                _, temp_ext = os.path.splitext(fileout)
                if len(temp_ext) == 0:
                    temp_ext = arg.FExt

                fileout = arg.FNameVar + str(frameNr).zfill(arg.FPadding) + temp_ext

            fileout = fileout.replace("<Channel>", elemName)
            if verbose:
                logMessageSET("element %20s output to '%s'" % (elemName, fileout))
            filedir = os.path.dirname(fileout)
            fileout = os.path.normpath(fileout)
            fileout.replace("\\", "\\\\")
            checkCreateFolder(filedir, verbose)
            MaxPlus.Core.EvalMAXScript(
                '(maxOps.GetCurRenderElementMgr()).SetRenderElementFilename {0} "{1}"'.format(elemNr, fileout))
    return mainFileName


def moveOutput_VRay(arg, frameNr, verbose):
    if (not arg.ElementsFolder) or (not arg.vraySeperateRenderChannels):
        return
    vray_ext = arg.FExt
    vray_settings = getVraySettingsContainer()
    if arg.vraySeperateRenderChannels:
        _, vray_ext = os.path.splitext(
            MaxPlus.Core.EvalMAXScript("{0}.output_splitfilename".format(vray_settings)).Get())
        if len(vray_ext) == 0:
            vray_ext = arg.FExt
    FNameVar_Rendered = arg.FNameVar
    FNameVar_Rendered = FNameVar_Rendered.replace("<Channel>\\", "")
    if (arg.vraySeperateRenderChannels and (
    MaxPlus.Core.EvalMAXScript("{0}.output_splitRGB".format(vray_settings)).Get())):
        moveOutput_VRay_sub(arg, frameNr, verbose, FNameVar_Rendered, "RGB_color", vray_ext)
    if (arg.vraySeperateRenderChannels and (
    MaxPlus.Core.EvalMAXScript("{0}.output_splitAlpha".format(vray_settings)).Get())):
        moveOutput_VRay_sub(arg, frameNr, verbose, FNameVar_Rendered, "Alpha", vray_ext)
    if (argValid(arg.FNameVar) and MaxPlus.Core.EvalMAXScript(
            "(maxOps.GetCurRenderElementMgr()).GetElementsActive()").Get()):
        nrOfElements = MaxPlus.Core.EvalMAXScript("(maxOps.GetCurRenderElementMgr()).NumRenderElements()").Get()
        for elemNr in xrange(0, nrOfElements):
            elemName = MaxPlus.Core.EvalMAXScript(
                "((maxOps.GetCurRenderElementMgr()).GetRenderElement " + str(elemNr) + ").elementName").Get()
            elemName = elemName.replace(" ", "_")
            moveOutput_VRay_sub(arg, frameNr, verbose, FNameVar_Rendered, elemName, vray_ext)


def applyRendererOptions_Vray(arg):
    logMessage("Rendering with VRay")

    vray_settings = getVraySettingsContainer()

    MaxPlus.Core.EvalMAXScript("{0}.system_lowThreadPriority=true".format(vray_settings))
    MaxPlus.Core.EvalMAXScript("{0}.system_vrayLog_level=2".format(vray_settings))
    MaxPlus.Core.EvalMAXScript('{0}.system_vrayLog_file="%TEMP%\\\\VRayLog.txt"'.format(vray_settings))

    if argValid(arg.RenderThreads):
        logMessageSET("VRay render threads  to " + str(arg.RenderThreads))
        MaxPlus.Core.EvalMAXScript("{0}.system_numThreads={1}".format(vray_settings, arg.RenderThreads))
    if argValid(arg.VRayMemLimit):
        logMessageSET("VRay mem limit to " + str(arg.VRayMemLimit))
        MaxPlus.Core.EvalMAXScript("{0}.system_raycaster_memLimit={1}".format(vray_settings, arg.VRayMemLimit))
    elif (argValid(arg.VRayMemLimitPercent) and argValid(arg.ClientTotalMemory)):
        memory = int(arg.ClientTotalMemory) * int(arg.VRayMemLimitPercent) / 100
        logMessageSET(
            "VRay mem limit to {0} % of {1} => {2}".format(arg.VRayMemLimitPercent, arg.ClientTotalMemory, memory))
        MaxPlus.Core.EvalMAXScript("{0}.system_raycaster_memLimit={1}".format(vray_settings, memory))

    arg.vrayOverrideResolution = not MaxPlus.Core.EvalMAXScript("{0}.output_getsetsfrommax".format(vray_settings)).Get()
    logMessage("VRay Override 3dsMax Resolution: " + str(arg.vrayOverrideResolution))
    if arg.vrayOverrideResolution:
        if argValid(arg.ResX):
            logMessageSET("width to " + str(arg.ResX))
            MaxPlus.Core.EvalMAXScript("{0}.output_width={1}".format(vray_settings, arg.ResX))
        if argValid(arg.ResY):
            logMessageSET("height to " + str(arg.ResY))
            MaxPlus.Core.EvalMAXScript("{0}.output_height={1}".format(vray_settings, arg.ResY))

    if (argValid(arg.limitNoise) or argValid(arg.limitTime)):
        samplerType = MaxPlus.Core.EvalMAXScript("{0}.imageSampler_type_new".format(vray_settings)).GetInt()
        if (samplerType != 1):
            logMessage("Error: VRays image sampler is not set to Progressive!")
            sys.exit()
        isResumeOn = MaxPlus.Core.EvalMAXScript("{0}.output_resumableRendering".format(vray_settings)).GetBool()
        if (not isResumeOn):
            logMessageSET("Resumable Rendering to enabled (Warning)")
            MaxPlus.Core.EvalMAXScript("{0}.output_resumableRendering=true".format(vray_settings))
        autoSaveInterval = MaxPlus.Core.EvalMAXScript("{0}.output_progressiveAutoSave".format(vray_settings)).GetFloat()
        if (autoSaveInterval > 0):
            logMessageSET(
                "Auto save interval off (Warning). It is slow and only required if you have more crashes than successful frames. ")
            MaxPlus.Core.EvalMAXScript("{0}.output_progressiveAutoSave=0".format(vray_settings))

    if argValid(arg.limitNoise):
        arg.limitNoise = float(arg.limitNoise)
        arg.limitNoise = arg.limitNoise / 100.0
        logMessageSET("VRay progressive noise limit to " + str(arg.limitNoise) + " minutes.")
        MaxPlus.Core.EvalMAXScript("{0}.progressive_noise_threshold={1}".format(vray_settings, arg.limitTime))

    if argValid(arg.limitTime):
        logMessageSET("VRay progressive time limit to {0} minutes".format(arg.limitTime))
        MaxPlus.Core.EvalMAXScript("{0}.progressive_max_render_time={1}".format(vray_settings, arg.limitTime))
        noiseThreshold = MaxPlus.Core.EvalMAXScript("{0}.progressive_noise_threshold".format(vray_settings)).GetFloat()
        if not argValid(arg.limitNoise):
            logMessage("VRay noiseThreshold setting: " + str(noiseThreshold))
        if (noiseThreshold <= 0.01):
            logMessageWarn(
                "VRay noiseThreshold not set or too low, applying high production quality default of 0.03 ")
            MaxPlus.Core.EvalMAXScript("{0}.progressive_noise_threshold=0.03".format(vray_settings))

    arg.vrayFramebuffer = MaxPlus.Core.EvalMAXScript("{0}.output_on".format(vray_settings)).Get()
    arg.vraySeperateRenderChannels = MaxPlus.Core.EvalMAXScript("{0}.output_splitgbuffer".format(vray_settings)).Get()
    arg.vrayRawFile = MaxPlus.Core.EvalMAXScript("{0}.output_saveRawFile".format(vray_settings)).Get()

    if arg.vrayFramebuffer:
        if (not arg.vrayRawFile) and (not arg.vraySeperateRenderChannels):
            arg.vrayFramebuffer = False
            arg.renderChannels = False
    if not arg.vrayFramebuffer:
        arg.vraySeperateRenderChannels = False
        MaxPlus.Core.EvalMAXScript("{0}.output_splitgbuffer=false".format(vray_settings))
        MaxPlus.Core.EvalMAXScript("{0}.output_saveRawFile=false".format(vray_settings))

    logMessage("VRay Framebuffer used: " + str(arg.vrayFramebuffer))
    logMessage("VRay Seperate Render Channels: " + str(arg.vraySeperateRenderChannels))
    logMessage("VRay Raw image: " + str(arg.vrayRawFile))

    if not argValid(arg.RendererMode):
        arg.RendererMode = "default"
        if arg.FExt == ".vrmap":
            arg.RendererMode = "GIPrePass"

    logMessage("VRay render mode is " + arg.RendererMode)
    logMessage("VRay GI irradiance mode: #" + str(
        MaxPlus.Core.EvalMAXScript("{0}.adv_irradmap_mode".format(vray_settings)).Get()))
    if arg.RendererMode == "GIPrePass":
        arg.FExt = ".vrmap"
        if not MaxPlus.Core.EvalMAXScript("{0}.gi_on".format(vray_settings)).Get():
            logMessageSET("VRay GI mode enabled")
            MaxPlus.Core.EvalMAXScript("{0}.gi_on=true".format(vray_settings))
        fileout = arg.FName + arg.FExt
        fileout = os.path.normpath(fileout)
        fileout = fileout.replace("\\", "\\\\")
        logMessageSET("VRay GI vrmap prepass to " + fileout)
        MaxPlus.Core.EvalMAXScript('{0}.adv_irradmap_autoSaveFileName="{1}"'.format(vray_settings, fileout))
        logMessageSET("VRay GI vrmap/animation prepass")
        MaxPlus.Core.EvalMAXScript("{0}.adv_irradmap_mode=6".format(vray_settings))
        logMessage("VRay GI irradiance mode: #" + str(
            MaxPlus.Core.EvalMAXScript("{0}.adv_irradmap_mode".format(vray_settings)).Get()))
        logMessageSET("VRay Seperate Render Channels On")
        MaxPlus.Core.EvalMAXScript("{0}.output_splitgbuffer=false".format(vray_settings))
        logMessageSET("VRay Framebuffer Off")
        MaxPlus.Core.EvalMAXScript("{0}.output_on=true".format(vray_settings))
        logMessageSET("Main 3dsmax save file Off")
        render = MaxPlus.RenderSettings
        render.SetSaveFile(False)
    else:
        if MaxPlus.Core.EvalMAXScript("{0}.adv_irradmap_mode".format(vray_settings)).Get() == 6:
            # the scene was saved with GI prepass animation, so change it to GI animation render
            loadFileName = MaxPlus.Core.EvalMAXScript("{0}.adv_irradmap_loadFileName".format(vray_settings)).Get()
            if (not argValid(loadFileName)):
                logMessageWarn("There is no irradiance map set to be loaded, switching to GI mode single frame")
                logMessageSET("VRay GI mode to single frame")
                MaxPlus.Core.EvalMAXScript("{0}.adv_irradmap_mode=0".format(vray_settings))
            else:
                logMessageSET("VRay GI mode to animation render")
                MaxPlus.Core.EvalMAXScript("{0}.adv_irradmap_mode=7".format(vray_settings))

    applyOutput_VRay(arg, 0, True)


def writeRenderPlaceholder(filename):
    logMessageFile(filename)

    import socket
    hostName = socket.gethostname()
    hostName = hostName[:100]
    img_file = open(filename, "wb")
    img_file.write("rrDB")  # Magic ID
    img_file.write("\x02\x0B")  # DataType ID
    img_file.write(chr(len(hostName)))
    img_file.write("\x00")
    img_file.write("\x00\x00")
    for x in range(0, len(hostName)):
        img_file.write(hostName[x])
        img_file.write("\x00")  # unicode
    for x in range(len(hostName), 51):
        img_file.write("\x00\x00")
    img_file.close()


def renderExecute(arg, frameStart, frameEnd, fileName, frameStep=1):
    beforeFrame = datetime.datetime.now()
    renderCmdLine = "render  vfb:false "
    if (arg.hdrFrameBuffer):
        renderCmdLine += " outputHDRbitmap:true "

    numFrames = frameEnd - frameStart + 1
    if numFrames > 1:
        renderCmdLine += " framerange:(interval {0} {1}) nthframe:({2})".format(frameStart, frameEnd, frameStep)
    else:
        renderCmdLine += " frame: " + str(frameStart)

    if argValid(arg.Camera):
        renderCmdLine += ' camera: (getnodebyname("{0}"))'.format(arg.Camera)
    if arg.regionEnabled:
        renderCmdLine += " renderType: #region region: #({0}, {1}, {2}, {3})".format(arg.RegionX1, arg.RegionY1,
                                                                                     arg.RegionX2, arg.RegionY2)
    else:
        if MaxPlus.RenderSettings.GetAreaType() == 1:
            renderCmdLine += " renderType: #selection "
        elif MaxPlus.RenderSettings.GetAreaType() == 2:
            renderCmdLine += " renderType: #region "
        elif MaxPlus.RenderSettings.GetAreaType() == 3:
            renderCmdLine += " renderType: #regionCrop "
        elif MaxPlus.RenderSettings.GetAreaType() == 4:
            renderCmdLine += " renderType: #blowUp "
        else:
            renderCmdLine += " renderType: #normal "

    if argValid(arg.GBufferString):
        renderCmdLine += " channels:#(" + arg.GBufferString + ")"

    if ((arg.RendererMode == "default" or arg.RendererMode == "")
        and MaxPlus.RenderSettings.GetSaveFile() and fileName != ""):
        renderCmdLine += ' outputfile:"{0}"'.format(fileName.replace("\\", "/"))

    logMessageDebug("executing  " + renderCmdLine)
    fpVal = MaxPlus.Core.EvalMAXScript(renderCmdLine)
    logMessageDebug("renderer result: " + str(fpVal.Get()))
    afterFrame = datetime.datetime.now()
    afterFrame = afterFrame - beforeFrame

    if numFrames > 1:
        logMessage("Frames #{0}-{1} done ({2} frames)".format(frameStart, frameEnd, numFrames))
        logMessage("Frames Time: {0}  h:m:s.ms - (Average: {1})".format(afterFrame, datetime.timedelta(seconds=afterFrame.total_seconds() / numFrames)))
        if arg.Renderer == "VRay":
            moveOutput_VRay(arg, frameStart, True)
    else:
        logMessage("Frame #{0} done".format(frameStart))
        logMessage("Frame Time: {0}  h:m:s.ms".format(afterFrame))
        if arg.Renderer == "VRay":
            moveOutput_VRay(arg, frameStart, True)


def render_frame(FrStart, FrEnd, FrStep, arg):
    FrStart = int(FrStart)
    FrEnd = int(FrEnd)
    FrStep = int(FrStep)

    localNoFrameLoop = arg.noFrameLoop

    if not localNoFrameLoop:
        if arg.avFrameTime == 0:
            localNoFrameLoop = arg.Renderer in ("redshift-s", "Octane-s", "Redshift_Renderer", "Octane")
        elif arg.avFrameTime < 60:
            localNoFrameLoop = True
        elif arg.avFrameTime < 140:
            localNoFrameLoop = arg.Renderer in ("redshift-s", "Octane-s", "Redshift_Renderer", "Octane")

    if localNoFrameLoop:
        MaxPlus.RenderSettings.SetNThFrame(FrStep)
        MaxPlus.RenderSettings.SetStart(FrStart * 4800 / MaxPlus.Core.EvalMAXScript('frameRate').GetInt())
        MaxPlus.RenderSettings.SetEnd(FrEnd * 4800 / MaxPlus.Core.EvalMAXScript('frameRate').GetInt())
        logMessage("Starting to render frames #{0}-{1}, step {2} ...".format(FrStart, FrEnd, FrStep))
        logMessage("Frame range of scene is set to " + str(
            MaxPlus.RenderSettings.GetStart() * MaxPlus.Core.EvalMAXScript('frameRate').GetInt() / 4800) + " - " + str(
            MaxPlus.RenderSettings.GetEnd() * MaxPlus.Core.EvalMAXScript('frameRate').GetInt() / 4800))

        FrNum = FrStart if FrStart == FrEnd else ""  # no frame number in range render
        if arg.Renderer == "VRay":
            fileName = applyOutput_VRay(arg, FrNum, False)
        else:
            fileName = applyOutput_default(arg, FrNum, False)

        renderExecute(arg, FrStart, FrEnd, fileName, frameStep=FrStep)
    else:
        MaxPlus.RenderSettings.SetNThFrame(1)
        # we have to loop single frames as max will not print any "frame done in between"
        for frameNr in xrange(FrStart, FrEnd + 1, FrStep):
            MaxPlus.RenderSettings.SetStart(frameNr * 4800 / MaxPlus.Core.EvalMAXScript('frameRate').GetInt())
            MaxPlus.RenderSettings.SetEnd(frameNr * 4800 / MaxPlus.Core.EvalMAXScript('frameRate').GetInt())
            logMessage("Starting to render frame #" + str(frameNr) + " ...")
            logMessage("Frame range of scene is set to " + str(
                MaxPlus.RenderSettings.GetStart() * MaxPlus.Core.EvalMAXScript(
                    'frameRate').GetInt() / 4800) + " - " + str(
                MaxPlus.RenderSettings.GetEnd() * MaxPlus.Core.EvalMAXScript('frameRate').GetInt() / 4800))

            if arg.Renderer == "VRay":
                fileName = applyOutput_VRay(arg, frameNr + int(arg.FrOffset), False)
            else:
                fileName = applyOutput_default(arg, frameNr + int(arg.FrOffset), False)

            # logMessageDebug("render_frame - fileName "+fileName)
            if len(fileName) > 1:
                writeRenderPlaceholder(fileName)

            # logMessageDebug("render_frame - renderCmdLine start")
            renderExecute(arg, frameNr, frameNr, fileName)

    return True


def ksoRenderFrame(FrStart, FrEnd, FrStep):
    global GLOBAL_ARG
    render_frame(FrStart, FrEnd, FrStep, GLOBAL_ARG)
    logMessage("rrKSO Frame(s) done #" + str(FrEnd) + " ")
    logMessage("                                                            ")
    logMessage("                                                            ")
    logMessage("                                                            ")


def rrKSOStartServer(arg):
    logMessage("rrKSO startup...")
    if (arg.KSOPort == None) or (len(str(arg.KSOPort)) <= 1):
        arg.KSOPort = 7774
    HOST, PORT = "localhost", int(arg.KSOPort)
    server = kso_tcp.rrKSOServer((HOST, PORT), kso_tcp.rrKSOTCPHandler)
    logMessage("rrKSO server started")
    server.print_port()
    kso_tcp.rrKSONextCommand = ""
    while server.continueLoop:
        try:
            logMessageDebug("rrKSO waiting for new command...")
            server.handle_request()
            time.sleep(1)  # handle_request() seem to return before handle() completed execution
        except Exception as e:
            logMessageError(e)
            server.continueLoop = False
            import traceback
            logMessageError(traceback.format_exc())
        logMessage("rrKSO NextCommand ___________________________________________________________________________________________")
        logMessage("rrKSO NextCommand '" + kso_tcp.rrKSONextCommand + "'")
        logMessage("rrKSO NextCommand ___________________________________________________________________________________________")
        if len(kso_tcp.rrKSONextCommand) > 0:
            if (kso_tcp.rrKSONextCommand == "ksoQuit()") or (kso_tcp.rrKSONextCommand == "ksoQuit()\n"):
                server.continueLoop = False
                kso_tcp.rrKSONextCommand = ""
            else:
                exec(kso_tcp.rrKSONextCommand)
                kso_tcp.rrKSONextCommand = ""

    server.closeTCP()
    logMessage("rrKSO closed")
    time.sleep(2)
    


def render_KSO(arg):
    rrKSOStartServer(arg)


def render_default(arg):
    render_frame(arg.FrStart, arg.FrEnd, arg.FrStep, arg)


def render_main():
    ##############################################################################
    # MAIN "FUNCTION":
    ##############################################################################
    global USE_LOGGER
    global GLOBAL_ARG
    global PRINT_DEBUG

    GLOBAL_ARG = ArgParser()
    timeStart = datetime.datetime.now()

    arg = ArgParser()
    arg.readArguments()
    if not argValid(arg.logFile):
        arg.logFile = os.path.join(os.environ['TEMP'], "rrMaxRender.log")
    if not argValid(arg.MaxBatchMode):
        arg.MaxBatchMode = False

    USE_LOGGER = arg.MaxBatchMode
    if USE_LOGGER:
        setLogger(log_to_stream=True, log_level=logging.DEBUG if PRINT_DEBUG else logging.INFO)
        logMessage("USE_LOGGER")
    else:
        setLogger(log_file=arg.logFile, log_level=logging.DEBUG if PRINT_DEBUG else logging.INFO)
        logMessage("USE_LOGFILE_PRINT")
    logMessage("###########################################################################################")
    logMessage("######################         RENDER IS STARTING FROM NOW           ######################")
    logMessage("###################### IGNORE OLDER MESSAGES ABOUT SCENE AND FRAMES  ######################")
    logMessage("###########################################################################################")

    if argValid(arg.PyModPath):
        sys.path.append(arg.PyModPath)

    logMessage("Importing rrKSO...")
    global kso_tcp
    import kso_tcp
    kso_tcp.USE_LOGGER= USE_LOGGER
    kso_tcp.USE_DEFAULT_PRINT= False
    kso_tcp.LOGGER_FILENAME= arg.logFile
    
    if argValid(arg.AdditionalCommandlineParam):
        # '-gammaCorrection:1 -gammaValueIn:2,2 -gammaValueOut:2,2'
        pos = arg.AdditionalCommandlineParam.find("gammaCorrection:")
        if pos > 0:
            part = arg.AdditionalCommandlineParam[pos + len("gammaCorrection:"):]
            pos = part.find(" ")
            if pos > 0:
                part = part[:pos]
            part = part.replace(",", ".")
            part = (part == "1")
            logMessageSET("Gamma Correction to " + str(part))
            MaxPlus.GammaMgr.Enable(part)

        pos = arg.AdditionalCommandlineParam.find("gammaValueIn:")
        if pos > 0:
            part = arg.AdditionalCommandlineParam[pos + len("gammaValueIn:"):]
            pos = part.find(" ")
            if pos > 0:
                part = part[:pos]
            part = part.replace(",", ".")
            part = float(part)
            logMessageSET("FileInGamma to " + str(part))
            MaxPlus.GammaMgr.SetFileInGamma(part)

        pos = arg.AdditionalCommandlineParam.find("gammaValueOut:")
        if pos > 0:
            part = arg.AdditionalCommandlineParam[pos + len("gammaValueOut:"):]
            pos = part.find(" ")
            if pos > 0:
                part = part[:pos]
            part = part.replace(",", ".")
            part = float(part)
            logMessageSET("FileOutGamma to " + str(part))
            MaxPlus.GammaMgr.SetFileOutGamma(part)

    logMessage("Loading Scene '" + str(arg.SName) + "'...")
    fm = MaxPlus.FileManager
    if not fm.Open(str(arg.SName), True, True, True):
        logMessageError("Unable to open scene file")

    logMessage("Gamma Settings: Enabled: {0} In: {1} Out: {2}".format(MaxPlus.GammaMgr.IsEnabled(),
                                                                      MaxPlus.GammaMgr.GetFileInGamma(),
                                                                      MaxPlus.GammaMgr.GetFileOutGamma()))

    if argValid(arg.StateSet):
        stateSet = str(arg.StateSet)
        logMessageSET("pass to '" + stateSet + "'")
        arg.StateSetFilename = arg.StateSet
        arg.StateSetFilename = arg.StateSetFilename.replace("::", "")
        arg.StateSetFilename = arg.StateSetFilename.replace(":", "_")

        if stateSet.startswith("::"):  # we submit State Sets as starting with ::
            stateMan = StateSetManager()
            if stateSet == "::MasterLayer":
                stateMan.setCurrentState(None)
                arg.StateSetFilename = ""
            # state set
            elif not stateMan.setCurrentState(arg.StateSet[2:]):
                logMessageError(stateSet + "state not found in scene")
        else:
            # scene state
            MaxPlus.Core.EvalMAXScript('sceneStateMgr.restoreAllParts "' + arg.StateSet + '"')
    else:
        arg.StateSetFilename = ""

    if argValid(arg.RPMPass):
        logMessageSET("RPM pass to '" + str(arg.RPMPass) + "'")
        MaxPlus.Core.EvalMAXScript(
            "RPass_nr =0;  for i= 1 to RPMdata.GetPassCount() do  (  if (" + arg.RPMPass + "==RPMdata.GetPassName(i))    then RPass_nr=i  );  if RPass_nr>0    then RPMData.RMRestValues RPass_nr    else quitMax #noPrompt")

    fpVal = MaxPlus.Core.EvalMAXScript("classof renderers.current as string")
    arg.Renderer = fpVal.Get()
    # logMessage("renderer used: '" + arg.Renderer + "'")
    if "V_Ray" in arg.Renderer:
        arg.Renderer = "VRay"
    elif "Brazil" in arg.Renderer:
        arg.Renderer = "Brazil"
    elif "Redshift" in arg.Renderer:
        arg.Renderer = "redshift"
    elif "Octane" in arg.Renderer:
        arg.Renderer = "Octane"
    logMessage("renderer used: '" + arg.Renderer + "'")

    showVfb = argValid(arg.showVfb) and arg.showVfb

    MaxPlus.RenderSettings.SetSkipFrames(False)
    MaxPlus.RenderSettings.SetTimeType(2)  # Frame range
    MaxPlus.RenderSettings.SetFileNumberBase(int(arg.FrOffset))
    MaxPlus.RenderSettings.SetShowVFB(showVfb)
    MaxPlus.RenderSettings.SetAreaType(0)

    logMessageSET("SetShowVFB: " + str(showVfb))

    IBitmapPagerEnabled = MaxPlus.Core.EvalMAXScript('IBitmapPager.enabled').GetBool()
    # logMessage("IBitmapPager is set to: '" + str(IBitmapPagerEnabled) +"'")
    if IBitmapPagerEnabled:
        logMessage("Disabling IBitmapPager... ")
        MaxPlus.Core.EvalMAXScript("IBitmapPager.enabled=false")
    # IBitmapPagerEnabled= MaxPlus.Core.EvalMAXScript('IBitmapPager.enabled').GetBool()
    # logMessage("IBitmapPager is set to: '" + str(IBitmapPagerEnabled) +"'")

    if argValid(arg.Camera):
        logMessageSET("camera to " + arg.Camera)
        camNode = MaxPlus.INode.GetINodeByName(arg.Camera)
        if str(camNode) == "None":
            logMessage("Unable to find camera node with name " + arg.Camera)
            arg.Camera = ""

        MaxPlus.RenderSettings.SetUseActiveView(False)
        MaxPlus.ViewportManager.SetActiveViewport(0)
        MaxPlus.RenderSettings.SetViewID(0)
        MaxPlus.Viewport.SetViewCamera(MaxPlus.ViewportManager.GetViewportByID(0), camNode)
        MaxPlus.RenderSettings.SetCamera(camNode)
    else:
        logMessage("Rendering active viewport number " + str(MaxPlus.RenderSettings.GetViewID()))

    MaxPlus.Core.EvalMAXScript("redrawViews()")
    viewID = MaxPlus.RenderSettings.GetViewID()
    logMessage(
        "Rendering camera/view #" + str(viewID) + " '" + str(MaxPlus.ViewportManager.getViewportLabel(viewID)) + "'")

    camFileName = arg.Camera
    camFileName = camFileName.replace(" ", "_")

    if argValid(arg.FPadding):
        arg.FPadding = int(arg.FPadding)
    else:
        arg.FPadding = 4

    arg.ElementsFolder = False  # this works for 3dsmax elements only. And artists are not used to it.
    # if (not argValid(arg.ElementsFolder)):
    #    arg.ElementsFolder=True

    if not argValid(arg.FExt):
        arg.FExt = ""

    if not argValid(arg.FNameVar):
        arg.FNameVar = arg.FName

    arg.FNameVar = arg.FNameVar.replace("<channel>", "<Channel>")
    arg.FNameVar = arg.FNameVar.replace("<camera>", camFileName)
    arg.FNameVar = arg.FNameVar.replace("<Camera>", camFileName)
    arg.FNameVar = arg.FNameVar.replace("<Layer>", arg.StateSetFilename)
    arg.FNameVar = arg.FNameVar.replace("<layer>", arg.StateSetFilename)

    arg.FName = arg.FNameVar
    if arg.FName.find("<Channel>") > 0:
        if any( ch_token in arg.FName for ch_token in ("\\<Channel>\\", "\\<Channel <Channel>>\\") ):
            arg.ElementsFolder = True
            arg.FName = arg.FName.replace("<Channel <Channel>>\\", "")
            arg.FName = arg.FName.replace("<Channel .<Channel>. >", "")
            arg.FName = arg.FName.replace("<Channel .<Channel>.>", "")
            arg.FName = arg.FName.replace("<Channel <Channel>.>", "")
            arg.FName = arg.FName.replace("<Channel>\\", "")
            arg.FName = arg.FName.replace(".<Channel>.", "")
            arg.FName = arg.FName.replace("<Channel>", "")
        else:
            arg.ElementsFolder = False
            arg.FName = arg.FName.replace("<Channel <Channel>>", "")
            arg.FName = arg.FName.replace("<Channel .<Channel>. >", "")
            arg.FName = arg.FName.replace("<Channel .<Channel>.>", "")
            arg.FName = arg.FName.replace("<Channel <Channel>.>", "")
            arg.FName = arg.FName.replace(".<Channel>.", "")
            arg.FName = arg.FName.replace("<Channel>", "")
    else:
        arg.FNameVar = arg.FName
        if arg.ElementsFolder:
            arg.FNameVar = os.path.dirname(arg.FNameVar) + "\\<Channel>\\" + os.path.basename(
                arg.FNameVar) + "<Channel>"
        else:
            arg.FNameVar += "<Channel>"

    arg.FNameVar = arg.FNameVar.replace("<Channel <Channel>>", "<Channel>")
    arg.FNameVar = arg.FNameVar.replace("<Channel .<Channel>. >", ".<Channel>.")
    arg.FNameVar = arg.FNameVar.replace("<Channel .<Channel>.>", ".<Channel>.")
    arg.FNameVar = arg.FNameVar.replace("<Channel <Channel>.>", "<Channel>.")
    arg.FNameVar = arg.FNameVar.replace("..<Channel>.", ".<Channel>.")

    #if (argValid(arg.FNameChannelAdd)):
    #    arg.FName   =arg.FName   +arg.FNameChannelAdd
    #    arg.FNameVar=arg.FNameVar+arg.FNameChannelAdd
    logMessage("Main    output is '" + arg.FName + "' ")
    if arg.AutoElementFileName:
        logMessage("Element output is '" + arg.FNameVar + "' ")
    else:
        logMessage("Element output is taken from scene")

    #if (argValid(arg.IgnoreError)):
        #logMessageSET("Ignore Error to " +str(arg.IgnoreError))
        #MaxPlus.RenderSettings.ShouldContinueOnError(arg.IgnoreError)
    #else:
        #logMessageSET("Ignore Error to True" )
        #MaxPlus.RenderSettings.ShouldContinueOnError(True)

    if argValid(arg.ResX):
        logMessageSET("width to " + str(arg.ResX))
        MaxPlus.RenderSettings.SetWidth(int(arg.ResX))
    if argValid(arg.ResY):
        logMessageSET("height to " + str(arg.ResY))
        MaxPlus.RenderSettings.SetHeight(int(arg.ResY))

    arg.GBufferString = ""
    if argValid(arg.GBuffer) and arg.GBuffer:
        arg.GBufferString = "#zDepth, #UVCoords, #objectID, #normal"

    if not argValid(arg.AutoElementFileName):
        arg.AutoElementFileName = False
    if not argValid(arg.noFrameLoop):
        arg.noFrameLoop = False
    if not argValid(arg.avFrameTime):
        arg.avFrameTime = 0
    else:
        arg.avFrameTime = int(arg.avFrameTime)
    if not argValid(arg.hdrFrameBuffer):
        arg.hdrFrameBuffer = False

    arg.regionEnabled = False
    if (arg.RegionX1 != None) and (len(str(arg.RegionX1)) > 0):
        arg.regionEnabled = True
        arg.RegionX1 = int(arg.RegionX1)
        arg.RegionX2 = int(arg.RegionX2) + 1
        logMessage("region rendering X:  {0}-{1}".format(arg.RegionX1, arg.RegionX2))
        if (arg.RegionY1 != None) and (len(str(arg.RegionY1)) > 0):
            arg.RegionY1 = int(arg.RegionY1)
            arg.RegionY2 = int(arg.RegionY2) + 1
            logMessage("region rendering Y: " + str(arg.RegionY1) + "-" + str(arg.RegionY2))
            logMessage("region rendering Y:  {0}-{1}".format(arg.RegionY1, arg.RegionY2))
        else:
            arg.RegionY1 = 0
            arg.RegionY2 = int(MaxPlus.RenderSettings.GetHeight()) + 1
            logMessage("region rendering Y:  {0}-{1}".format(arg.RegionY1, arg.RegionY2))

    arg.renderChannels = True

    if arg.Renderer == "VRay":
        applyRendererOptions_Vray(arg)
    else:
        applyRendererOptions_default(arg)

    timeEnd = datetime.datetime.now()
    timeEnd = timeEnd - timeStart
    logMessage("Scene load time:  {0}  h:m:s.ms".format(timeEnd))
    logMessage("Scene init done, starting to render... ")

    if (argValid(arg.multiExr) and arg.multiExr):
        logMessageSET("exr settings to Multi-Layer EXR")
        MaxPlus.Core.EvalMAXScript('fopenexr.setAutoAddRenderElements true')
        # enforce 16 bit float exr
        MaxPlus.Core.EvalMAXScript('fopenexr.setLayerOutputFormat 0 1')

    GLOBAL_ARG = arg  # copy for kso render
    if argValid(arg.KSOMode) and arg.KSOMode:
        render_KSO(arg)
    else:
        render_default(arg)

    if showVfb:
        # Leaving Vfb on might prevent exiting
        MaxPlus.RenderSettings.SetShowVFB(False)

    logMessage("Render done")
    logMessage("                                        ")
    logMessage("                                        ")
    logMessage("                                        ")
    logMessage("                                        ")


if __name__ == "__main__":
    try:
        render_main()
    except:
        if not USE_LOGGER:
            # make sure we release "rrMaxRender.log": the .ms script needs to write to it
            closeHandlers(logging.getLogger("rrMax"))
        raise

    MaxPlus.Core.EvalMAXScript("quitmax #noprompt")
