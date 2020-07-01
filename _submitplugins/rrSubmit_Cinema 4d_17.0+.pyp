# -*- coding: cp1252 -*-
######################################################################
#
# Royal Render Plugin script for Cinema R13+
# Author: Paolo Acampora - Binary Alchemy, Holger Schoenberger - Binary Alchemy,  Michael Auerswald - 908video.de
# Last change: %rrVersion%
# Copyright (c)  Holger Schoenberger
# #win:   rrInstall_Copy:         plugins\
# #linux: rrInstall_Copy:         plugins\
# #mac:   rrInstall_Copy:         ..\..\..\plugins\
# #win:   rrInstall_Delete:       plugins\rrSubmit_Cinema 4d_11.0+.cof
# #linux: rrInstall_Delete:       plugins\rrSubmit_Cinema 4d_11.0+.cof
# #mac:   rrInstall_Delete:       ..\..\..\plugins\rrSubmit_Cinema 4d_11.0+.cof
# #win:   rrInstall_Delete:       plugins\rrSubmit_Cinema 4d_13.0+.pyp
# #linux: rrInstall_Delete:       plugins\rrSubmit_Cinema 4d_13.0+.pyp
# #mac:   rrInstall_Delete:       ..\..\..\plugins\rrSubmit_Cinema 4d_13.0+.pyp
# #win:   rrInstall_Delete:       plugins\rrSubmit_Cinema 4d_16.0+.pyp
# #linux: rrInstall_Delete:       plugins\rrSubmit_Cinema 4d_16.0+.pyp
# #mac:   rrInstall_Delete:       ..\..\..\plugins\rrSubmit_Cinema 4d_16.0+.pyp
#
######################################################################

import c4d
from c4d import gui, plugins

import copy
import datetime
import logging
import os
import sys
import tempfile
from subprocess import call
from xml.etree.ElementTree import ElementTree, Element, SubElement


###############################################################################
# To enable tile rendering for sequences as well, set  SHOWTILEDIALOG = True  #
###############################################################################

# NOTE: deprecated, we are now using rrSubmiteer optionsfor tiled rendering
SHOWTILEDIALOG = False
NORRTILE = False  # use command line tiling rather than c4d option
TILES = 1


##############################################
# GLOBAL VARIABLES                           #
##############################################

PLUGIN_ID_ASS = 1038331
PLUGIN_ID_CAM = 1039082
PLUGIN_ID = 1027715


# Arnold plugin constants

# From plugins/C4DtoA/res/c4dtoa_symbols.h
ARNOLD_DRIVER = 1030141
ARNOLD_AOV = 1030369
ARNOLD_SCENE_HOOK = 1032309

# From plugins/C4DtoA/res/description/ainode_driver_exr.h
C4DAIP_DRIVER_EXR_FILENAME  = 1285755954
C4DAIP_DRIVER_EXR_NAME = 55445461

# From plugins/C4DtoA/res/description/arnold_driver.h
C4DAI_DRIVER_TYPE = 101

# From plugins/C4DtoA/api/include/util/NodeIds.h
C4DAIN_DRIVER_EXR = 9504161
C4DAIN_DRIVER_DEEPEXR = 1058716317
C4DAIN_DRIVER_JPEG = 313466666
C4DAIN_DRIVER_PNG = 9492523
C4DAIN_DRIVER_TIFF = 313114887
C4DAIN_DRIVER_C4D_DISPLAY = 1927516736

# plugins/C4DtoA/api/include/util/Constants.h
C4DTOA_MSG_TYPE = 1000
C4DTOA_MSG_GET_VERSION = 1040
C4DTOA_MSG_RESP1 = 2011
C4DTOA_MSG_RESP2 = 2012
C4DTOA_MSG_RESP3 = 2013


##############################################
# GLOBAL LOGGER                              #
##############################################

LOGGER = logging.getLogger('rrSubmit')
# reload plugin creates another handler, so remove all at script start
for h in list(LOGGER.handlers):
    LOGGER.removeHandler(h)
LOGGER.setLevel(logging.INFO)
#LOGGER.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
LOGGER.addHandler(ch)


##############################################
# GLOBAL FUNCTIONS                           #
##############################################

def GetC4DtoAMessage(doc):
    """ Returns the arnold plugin version used for given doc

    :param doc: cinema 4d document
    :return: c4dtoa version as string, "" if no arnold hook is found
    """
    arnoldSceneHook = doc.FindSceneHook(ARNOLD_SCENE_HOOK)
    if arnoldSceneHook is None:
        return
    msg = c4d.BaseContainer()
    msg.SetInt32(C4DTOA_MSG_TYPE, C4DTOA_MSG_GET_VERSION)
    arnoldSceneHook.Message(c4d.MSG_BASECONTAINER, msg)
    return msg


def GetArnoldVersion(doc):
    msg = GetC4DtoAMessage(doc)
    if not msg:
        return ""
    return msg.GetString(C4DTOA_MSG_RESP2)


def GetC4DtoAVersion(doc):
    """Return the arnold plugin version used for given doc

    :param doc: cinema 4d document
    :return: c4dtoa version as string, "" if no arnold hook is found
    """
    msg = GetC4DtoAMessage(doc)
    if not msg:
        return ""
    return msg.GetString(C4DTOA_MSG_RESP1)


def GetRedshiftVersion():
    try:
      import redshift
      return redshift.GetCoreVersion()
    except:
      LOGGER.warning("Error getting RedShift version, perhaps <2.6.23")

      rs_prefs = c4d.plugins.FindPlugin(1036220, c4d.PLUGINTYPE_PREFS)
      if not rs_prefs:
          return ""

      rs_ver = rs_prefs[c4d.PREFS_REDSHIFT_REDSHIFT_VERSION]
      rs_ver = rs_ver.split(" ")[0]  # remove " Demo" or other suffix

      return rs_ver


def GetRedshiftPluginVersion():
    try:
      import redshift
      return redshift.GetPluginVersion()
    except:
        LOGGER.warning("Error getting RedShift plugin version, perhaps <2.6.23")
        rs_prefs = c4d.plugins.FindPlugin(1036220, c4d.PLUGINTYPE_PREFS)
        if not rs_prefs:
            return ""

        plug_ver = rs_prefs[c4d.PREFS_REDSHIFT_PLUGIN_VERSION]
        plug_ver = plug_ver.split(",")[0]

        return plug_ver


def GetOctaneVersion(doc):
    ID_OCTANE_LIVEPLUGIN = 1029499
    bc = doc[ID_OCTANE_LIVEPLUGIN]

    if bc:
        oc_ver = str(bc[c4d.SET_OCTANE_VERSION])
        # format to major.minor.update, i.e. 4000016 is V4.00.0-RC6
        return ".".join((oc_ver[0], oc_ver[1:3] , oc_ver[3]))

    return None


def isWin():
    if c4d.GeGetCurrentOS() == c4d.GE_WIN:
        LOGGER.debug("OS: Windows")
        return True
    elif c4d.GeGetCurrentOS() == c4d.GE_MAC:
        LOGGER.debug("OS: Mac")
        return False
    else:
        LOGGER.warning("OS: not found (this should not happen)")
        return False


def rrGetRR_Root():
    """Return Royal Render directory. Relies on RR_ROOT environment variable,
     or on paths hard coded by rrWorkstationInstaller"""

    if 'RR_ROOT' in os.environ:
        return os.environ['RR_ROOT'].strip("\r")

    if sys.platform.lower() in ("win32", "win64"):
        HCPath = "%RRLocationWin%"
    elif sys.platform.lower() == "darwin":
        HCPath = "%RRLocationMac%"
    else:
        HCPath = "%RRLocationLx%"
    if HCPath[0] != "%":
        return HCPath

    LOGGER.warning("No RR_ROOT environment variable set!\n Please execute rrWorkstationInstaller and restart the machine.")
    return ""


def PD():
    """Return Path Divider for current OS"""
    # NOTE: we can use the os module unless there are reasons to do otherwise: os.sep, and combine with os.path.join
    if sys.platform.lower() in ("win32", "win64"):
        return "\\"
    elif sys.platform.lower() == "darwin":
        return "/"
    else:
        return "/"


##############################################
# UTILITY CLASSES                            #
##############################################

class MultipassInfo(object):
    """Convenience class for storing multipass info:

        channel_name: multipass type used as default name, c4d token: $pass, RR token <Channel_intern>
        channel_description: multipass name set by user, c4d token: $userpass, <Channel_name>

        3d party renderes might not use c4d multipass
    """
    def __init__(self, channel_name, channel_description):
        """

        :param channel_name: multipass type used as default name
        :param channel_description: multipass name set by user
        """
        self.channel_name = channel_name
        self.channel_description = channel_description

    def __nonzero__(self):
        if self.channel_name or self.channel_description:
            return True

        return False


class JobProps(object):
    """Default parameters for the submit jobs
    WARNING: non basic types should rather go in the init function, or they might share changes between jobs"""
    camera = ""
    channel = ""
    CustomA = ""
    CustomB = ""
    CustomC = ""
    height = 99
    width = 99
    imageDir = ""
    imageExtension = ""  # Unused: use imageFormat
    imageFileName = ""  # Unused: use imageName
    imageFormat = ""
    imageFormatID = 0
    imageFormatIDMultiPass = 0
    imageFormatMultiPass = ""
    imageFramePadding = 4
    imageName = ""
    imageNamingID = 0
    imagePreNumberLetter = ""
    imageSingleOutput = False
    imageHeight = 99  # Unused: use height
    imageWidth = 99  # Unused: use width
    isActive = False
    isTiledMode = False
    layer = ""
    layerName = ""
    LocalTexturesFile = ""
    maxChannels = 0
    osString = ""
    preID = ""
    renderer = ""
    RequiredLicenses = ""
    sceneDatabaseDir = ""
    sceneFilename = ""
    sceneName = ""  # Unused: use sceneFilename
    sceneOS = ""  # Unused: use osString
    sendAppBit = ""
    seqEnd = 100
    seqFileOffset = 0
    seqFrameSet = ""
    seqStart = 0
    seqStep = 1
    software = "Cinema 4D"
    version = ""  # Unused: use versionInfo
    versionInfo = ""
    rendererVersion = ""
    Arnold_C4DtoAVersion = ""
    Redshift_C4DtoRSVersion = ""
    waitForPreID = ""
    linearColorSpace = False

    def __init__(self):
        self.channelFileName = []
        self.channelExtension = []


class rrJob(JobProps):
    """Collect job properties from the scene, export xml file"""

    def __init__(self):
        super(rrJob, self).__init__()
        self.clear()

    def clear(self):
        """Set the job attributes to their default values. This will also unlink the inherited static members

        :return: None
        """
        self.channelFileName = []
        self.channelExtension = []
        for attr in dir(JobProps):
            if attr.startswith("__"):
                continue
            val = getattr(JobProps, attr)
            if callable(val):
                continue

            setattr(self, attr, val)

    def indent(self, elem, level=0):
        """Nice xml formatting with proper indent"
        # from infix.se (Filip Solomonsson) #

        :param elem:
        :param level:
        :return: success status
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

    @staticmethod
    def subE(root_element, element_name, text_parameter):
        """Add information parameter to the job xml

        :param root_element: rootElement
        :param element_name: SubmitterParameter
        :param text_parameter: "PARAMETERNAME=" + PARAMETERVALUE_AS_STRING
        :return:
        """
        sub = SubElement(root_element, element_name)
        text_parameter = str(text_parameter)
        text_parameter = unicode(text_parameter, "utf-8")
        sub.text = text_parameter
        return sub

    def writeToXMLstart(self):
        rootElement = Element("rrJob_submitFile")
        rootElement.attrib["syntax_version"] = "6.0"
        self.subE(rootElement, "DeleteXML", "1")
        self.subE(rootElement, "decodeUTF8", "_")
        return rootElement

    def writeToXMLJob(self, rootElement):
        # YOU CAN ADD OTHER NOT SCENE-INFORMATION PARAMETERS USING:
        # self.subE(rootElement, "SubmitterParameter", "PARAMETERNAME=" + PARAMETERVALUE_AS_STRING)
        if self.isTiledMode:
            # NOTE: we have moved Tiled Mode to the rrSubmitter
            self.subE(rootElement, "SubmitterParameter", "TileFrame=0~0")
            self.subE(rootElement, "SubmitterParameter", "PPAssembleTiles=0~1")

        jobElement = self.subE(rootElement, "Job", "")
        self.subE(jobElement, "rrSubmitterPluginVersion", "%rrVersion%")
        self.subE(jobElement, "Software", self.software)
        self.subE(jobElement, "Renderer", self.renderer)
        self.subE(jobElement, "Version", self.versionInfo)
        self.subE(jobElement, "rendererVersion", self.rendererVersion)
        self.subE(jobElement, "customRenVer_Arnold", self.Arnold_C4DtoAVersion)
        self.subE(jobElement, "customRenVer_ArnoldExportAss", self.Arnold_C4DtoAVersion)
        #self.subE(jobElement, "customRenVer_Redshift", self.Redshift_C4DtoRSVersion)
        self.subE(jobElement, "SceneName", self.sceneFilename)
        self.subE(jobElement, "IsActive", self.isActive)
        self.subE(jobElement, "Layer", self.layerName)
        self.subE(jobElement, "Channel", self.channel)
        self.subE(jobElement, "SeqStart", self.seqStart)
        self.subE(jobElement, "SeqEnd", self.seqEnd)
        self.subE(jobElement, "SeqStep", self.seqStep)
        self.subE(jobElement, "ImageWidth", int(self.width))
        self.subE(jobElement, "ImageHeight", int(self.height))
        self.subE(jobElement, "ImageFilename", self.imageName)
        self.subE(jobElement, "ImageFramePadding", self.imageFramePadding)
        self.subE(jobElement, "ImageExtension", self.imageFormat)
        self.subE(jobElement, "SceneOS", self.osString)
        self.subE(jobElement, "Camera", self.camera)
        if self.linearColorSpace:
            self.subE(jobElement, "SubmitterParameter", "PreviewGamma2.2=1~1")
        for c in xrange(0, self.maxChannels):
            self.subE(jobElement, "ChannelFilename", self.channelFileName[c])
            self.subE(jobElement, "ChannelExtension", self.channelExtension[c])
            LOGGER.debug("channel {0}: {1} {2}".format(c, self.channelFileName[c], self.channelExtension[c]))

        # self.subE(jobElement, "preID", self.preID)
        # self.subE(jobElement, "WaitForPreID", self.WaitForPreID)
        return True

    def writeToXMLEnd(self, f, rootElement):
        xml = ElementTree(rootElement)
        self.indent(xml.getroot())

        if not f == None:
            xml.write(f, encoding="utf-8", xml_declaration=True)
            LOGGER.debug("XML written to " + f.name)
            f.close()
        else:
            LOGGER.error("Invalid file for writing XML end")
            try:
                f.close()
            except Exception as e:
                LOGGER.warning("Error writing XML end: " + e.message)
            return False
        return True


##############################################
# CINEMA                                     #
##############################################

class RRDialog(c4d.gui.GeDialog):
    """asks for input when in tiled mode"""
    # Note: we are now using rrSubmitter, this dialog is Unused
    tiles = 1

    def CreateLayout(self):
        self.SetTitle("Tiled RRSubmit %rrVersion%")
        self.GroupBegin(20001, c4d.BFH_SCALEFIT | c4d.BFV_FIT, 2, 0, "")
        self.AddStaticText(0, c4d.BFH_LEFT, 0, 0, "Tiles:", 0)
        self.AddEditNumberArrows(20100, c4d.BFH_LEFT)
        self.GroupEnd()
        self.AddButton(20101, c4d.BFH_SCALE | c4d.BFV_SCALE, 75, 15, "Run")
        self.SetLong(20100, self.tiles, 1, 100)
        return True

    def Command(self, cmd_id, msg):
        global TILES
        if cmd_id == 20100:
            self.tiles = self.GetLong(20100)
        if cmd_id == 20101:
            TILES = self.tiles
            self.Close()
        return True


def setSeq(job, localRenderSettings):
    """gets the beginning, end and step size for the current frame sequence from the render settings"""
    doc = c4d.documents.GetActiveDocument()
    seqMode = localRenderSettings[c4d.RDATA_FRAMESEQUENCE]

    if seqMode == c4d.RDATA_FRAMESEQUENCE_MANUAL:
        startTime = localRenderSettings[c4d.RDATA_FRAMEFROM]
        endTime = localRenderSettings[c4d.RDATA_FRAMETO]
        frameRate = job.frameRateRender
        job.seqStart = startTime.GetFrame(int(frameRate))
        job.seqEnd = endTime.GetFrame(int(frameRate))
    elif seqMode == c4d.RDATA_FRAMESEQUENCE_CURRENTFRAME:
        startTime = localRenderSettings[c4d.RDATA_FRAMEFROM]
        endTime = startTime
        frameRate = job.frameRateRender
        job.seqStart = startTime.GetFrame(int(frameRate))
        job.seqEnd = endTime.GetFrame(int(frameRate))
    elif seqMode == c4d.RDATA_FRAMESEQUENCE_PREVIEWRANGE:
        startTime = doc.GetLoopMinTime()
        endTime = doc.GetLoopMaxTime()
        frameRate = job.frameRateRender
        job.seqStart = startTime.GetFrame(int(frameRate))
        job.seqEnd = endTime.GetFrame(int(frameRate))
    else:
        startTime = doc.GetMinTime()
        endTime = doc.GetMaxTime()
        frameRate = job.frameRateRender
        job.seqStart = startTime.GetFrame(int(frameRate))
        job.seqEnd = endTime.GetFrame(int(frameRate))

    job.seqStep = localRenderSettings[c4d.RDATA_FRAMESTEP]
    if not job.seqStep:
        job.seqStep = 1

    return True


def insertPathTake(img_path):
    """Insert the "$take" token in given image path

    :param img_path: image path
    :return: take sub-path
    """
    return os.path.join(os.path.dirname(img_path), "$take", os.path.basename(img_path))


def duplicateJobsWithNewTake(doc, jobList, take, currentTakeName, takeData):
    """Create a new job with current parameters but different take. Used to submit c4d takes as RR layers

    :param doc: c4d document
    :param jobList: list of current jobs
    :param take: take for the newjob
    :param currentTakeName: name of current take
    :param takeData: takes data of the document
    """

    takeName = take.GetName()
    newJob = copy.deepcopy(jobList[0])
    if "$take" not in newJob.imageName:
        # user has forgotten to add $take, which means you overwrite the same file
        newJob.imageName = insertPathTake(newJob.imageName)
    for ch in xrange(0, newJob.maxChannels):
        if "$take" not in newJob.channelFileName[ch]:
            newJob.channelFileName[ch] = insertPathTake(newJob.channelFileName[ch])

    newJob.imageName = newJob.imageName.replace("$take", takeName)
    newJob.layerName = takeName
    if currentTakeName == takeName:
        newJob.isActive = True
    for ch in range(0, newJob.maxChannels):
        newJob.channelFileName[ch] = newJob.channelFileName[ch].replace("$take", takeName)

    takeData.SetCurrentTake(take)
    rd = doc.GetActiveRenderData()
    setSeq(newJob, rd)

    LOGGER.debug("childTake: " + takeName + "  " + newJob.imageName)
    jobList.append(newJob)


def addTakes_recursiveLoop(doc, jobList, parentTake, currentTakeName, takeData):
    """ Travel all takes looking for job layers

    :param doc: c4d document
    :param jobList: list of RR jobs
    :param parentTake: up-level take
    :param currentTakeName: name of current take
    :param takeData: takes data of the document
    :return: None
    """
    childTake = parentTake.GetDown()
    while childTake is not None:
        duplicateJobsWithNewTake(doc, jobList, childTake, currentTakeName, takeData)
        addTakes_recursiveLoop(doc, jobList, childTake, currentTakeName, takeData)
        childTake = childTake.GetNext()


def addTakes(doc, jobList, takeData):
    """Add takes as RR layer jobs

    :param doc: c4d document
    :param jobList: list of jobs
    :param takeData: document takes data
    :return:
    """
    LOGGER.debug("takeData: " + str(takeData))
    currentTakeName = takeData.GetCurrentTake().GetName()
    mainTake = takeData.GetMainTake()
    addTakes_recursiveLoop(doc, jobList, mainTake, currentTakeName, takeData)

    jobList[0].imageName = jobList[0].imageName.replace("$take", mainTake.GetName())
    jobList[0].layerName = mainTake.GetName()

    for ch in range(0, jobList[0].maxChannels):
        jobList[0].channelFileName[ch] = jobList[0].channelFileName[ch].replace("$take", mainTake.GetName())

    takeData.SetCurrentTake(mainTake)
    rd = doc.GetActiveRenderData()
    setSeq(jobList[0], rd)


class RRSubmitBase(object):
    """Base class for RRSubmit and RRSubmitAssExport"""

    def __init__(self):
        self.isMP = False
        self.renderSettings = None
        self.isMPSinglefile = False
        self.takeData = None

        self.languageStrings = {}
        self.job = [rrJob()]
        self.job[0].clear()

    def submitToRR(self, submitjobs, useConsole, PID=None, WID=None):
        """Write XML Job file into a temporary file, then call the method
         to pass it either to the rrSubmitter or rrSubmitterconsole """

        tmpDir = tempfile.gettempdir()
        xmlObj = submitjobs[0].writeToXMLstart()

        tmpFile = open(tmpDir + os.sep + "rrTmpSubmitC4d.xml", "w")

        if TILES > 1:  # tiled documents
            LOGGER.warning("Tiled document submission from c4d is deprecated")
            LOGGER.debug("tiled documents " + str(TILES))
            doc = c4d.documents.GetActiveDocument()
            filelist = self.saveTiledDocument(doc, TILES, submitjobs[0].sceneFilename)
            for jobLyr in submitjobs:
                jobLyr.isTiledMode = True
                base, ext = os.path.splitext(jobLyr.imageName)
                posMPass= base.find("<ValueVar ")
                if (posMPass>0):
                    ext= base[posMPass:]+ext
                    base= base[:posMPass]
                i = 0
                for f in filelist:
                    LOGGER.debug("tiled document  "+str(f))
                    jobLyr.sceneFilename = f
                    jobLyr.imageName = base + "_tile" + str(i).zfill(2) + ext
                    i += 1
                    junk, rest = os.path.split(f)
                    fname, junk = os.path.splitext(rest)
                    jobLyr.writeToXMLJob(xmlObj)
        else:  # single document
            # Send XML to RR Submitter
            for jobLyr in submitjobs:
                LOGGER.debug("submit job  " + str(jobLyr.imageName))
                jobLyr.writeToXMLJob(xmlObj)

        ret = submitjobs[0].writeToXMLEnd(tmpFile, xmlObj)
        if ret:
            LOGGER.debug("Job written to " + tmpFile.name)
        else:
            LOGGER.warning("There was a problem writing the job file to " + tmpFile.name)
        if useConsole:
            self.submitRRConsole(tmpFile.name, PID, WID)
        else:
            self.submitRR(tmpFile.name)

    def submitRR(self, filename):
        """Call rrSubmit and pass the XML job file as a parameter"""
        c4d.storage.GeExecuteProgram(rrGetRR_Root() + self.getRRSubmitter(), filename)
        return True

    def submitRRConsole(self, filename, PID=None, WID=None):
        """Call rrSubmitterconsole and pass the XML job file as a parameter"""
        if WID is not None:
            #c4d.storage.GeExecuteProgramEx(rrGetRR_Root() + self.getRRSubmitterConsole(), filename + " -PreID " + PID + " -WaitForID " + WID)
            call([rrGetRR_Root + self.getRRSubmitterConsole(), filename, "-PID", PID, "-WID", WID])
        elif PID is not None:
            #c4d.storage.GeExecuteProgramEx(rrGetRR_Root() + self.getRRSubmitterConsole(), filename + " -PreID " + PID)
            call([rrGetRR_Root + self.getRRSubmitterConsole(), filename, "-PID", PID])
        else:
            c4d.storage.GeExecuteProgram(rrGetRR_Root() + self.getRRSubmitterConsole(), filename)
        return True

    def getRRSubmitter(self):
        """Return the rrSubmitter executable"""
        if isWin() == True:
            rrSubmitter = "\\win__rrSubmitter.bat"
        else:
            rrSubmitter = "/bin/mac64/rrSubmitter.app/Contents/MacOS/startlocal.sh"
        return rrSubmitter

    def getRRSubmitterConsole(self):
        """Return the rrSubmitterconsole filename"""
        if isWin() == True:
            rrSubmitterConsole = "\\bin\\win64\\rrSubmitterconsole.exe"
        else:
            rrSubmitterConsole = "/bin/mac64/rrSubmitterConsole.app/Contents/MacOS/startlocal.sh"
        return rrSubmitterConsole


class RRSubmit(RRSubmitBase, c4d.plugins.CommandData):
    """Launch rrSubmitter for rrJob of current scene. The same class is used for multicamera mode"""
    hasAlpha = False
    isRegular = False
    objectChannelID = 0

    def __init__(self, multi_cam=False):
        super(RRSubmit, self).__init__()
        self.multiCameraMode = multi_cam

    def setImageFormat(self):
        """evaluates the image format extension from the currently selected render settings"""
        if self.isRegular:
            self.job[0].imageFormatID = self.renderSettings[c4d.RDATA_FORMAT]
        else:
            self.job[0].imageFormatID = self.renderSettings[c4d.RDATA_MULTIPASS_SAVEFORMAT]

        img_formats = {
            c4d.FILTER_TIF: ".tif",
            c4d.FILTER_PNG: ".png",
            c4d.FILTER_IES: ".ies",
            c4d.FILTER_PSB: ".psb",
            c4d.FILTER_EXR: ".exr",
            c4d.FILTER_DPX: ".dpx",
            c4d.FILTER_TGA: ".tga",
            c4d.FILTER_BMP: ".bmp",
            c4d.FILTER_IFF: ".iff",
            c4d.FILTER_JPG: ".jpg",
            c4d.FILTER_PICT: ".pict",
            c4d.FILTER_PSD: ".psd",
            c4d.FILTER_RLA: ".rla",
            c4d.FILTER_RPF: ".rpf",
            c4d.FILTER_B3D: ".b3d",
            c4d.FILTER_TIF_B3D: ".tif",
            c4d.FILTER_HDR: ".hdr",
            # c4d.FILTER_QTVRSAVER_PANORAMA: ".qtvr",
            # c4d.FILTER_QTVRSAVER_OBJECT: ".qtvr",
            1785737760: ".jp2",
            1903454566: ".mov",
            c4d.FILTER_MOVIE: ".mov",
            c4d.FILTER_AVI: ".avi",
            # Multipass file types
            1035823: ".exr",
            1016606: ".exr",
            1023737: ".dpx",
            777209673: ".sgi"
        }

        try:
            self.job[0].imageFormat = img_formats[self.job[0].imageFormatID]
        except KeyError:
            self.job[0].imageFormat = ".exr"
            LOGGER.error("Unknown File Format: " + str(self.job[0].imageFormatID))

        if self.job[0].imageFormat in (".mov", ".avi"):
            self.job[0].imageSingleOutput = True
            LOGGER.debug("SingleOutput: yes")
        else:
            LOGGER.debug("SingleOutput: no")

        self.job[0].imageFormatIDMultiPass = self.renderSettings[c4d.RDATA_MULTIPASS_SAVEFORMAT]
        try:
            self.job[0].imageFormatMultiPass = img_formats[self.job[0].imageFormatIDMultiPass]
        except KeyError:
            LOGGER.error("Unknown File Format Multi Pass: " + str(self.job[0].imageFormatIDMultiPass))
            self.job[0].imageFormatMultiPass = ".exr"

        colorProfile = self.renderSettings[c4d.RDATA_IMAGECOLORPROFILE]
        if colorProfile.HasProfile() and colorProfile.GetInfo(0) == colorProfile.GetDefaultLinearRGB().GetInfo(0):
            self.job[0].linearColorSpace = True

        return True

    def getNameFormat(self, imagefilename, imageformat):
        if self.job[0].imageNamingID == c4d.RDATA_NAMEFORMAT_0:
            # name0000.ext
            imageformat = imageformat
        elif self.job[0].imageNamingID == c4d.RDATA_NAMEFORMAT_1:
            # name0000
            imageformat = ""
        elif self.job[0].imageNamingID == c4d.RDATA_NAMEFORMAT_2:
            # name.0000
            self.job[0].imageFormat = ""
            imageformat += "."
        elif self.job[0].imageNamingID == c4d.RDATA_NAMEFORMAT_3:
            # name000.ext
            imageformat = imageformat
        elif self.job[0].imageNamingID == c4d.RDATA_NAMEFORMAT_4:
            # name000
            imageformat = ""
        elif self.job[0].imageNamingID == c4d.RDATA_NAMEFORMAT_5:
            # name.0000
            imageformat = ""
            imagefilename += "."
        elif self.job[0].imageNamingID == c4d.RDATA_NAMEFORMAT_6:
            # name.0000.ext
            imagefilename += "."
        if ((len(imagefilename) > 0) and imagefilename[-1].isdigit()):
            imagefilename += "_"
        elif ((len(imagefilename) > 3) and imagefilename[-1]==">" and imagefilename[-2]=="@" and imagefilename[-3].isdigit()):
            imagefilename = imagefilename[ :-2] + "_" + imagefilename[-2:]

        return imagefilename, imageformat

    def getChannelName(self, pass_type, display_name):
        """Return nice name for c4d pass type id

        :param pass_type: c4d pass type id
        :param display_name: UI name
        :return:
        """
        type_channel_names = {
            c4d.VPBUFFER_TRANSPARENCY: "refr",
            c4d.VPBUFFER_RADIOSITY: "gi",
            c4d.VPBUFFER_ATMOSPHERE: "atmos",
            c4d.VPBUFFER_ATMOSPHERE_MUL: "atmosmul",
            c4d.VPBUFFER_MAT_COLOR: "matcolor",
            c4d.VPBUFFER_MAT_DIFFUSION: "matdif",
            c4d.VPBUFFER_MAT_LUMINANCE: "matlum",
            c4d.VPBUFFER_MAT_TRANSPARENCY: "mattrans",
            c4d.VPBUFFER_MAT_REFLECTION: "matrefl",
            c4d.VPBUFFER_MAT_ENVIRONMENT: "matenv",
            c4d.VPBUFFER_MAT_SPECULAR: "matspec",
            c4d.VPBUFFER_MAT_SPECULARCOLOR: "matspeccol",
            c4d.VPBUFFER_ILLUMINATION: "illum",
            c4d.VPBUFFER_MOTIONVECTOR: "motion",
            c4d.VPBUFFER_RGBA: "rgba" if self.hasAlpha else "rgb"
        }

        try:
            return type_channel_names[pass_type]
        except KeyError:
            for key, val in self.languageStrings.items():
                if val == display_name:
                    return str(key)

        pass_type_names = {
            getattr(c4d, attr): attr.rsplit("_", 1)[1].lower() for attr in dir(c4d) if attr.startswith("VPBUFFER_")
            }

        return pass_type_names.get(pass_type, "")

    def getChannelNameMP(self, MP):
        """Return channel name for given MP

        :param MP: c4d MultiPass
        :return: Channel name
        """
        displayName = MP.GetName()

        if self.renderSettings[c4d.RDATA_MULTIPASS_USERNAMES]:
            return displayName

        passType = MP[c4d.MULTIPASSOBJECT_TYPE]

        if passType == c4d.VPBUFFER_OBJECTBUFFER:
            return "object_" + str(MP[c4d.MULTIPASSOBJECT_OBJECTBUFFER])

        return self.getChannelName(passType, displayName)

    def getChannelNameExt(self, channelName, channelDescription):
        """Return filename and file extension for given channel name and description

        :param channelName: name of the channel
        :param channelDescription: nice format for channel type
        :return: filename, fileextension
        """
        imageName = self.job[0].imageName

        if len(channelName) < 2:
            return "", ""

        if "<Channel_" in imageName:  # <Channel_intern>, <Channel_name>
            filenameComb = imageName.replace("<Channel_intern>", channelName)
            filenameComb = filenameComb.replace("<Channel_name>", channelDescription)
        elif self.renderSettings[c4d.RDATA_MULTIPASS_SUFFIX]:
            # if imageName.rstrip("<IMS>").endswith("_"):
            #     filenameComb = imageName + channelName
            # else:
            #    filenameComb = imageName + "_" + channelName
            filenameComb = imageName + "_" + channelName
        else:
            filedir, filename = os.path.split(imageName)
            # if filename.startswith("_"):
            #     filenameComb = channelName + filename
            # else:
            #     filenameComb = channelName + "_" + filename
            filenameComb = channelName + "_" + filename
            filenameComb = os.path.join(filedir, filenameComb)

        fileext = self.job[0].imageFormatMultiPass
        filenameComb, fileext = self.getNameFormat(filenameComb, fileext)

        return filenameComb, fileext

    def addChannel(self, channelName, channelDescription):
        """Add given channel to the job

        :param channelName: channel name
        :param channelDescription: nice name for channel type
        :return: None
        """
        filenameComb, fileext = self.getChannelNameExt(channelName, channelDescription)

        self.job[0].channelExtension.append(fileext)
        self.job[0].channelFileName.append(filenameComb)
        self.job[0].maxChannels = self.job[0].maxChannels + 1

    def addChannelMultipass(self, MP):
        """Add channel for given MultiPass

        :param MP: c4d multipass
        :return: None
        """
        channelName = self.getChannelNameMP(MP)
        channelDescription = MP.GetName().replace(" ", "_")

        self.addChannel(channelName, channelDescription)

    def addChannelsOctane(self, mainMP):
        """Add channels for Octane render passes and populate mainMP if empty. Return the number of Octane channels"""

        _vp = self.renderSettings.GetFirstVideoPost()
        oc_vp = None  # Octane VideoPost

        while _vp:
            if _vp.CheckType(1029525):  # Octane ID
                oc_vp = _vp
                break
            _vp = _vp.GetNext()

        if not oc_vp:
            return 0

        if not oc_vp[c4d.SET_PASSES_ENABLED]:
            return 0

        if not mainMP and c4d.GetC4DVersion() < 20000:
            # octane writes rgb or rgba image when multipass is enabled
            mainMP.channel_name = "rgba" if self.hasAlpha else "rgb"
            mainMP.channel_description = mainMP.channel_name

        pass_formats = (
            None,
            '.tif',
            '.psd',
            '.exr',
            '.jpg',
            '.tga',
            '.png',
            '.psb',
            '.exr',  # octane exr
        )

        # order of passes is important, as octane will append an index number to the pass name
        diffuse_passes = ["SET_PASSES_DIFFUSE", "SET_PASSES_DIF_D", "SET_PASSES_DIF_I", "SET_PASSES_DIF_FILTER"]
        oc_passes = [
            "SET_PASSES_SAVE_MAINPASS",
            # layer group
            "SET_PASSES_LAYERREFL", "SET_PASSES_COLORSHD", "SET_PASSES_BLACKSHD",
            # beauty group
            "SET_PASSES_DIFFUSE", "SET_PASSES_DIF_D", "SET_PASSES_DIF_I", "SET_PASSES_DIF_FILTER",

            "SET_PASSES_SSS", "SET_PASSES_TRANSM_FILTER", "SET_PASSES_TRANS", "SET_PASSES_REFRACT_FILTER",
            "SET_PASSES_REFRACT", "SET_PASSES_REFLECTION", "SET_PASSES_REFL_D", "SET_PASSES_REFL_I",
            "SET_PASSES_REFL_FILTER", "SET_PASSES_POST", "SET_PASSES_ENV", "SET_PASSES_EMIT", "SET_PASSES_SHADOW",
            "SET_PASSES_NOISE", "SET_PASSES_VOLUME", "SET_PASSES_VOLUME_EMISSION", "SET_PASSES_VOLUME_MASK",
            "SET_PASSES_VOLUME_Z_DEPTH_BACK", "SET_PASSES_VOLUME_Z_DEPTH_FRONT",
            "SET_PASSES_IRRADIANCE", "SET_PASSES_LIGHT_DIRECTION",
            #denoise group
            "SET_PASSES_BEAUTY_DENOISER", "SET_PASSES_DENOISER_DIFFUSE_D", "SET_PASSES_DENOISER_DIFFUSE_I",
            "SET_PASSES_DENOISER_REFLECT_D", "SET_PASSES_DENOISER_REFLECT_I", "SET_PASSES_DENOISER_REMAINDER",
            "SET_PASSES_DENOISER_EMISSION", "SET_PASSES_DENOISER_VOLUME", "SET_PASSES_DENOISER_VOL_EMIS",
            # info group
            "SET_PASSES_AO", "SET_PASSES_WIRE", "SET_PASSES_RENDER_LAYER_MASK", "SET_PASSES_RENDER_LAYER_ID",
            "SET_PASSES_LIGHT_PASS_ID", "SET_PASSES_BAKEGROUP_ID", "SET_PASSES_OBJ_LAYERCOLOR_ID", "SET_PASSES_OBJID",
            "SET_PASSES_MATID", "SET_PASSES_MOT_VECTOR", "SET_PASSES_TEX_TANGENT", "SET_PASSES_UV_COORD",
            "SET_PASSES_POSITION", "SET_PASSES_ZDEPTH", "SET_PASSES_TANGENT", "SET_PASSES_SHDNORM",
            "SET_PASSES_VTXNORM", "SET_PASSES_GEONORM",
            # filter group
            "SET_PASSES_INFO_OPACITY", "SET_PASSES_INFO_ROUGHNESS", "SET_PASSES_INFO_IOR", "SET_PASSES_INFO_DIFFUSE",
            "SET_PASSES_INFO_REFLECTION", "SET_PASSES_INFO_REFRACTION", "SET_PASSES_INFO_TRANSMISSON",
            # mask group
            "VP_PASSES_RL_MASK1", "VP_PASSES_RL_MASK2", "VP_PASSES_RL_MASK3", "VP_PASSES_RL_MASK4",
            "VP_PASSES_RL_MASK5", "VP_PASSES_RL_MASK6", "VP_PASSES_RL_MASK7", "VP_PASSES_RL_MASK8",
            "VP_PASSES_RL_MASK9", "VP_PASSES_RL_MASK10", "VP_PASSES_RL_MASK11", "VP_PASSES_RL_MASK12",
            "VP_PASSES_RL_MASK13", "VP_PASSES_RL_MASK14", "VP_PASSES_RL_MASK15", "VP_PASSES_RL_MASK16",
            "VP_PASSES_RL_MASK17", "VP_PASSES_RL_MASK18", "VP_PASSES_RL_MASK19", "VP_PASSES_RL_MASK20",
            "VP_PASSES_RL_MASK21", "VP_PASSES_RL_MASK22", "VP_PASSES_RL_MASK23", "VP_PASSES_RL_MASK24",
            # materials group
            "SET_LIGHTPASS_8", "SET_LIGHTPASS_8_D", "SET_LIGHTPASS_8_I",
            "SET_LIGHTPASS_7", "SET_LIGHTPASS_7_D", "SET_LIGHTPASS_7_I",
            "SET_LIGHTPASS_6", "SET_LIGHTPASS_6_D", "SET_LIGHTPASS_6_I",
            "SET_LIGHTPASS_5", "SET_LIGHTPASS_5_D", "SET_LIGHTPASS_5_I",
            "SET_LIGHTPASS_4", "SET_LIGHTPASS_4_D", "SET_LIGHTPASS_4_I",
            "SET_LIGHTPASS_3", "SET_LIGHTPASS_3_D", "SET_LIGHTPASS_3_I",
            "SET_LIGHTPASS_2", "SET_LIGHTPASS_2_D", "SET_LIGHTPASS_2_I",
            "SET_LIGHTPASS_1", "SET_LIGHTPASS_1_D", "SET_LIGHTPASS_1_I",
            "SET_LIGHTPASS_SUNLIGHT", "SET_LIGHTPASS_SUNLIGHT_D", "SET_LIGHTPASS_SUNLIGHT_I",
            "SET_LIGHTPASS_AMBIENT", "SET_LIGHTPASS_AMBIENT_D", "SET_LIGHTPASS_AMBIENT_I",
        ]

        oc_pass_names = dict(
            SET_PASSES_SAVE_MAINPASS=("", "Main"),
            SET_PASSES_LAYERREFL=("layer reflection", "LRef"), SET_PASSES_COLORSHD=("colored shadows", "LCSh"),
            SET_PASSES_BLACKSHD=("black shadows", "LBSh"),

            SET_PASSES_DIFFUSE=("diffuse", "Dif"), SET_PASSES_DIF_D=("diffuse direct", "DifD"),
            SET_PASSES_DIF_I=("diffuse indirect", "DifI"), SET_PASSES_DIF_FILTER=("diffuse filter", "DiffFi"),
            SET_PASSES_REFLECTION=("reflection", "Ref"),
            SET_PASSES_REFL_D=("reflection direct", "RefD"), SET_PASSES_REFL_I=("reflection indirect", "RflFi"),
            SET_PASSES_REFL_FILTER=("reflection filter", "RflFi"), SET_PASSES_REFRACT=("refraction", "Refr"),
            SET_PASSES_REFRACT_FILTER=("refraction filter", "RflFi"), SET_PASSES_TRANS=("transmission", "Tran"),
            SET_PASSES_TRANSM_FILTER=("transmission filter", "TraFi"),

            SET_PASSES_EMIT=("emit", "Emit"), SET_PASSES_ENV=("environment", "Env"), SET_PASSES_SSS=("sss", "SSS"),
            SET_PASSES_POST=("post", "Post"), SET_PASSES_SHADOW=("shadow", "Shdw"), SET_PASSES_IRRADIANCE=("", "Irr"),
            SET_PASSES_LIGHT_DIRECTION=("", "LiDir"), SET_PASSES_VOLUME=("volume", "Vol"),
            SET_PASSES_VOLUME_MASK=("volume mask", "VolMa"), SET_PASSES_VOLUME_EMISSION=("volume emission", "VolEmit"),
            SET_PASSES_VOLUME_Z_DEPTH_FRONT=("volume z-depth front", "VolZFr"),
            SET_PASSES_VOLUME_Z_DEPTH_BACK=("volume z-depth back", "VolZbk"), SET_PASSES_NOISE=("noise", "Noise"),

            SET_PASSES_AO=("ao", "AO"), SET_PASSES_WIRE=("wireframe", "Wire"),
            SET_PASSES_RENDER_LAYER_MASK=("render layer mask", "RLMa"),
            SET_PASSES_RENDER_LAYER_ID=("render layer id", "RLID"), SET_PASSES_LIGHT_PASS_ID=("light pass id", "LPid"),
            SET_PASSES_BAKEGROUP_ID=("baking group id", "BGid"), SET_PASSES_OBJ_LAYERCOLOR_ID=("object color id", "OCol"),
            SET_PASSES_OBJID=("objectid", "OID"), SET_PASSES_MATID=("matid", "MID"),
            SET_PASSES_MOT_VECTOR=("motion vector", "MV"), SET_PASSES_TEX_TANGENT=("texture tangent", ""),
            SET_PASSES_UV_COORD=("uv", "UV"), SET_PASSES_POSITION=("position", "Pos"),
            SET_PASSES_ZDEPTH=("z-depth", "Z"), SET_PASSES_TANGENT=("tangent normal", "Tang"),
            SET_PASSES_SHDNORM=("shading normal", "ShN"), SET_PASSES_VTXNORM=("vertex normal", "SmN"),
            SET_PASSES_GEONORM=("geometric normal", "GN"),

            SET_PASSES_BEAUTY_DENOISER=("denoised beauty", "DeMain"),
            SET_PASSES_DENOISER_DIFFUSE_D=("denoised diffuse direct", "DeDifD"),
            SET_PASSES_DENOISER_DIFFUSE_I=("denoised diffuse indirect", "DeDifI"),
            SET_PASSES_DENOISER_REFLECT_D=("denoised reflection direct", "DeRefD"),
            SET_PASSES_DENOISER_REFLECT_I=("denoised reflection indirect", "DeRefI"),
            SET_PASSES_DENOISER_REMAINDER=("denoised remainder", "DeRem"),
            SET_PASSES_DENOISER_EMISSION=("denoised emission", "DeEmit"),
            SET_PASSES_DENOISER_VOLUME=("denoised volume", "DeVol"),
            SET_PASSES_DENOISER_VOL_EMIS=("denoised volume emission", "DeVolE"),

            SET_LIGHTPASS_SUNLIGHT=("sun light", "SLi"),
            SET_LIGHTPASS_SUNLIGHT_D=("sun light direct", "SLiD"),
            SET_LIGHTPASS_SUNLIGHT_I=("sun light indirect", "SLiI"),
            SET_LIGHTPASS_AMBIENT=("ambient light", "ALi"),
            SET_LIGHTPASS_AMBIENT_D=("ambient light direct", "ALiD"),
            SET_LIGHTPASS_AMBIENT_I=("ambient light indirect", "ALiI"),

            SET_PASSES_INFO_OPACITY=("opacity filter", "Op"), SET_PASSES_INFO_ROUGHNESS=("roughness filter", "Ro"),
            SET_PASSES_INFO_IOR=("ior filter", "Ior"), SET_PASSES_INFO_DIFFUSE=("diffuse filter", "DifF"),
            SET_PASSES_INFO_REFLECTION=("reflection filter", "RflFi"),
            SET_PASSES_INFO_REFRACTION=("refraction filter", "RfrFi"),
            SET_PASSES_INFO_TRANSMISSON=("transmission filter", "TraFi"),
        )

        use_subfolder = bool(oc_vp[c4d.SET_PASSES_MAKEFOLDER])
        use_c4d_path = bool(oc_vp[c4d.SET_PASSES_SHOWPASSES])
        use_multi_layer = bool(oc_vp[c4d.SET_PASSES_MULTILAYER])
        passes_path = self.handleRelativeFileOut(oc_vp[c4d.SET_PASSES_SAVEPATH])
        passes_dir, passes_fname = os.path.split(passes_path)
        passes_ext = pass_formats[oc_vp[c4d.SET_PASSES_FILEFORMAT]]
        pass_sep = oc_vp[c4d.SET_PASSES_SEPERATOR]

        num_channels = 0
        num_channels_idx = 1

        nondiffuse_main = False
        for oc_pass in oc_passes:
            try:
                pass_enabled = oc_vp[getattr(c4d, oc_pass)]
            except AttributeError:
                LOGGER.debug("pass not found " + oc_pass)
                continue
            else:
                if not pass_enabled:
                    continue

            added = False

            try:
                nice_name, short_name = oc_pass_names[oc_pass]
            except KeyError:
                if oc_pass.startswith("VP_PASSES_RL_MASK"):
                    mask_id = oc_pass.strip("VP_PASSES_RL_MASK")
                    short_name = "RLMa" + pass_sep + mask_id
                    nice_name = "objmaskid" + mask_id
                elif oc_pass.startswith("SET_LIGHTPASS_"):
                    mask_id = oc_pass.lstrip("SET_LIGHTPASS_")
                    try:
                        mask_id, suffix = mask_id.rsplit("_", 1)
                        nice_suffix = " direct" if suffix == "D" else " indirect"
                    except ValueError:
                        suffix = ""
                        nice_suffix = ""

                    short_name = "Li" + mask_id + suffix  # e.g. "Li1", "Li2", "Li2D" etc...
                    nice_name = "light pass " + mask_id + nice_suffix

            if use_c4d_path and nice_name:
                nice_name = "{0}_{1}".format(nice_name, num_channels_idx)
                if not mainMP:
                    mainMP.channel_name = nice_name
                    mainMP.channel_description = mainMP.channel_name
                    if oc_pass not in diffuse_passes:
                        nondiffuse_main = True
                elif nondiffuse_main and oc_pass in diffuse_passes:
                    # we want a diffuse or beauty pass as main output, for better previews
                    self.addChannel(mainMP.channel_name, mainMP.channel_description)
                    mainMP.channel_name = nice_name
                    mainMP.channel_description = mainMP.channel_name
                    nondiffuse_main = False
                else:
                    self.addChannel(nice_name, nice_name)
                    num_channels += 1

                num_channels_idx += 1
                added = True  # passes not added here can be rendered to passes_path

            if not passes_path:
                # if passes_path is not set, renderpasses will not be saved
                continue
            if not short_name:
                # if a short name is not available, the renderpass will not be saved
                continue
            if use_multi_layer:
                # if renderpass multilayer output is enabled we are not saving a file for each pass
                continue

            pass_fname = passes_fname + pass_sep + short_name + pass_sep
            # NOTE: Octane renderpasses don't follow c4d name format and padding

            if use_subfolder:
                pass_path = os.path.join(passes_dir, short_name, pass_fname)
            else:
                pass_path = os.path.join(passes_dir, pass_fname)

            self.job[0].channelExtension.append(passes_ext)
            self.job[0].channelFileName.append(pass_path)
            self.job[0].maxChannels += 1
            if not added:
                num_channels += 1
                added = True

        if use_multi_layer and passes_path:
            self.job[0].channelExtension.append(passes_ext)
            self.job[0].channelFileName.append(passes_path)
            self.job[0].maxChannels += 1
            num_channels += 1

        return num_channels

    def addChannelsArnold(self, mainMP):
        """Add channels for arnold AOVs and populates mainMP if empty. Return the number of Arnold channels"""
        # TODO: if multipass username, will keep uppercases
        doc = c4d.documents.GetActiveDocument()
        ob = doc.GetFirstObject()
        elems = []

        # these passes are not displayed in the picture viewer
        display_skips_passes = ("beauty", "crypto_asset", "crypto_material", "crypto_object")

        display_driver_found = False
        while ob:
            type_id = ob.GetType()
            if type_id == ARNOLD_DRIVER:

                if ob[c4d.ID_BASEOBJECT_GENERATOR_FLAG] == 0:
                    # not enabled in c4d
                    ob = ob.GetNext()
                    continue

                if ob[c4d.C4DAI_DRIVER_ENABLE_AOVS] == 0:
                    ob = ob.GetNext()
                    continue

                if ob[c4d.C4DAI_DRIVER_TYPE] == C4DAIN_DRIVER_C4D_DISPLAY:
                    if display_driver_found:
                        print 'Warning: only one AOV driver of type "display" is considered by c4dtoa'
                        ob = ob.GetNext()
                        continue

                    display_driver_found = True
                    if not mainMP:
                        mainMP.channel_name = "rgb"
                        mainMP.channel_description = "rgb"

                        elems.append("alpha")
                else:
                    # TODO
                    LOGGER.warning('AOV driver "{0}" skipped: only driver of type "display" is considered at the moment'.format(ob.GetName()))
                    ob = ob.GetNext()
                    continue

                aov = ob.GetDown()
                while aov:
                    if aov[c4d.ID_BASEOBJECT_GENERATOR_FLAG] == 0:
                        aov = aov.GetNext()
                        continue
                    if aov[c4d.C4DAI_AOV_RENDER_AOV] == 0:
                        aov = aov.GetNext()
                        continue

                    aov_name = aov.GetName()
                    if aov[c4d.C4DAI_AOV_USE_CUSTOM_LAYER_NAME] == 1:
                        # TODO: Custom name is used with drivers of type other than c4d_display
                        LOGGER.warning("Custom name is ignored for aov " + aov_name)

                    if aov[c4d.C4DAI_AOV_USE_CUSTOM_PATH] == 1:
                        # TODO: Custom path is used with drivers of type other than c4d_display.
                        # It has to include hashes for frame numbers `#` in case of animations,
                        # otherwise each frame will overwrite the others
                        LOGGER.warning("Custom path is ignored for aov " + aov_name)

                    if aov_name in display_skips_passes:
                        # the c4d display driver doesn't render some passes
                        LOGGER.debug("Skipping aov " + aov_name + ": not considered with displaydriver")
                        aov = aov.GetNext()
                        continue

                    elems.append(aov_name)
                    aov = aov.GetNext()

            ob = ob.GetNext()

        if not elems:
            return 0

        for i, elem in enumerate(elems):
            descr_name = elem.replace(" ", "_")
            pass_name = "{0}_{1}".format(descr_name.lower(), i + 1)

            self.addChannel(pass_name, descr_name)

        return len(elems)

    def addChannelsRedshift(self, mainMP):
        """Add channels for redshift AOVs and populates mainMP if empty. Return the number of Redshift channels"""
        _vp = self.renderSettings.GetFirstVideoPost()
        rs_vp = None  # Redshift VideoPost

        while _vp:
            if _vp.CheckType(1036219):  # Redshift ID
                rs_vp = _vp
                break
            _vp = _vp.GetNext()

        if not rs_vp:
            return 0

        num_AOV = rs_vp[c4d.REDSHIFT_RENDERER_AOV_COUNT]
        LOGGER.debug("found {0} Redshift AOVs".format(num_AOV))

        if not num_AOV:
            return 0

        # aov_types: {type_id: type_name}
        aov_types = {getattr(c4d, attr): attr for attr in dir(c4d) if attr.startswith("REDSHIFT_AOV_TYPE_")}

        aov_formats = {
            c4d.REDSHIFT_AOV_FILE_FORMAT_JPEG: ".jpg",
            c4d.REDSHIFT_AOV_FILE_FORMAT_OPENEXR: ".exr",
            c4d.REDSHIFT_AOV_FILE_FORMAT_PNG: ".png",
            c4d.REDSHIFT_AOV_FILE_FORMAT_TGA: ".tga",
            c4d.REDSHIFT_AOV_FILE_FORMAT_TIFF: ".tif"
        }

        # aov_names: {type_id: type_default_name}
        # some default names are not the nice name: Depth -> Z, Normals -> N...
        aov_names = {
            c4d.REDSHIFT_AOV_TYPE_WORLD_POSITION: "P",
            c4d.REDSHIFT_AOV_TYPE_DEPTH: "Z",
            c4d.REDSHIFT_AOV_TYPE_OBJECT_ID: "ID",
            c4d.REDSHIFT_AOV_TYPE_SUB_SURFACE_SCATTER: "SSS",
            c4d.REDSHIFT_AOV_TYPE_SUB_SURFACE_SCATTER_RAW: "SSSRaw",
            c4d.REDSHIFT_AOV_TYPE_GLOBAL_ILLUMINATION: "GI",
            c4d.REDSHIFT_AOV_TYPE_GLOBAL_ILLUMINATION_RAW: "GIRaw",
            c4d.REDSHIFT_AOV_TYPE_AMBIENT_OCCLUSION: "AO",
            c4d.REDSHIFT_AOV_TYPE_NORMALS: "N",
            c4d.REDSHIFT_AOV_TYPE_TRANSLUCENCY_LIGHTING_RAW: "TransLightingRaw",
            c4d.REDSHIFT_AOV_TYPE_TRANSLUCENCY_FILTER: "TransTint",
            c4d.REDSHIFT_AOV_TYPE_TRANSLUCENCY_GI_RAW: "TransGIRaw",
            c4d.REDSHIFT_AOV_TYPE_OBJECT_SPACE_POSITIONS: "ObjectPosition",
            c4d.REDSHIFT_AOV_TYPE_OBJECT_SPACE_BUMP_NORMALS: "ObjectBumpNormal"
        }

        use_c4d_names = rs_vp[c4d.REDSHIFT_RENDERER_AOV_MULTIPASS_COMPATIBILITY]

        aov_c4d_names = {
            c4d.REDSHIFT_AOV_TYPE_DEPTH: "depth",
            c4d.REDSHIFT_AOV_TYPE_MOTION_VECTORS: "motion"
        }

        ID_CUSTOM_UI_AOV = 1036235  # Redshift AOVs ID

        # AOV can use these tokens
        img_dir, img_name = os.path.split(os.path.normpath(self.job[0].imageName))
        scn_dir, scn_name = os.path.split(os.path.normpath(self.job[0].sceneFilename))
        scn_name, _ = os.path.splitext(scn_name)
        img_dir += os.sep
        scn_dir += os.sep

        rs_name_idx = 1  # redshift appends an aov index to the aov multipass name
        aov_channels = 0 # 'enabled' and at least one between 'multipass' and 'direct' must be checked
        for i in xrange(num_AOV):
            added_to_channels = False
            aov_idx = c4d.REDSHIFT_RENDERER_AOV_LAYER_FIRST + i

            # we are going to query the Redshift UI container for
            # AOVs attributes via GetParameter()
            # GetParameter needs to be pointed to the correct SubGroup level
            # rs_vp[aov_idx, c4d.REDSHIFT_ATTR_KEY] can work too,
            # but not in all cases

            aov_attrs = c4d.DescLevel(aov_idx, ID_CUSTOM_UI_AOV, 0)
            aov_param = c4d.DescLevel(c4d.REDSHIFT_AOV_ENABLED, c4d.DTYPE_BOOL, 0)
            enabled = rs_vp.GetParameter(c4d.DescID(aov_attrs, aov_param), c4d.DESCFLAGS_GET_0)

            if not enabled:
                LOGGER.debug("Skipping AOV at {0}: not enabled".format(aov_idx))
                continue

            aov_param = c4d.DescLevel(c4d.REDSHIFT_AOV_TYPE, c4d.DTYPE_LONG, 0)
            aov_type = rs_vp.GetParameter(c4d.DescID(aov_attrs, aov_param), c4d.DESCFLAGS_GET_0)
            aov_type_name = aov_types[aov_type]
            # nice name: i.e. REDSHIFT_AOV_TYPE_MOTION_VECTORS -> MotionVectors
            aov_type_nice = aov_type_name.replace("REDSHIFT_AOV_TYPE_", "")
            aov_type_nice = ''.join(aov.title() for aov in aov_type_nice.split("_"))

            aov_param = c4d.DescLevel(c4d.REDSHIFT_AOV_MULTIPASS_ENABLED, c4d.DTYPE_BOOL, 0)
            multipass = rs_vp.GetParameter(c4d.DescID(aov_attrs, aov_param), c4d.DESCFLAGS_GET_0)

            # TODO: duplicate entries
            if multipass:
                aov_param = c4d.DescLevel(c4d.REDSHIFT_AOV_NAME, c4d.DTYPE_STRING, 0)
                aov_name = rs_vp.GetParameter(c4d.DescID(aov_attrs, aov_param), c4d.DESCFLAGS_GET_0)

                if not aov_name:
                    if use_c4d_names and aov_type in aov_c4d_names:
                            aov_name = aov_c4d_names[aov_type]
                    else:
                        aov_name = aov_names.get(aov_type, aov_type_nice)
                        # Redshift appends an index to the name, only when Redshift names (not c4d) are used
                        aov_name = "{0}_{1}".format(aov_name, rs_name_idx)
                        rs_name_idx += 1  # redshift appends the AOV index unless compatibility picks a c4d name

                if mainMP:
                    self.addChannel(aov_name, "$userpass")  # aov don't support $userpass
                    added_to_channels = True
                else:
                    mainMP.channel_name = aov_name
                    mainMP.channel_description = "$userpass"

                    LOGGER.warning(
                        """Using {0} as first pass, but adding at least
                         a 'rgba' multipass is reccomended""".format(aov_type_nice)
                    )

            aov_param = c4d.DescLevel(c4d.REDSHIFT_AOV_FILE_ENABLED, c4d.DTYPE_BOOL, 0)
            direct_save = rs_vp.GetParameter(c4d.DescID(aov_attrs, aov_param), c4d.DESCFLAGS_GET_0)

            if direct_save:
                aov_param = c4d.DescLevel(c4d.REDSHIFT_AOV_NAME, c4d.DTYPE_STRING, 0)
                aov_name = rs_vp.GetParameter(c4d.DescID(aov_attrs, aov_param), c4d.DESCFLAGS_GET_0)

                aov_name = aov_name if aov_name else aov_names.get(aov_type, aov_type_nice)

                aov_param = c4d.DescLevel(c4d.REDSHIFT_AOV_FILE_PATH, c4d.DTYPE_STRING, 0)
                aov_file = rs_vp.GetParameter(c4d.DescID(aov_attrs, aov_param), c4d.DESCFLAGS_GET_0)
                aov_param = c4d.DescLevel(c4d.REDSHIFT_AOV_FILE_FORMAT, c4d.DTYPE_LONG, 0)
                aov_format = rs_vp.GetParameter(c4d.DescID(aov_attrs, aov_param), c4d.DESCFLAGS_GET_0)

                aov_file = aov_file.replace("$filepath", img_dir)
                aov_file = aov_file.replace("$filename", scn_name)
                aov_file = aov_file.replace("$pass", aov_name)

                aov_file = self.replacePathTokens(aov_file)
                aov_file = aov_file.replace("<Channel_intern>", aov_name)
                # aov_file = aov_file.replace("<Channel_name>", aov_name)  # aov don't support $userpass
                aov_file, aov_ext = self.getNameFormat(aov_file, aov_formats[aov_format])

                if mainMP:
                    self.job[0].channelExtension.append(aov_ext)
                    self.job[0].channelFileName.append(aov_file)
                    self.job[0].maxChannels += 1
                    added_to_channels = True
                    self.isMPSinglefile = False
                else:
                    mainMP.channel_name = aov_name
                    mainMP.channel_description = "$userpass"

                    LOGGER.warning(
                        """Using {0} as first pass, but adding at least
                         a 'rgba' multipass is reccomended""".format(aov_type_nice)
                    )

            if added_to_channels:
                aov_channels += 1

        return aov_channels

    def addChannelsVray(self, mainMP):
        doc = c4d.documents.GetActiveDocument()
        mp_hook = doc.FindSceneHook(1028268)  # VRayBridge/res/c4d_symbols.h, ID_MPHOOK
        if not mp_hook:
            return

        mp_branches = mp_hook.GetBranchInfo()

        for branch in mp_branches:
            if branch['id'] != 431000051:
                continue

            sub = branch['head'].GetFirst()

            elems = []
            while sub:
                # Multipass Category (Standard, Raw, Special...)
                sub_enabled = sub[c4d.MPNODE_ISENABLED]
                if sub_enabled:
                    elem = sub.GetDown()

                    while elem:
                        if elem[c4d.MPNODE_ISENABLED]:
                            elems.append(elem.GetName())
                            elem = elem.GetNext()

                sub = sub.GetNext()

            elems.reverse()
            for i, elem in enumerate(elems):
                descr_name = elem.replace(" ", "_")
                pass_name = "{0}_{1}".format(descr_name.lower(), i + 2)
                if mainMP:
                    self.addChannel(pass_name, descr_name)
                else:
                    mainMP.channel_name = pass_name
                    mainMP.channel_description = descr_name

                    LOGGER.warning(
                        """Using {0} as first pass, but adding at least
                         a 'rgba' multipass is reccomended""".format(elem)
                    )

    def replacePathTokens(self, image_name):
        image_name = image_name.replace("$camera", "<Camera>")
        image_name = image_name.replace("$prj", "<Scene>")
        image_name = image_name.replace("$pass", "<Channel_intern>")
        image_name = image_name.replace("$userpass", "<Channel_name>")

        image_name = image_name.replace("$rs", self.renderSettings.GetName())
        image_name = image_name.replace("$res", "{0}x{1}".format(self.job[0].width, self.job[0].height))
        image_name = image_name.replace("$range", "{0}_{1}".format(self.job[0].seqStart, self.job[0].seqEnd))
        image_name = image_name.replace("$fps", str(self.job[0].frameRateRender))

        return image_name

    @staticmethod
    def handleRelativeFileOut(file_path):
        if not file_path:
            return file_path

        is_relative = True

        if file_path.startswith(".") and file_path[1] != ".":
            file_path = file_path[1:]
            is_relative = True
        elif file_path[1] == ":":    #windows drive letter
            is_relative=False
        elif file_path.startswith("/"):  #osx root path
            is_relative=False
        elif file_path.startswith("\\"): #windows unc path
            is_relative=False

        if is_relative:
            return "<SceneFolder>/" + file_path

    def setFileout(self):
        if self.isMP:
            LOGGER.debug("MultiPass: yes")
            if self.isRegular:
                LOGGER.debug("Channel: Reg_Multi")
                self.job[0].channel = "Reg_Multi"
            else:
                LOGGER.debug("Channel: MultiPass")
                self.job[0].channel = "MultiPass"
            self.job[0].imageName = self.renderSettings[c4d.RDATA_MULTIPASS_FILENAME]
        else:
            LOGGER.debug("MultiPass: no")
            self.job[0].channel = ""
            self.job[0].imageName = self.renderSettings[c4d.RDATA_PATH]

        self.job[0].layerName = ""

        self.job[0].imageNamingID = self.renderSettings[c4d.RDATA_NAMEFORMAT]

        self.job[0].imageName = self.replacePathTokens(self.job[0].imageName)
        LOGGER.debug("imageName is: " + self.job[0].imageName)

        self.job[0].imageName = self.handleRelativeFileOut(self.job[0].imageName)
        self.job[0].imageName = self.job[0].imageName + "<IMS>"

        addStereoString = ""
        if self.renderSettings[c4d.RDATA_STEREO]:
            dirName = os.path.dirname(self.job[0].imageName)
            fileName = os.path.basename(self.job[0].imageName)
            if self.renderSettings[c4d.RDATA_STEREO_CALCRESULT] == c4d.RDATA_STEREO_CALCRESULT_S:
                addStereoString = self.languageStrings['STREAM'] + " " + self.languageStrings['STEREO_ANA_COL_RIGHT']
            elif self.renderSettings[c4d.RDATA_STEREO_CALCRESULT] == c4d.RDATA_STEREO_CALCRESULT_R:
                addStereoString = self.languageStrings['STREAM'] + " " + self.languageStrings['MERGEDSTREAM']
            elif self.renderSettings[c4d.RDATA_STEREO_CALCRESULT] == c4d.RDATA_STEREO_CALCRESULT_SR:
                addStereoString = self.languageStrings['STREAM'] + " " + self.languageStrings['MERGEDSTREAM']
            elif self.renderSettings[c4d.RDATA_STEREO_CALCRESULT] == c4d.RDATA_STEREO_CALCRESULT_SINGLE:
                if self.renderSettings[c4d.RDATA_STEREO_SINGLECHANNEL]==1:
                    addStereoString = self.languageStrings['STREAM'] + " " + self.languageStrings['STEREO_ANA_COL_LEFT']
                else:
                    addStereoString = self.languageStrings['STREAM'] + " " + self.languageStrings['STEREO_ANA_COL_RIGHT']
            if self.renderSettings[c4d.RDATA_STEREO_SAVE_FOLDER]:
                self.job[0].imageName = os.path.join(dirName, addStereoString, fileName)
            else:
                self.job[0].imageName = os.path.join(dirName, addStereoString, fileName)

        LOGGER.debug("imageName: before pass "+self.job[0].imageName)
        self.objectChannelID = 0
        mainMP = MultipassInfo("", "")  # (usually channelName = getChannelNameMP(MP), channelDescription = MP.GetName())
        post_effects_MP = None  # used for vray multipass
        if self.isMP and not self.isMPSinglefile:
            firstPassAdded = False
            ignoreFirstPass = not self.isRegular
            MP = self.renderSettings.GetFirstMultipass()
            while MP:
                if MP.GetBit(c4d.BIT_VPDISABLED):
                    MP = MP.GetNext()
                    continue
                if MP[c4d.MULTIPASSOBJECT_TYPE] == c4d.VPBUFFER_ALLPOSTEFFECTS:
                    post_effects_MP = MP
                    MP = MP.GetNext()
                    continue

                LOGGER.debug("pass: " + MP.GetName())
                if not firstPassAdded:
                    firstPassAdded = True
                    mainMP = MultipassInfo(self.getChannelNameMP(MP), MP.GetName())
                if ignoreFirstPass:
                    ignoreFirstPass = False
                    mainMP = MultipassInfo(self.getChannelNameMP(MP), MP.GetName())
                    LOGGER.debug("pass: Add main output: " + MP.GetName())
                else:
                    self.addChannelMultipass(MP)
                    LOGGER.debug("pass: Add addChannel : " + MP.GetName())

                MP = MP.GetNext()

            # 3d party multipass channels
            if self.job[0].renderer == "Redshift":
                # RR will set the first aov as main pass if mainMP is still empty
                self.addChannelsRedshift(mainMP)
            elif self.job[0].renderer == "Octane":
                self.addChannelsOctane(mainMP)
            elif self.job[0].renderer == "vray" and post_effects_MP:
                self.addChannelsVray(mainMP)
            elif self.job[0].renderer == "Arnold":
                self.addChannelsArnold(mainMP)

        if not mainMP:
            self.isMP= False
            if not self.isMPSinglefile:
                self.job[0].channel = ""

        if self.hasAlpha:
            regularImageName = "RGBA"
        else:
            regularImageName = "RGB"
        if self.job[0].renderer == "Arnold":
            regularImageName = "RGBA"
        LOGGER.debug("imageName is: " + self.job[0].imageName)

        c4dVersionMajor = int(c4d.GetC4DVersion() / 1000)

        if not self.isMP or self.isMPSinglefile:
            if self.hasAlpha:
                self.job[0].imageName = self.job[0].imageName.replace("<Channel_intern>", "rgba")
            else:
                self.job[0].imageName = self.job[0].imageName.replace("<Channel_intern>", "rgb")
            self.job[0].imageName = self.job[0].imageName.replace("<Channel_name>", regularImageName)
            self.job[0].imageName, self.job[0].imageFormat = self.getNameFormat(self.job[0].imageName, self.job[0].imageFormat)

        else:
            # filenameComb = ""
            # fileext = ""
            if self.isRegular and not self.isMP:
                if self.hasAlpha:
                    channelName = "rgba"
                else:
                    channelName = "rgb"
                channelDescription = regularImageName
                filenameComb =self.job[0].imageName
                fileext = self.job[0].imageFormat
                LOGGER.debug("fileext reg: " + fileext)
            else:
                channelName = mainMP.channel_name
                channelDescription = mainMP.channel_description
                if (c4dVersionMajor > 18) and (any(tok in self.renderSettings[c4d.RDATA_MULTIPASS_FILENAME] for tok in ("$userpass", "$pass"))):
                    # starting from R19, channel is not added to filename if already present
                    filenameComb = self.job[0].imageName
                elif self.renderSettings[c4d.RDATA_MULTIPASS_SUFFIX]:
                    # if self.job[0].imageName[-1].endswith("_"):
                    #     suffix = "<ValueVar " + channelName + "@>"
                    # else:
                    #     suffix = "<ValueVar _" + channelName + "@>"

                    filenameComb = self.job[0].imageName + "<ValueVar _" + channelName + "@>"
                else:
                    # if self.job[0].imageName.startswith("_"):
                    #     prefix = "<ValueVar " + channelName + "@>"
                    # else:
                    #     prefix = "<ValueVar _" + channelName + "@>"

                    filedir, filename = os.path.split(self.job[0].imageName)
                    filenameComb = os.path.join(filedir, "<ValueVar " + channelName + "_@>" + filename)

                fileext = self.job[0].imageFormatMultiPass
                LOGGER.debug("fileext mp: " + fileext)
            channelDescription = channelDescription.replace(" ", "_")
            filenameComb = filenameComb.replace("<Channel_intern>", "<ValueVar " + channelName + "@$pass>")
            filenameComb = filenameComb.replace("<Channel_name>","<ValueVar " + channelDescription + "@$userpass>")
            filenameComb, fileext = self.getNameFormat(filenameComb, fileext)

            self.job[0].imageName = filenameComb
            self.job[0].imageFormat = fileext

        LOGGER.debug("imageName is: " + self.job[0].imageName)

        if (self.renderSettings[c4d.RDATA_STEREO] and (self.renderSettings[c4d.RDATA_STEREO_CALCRESULT]==c4d.RDATA_STEREO_CALCRESULT_S)):
            curMaxChannels = self.job[0].maxChannels
            tempName = self.job[0].imageName
            tempName = tempName.replace(self.languageStrings['STEREO_ANA_COL_RIGHT'], self.languageStrings['STEREO_ANA_COL_LEFT'])
            self.job[0].channelFileName.append(tempName)
            self.job[0].channelExtension.append(self.job[0].imageFormat)
            self.job[0].maxChannels += 1
            for po in range(0, curMaxChannels):
                tempName = self.job[0].channelFileName[po]
                tempName = tempName.replace(self.languageStrings['STEREO_ANA_COL_RIGHT'], self.languageStrings['STEREO_ANA_COL_LEFT'])
                self.job[0].channelFileName.append(tempName)
                self.job[0].channelExtension.append(self.job[0].channelExtension[po])
                self.job[0].maxChannels += 1

        if self.renderSettings[c4d.RDATA_STEREO]:
            tempName = self.job[0].imageName
            if self.renderSettings[c4d.RDATA_STEREO_SAVE_FOLDER]:
                tempName = tempName.replace(addStereoString + "/", "<removeVar " + addStereoString + "/" + ">")
            else:
                tempName = tempName.replace(addStereoString + "_", "<removeVar " + addStereoString + "_" + ">")
            self.job[0].imageName=tempName

        if self.job[0].imageNamingID == c4d.RDATA_NAMEFORMAT_0:
            # name0000.ext
            self.job[0].imageFramePadding = 4
        elif self.job[0].imageNamingID == c4d.RDATA_NAMEFORMAT_1:
            # name0000
            self.job[0].imageFramePadding = 4
        elif self.job[0].imageNamingID == c4d.RDATA_NAMEFORMAT_2:
            # name.0000
            self.job[0].imageFramePadding = 4
        elif self.job[0].imageNamingID == c4d.RDATA_NAMEFORMAT_3:
            # name000.ext
            self.job[0].imageFramePadding = 3
        elif self.job[0].imageNamingID == c4d.RDATA_NAMEFORMAT_4:
            # name000
            self.job[0].imageFramePadding = 3
        elif self.job[0].imageNamingID == c4d.RDATA_NAMEFORMAT_5:
            # name.0000
            self.job[0].imageFramePadding = 3
        elif self.job[0].imageNamingID == c4d.RDATA_NAMEFORMAT_6:
            # name.0000.ext
            self.job[0].imageFramePadding = 4
        return True

    def saveTiledDocument(self, doc, tiles, filename):
        """experimental function to store tiled versions of a single document. Now Unused"""
        basename, ext = os.path.splitext(filename)
        filelist = []

        # store original state
        oRegion = self.renderSettings[c4d.RDATA_RENDERREGION]
        oRegionLeft = self.renderSettings[c4d.RDATA_RENDERREGION_LEFT]
        oRegionTop = self.renderSettings[c4d.RDATA_RENDERREGION_TOP]
        oRegionRight = self.renderSettings[c4d.RDATA_RENDERREGION_RIGHT]
        oRegionBottom = self.renderSettings[c4d.RDATA_RENDERREGION_BOTTOM]

        left = oRegionLeft
        top = oRegionTop
        right = oRegionRight
        bottom = oRegionBottom

        width = self.job[0].width - left - right

        step, rest = divmod(width, tiles)

        for i in range(0, tiles):
            self.renderSettings[c4d.RDATA_RENDERREGION] = True
            self.renderSettings[c4d.RDATA_RENDERREGION_LEFT] = int(left + (step * i))

            self.renderSettings[c4d.RDATA_RENDERREGION_RIGHT] = int(((tiles - 1) * step) - (self.renderSettings[c4d.RDATA_RENDERREGION_LEFT]))
            if self.renderSettings[c4d.RDATA_RENDERREGION_RIGHT] < right:
                self.renderSettings[c4d.RDATA_RENDERREGION_RIGHT] = int(right)

            self.renderSettings[c4d.RDATA_RENDERREGION_TOP] = int(top)
            self.renderSettings[c4d.RDATA_RENDERREGION_BOTTOM] = int(bottom)
            tiledname = basename + "_tile" + str(i).zfill(2) + ext
            c4d.documents.SaveDocument(doc, tiledname, c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST, c4d.FORMAT_C4DEXPORT)
            filelist.append(tiledname)

        # back to previous state
        self.renderSettings[c4d.RDATA_RENDERREGION] = oRegion
        self.renderSettings[c4d.RDATA_RENDERREGION_LEFT] = oRegionLeft
        self.renderSettings[c4d.RDATA_RENDERREGION_TOP] = oRegionTop
        self.renderSettings[c4d.RDATA_RENDERREGION_RIGHT] = oRegionRight
        self.renderSettings[c4d.RDATA_RENDERREGION_BOTTOM] = oRegionBottom
        return filelist

    def convert_umlaut(self, inStr):
        return inStr

    def getLanguage(self):
        self.languageStrings = {}
        language = "US"
        lID = 0
        lanDesc = c4d.GeGetLanguage(lID)
        while lanDesc != None:
            if lanDesc["default_language"]:
                language=lanDesc["extensions"]
                break
            lID = lID + 1
            lanDesc = c4d.GeGetLanguage(lID)
        CinemaPath = os.path.dirname(c4d.storage.GeGetPluginPath())
        CinemaPath = os.path.join(
            CinemaPath, "resource", "modules", "newman", "strings_" + str(language).lower(), "c4d_strings.str"
        )

        LOGGER.debug("Language file 1: "+CinemaPath)
        strfile = open(CinemaPath)
        for sline in strfile :
            sline = sline.rstrip()
            svalue = ""
            if ';' in sline and '"' in sline:
                sline = sline.split('"')
                svalue = sline[1].rstrip()
                sline = sline[0].rstrip()
                if "IDS_PV_STEREO_CHANNEL" in sline:
                    self.languageStrings['STEREO_CHANNEL'] = svalue
                elif "IDS_PV_STEREO_ANA_COL_LEFT" in sline:
                    self.languageStrings['STEREO_ANA_COL_LEFT'] = svalue
                elif "IDS_PV_STEREO_ANA_COL_RIGHT" in sline:
                    self.languageStrings['STEREO_ANA_COL_RIGHT'] = svalue
        strfile.close()

        CinemaPath = os.path.dirname(c4d.storage.GeGetPluginPath())
        CinemaPath = os.path.join(CinemaPath, "resource", "modules", "c4dplugin", "strings_" + str(language).lower(), "c4d_strings.str")
        LOGGER.debug("Language file 2: " + CinemaPath)
        strfile = open(CinemaPath)
        for sline in strfile:
            sline = sline.rstrip()
            svalue = ""
            if ';' in sline and '"' in sline:
                sline = sline.split('"')
                svalue = sline[1].rstrip()
                sline = sline[0].rstrip()
                if "IDS_STREAM" in sline:
                    self.languageStrings['STREAM'] = self.convert_umlaut(svalue)
                if "IDS_MERGEDSTREAM" in sline:
                    self.languageStrings['MERGEDSTREAM'] = self.convert_umlaut(svalue)
                if "IDS_MULTIPASS_AMBIENT" in sline:
                    self.languageStrings['ambient'] = self.convert_umlaut(svalue)
                if "IDS_MULTIPASS_ATMOSPHERE" in sline:
                    self.languageStrings['atmos'] = self.convert_umlaut(svalue)
                if "IDS_MULTIPASS_ATMOSPHERE_MULTIPLY" in sline:
                    self.languageStrings['atmosmul'] = self.convert_umlaut(svalue)
                if "IDS_MULTIPASS_TRANSPARENCY" in sline:
                    self.languageStrings['refr'] = self.convert_umlaut(svalue)
                if "IDS_MULTIPASS_REFLECTION" in sline:
                    self.languageStrings['refl'] = self.convert_umlaut(svalue)
                if "IDS_MULTIPASS_RADIOSITY" in sline:
                    self.languageStrings['gi'] = self.convert_umlaut(svalue)
                if "IDS_MULTIPASS_CAUSTICS" in sline:
                    self.languageStrings['caustics'] = self.convert_umlaut(svalue)
                if "IDS_MULTIPASS_DEPTH" in sline:
                    self.languageStrings['depth'] = self.convert_umlaut(svalue)
                if "IDS_MULTIPASS_SHADOW" in sline:
                    self.languageStrings['shadow'] = self.convert_umlaut(svalue)
                if "IDS_MULTIPASS_SPECUALR" in sline:
                    self.languageStrings['specular'] = self.convert_umlaut(svalue)
                if "IDS_MULTIPASS_DIFFUSE" in sline:
                    self.languageStrings['diffuse'] = self.convert_umlaut(svalue)
                if "IDS_MULTIPASS_ILLUMINATION" in sline:
                    self.languageStrings['illum'] = self.convert_umlaut(svalue)
                if "IDS_MULTIPASS_MATERIAL_SPECULAR" in sline:
                    self.languageStrings['matspeccol'] = self.convert_umlaut(svalue)
                if "IDS_MULTIPASS_MATERIAL_SPECULAR_COLOR" in sline:
                    self.languageStrings['matspec'] = self.convert_umlaut(svalue)
                if "IDS_MULTIPASS_MATERIAL_ENVIRONMENT" in sline:
                    self.languageStrings['matenv'] = self.convert_umlaut(svalue)
                if "IDS_MULTIPASS_MATERIAL_REFLECTION" in sline:
                    self.languageStrings['matrefl'] = self.convert_umlaut(svalue)
                if "IDS_MULTIPASS_MATERIAL_TRANSPARENCY" in sline:
                    self.languageStrings['mattrans'] = self.convert_umlaut(svalue)
                if "IDS_MULTIPASS_MATERIAL_LUMINANCE" in sline:
                    self.languageStrings['matlum'] = self.convert_umlaut(svalue)
                if "IDS_MULTIPASS_MATERIAL_DIFFUSION" in sline:
                    self.languageStrings['matdif'] = self.convert_umlaut(svalue)
                if "IDS_MULTIPASS_MATERIAL_COLOR" in sline:
                    self.languageStrings['matcolor'] = self.convert_umlaut(svalue)
                if "IDS_MULTIPASS_MATERIAL_AMBIENTOCCLUSION" in sline:
                    self.languageStrings['ao'] = self.convert_umlaut(svalue)
                if "IDS_MULTIPASS_MOTIONVECTOR" in sline:
                    self.languageStrings['motion'] = self.convert_umlaut(svalue)
                if "IDS_MULTIPASS_MATERIAL_UV" in sline:
                    self.languageStrings['uv'] = self.convert_umlaut(svalue)
                if "IDS_MULTIPASS_MATERIAL_NORMAL" in sline:
                    self.languageStrings['normal'] = self.convert_umlaut(svalue)
                if "IDS_MULTIPASS_RGBA" in sline:
                    self.languageStrings['rgb'] = self.convert_umlaut(svalue)
                    self.languageStrings['rgba'] = self.convert_umlaut(svalue)
                if "IDS_MULTIPASS_OBJECT_LAYER" in sline:
                    strg = self.convert_umlaut(svalue)
                    strg = strg.replace("#", "")
                    strg = strg.strip()
                    self.languageStrings['object_#_'] = strg
        strfile.close()

    def addCameras(self, doc):
        ob = doc.GetFirstObject()

        newcams = []
        while ob:
            type_id = ob.GetType()
            if type_id == c4d.OBJECT_STAGE:
                # if stage object is selecting a camera
                if ob[c4d.STAGEOBJECT_CLINK]:
                    self.job[0].camera = ob.GetName()
            elif type_id == c4d.OBJECT_CAMERA:
                newcam = ob.GetName()
                if newcam != self.job[0].camera:
                    newcams.append(newcam)

            ob = ob.GetNext()

        firstJob = True
        outdir, outname = os.path.split(self.job[0].imageName)
        for newcam in newcams:
            if (firstJob):
                newJob = self.job[0]
            else:
                newJob = copy.deepcopy(self.job[0])
            newJob.camera = newcam

            if "<Camera>" not in newJob.imageName:
                # user has forgotten to add <Camera>, which means you overwrite the same file
                newJob.imageName = os.path.join(outdir, "<Camera>", outname)
            for ch in range(0, newJob.maxChannels):
                ch_outdir, ch_outname = os.path.split(newJob.channelFileName[ch])
                if "<Camera>" not in newJob.channelFileName[ch]:
                    newJob.channelFileName[ch] = os.path.join(ch_outdir, "<Camera>", ch_outname)

            if firstJob:
                firstJob = False
            else:
                self.job.append(newJob)

    def Execute(self, doc):
        print "rrSubmit %rrVersion%"
        del self.job[:]
        self.job.append(rrJob())
        self.job[0].clear()

        # read current render settings
        self.getLanguage()
        self.renderSettings = doc.GetActiveRenderData()

        # collects some data and populates the job with initial settings
        self.hasAlpha = self.renderSettings[c4d.RDATA_ALPHACHANNEL]
        self.isRegular = self.renderSettings[c4d.RDATA_SAVEIMAGE] and (len(self.renderSettings[c4d.RDATA_PATH]) > 0)
        self.isMP = self.renderSettings[c4d.RDATA_MULTIPASS_SAVEIMAGE] and self.renderSettings[c4d.RDATA_MULTIPASS_ENABLE]  # is Multipass enabled?

        multilayer = (
            c4d.FILTER_PSD,
            c4d.FILTER_EXR,
            c4d.FILTER_TIF,
            c4d.FILTER_B3D,
            c4d.FILTER_PSB,
            1016606,
            1035823
        )
        self.isMPSinglefile = self.renderSettings[c4d.RDATA_MULTIPASS_SAVEONEFILE] and  self.renderSettings[c4d.RDATA_MULTIPASS_SAVEFORMAT] in multilayer

        LOGGER.debug("isMPSinglefile: " + str(self.isMPSinglefile))
        self.takeData = doc.GetTakeData()
        backupCurrentTake = self.takeData.GetCurrentTake()

        self.job[0].sceneFilename = doc.GetDocumentPath() + os.sep + doc.GetDocumentName()
        self.job[0].width = round(self.renderSettings[c4d.RDATA_XRES], 3)
        self.job[0].height = round(self.renderSettings[c4d.RDATA_YRES], 3)
        self.job[0].versionInfo = str(int(c4d.GetC4DVersion() / 1000))+"."+str(int(c4d.GetC4DVersion() % 1000)).zfill(3)

        if isWin():
            self.job[0].osString = "win"
        else:
            self.job[0].osString = "mac"
        #self.job[0].camera = doc.GetRenderBaseDraw().GetSceneCamera(doc).GetName()
        self.job[0].camera = "" #current cam
        self.job[0].frameRateDoc = doc.GetFps()
        self.job[0].frameRateRender = self.renderSettings[c4d.RDATA_FRAMERATE]
        if self.job[0].frameRateDoc != self.job[0].frameRateRender:
            ret = gui.QuestionDialog("Document (" + str(self.job[0].frameRateDoc) + ") and Render Settings (" + str(self.job[0].frameRateRender) + ") are not using the same framerate - do you wish to continue anyway?")
            if not ret:
                return False

        renderers = {
            c4d.RDATA_RENDERENGINE_STANDARD: "",
            c4d.RDATA_RENDERENGINE_PHYSICAL: "Physical",
            c4d.RDATA_RENDERENGINE_PREVIEWHARDWARE: "Hardware",
            c4d.RDATA_RENDERENGINE_CINEMAN: "CineMan",
            1029525: "Octane",
            1029988: "Arnold",
            1036219: "Redshift",
            1019782: "vray",
            1035287: "cycles",
        }

        try:
            renderers[c4d.RDATA_RENDERENGINE_PREVIEWSOFTWARE] = "preview"
        except AttributeError:
            pass  # missing in R21

        rendererID = self.renderSettings[c4d.RDATA_RENDERENGINE]
        self.job[0].renderer = renderers.get(rendererID, "RID"+str(rendererID))

        if self.job[0].renderer == "Arnold":
            self.job[0].rendererVersion = GetArnoldVersion(doc)
            self.job[0].Arnold_C4DtoAVersion = GetC4DtoAVersion(doc)
        elif self.job[0].renderer == "Redshift":
            self.job[0].rendererVersion = GetRedshiftVersion()
            self.job[0].Redshift_C4DtoRSVersion = GetRedshiftPluginVersion()
        elif self.job[0].renderer == "Octane":
            self.job[0].rendererVersion = GetOctaneVersion(doc)

        if doc.GetChanged():
            rvalue = gui.QuestionDialog("Save Scene?")
            if rvalue:
                c4d.documents.SaveDocument(doc, self.job[0].sceneFilename, c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST, c4d.FORMAT_C4DEXPORT)

        self.setImageFormat()
        self.setFileout()
        addTakes(doc, self.job, self.takeData)

        if self.multiCameraMode:
            self.addCameras(doc)

        if NORRTILE and ((SHOWTILEDIALOG) or (self.job[0].seqStart == self.job[0].seqEnd)):
            self.dialog = RRDialog()
            ret = self.dialog.Open(dlgtype=c4d.DLG_TYPE_MODAL_RESIZEABLE, pluginid=PLUGIN_ID)
            if not ret:
                return False

        self.submitToRR(self.job, False, PID=None, WID=None)

        self.takeData.SetCurrentTake(backupCurrentTake)
        return True


class RRSubmitAssExport(RRSubmitBase, c4d.plugins.CommandData):
    """Launch rrSubmitter for export .ass job"""
    def Execute(self, doc):
        print "rrSubmit %rrVersion%"

        self.renderSettings = doc.GetActiveRenderData()
        rendererID = self.renderSettings[c4d.RDATA_RENDERENGINE]
        if rendererID != 1029988:
            gui.MessageDialog("Arnold has to be the renderer of this scene.")
            LOGGER.warning("Arnold has to be the renderer of this scene.")
            return False

        del self.job[:]
        self.job.append(rrJob())
        self.job[0].clear()        
        self.job[0].renderer = "Arnold - Export Ass"

        self.takeData = doc.GetTakeData()
        backupCurrentTake= self.takeData.GetCurrentTake()
        
        self.job[0].sceneFilename = doc.GetDocumentPath() + os.sep + doc.GetDocumentName()
        self.job[0].width = self.renderSettings[c4d.RDATA_XRES]
        self.job[0].height = self.renderSettings[c4d.RDATA_YRES]
        self.job[0].versionInfo = str(int(c4d.GetC4DVersion() / 1000)) + "." + str(int(c4d.GetC4DVersion() % 1000)).zfill(3)
        self.job[0].Arnold_C4DtoAVersion = GetC4DtoAVersion(doc)

        if isWin():
            self.job[0].osString = "win"
        else:
            self.job[0].osString = "mac"

        self.job[0].camera = doc.GetRenderBaseDraw().GetSceneCamera(doc).GetName()
        self.job[0].frameRateDoc = doc.GetFps()
        self.job[0].frameRateRender = self.renderSettings[c4d.RDATA_FRAMERATE]
        if self.job[0].frameRateDoc != self.job[0].frameRateRender:
            ret = gui.QuestionDialog("Document (" + str(self.job[0].frameRateDoc) + ") and Render Settings (" + str(self.job[0].frameRateRender) + ") are not using the same framerate - do you wish to continue anyway?")
            if not ret:
                return False

        self.job[0].imageName = "<SceneFolder>/ass/<SceneFilename>/" + datetime.datetime.now().strftime("%Y%m%d%H%M%S") + "__.#####"
        self.job[0].imageFormat = ".ass.gz"

        if doc.GetChanged():
            rvalue = gui.QuestionDialog("Save Scene?")
            if rvalue:
                c4d.documents.SaveDocument(doc, self.job[0].sceneFilename,
                                           c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST,
                                           c4d.FORMAT_C4DEXPORT)

        addTakes(doc, self.job, self.takeData)
        self.submitToRR(self.job, False, PID=None, WID=None)
        
        self.takeData.SetCurrentTake(backupCurrentTake)
        return True


if __name__ == '__main__':
    result = plugins.RegisterCommandPlugin(PLUGIN_ID, "#$0rrSubmit", 0, None, "rrSubmit", RRSubmit())
    result = plugins.RegisterCommandPlugin(PLUGIN_ID_CAM, "#$1rrSubmit - Select Camera...", 0, None, "rrSubmit - Select Camera...", RRSubmit(multi_cam=True))
    result = plugins.RegisterCommandPlugin(PLUGIN_ID_ASS, "#$2rrSubmit - Export Arnold .ass files", 0, None,  "rrSubmit - Export Arnold .ass files", RRSubmitAssExport())
