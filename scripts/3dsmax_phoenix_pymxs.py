# Simulation script for 3dsmax
#  %rrVersion%
#  Copyright (c)  Holger Schoenberger - Binary Alchemy

import datetime
import logging
import os
import sys
import time
from pymxs import runtime as rt
try:
    import configparser
except:
    import ConfigParser as configparser

if (sys.version_info.major == 2):
    range = xrange


USE_DEFAULT_PRINT = False
USE_LOGGER = False
LOGGER_ADD_TIME = True
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
    global LOGGER_ADD_TIME
    if LOGGER_ADD_TIME:
        log_format = logging.Formatter("' %(asctime)s %(name)s %(levelname)5s: %(message)s", "%H:%M:%S")
    else:
        log_format = logging.Formatter("' %(name)s %(levelname)5s: %(message)s")

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
        str_handler = logging.StreamHandler(sys.stdout)
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
            rt.flushlog()
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
            for _ in range(num_tries):
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
        except (configparser.NoOptionError, configparser.NoSectionError):
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
        self.config = configparser.RawConfigParser()
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
                
        

   
    
##############################################################################
#MAIN "FUNCTION":
##############################################################################

def simulate_execute():
    cmdLine = ("--If there are selected simulators, use only those\n"
        "PhoenixFDObjectsAll = for o in selection where classof o == LiquidSim or classof o == FireSmokeSim or classof o == PHXSimulator collect o\n"
        "if PhoenixFDObjectsAll.count == 0 do( --Otherwise, use all PhoenixFD simulators\n"
        "PhoenixFDObjectsAll = for o in objects where classof o == LiquidSim or classof o == FireSmokeSim or classof o == PHXSimulator collect o\n"
        ")\n"
        "-- Filter out the hidden particle group nodes from the actual simulators:\n"
        "PhoenixFDObjectsToSim = #()\n"
        "for i=1 to PhoenixFDObjectsAll.count do(\n"
        "    local phxUserPropGroup = getUserProp PhoenixFDObjectsAll[i] \"phxgroupname\"\n"
        "    local phxUserPropSysId = getUserProp PhoenixFDObjectsAll[i] \"phx_system_id\"\n"
        "    if phxUserPropGroup==undefined and phxUserPropSysId==undefined do(\n"
        "    	append PhoenixFDObjectsToSim PhoenixFDObjectsAll[i]\n"
        "	)\n"
        ")\n"
        "-- Start the simulation\n"
        "countString= PhoenixFDObjectsToSim.count as string\n"
        "PhoenixFDObjectsToSimStr= PhoenixFDObjectsToSim as string\n"
        "python.Execute (\"logMessage('Found \" + countString + \" PhoenixFD objects')\")\n"
        "python.Execute (\"logMessage('PhoenixFD objects: \" + PhoenixFDObjectsToSimStr + \" ')\")\n"
        "for i=1 to PhoenixFDObjectsToSim.count do(\n"
        "    currentObjectStr= PhoenixFDObjectsToSim[i] as string\n"
        "    python.Execute (\"logMessage('Starting to simulate \" + currentObjectStr + \" ')\")\n"
        "    A_StartSim(PhoenixFDObjectsToSim[i])\n"
        "    A_Wait(PhoenixFDObjectsToSim[i])\n"
        ")\n"
               )

    rt.execute(cmdLine)


def simulate_main():
    global USE_LOGGER
    global GLOBAL_ARG
    global PRINT_DEBUG
    global LOGGER_ADD_TIME

    logMessageDebug('----------------------startup-----------------')

    GLOBAL_ARG = ArgParser()
    timeStart = datetime.datetime.now()

    arg = ArgParser()
    arg.readArguments()
    if not argValid(arg.logFile):
        arg.logFile = os.path.join(os.environ['TEMP'], "rrMaxRender.log")
    if not argValid(arg.MaxBatchMode):
        arg.MaxBatchMode = False

    USE_LOGGER = False  # it is not possible to use print to stdOut in 3dsmax-batch/-cmd. stdErr is possible, but 3dsmax reports an error in this case
    if USE_LOGGER:
        LOGGER_ADD_TIME = False
        setLogger(log_to_stream=True, log_level=logging.DEBUG if PRINT_DEBUG else logging.INFO)
        logMessageDebug("USE_LOGGER")
    else:
        setLogger(log_file=arg.logFile, log_level=logging.DEBUG if PRINT_DEBUG else logging.INFO)
        logMessageDebug("USE_LOGFILE_PRINT")

    logMessage(os.path.basename(__file__) + "  %rrVersion%")
    if arg.MaxBatchMode:
        logMessage("###########################################################################################")
        logMessage("######################         RENDER IS STARTING FROM NOW           ######################")
        logMessage("###################### IGNORE OLDER MESSAGES ABOUT SCENE AND FRAMES  ######################")
        logMessage("###########################################################################################")

    if argValid(arg.PyModPath):
        sys.path.append(arg.PyModPath)

    logMessage("Loading Scene '" + str(arg.SName) + "'...")
    if not rt.loadMaxFile(str(arg.SName), useFileUnits=True, quiet=True):
        logMessageError("Unable to open scene file")

    if argValid(arg.StateSet):
        stateSet = str(arg.StateSet)
        logMessageSET("pass to '" + stateSet + "'")
        arg.StateSetFilename = arg.StateSet
        arg.StateSetFilename = arg.StateSetFilename.replace("::", "")
        arg.StateSetFilename = arg.StateSetFilename.replace(":", "_")

        if stateSet.startswith("::"):  # we submit State Sets as starting with ::
            logMessageWarn("State Sets not yet supported for Phoenix jobs, please use Scene States if possible")
        else:
            # scene state
            rt.sceneStateMgr.restoreAllParts(arg.StateSet)

        if argValid(arg.RPMPass):
            logMessageSET("RPM pass to '" + str(arg.RPMPass) + "'")
            rt.execute(
                "RPass_nr =0;  for i= 1 to RPMdata.GetPassCount() do  (  if (" + arg.RPMPass + "==RPMdata.GetPassName(i))    then RPass_nr=i  );  if RPass_nr>0    then RPMData.RMRestValues RPass_nr    else quitMax #noPrompt")

    timeEnd = datetime.datetime.now()
    timeEnd = timeEnd - timeStart
    logMessage("Scene load time:  {0}  h:m:s.ms".format(timeEnd))
    logMessage("Scene init done, starting to simulate... ")

    simulate_execute()

    logMessage("Finished simulating... ")


if __name__ == "__main__":
    try:
        simulate_main()
    except:
        if not USE_LOGGER:
            # make sure we release "rrMaxRender.log": the .ms script needs to write to it
            closeHandlers(logging.getLogger("rrMax"))
        raise

