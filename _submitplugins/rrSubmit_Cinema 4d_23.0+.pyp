# -*- coding: cp1252 -*-
######################################################################
#
# Royal Render Plugin script for Cinema R23+
# Author: Paolo Acampora - Binary Alchemy, Holger Schoenberger - Binary Alchemy,  Michael Auerswald - 908video.de
# Last change: %rrVersion%
# Copyright (c)  Holger Schoenberger
# #win:   rrInstall_Copy:         plugins\
# #linux: rrInstall_Copy:         plugins\
# #mac:   rrInstall_Copy:         ..\..\..\plugins\
# #win:   rrInstall_Delete:       plugins\rrSubmit_Cinema 4d_17.0+.pyp
# #linux: rrInstall_Delete:       plugins\rrSubmit_Cinema 4d_17.0+.pyp
# #mac:   rrInstall_Delete:       ..\..\..\plugins\rrSubmit_Cinema 4d_17.0+.pyp
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


##############################################
# PYTHON2 COMPATIBILITY                      #
##############################################

if sys.version_info.major == 2:
    range = xrange


##############################################
# GLOBAL VARIABLES                           #
##############################################

PLUGIN_ID_ASS = 1038331
PLUGIN_ID_CAM = 1039082
PLUGIN_ID = 1027715


##############################################
# GLOBAL LOGGER                              #
##############################################

LOGGER = logging.getLogger('rrSubmit')
# reload plugin creates another handler, so remove all at script start
for h in list(LOGGER.handlers):
    LOGGER.removeHandler(h)
LOGGER.setLevel(logging.INFO)
LOGGER.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
LOGGER.addHandler(ch)


##############################################
# GLOBAL FUNCTIONS                           #
##############################################

# c4d

IMG_FORMATS = {
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

MULTILAYER_FORMATS = (
    c4d.FILTER_PSD,
    c4d.FILTER_EXR,
    c4d.FILTER_TIF,
    c4d.FILTER_B3D,
    c4d.FILTER_PSB,
    1016606,
    1035823
)


# Arnold

class ArnoldSymbols:
    """Arnold identifiers from C4DtoA/res

    the numeric IDs are actually built via hashing

    def hashid(name):  # name = node_name.parameter_name
        if name is None: return 0

        h = 5381
        for c in name:
            h = (h << 5) + h + ord(c)
        h = ctypes.c_int32(h).value
        if h < 0: h = -h
        return h

    https://docs.arnoldrenderer.com/display/AFCUG/Shader+Network+%7C+Python
    """

    # C4DtoA/res/c4d_symbols.h
    ARNOLD_RENDERER = 1029988
    ARNOLD_RENDERER_COMMAND = 1039333

    ARNOLD_AOV = 1030369
    ARNOLD_DRIVER = 1030141
    ARNOLD_LIGHT = 1030424
    ARNOLD_PROCEDURAL = 1032509
    ARNOLD_VOLUME = 1033693
    ARNOLD_SCENE_HOOK = 1032309
    ARNOLD_DUMMY_BITMAP_SAVER = 1035823
    ARNOLD_SHADER_NETWORK = 1033991
    ARNOLD_SHADER_GV = 1033990
    ARNOLD_C4D_SHADER_GV = 1034190
    ARNOLD_SKY = 1034624

    # // shader links
    C4DAI_SHADERLINK_CONTAINER = 9988000
    C4DAI_SHADERLINK_TYPE = 101
    C4DAI_SHADERLINK_VALUE = 102
    C4DAI_SHADERLINK_TEXTURE = 103

    # C4DtoA/api/include/customgui/ArnoldShaderLinkCustomGui.h
    C4DAI_SHADERLINK_TYPE__CONSTANT = 1
    C4DAI_SHADERLINK_TYPE__TEXTURE = 2
    C4DAI_SHADERLINK_TYPE__SHADER_NETWORK = 3

    # C4DtoA/res/description/ainode_*_light.h
    C4DAIP_CYLINDER_LIGHT_COLOR = 557215133
    C4DAIP_DISK_LIGHT_COLOR = 2014459500
    C4DAIP_DISTANT_LIGHT_COLOR = 47856576
    C4DAIP_MESH_LIGHT_COLOR = 2056342262
    C4DAIP_QUAD_LIGHT_COLOR = 2010942260
    C4DAIP_PHOTOMETRIC_LIGHT_COLOR = 2101923881
    C4DAIP_POINT_LIGHT_COLOR = 1458609997
    C4DAIP_SKYDOME_LIGHT_COLOR = 268620635
    C4DAIP_SPOT_LIGHT_COLOR = 1823117041

    # C4DtoA/res/description/ainode_photometric_light.h
    C4DAIP_PHOTOMETRIC_LIGHT_FILENAME = 1413133543

    # C4DtoA/api/include/util/NodeIds.h
    C4DAIN_DRIVER_EXR = 9504161
    C4DAIN_DRIVER_DEEPEXR = 1058716317
    C4DAIN_DRIVER_JPEG = 313466666
    C4DAIN_DRIVER_PNG = 9492523
    C4DAIN_DRIVER_TIFF = 313114887
    C4DAIN_DRIVER_C4D_DISPLAY = 1927516736
    C4DAIN_DRIVER_C4D_EXR = 1927516736

    C4DAIN_IMAGE = 262700200

    # // lights
    C4DAIN_CYLINDER_LIGHT = 1944046294
    C4DAIN_DISK_LIGHT = 998592185
    C4DAIN_DISTANT_LIGHT = 1381557517
    C4DAIN_MESH_LIGHT = 804868393
    C4DAIN_PHOTOMETRIC_LIGHT = 1980850506
    C4DAIN_POINT_LIGHT = 381492518
    C4DAIN_QUAD_LIGHT = 1218397465
    C4DAIN_SKYDOME_LIGHT = 2054857832
    C4DAIN_SPOT_LIGHT = 876943490

    light_color_attr = {
        C4DAIN_CYLINDER_LIGHT: C4DAIP_CYLINDER_LIGHT_COLOR,
        C4DAIN_DISK_LIGHT: C4DAIP_DISK_LIGHT_COLOR,
        C4DAIN_DISTANT_LIGHT: C4DAIP_DISTANT_LIGHT_COLOR,
        C4DAIN_MESH_LIGHT: C4DAIP_MESH_LIGHT_COLOR,
        C4DAIN_PHOTOMETRIC_LIGHT: C4DAIP_PHOTOMETRIC_LIGHT_COLOR,
        C4DAIN_POINT_LIGHT: C4DAIP_POINT_LIGHT_COLOR,
        C4DAIN_QUAD_LIGHT: C4DAIP_QUAD_LIGHT_COLOR,
        C4DAIN_SKYDOME_LIGHT: C4DAIP_SKYDOME_LIGHT_COLOR,
        C4DAIN_SPOT_LIGHT: C4DAIP_SPOT_LIGHT_COLOR
    }

    # From plugins/C4DtoA/res/description/arnold_driver.h
    C4DAI_DRIVER_TYPE = 101

    # C4DtoA/res/description/ainode_driver_exr.h
    C4DAIP_DRIVER_EXR_FILENAME  = 1285755954
    C4DAIP_DRIVER_EXR_NAME = 55445461

    # # C4DtoA/res/description/ainode_driver_deepexr.h
    C4DAIP_DRIVER_DEEPEXR_FILENAME = 1429220916
    C4DAIP_DRIVER_DEEPEXR_NAME = 278349996

    # C4DtoA/res/description/ainode_driver_jpeg.h
    C4DAIP_DRIVER_JPEG_FILENAME = 766183461
    C4DAIP_DRIVER_JPEG_NAME = 965425797

    # C4DtoA/res/description/ainode_driver_png.h
    C4DAIP_DRIVER_PNG_FILENAME = 1807654404
    C4DAIP_DRIVER_PNG_NAME = 363284252

    # C4DtoA/res/description/ainode_driver_tiff.h
    C4DAIP_DRIVER_TIFF_FILENAME = 1913388456
    C4DAIP_DRIVER_TIFF_NAME = 1690311032

    # C4DtoA/api/include/customgui/ArnoldSavePathCustomGui.h
    C4DAI_SAVEPATH_TYPE__CUSTOM = 0
    C4DAI_SAVEPATH_TYPE__CUSTOM_WITH_NAME = 1
    C4DAI_SAVEPATH_TYPE__C4D_REGULAR = 2
    C4DAI_SAVEPATH_TYPE__C4D_MULTIPASS = 3

    # res/description/gvarnoldshader.h
    C4DAI_GVSHADER_TYPE = 200

    # res/description/gvc4dshader.h
    C4DAI_GVC4DSHADER_TYPE = 200

    # res/description/ainode_image.h
    C4DAIP_IMAGE_FILENAME = 1737748425

    driver_save_attr = {
        C4DAIN_DRIVER_DEEPEXR: (C4DAIP_DRIVER_DEEPEXR_FILENAME, ".exr"),
        C4DAIN_DRIVER_EXR: (C4DAIP_DRIVER_EXR_FILENAME, ".exr"),
        C4DAIN_DRIVER_JPEG: (C4DAIP_DRIVER_JPEG_FILENAME, ".jpg"),
        C4DAIN_DRIVER_PNG: (C4DAIP_DRIVER_PNG_FILENAME, ".png"),
        C4DAIN_DRIVER_TIFF: (C4DAIP_DRIVER_TIFF_FILENAME, ".tif")
    }

    # res/description/ainode_volume.h
    C4DAIP_VOLUME_FILENAME = 1869200172

    # Message IDs
    C4DTOA_MSG_TYPE = 1000
    C4DTOA_MSG_GET_VERSION = 1040
    C4DTOA_MSG_PARAM1 = 2001
    C4DTOA_MSG_PARAM2 = 2002
    C4DTOA_MSG_PARAM3 = 2003
    C4DTOA_MSG_PARAM4 = 2004
    C4DTOA_MSG_RESP1 = 2011
    C4DTOA_MSG_RESP2 = 2012
    C4DTOA_MSG_RESP3 = 2013
    C4DTOA_MSG_RESP4 = 2014

    C4DTOA_MSG_ADD_SHADER = 1029
    C4DTOA_MSG_QUERY_SHADER_NETWORK = 1028


def GetC4DtoAMessage(doc):
    """ Returns the arnold plugin version used for given doc

    :param doc: cinema 4d document
    :return: c4dtoa version as string, "" if no arnold hook is found
    """
    arnoldSceneHook = doc.FindSceneHook(ArnoldSymbols.ARNOLD_SCENE_HOOK)
    if arnoldSceneHook is None:
        return
    msg = c4d.BaseContainer()
    msg.SetInt32(ArnoldSymbols.C4DTOA_MSG_TYPE, ArnoldSymbols.C4DTOA_MSG_GET_VERSION)
    arnoldSceneHook.Message(c4d.MSG_BASECONTAINER, msg)
    return msg


def GetArnoldVersion(doc):
    msg = GetC4DtoAMessage(doc)
    if not msg:
        return ""
    return msg.GetString(ArnoldSymbols.C4DTOA_MSG_RESP2)


def GetC4DtoAVersion(doc):
    """Return the arnold plugin version used for given doc

    :param doc: cinema 4d document
    :return: c4dtoa version as string, "" if no arnold hook is found
    """
    msg = GetC4DtoAMessage(doc)
    if not msg:
        return ""
    return msg.GetString(ArnoldSymbols.C4DTOA_MSG_RESP1)


def arnoldGetOutputDrivers(doc):
    ob = doc.GetFirstObject()

    while ob:
        type_id = ob.GetType()
        if type_id != ArnoldSymbols.ARNOLD_DRIVER:
            ob = ob.GetNext()
            continue

        driver_type = ob[c4d.C4DAI_DRIVER_TYPE]
        if driver_type == ArnoldSymbols.C4DAIN_DRIVER_C4D_DISPLAY:
            # display driver has no output settings
            ob = ob.GetNext()
            continue
        try:
            save_attr, save_ext = ArnoldSymbols.driver_save_attr[driver_type]
        except KeyError:
            LOGGER.warning("invalid path attribute for driver of type " + str(driver_type))
            ob = ob.GetNext()
            continue

        type_parameter = c4d.DescID(c4d.DescLevel(save_attr), c4d.DescLevel(2))

        save_type = ob.GetParameter(type_parameter, c4d.DESCFLAGS_GET_0)
        if save_type not in (ArnoldSymbols.C4DAI_SAVEPATH_TYPE__CUSTOM, ArnoldSymbols.C4DAI_SAVEPATH_TYPE__CUSTOM_WITH_NAME):
            ob = ob.GetNext()
            continue

        path_parameter = c4d.DescID(c4d.DescLevel(save_attr), c4d.DescLevel(1))

        outpath = ob.GetParameter(path_parameter, c4d.DESCFLAGS_GET_0)

        if not outpath:
            ob = ob.GetNext()
            continue

        yield ob, path_parameter, outpath
        ob = ob.GetNext()


# Redshift
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


# Octane
def GetOctaneVersion(doc):
    ID_OCTANE_LIVEPLUGIN = 1029499
    octane_container = doc[ID_OCTANE_LIVEPLUGIN]

    if not octane_container:
        return

    oc_ver_num = str(octane_container[c4d.SET_OCTANE_VERSION])

    # format to major.minor.update
    # 3080400 is 3.08.4
    # 4000016 is 4.00.0-RC6
    # 10021301 is 10.02.13

    # strip release candidate
    oc_ver_num = oc_ver_num[:-2]
    oc_update = oc_ver_num[-2:]

    oc_ver_num = oc_ver_num[:-2]
    oc_minor = oc_ver_num[-2:]

    oc_major = oc_ver_num[:-2]
    # format to major.minor.update, i.e. 4000016 is V4.00.0-RC6
    return ".".join((oc_major, oc_minor, oc_update))


# Global

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


def allForwardSlashes(filepath):
    return os.path.normpath(filepath).replace('\\', '/')


def applyPathCorrections(filepath, truncate_dot=True, separate_digit=True):
    """c4d truncates the output to the last dot. Also, adds a _ if the path ends with a number"""
    if truncate_dot:
        filepath = truncateToLastDot(filepath)

    doc = c4d.documents.GetActiveDocument()
    if separate_digit and filepath and check_trailing_digit(doc.GetActiveRenderData()[c4d.RDATA_NAMEFORMAT]):
        if filepath.endswith("<IMS>"):
            if filepath[-6].isdigit():
                filepath = filepath[:-5] + "_" + "<IMS>"
        elif filepath[-1].isdigit():
            filepath += '_'

    return filepath


def truncateToLastDot(filepath):
    dirname, filename = os.path.split(filepath)

    if "." in filename:
        LOGGER.warning('filepaths with dots "{0}" are truncated by c4d'.format(filename))

    return os.path.join(dirname, filename.rsplit('.', 1)[0])


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

    def isValid(self):
        return bool(self.channel_name) or bool(self.channel_description)


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
    imageFormat = ""
    imageFormatID = 0
    imageFormatIDMultiPass = 0
    imageFormatMultiPass = ""
    imageFramePadding = 4
    imageName = ""
    imagePreNumberLetter = ""
    imageSingleOutput = False
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
    sendAppBit = ""
    seqEnd = 100
    seqFileOffset = 0
    seqFrameSet = ""
    seqStart = 0
    seqStep = 1
    software = "Cinema 4D"
    versionInfo = ""
    rendererVersion = ""
    Arnold_C4DtoAVersion = ""
    Arnold_DriverOut = False
    Redshift_C4DtoRSVersion = ""
    waitForPreID = ""
    linearColorSpace = False

    def __init__(self):
        self.channelFileName = []
        self.channelExtension = []

    def setImagePadding(self, name_id):
        self._imageNamingID = name_id
        if self._imageNamingID == c4d.RDATA_NAMEFORMAT_0:
            # name0000.ext
            self.imageFramePadding = 4
        elif self._imageNamingID == c4d.RDATA_NAMEFORMAT_1:
            # name0000
            self.imageFramePadding = 4
        elif self._imageNamingID == c4d.RDATA_NAMEFORMAT_2:
            # name.0000
            self.imageFramePadding = 4
        elif self._imageNamingID == c4d.RDATA_NAMEFORMAT_3:
            # name000.ext
            self.imageFramePadding = 3
        elif self._imageNamingID == c4d.RDATA_NAMEFORMAT_4:
            # name000
            self.imageFramePadding = 3
        elif self._imageNamingID == c4d.RDATA_NAMEFORMAT_5:
            # name.0000
            self.imageFramePadding = 3
        elif self._imageNamingID == c4d.RDATA_NAMEFORMAT_6:
            # name.0000.ext
            self.imageFramePadding = 4


class rrJob(JobProps):
    """Collect job properties from the scene, export xml file"""

    def __init__(self):
        super(rrJob, self).__init__()
        self.clear()

        self._imageNamingID = 0

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
        if sys.version_info.major == 2:
            text_parameter = unicode(text_parameter, "utf-8")
        sub.text = text_parameter
        return sub

    def writeToXMLstart(self):
        rootElement = Element("rrJob_submitFile")
        rootElement.attrib["syntax_version"] = "6.0"
        self.subE(rootElement, "DeleteXML", "1")
        self.subE(rootElement, "decodeUTF8", "_")

        if self.Arnold_DriverOut:
            self.subE(rootElement, "SubmitterParameter", "COArnoldDriverOut=1~1")
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
        self.subE(jobElement, "ImagePreNumberLetter", self.imagePreNumberLetter)
        self.subE(jobElement, "SceneOS", self.osString)
        self.subE(jobElement, "Camera", self.camera)
        if self.linearColorSpace:
            self.subE(jobElement, "SubmitterParameter", "PreviewGamma2.2=1~1")
        for c in range(0, self.maxChannels):
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

    def setOutputFromArnoldDriver(self):
        """Set job  name and extension as set in the arnold driver node.
         If a driver output is found, all the other drivers are ignored.
         Returns True if driver settings have been used.

         To use output of a different driver, move it on top in c4d outliner
        """
        LOGGER.debug("Looking for arnold drivers output path")

        doc = c4d.documents.GetActiveDocument()
        for driver, path_parameter, outpath in arnoldGetOutputDrivers(doc):

            if not outpath:
                ob = ob.GetNext()
                continue

            save_attr, save_ext = ArnoldSymbols.driver_save_attr[driver[c4d.C4DAI_DRIVER_TYPE]]
            filename, file_ext = os.path.splitext(outpath)
            if file_ext and file_ext != save_ext and '#' not in file_ext:
                LOGGER.warning("Extension {0}, differs from driver extension {1}".format(file_ext, save_ext))
                filename = outpath

            self.imageName = filename
            self.imageFormat = save_ext

            if '#' in filename:
                if not filename.endswith("#"):
                    gui.MessageDialog("Arnold driver '{0}' has non-trailing '#' in output filename."
                                      " Please change it so that it ends with '####' or '####.ext'".format(ob.GetName()))
                self.imageFramePadding = filename.count('#')
            else:
                self.imagePreNumberLetter = "."

            return True

        return False  # no output set


##############################################
# CINEMA 4D                                  #
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


def convert_filename_tokens(doc, take, filename, exclude=[]):
    """Convert tokens using c4d native utilities"""
    if c4d.GetC4DVersion() < 21000:
        LOGGER.warning("No native token conversion on versions earlier than R21")
        return filename

    render_data = doc.GetActiveRenderData()
    render_settings = render_data.GetDataInstance()

    render_path_data = {'_doc': doc, '_rData': render_data, '_rBc': render_settings, '_take': take}
    resolved = c4d.modules.tokensystem.FilenameConvertTokensFilter(filename, render_path_data, exclude)
    if resolved.startswith('./<SceneFolder>') or resolved.startswith('.\\<SceneFolder>'):
        # FilenameConvertTokensFilter has duplicated relative path
        resolved = resolved[2:]

    return applyPathCorrections(resolved, truncate_dot=False)


class TakeManager(object):
    def __init__(self, rr_submit, doc, is_archive=False):
        """
        :param rr_submit: submitter class
        :param doc: c4d document
        :param archive: is archive export (i.e. arnold ass)
        """
        self._submitter = rr_submit
        self._doc = doc
        self._is_archive = is_archive

        self._takedata = self._doc.GetTakeData()

    @property
    def _joblist(self):
        return self._submitter.job

    @property
    def _main_rdata(self):
        return self._submitter.renderSettings

    @property
    def main_job(self):
        return self._joblist[0]

    def _duplicate_with_new_take(self, take, current_take_name, parent_take_name=""):
        """Create a new job with current parameters but different take. Used to submit c4d takes as RR layers

        :param take: take for the newjob
        :param current_take_name: name of current take
        """

        take_name = take.GetName()
        take_name_full = '*'.join([name for name in (parent_take_name, take_name) if name])

        new_job = copy.deepcopy(self.main_job)

        new_job.isActive = take.IsChecked()
        if current_take_name == take_name_full:
            new_job.isActive = True

        self._takedata.SetCurrentTake(take)
        try:
            render_data, _ = take.GetEffectiveRenderData(self._takedata)
        except TypeError:
            LOGGER.warning("Could not submit Take {0}: RenderData not found".format(take_name))
            return

        if render_data and not self._is_archive:
            new_job.channelFileName = []
            new_job.channelExtension = []
            new_job.maxChannels = 0

            self._submitter.setImageFormat(job=new_job, render_data=render_data)
            self._submitter.setFileout(job=new_job, render_data=render_data)
        else:
            render_data = self._main_rdata

            if "$take" not in new_job.imageName:
                # user forgot to add $take, which means you overwrite the same file
                new_job.imageName = insertPathTake(new_job.imageName)
            for ch in range(0, new_job.maxChannels):
                if "$take" not in new_job.channelFileName[ch]:
                    new_job.channelFileName[ch] = insertPathTake(new_job.channelFileName[ch])

        new_job.layerName = take_name_full
        new_job.imageName = convert_filename_tokens(self._doc, take, new_job.imageName)
        new_job.imageName = new_job.imageName.replace("$take", take_name)  # manual replace for older versions

        for ch in range(0, new_job.maxChannels):
            new_job.channelFileName[ch] = convert_filename_tokens(self._doc, take, new_job.channelFileName[ch])
            new_job.channelFileName[ch] = new_job.channelFileName[ch].replace("$take", take_name)

        setSeq(new_job, render_data)
        if new_job.Arnold_DriverOut:
            new_job.setOutputFromArnoldDriver()

        LOGGER.debug("childTake: " + take_name_full + "  " + new_job.imageName)
        self._joblist.append(new_job)

    def _add_takes_recursive(self, parent_take, current_take_name, fullPath=""):
        """ Travel all takes looking for job layers

        :param parent_take: up-level take
        :param current_take_name: name of current take

        :return: None
        """
        child_take = parent_take.GetDown()
        while child_take != None:
            self._duplicate_with_new_take(child_take, current_take_name, fullPath)
            current_path = '*'.join([name for name in (fullPath, child_take.GetName()) if name])
            self._add_takes_recursive(child_take, current_take_name, current_path)
            child_take = child_take.GetNext()

    def add_takes(self):
        """Add takes as RR layer jobs

        :return:
        """
        LOGGER.debug("takeData: " + str(self._takedata))
        current_take_name = self._takedata.GetCurrentTake().GetName()
        main_take = self._takedata.GetMainTake()
        self._add_takes_recursive(main_take, current_take_name, fullPath="")

        main_job = self.main_job

        main_job.imageName = convert_filename_tokens(self._doc, main_take, main_job.imageName)
        main_job.imageName = main_job.imageName.replace("$take", main_take.GetName())
        main_job.layerName = main_take.GetName()

        for ch in range(0, main_job.maxChannels):
            main_job.channelFileName[ch] = convert_filename_tokens(self._doc, main_take, main_job.channelFileName[ch])
            main_job.channelFileName[ch] = main_job.channelFileName[ch].replace("$take", main_take.GetName())

        if self._takedata.GetCurrentTake() != main_take:
            self._takedata.SetCurrentTake(main_take)

        rd = self._doc.GetActiveRenderData()
        setSeq(main_job, rd)


class RRSubmitBase(object):
    """Base class for RRSubmit and RRSubmitAssExport"""

    def __init__(self):
        self.isMP = False
        self.renderSettings = None
        self.isMPSinglefile = False
        self.takeData = None

        self.languageStrings = {}
        self.job = [rrJob()]

    def submitToRR(self, submitjobs, useConsole, PID=None, WID=None):
        """Write XML Job file into a temporary file, then call the method
         to pass it either to the rrSubmitter or rrSubmitterconsole """

        tmpDir = tempfile.gettempdir()
        xmlObj = submitjobs[0].writeToXMLstart()

        write_mode = 'w' if sys.version_info.major < 3 else 'wb'
        tmpFile = open(tmpDir + os.sep + "rrTmpSubmitC4d.xml", write_mode)

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
        if WID != None:
            #c4d.storage.GeExecuteProgramEx(rrGetRR_Root() + self.getRRSubmitterConsole(), filename + " -PreID " + PID + " -WaitForID " + WID)
            call([rrGetRR_Root + self.getRRSubmitterConsole(), filename, "-PID", PID, "-WID", WID])
        elif PID != None:
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


def check_trailing_digit(name_format):
    return name_format not in (c4d.RDATA_NAMEFORMAT_2, c4d.RDATA_NAMEFORMAT_5, c4d.RDATA_NAMEFORMAT_6)


class RRSubmit(RRSubmitBase, c4d.plugins.CommandData):
    """Launch rrSubmitter for rrJob of current scene. The same class is used for multicamera mode"""
    hasAlpha = False
    isRegular = False
    objectChannelID = 0

    def __init__(self, multi_cam=False):
        super(RRSubmit, self).__init__()
        self.multiCameraMode = multi_cam

    def setImageFormat(self, job=None, render_data=None):
        """evaluates the image format extension from the currently selected render settings"""

        if not job:
            job = self.job[0]
        if not render_data:
            render_data = self.renderSettings

        if job.channel:
            job.imageFormatID = render_data[c4d.RDATA_MULTIPASS_SAVEFORMAT]
        else:
            job.imageFormatID = render_data[c4d.RDATA_FORMAT]

        try:
            job.imageFormat = IMG_FORMATS[job.imageFormatID]
        except KeyError:
            job.imageFormat = ".exr"
            LOGGER.error("Unknown File Format: " + str(job.imageFormatID))

        if job.imageFormat in (".mov", ".avi"):
            job.imageSingleOutput = True
            LOGGER.debug("SingleOutput: yes")
        else:
            LOGGER.debug("SingleOutput: no")

        job.imageFormatIDMultiPass = render_data[c4d.RDATA_MULTIPASS_SAVEFORMAT]
        try:
            job.imageFormatMultiPass = IMG_FORMATS[job.imageFormatIDMultiPass]
        except KeyError:
            LOGGER.error("Unknown File Format Multi Pass: " + str(job.imageFormatIDMultiPass))
            job.imageFormatMultiPass = ".exr"

        colorProfile = render_data[c4d.RDATA_IMAGECOLORPROFILE]
        if colorProfile.HasProfile() and colorProfile.GetInfo(0) == colorProfile.GetDefaultLinearRGB().GetInfo(0):
            job.linearColorSpace = True

        return True

    def getNameFormat(self, job, imagefilename, imageformat):
        if job._imageNamingID == c4d.RDATA_NAMEFORMAT_0:
            # name0000.ext
            imageformat = imageformat
        elif job._imageNamingID == c4d.RDATA_NAMEFORMAT_1:
            # name0000
            imageformat = ""
        elif job._imageNamingID == c4d.RDATA_NAMEFORMAT_2:
            # name.0000
            job.imageFormat = ""
            imageformat = ""
            imagefilename += "."
        elif job._imageNamingID == c4d.RDATA_NAMEFORMAT_3:
            # name000.ext
            imageformat = imageformat
        elif job._imageNamingID == c4d.RDATA_NAMEFORMAT_4:
            # name000
            imageformat = ""
        elif job._imageNamingID == c4d.RDATA_NAMEFORMAT_5:
            # name.0000
            job.imageFormat = ""
            imageformat = ""
            imagefilename += "."
        elif job._imageNamingID == c4d.RDATA_NAMEFORMAT_6:
            # name.0000.ext
            imagefilename += "."

        if check_trailing_digit(job._imageNamingID):
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

    def getChannelNameMP(self, MP, render_data):
        """Return channel name for given MP

        :param MP: c4d MultiPass
        :param render_data: c4d render settings
        :return: Channel name
        """
        displayName = MP.GetName()

        if render_data[c4d.RDATA_MULTIPASS_USERNAMES]:
            return displayName

        passType = MP[c4d.MULTIPASSOBJECT_TYPE]

        if passType == c4d.VPBUFFER_OBJECTBUFFER:
            return "object_" + str(MP[c4d.MULTIPASSOBJECT_OBJECTBUFFER])

        return self.getChannelName(passType, displayName)

    def getChannelNameExt(self, job, channelName, channelDescription, as_suffix=True):
        """Return filename and file extension for given channel name and description

        :param job: job containing the channel
        :param channelName: name of the channel
        :param channelDescription: nice format for channel type
        :param as_suffix: append channel name after image name if True, otherwise channel is a prefix
        :return: filename, fileextension
        """
        imageName = job.imageName

        if len(channelName) < 2:
            return "", ""

        if "<Channel_" in imageName:  # <Channel_intern>, <Channel_name>
            filenameComb = imageName.replace("<Channel_intern>", channelName)
            filenameComb = filenameComb.replace("<Channel_name>", channelDescription)
        elif as_suffix:
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

        fileext = job.imageFormatMultiPass
        filenameComb, fileext = self.getNameFormat(job, filenameComb, fileext)

        return filenameComb, fileext

    def addChannel(self, job, channelName, channelDescription, as_suffix=True):
        """Add given channel to the job

        :param job: job containing the channel
        :param channelName: channel name
        :param channelDescription: nice name for channel type
        :param as_suffix: append channel name after image name if True, otherwise channel is a prefix

        :return: None
        """
        filenameComb, fileext = self.getChannelNameExt(job, channelName, channelDescription, as_suffix)

        LOGGER.debug(f"Adding {channelName} - {filenameComb}, {fileext}")
        job.channelExtension.append(fileext)
        job.channelFileName.append(filenameComb)
        job.maxChannels += 1

    def addChannelMultipass(self, job, MP, render_data):
        """Add channel for given MultiPass

        :param job: job containing the channel
        :param MP: c4d multipass
        :param render_data: c4d render settings
        :return: None
        """
        channelName = self.getChannelNameMP(MP, render_data)
        channelDescription = MP.GetName().replace(" ", "_")

        self.addChannel(job, channelName, channelDescription, render_data[c4d.RDATA_MULTIPASS_SUFFIX])

    def addChannelsOctane(self, job, mainMP, render_data, has_alpha=False):
        """Add channels for Octane render passes and populate mainMP if empty. Return the number of Octane channels"""

        _vp = render_data.GetFirstVideoPost()
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

        if not mainMP.isValid() and c4d.GetC4DVersion() < 20000:
            # octane writes rgb or rgba image when multipass is enabled
            mainMP.channel_name = "rgba" if has_alpha else "rgb"
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
                if not mainMP.isValid():
                    mainMP.channel_name = nice_name
                    mainMP.channel_description = mainMP.channel_name
                    if oc_pass not in diffuse_passes:
                        nondiffuse_main = True
                elif nondiffuse_main and oc_pass in diffuse_passes:
                    # we want a diffuse or beauty pass as main output, for better previews
                    self.addChannel(job, mainMP.channel_name, mainMP.channel_description, render_data[c4d.RDATA_MULTIPASS_SUFFIX])
                    mainMP.channel_name = nice_name
                    mainMP.channel_description = mainMP.channel_name
                    nondiffuse_main = False
                else:
                    self.addChannel(job, nice_name, nice_name, render_data[c4d.RDATA_MULTIPASS_SUFFIX])
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

            job.channelExtension.append(passes_ext)
            job.channelFileName.append(pass_path)
            job.maxChannels += 1
            if not added:
                num_channels += 1
                added = True

        if use_multi_layer and passes_path:
            job.channelExtension.append(passes_ext)
            job.channelFileName.append(passes_path)
            job.maxChannels += 1
            num_channels += 1

        return num_channels

    def addDriverChannelsArnold(self, job):
        doc = c4d.documents.GetActiveDocument()
        out_dir = os.path.dirname(allForwardSlashes(job.imageName))

        for driver, path_parameter, outpath in arnoldGetOutputDrivers(doc):
            if driver[c4d.C4DAI_DRIVER_ENABLE_AOVS] == 0:
                continue

            file_ext = ArnoldSymbols.driver_save_attr[driver[c4d.C4DAI_DRIVER_TYPE]][1]
            main_out, _ = os.path.splitext(outpath)

            if '#' not in outpath:
                LOGGER.warning(
                    "arnold driver {0} output has no frame number placeholders ('#'), they will be added".format(
                        driver.GetName())
                )
            elif not main_out.endswith('#'):
                LOGGER.warning("arnold driver {0} output: '#' is not trailing".format(driver.GetName()))
            else:
                main_out = main_out.strip("#")

            main_out += '<IMS>'
            if outpath.endswith('.'):
                # arnold driver will duplicate the trailing '.'
                main_out += "."

            if driver[c4d.C4DAI_DRIVER_MERGE_AOVS] == 1:
                job.channelExtension.append(file_ext)
                job.channelFileName.append(main_out)
                job.maxChannels += 1
            else:
                channel_out = outpath.rstrip("#.")
                trailing_underscores = next(i for i in range(len(channel_out)) if channel_out[-(i + 1)] != "_")
                aov = driver.GetDown()
                while aov:
                    if aov[c4d.ID_BASEOBJECT_GENERATOR_FLAG] == 0:
                        aov = aov.GetNext()
                        continue
                    if aov[c4d.C4DAI_AOV_RENDER_AOV] == 0:
                        aov = aov.GetNext()
                        continue

                    channel_out.rstrip('_')
                    channel_out += '<IMS>'

                    aov_name = aov.GetName()
                    if aov_name != 'beauty':
                        channel_out += "_" + aov_name
                        channel_out += "_" * trailing_underscores  # arnold driver re-appends underscore at the end

                    if '#' not in outpath:
                        channel_out += '.'  # exr drivers use "." as separator: filename.framenum.ext
                    if outpath.endswith('.'):
                        # arnold driver will duplicate the trailing '.'
                        channel_out += '.'

                    job.channelExtension.append(file_ext)
                    job.channelFileName.append(channel_out)
                    job.maxChannels += 1

                    aov = aov.GetNext()

    def addChannelsArnold(self, job, mainMP, render_data):
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
            if type_id != ArnoldSymbols.ARNOLD_DRIVER:
                ob = ob.GetNext()
                continue

            if ob[c4d.ID_BASEOBJECT_GENERATOR_FLAG] == 0:
                # not enabled in c4d
                ob = ob.GetNext()
                continue

            if ob[c4d.C4DAI_DRIVER_ENABLE_AOVS] == 0:
                ob = ob.GetNext()
                continue

            if ob[c4d.C4DAI_DRIVER_TYPE] != ArnoldSymbols.C4DAIN_DRIVER_C4D_DISPLAY:
                # Handled in addDriverChannelsArnold()
                ob = ob.GetNext()
                continue

            if display_driver_found:
                LOGGER.warning('only one AOV driver of type "display" is considered by c4dtoa')
                break

            display_driver_found = True
            elems.append("alpha")

            aov = ob.GetDown()
            while aov:
                if aov[c4d.ID_BASEOBJECT_GENERATOR_FLAG] == 0:
                    aov = aov.GetNext()
                    continue
                if aov[c4d.C4DAI_AOV_RENDER_AOV] == 0:
                    aov = aov.GetNext()
                    continue

                aov_name = aov.GetName()

                if aov_name in display_skips_passes:
                    # the c4d display driver doesn't render some passes
                    LOGGER.debug("Skipping aov " + aov_name + ": not considered for display_drivers")
                    aov = aov.GetNext()
                    continue

                elems.append(aov_name)
                aov = aov.GetNext()
            ob = ob.GetNext()

        passes = []
        for i, elem in enumerate(elems):
            if not elem:
                continue
            descr_name = elem.replace(" ", "_")
            pass_name = "{0}_{1}".format(descr_name.lower(), i + 1)
            if "diffuse" in descr_name.lower() and not (mainMP.isValid() and mainMP.channel_name):
                mainMP.channel_name = pass_name
                elems.pop(i)
            else:
                passes.append((pass_name, descr_name))

        if not (mainMP.isValid() and mainMP.channel_name):
            mainMP.channel_name = passes.pop(0)[0]

        for pass_name, descr_name in passes:
            self.addChannel(job, pass_name, descr_name, render_data[c4d.RDATA_MULTIPASS_SUFFIX])

        return len([elem for elem in elems if elem])

    def addChannelsRedshift(self, job, mainMP, render_data, direct_only=False):
        """Add channels for redshift AOVs and populates mainMP if empty. Return the number of Redshift channels"""
        _vp = render_data.GetFirstVideoPost()
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
        diffuse_passes = ['REDSHIFT_AOV_TYPE_BEAUTY', 'REDSHIFT_AOV_TYPE_DIFFUSE_FILTER',
                          'REDSHIFT_AOV_TYPE_DIFFUSE_LIGHTING', 'REDSHIFT_AOV_TYPE_DIFFUSE_LIGHTING_RAW']

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
            c4d.REDSHIFT_AOV_TYPE_MOTION_VECTORS: "motion",
            # c4d.REDSHIFT_AOV_TYPE_OBJECT_ID: "object"
        }

        ID_CUSTOM_UI_AOV = 1036235  # Redshift AOVs ID

        # AOV can use these tokens
        img_dir, img_name = os.path.split(os.path.normpath(job.imageName))
        scn_dir, scn_name = os.path.split(os.path.normpath(job.sceneFilename))
        scn_name, _ = os.path.splitext(scn_name)
        img_dir += os.sep
        scn_dir += os.sep

        rs_name_idx = 1  # redshift appends an aov index to the aov multipass name
        aov_channels = 0  # 'enabled' and at least one between 'multipass' and 'direct' must be checked

        nondiffuse_main = False
        for i in range(num_AOV):
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
            if multipass and not direct_only:
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
                else:
                    aov_name = "{0}_{1}".format(aov_name, rs_name_idx)
                    rs_name_idx += 1  # redshift appends the AOV index unless compatibility picks a c4d name

                aov_name = aov_name.lower().replace(" ", "_")

                if mainMP.isValid():
                    if nondiffuse_main and aov_type_name in diffuse_passes:
                        # we have a main pass, but we wish it for a diffuse pass instead
                        # store current main pass as an additional channel
                        self.addChannel(job, mainMP.channel_name, mainMP.channel_description,
                                        render_data[c4d.RDATA_MULTIPASS_SUFFIX])
                        # store diffuse pass as main pass
                        LOGGER.info("switched main pass to {0}".format(aov_name))
                        mainMP.channel_name = aov_name
                        mainMP.channel_description = "$userpass"
                        nondiffuse_main = False
                        added_to_channels = True
                    else:
                        self.addChannel(job, aov_name, "$userpass", render_data[c4d.RDATA_MULTIPASS_SUFFIX])  # aov don't support $userpass
                        added_to_channels = True
                else:
                    # store as main pass
                    mainMP.channel_name = aov_name
                    mainMP.channel_description = "$userpass"
                    
                    nondiffuse_main = aov_type_name not in diffuse_passes
                    if nondiffuse_main:
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
                try:
                    aov_param = c4d.DescLevel(c4d.REDSHIFT_AOV_FILE_EFFECTIVE_PATH, c4d.DTYPE_STRING, 0)
                except AttributeError:
                    # build output path the old way
                    aov_param = c4d.DescLevel(c4d.REDSHIFT_AOV_FILE_PATH, c4d.DTYPE_STRING, 0)
                    aov_file = rs_vp.GetParameter(c4d.DescID(aov_attrs, aov_param), c4d.DESCFLAGS_GET_0)

                    aov_file = aov_file.replace("$filepath", img_dir)
                    aov_file = aov_file.replace("$filename", f'{scn_name}_AOV_')
                    aov_file = aov_file.replace("$pass", aov_name)

                    aov_file = self.replacePathTokens(job, aov_file, render_data)
                    aov_file = aov_file.replace("<Channel_intern>", aov_name)

                    # aov_file = aov_file.replace("<Channel_name>", aov_name)  # aov don't support $userpass
                else:
                    aov_file = rs_vp.GetParameter(c4d.DescID(aov_attrs, aov_param), c4d.DESCFLAGS_GET_0)

                    # remove extension from effective path
                    aov_file, _ = os.path.splitext(aov_file)
                    # remove frame number from effective path
                    if aov_file[-job.imageFramePadding:].isdigit():
                        aov_file = aov_file[:-job.imageFramePadding]
                
                aov_param = c4d.DescLevel(c4d.REDSHIFT_AOV_FILE_FORMAT, c4d.DTYPE_LONG, 0)
                aov_format = rs_vp.GetParameter(c4d.DescID(aov_attrs, aov_param), c4d.DESCFLAGS_GET_0)
                aov_file, aov_ext = self.getNameFormat(job, aov_file, aov_formats[aov_format])

                if aov_file.startswith("./"):
                    aov_file = "<SceneFolder>" + aov_file[1:]

                if mainMP.isValid() or direct_only:
                    job.channelExtension.append(aov_ext)
                    job.channelFileName.append(aov_file)
                    job.maxChannels += 1
                    added_to_channels = True
                else:
                    mainMP.channel_name = aov_name
                    mainMP.channel_description = "$userpass"

                    if aov_type not in diffuse_passes:
                        LOGGER.warning(
                            """Using {0} as first pass, but adding at least
                            a 'rgba' multipass is reccomended""".format(aov_type_nice)
                        )

            if added_to_channels:
                aov_channels += 1

        return aov_channels

    def addChannelsVray(self, job, mainMP, render_data):
        doc = c4d.documents.GetActiveDocument()
        mp_hook = doc.FindSceneHook(1028268)  # VRayBridge/res/c4d_symbols.h, ID_MPHOOK
        if not mp_hook:
            return

        mp_branches = mp_hook.GetBranchInfo()
        num_elems = 0

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
                if mainMP.isValid():
                    self.addChannel(job, pass_name, descr_name, render_data[c4d.RDATA_MULTIPASS_SUFFIX])
                else:
                    mainMP.channel_name = pass_name
                    mainMP.channel_description = descr_name

                    LOGGER.warning(
                        """Using {0} as first pass, but adding at least
                         a 'rgba' multipass is reccomended""".format(elem)
                    )
            num_elems += len(elems)
        
        return num_elems

    def replacePathTokens(self, job, image_name, render_data, separate_digit=True):
        # replace c4d tokens with RR tokens
        image_name = image_name.replace("$camera", "<Camera>")
        # image_name = image_name.replace("$prj", "<Scene>")  # do not need tokens that cannot be changed in rrSubmitter
        image_name = image_name.replace("$pass", "<Channel_intern>")
        image_name = image_name.replace("$userpass", "<Channel_name>")
        image_name = image_name.replace("$frame", '#' * job.imageFramePadding)

        if c4d.GetC4DVersion() < 21000:
            # native replacement
            doc = c4d.documents.GetActiveDocument()
            exclude_tokens = ['take', 'cvTake', 'cvParentTake']
            convert_filename_tokens(doc, image_name, doc.GetTakeData().GetCurrentTake(),
                                    exclude=exclude_tokens)

            tokens = c4d.modules.tokensystem.GetAllTokenEntries()
            for entry in tokens:
                # Take related tokens should be fed a take explicitly. Done on take add
                token_str = entry['_token']
                if 'take' in token_str.lower() and token_str not in exclude_tokens:
                    logging.warning("custom token {0} might be evaluated incorrectly. Please, contact support")

        image_name = image_name.replace("$rs", render_data.GetName())
        image_name = image_name.replace("$res", "{0}x{1}".format(job.width, job.height))
        image_name = image_name.replace("$range", "{0}_{1}".format(job.seqStart, job.seqEnd))
        image_name = image_name.replace("$fps", str(job.frameRateRender))

        return applyPathCorrections(image_name, truncate_dot=False, separate_digit=separate_digit)

    @staticmethod
    def handleRelativeFileOut(file_path):
        if not file_path:
            return file_path

        is_relative = True

        if file_path.startswith(".") and file_path[1] != ".":
            file_path = file_path[1:]
            is_relative = True
        elif file_path[1] == ":":  # windows drive letter
            is_relative = False
        elif file_path.startswith("/"):  # osx root path
            is_relative = False
        elif file_path.startswith("\\"):  # windows unc path
            is_relative = False

        if is_relative:
            return "<SceneFolder>/" + file_path

        return file_path

    def setFileout(self, job=None, render_data=None):
        if not job:
            job = self.job[0]
        if not render_data:
            render_data = self.renderSettings

        has_alpha = render_data[c4d.RDATA_ALPHACHANNEL]
        is_regular = render_data[c4d.RDATA_SAVEIMAGE] and render_data[c4d.RDATA_PATH]
        is_multipass = render_data[c4d.RDATA_MULTIPASS_SAVEIMAGE] and render_data[c4d.RDATA_MULTIPASS_ENABLE]
        is_mp_single = render_data[c4d.RDATA_MULTIPASS_SAVEONEFILE] and render_data[c4d.RDATA_MULTIPASS_SAVEFORMAT] in MULTILAYER_FORMATS

        if is_multipass:
            LOGGER.debug("MultiPass: yes")
            if is_regular:
                LOGGER.debug("Channel: Reg_Multi")
                job.channel = "Reg_Multi"

                reg_out = applyPathCorrections(render_data[c4d.RDATA_PATH])
                reg_out = self.handleRelativeFileOut(reg_out)
                reg_out = self.replacePathTokens(job, reg_out, render_data)
                reg_out += "<IMS>"

                # if $pass is present then rgb/rgba should be used
                reg_out = reg_out.replace("<Channel_intern>", "rgba" if has_alpha else "rgb")

                job.channelFileName.append(reg_out)
                job.channelExtension.append(IMG_FORMATS.get(render_data[c4d.RDATA_FORMAT], ".exr"))
                job.maxChannels += 1
                job.imageFormat = IMG_FORMATS.get(render_data[c4d.RDATA_MULTIPASS_SAVEFORMAT], ".exr")
            else:
                LOGGER.debug("Channel: MultiPass")
                job.channel = "MultiPass"
            job.imageName = applyPathCorrections(render_data[c4d.RDATA_MULTIPASS_FILENAME], separate_digit=False)
            if job.renderer == "Arnold" and render_data[c4d.RDATA_MULTIPASS_SAVEFORMAT] == ArnoldSymbols.ARNOLD_DUMMY_BITMAP_SAVER:
                job.Arnold_DriverOut = job.setOutputFromArnoldDriver()
        else:
            LOGGER.debug("MultiPass: no")
            job.channel = ""
            job.imageName = applyPathCorrections(render_data[c4d.RDATA_PATH])

            if job.renderer == "Arnold" and render_data[c4d.RDATA_FORMAT] == ArnoldSymbols.ARNOLD_DUMMY_BITMAP_SAVER:
                job.Arnold_DriverOut = job.setOutputFromArnoldDriver()

        job.layerName = ""
        job.setImagePadding(name_id=render_data[c4d.RDATA_NAMEFORMAT])

        LOGGER.debug("0 - imageName is: " + job.imageName)

        job.imageName = self.replacePathTokens(job, job.imageName, render_data, separate_digit=not (is_multipass and not is_mp_single))
        LOGGER.debug("1 - imageName is: " + job.imageName)

        job.imageName = self.handleRelativeFileOut(job.imageName)
        job.imageName = job.imageName + "<IMS>"

        addStereoString = ""
        if render_data[c4d.RDATA_STEREO]:
            dirName = os.path.dirname(job.imageName)
            fileName = os.path.basename(job.imageName)
            if render_data[c4d.RDATA_STEREO_CALCRESULT] == c4d.RDATA_STEREO_CALCRESULT_S:
                addStereoString = self.languageStrings['STREAM'] + " " + self.languageStrings['STEREO_ANA_COL_RIGHT']
            elif render_data[c4d.RDATA_STEREO_CALCRESULT] == c4d.RDATA_STEREO_CALCRESULT_R:
                addStereoString = self.languageStrings['STREAM'] + " " + self.languageStrings['MERGEDSTREAM']
            elif render_data[c4d.RDATA_STEREO_CALCRESULT] == c4d.RDATA_STEREO_CALCRESULT_SR:
                addStereoString = self.languageStrings['STREAM'] + " " + self.languageStrings['MERGEDSTREAM']
            elif render_data[c4d.RDATA_STEREO_CALCRESULT] == c4d.RDATA_STEREO_CALCRESULT_SINGLE:
                if render_data[c4d.RDATA_STEREO_SINGLECHANNEL]==1:
                    addStereoString = self.languageStrings['STREAM'] + " " + self.languageStrings['STEREO_ANA_COL_LEFT']
                else:
                    addStereoString = self.languageStrings['STREAM'] + " " + self.languageStrings['STEREO_ANA_COL_RIGHT']
            if render_data[c4d.RDATA_STEREO_SAVE_FOLDER]:
                job.imageName = os.path.join(dirName, addStereoString, fileName)
            else:
                job.imageName = os.path.join(dirName, addStereoString, fileName)

        LOGGER.debug("imageName: before pass "+job.imageName)
        self.objectChannelID = 0
        mainMP = MultipassInfo("", "")  # (usually channelName = getChannelNameMP(MP), channelDescription = MP.GetName())
        post_effects_MP = None  # used for vray multipass
        if is_multipass and not is_mp_single:
            firstPassAdded = False
            ignoreFirstPass = not is_regular
            MP = render_data.GetFirstMultipass()
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
                    mainMP = MultipassInfo(self.getChannelNameMP(MP, render_data), MP.GetName())
                if ignoreFirstPass:
                    ignoreFirstPass = False
                    mainMP = MultipassInfo(self.getChannelNameMP(MP, render_data), MP.GetName())
                    LOGGER.debug("pass: Add main output: " + MP.GetName())
                else:
                    self.addChannelMultipass(job, MP, render_data)
                    LOGGER.debug("pass: Add addChannel : " + MP.GetName())

                MP = MP.GetNext()

            # 3d party multipass channels
            if job.renderer == "Redshift":
                # RR will set the first aov as main pass if mainMP is still empty
                self.addChannelsRedshift(job, mainMP, render_data)
            elif job.renderer == "Octane":
                self.addChannelsOctane(job, mainMP, render_data, has_alpha=has_alpha)
            elif job.renderer == "vray" and post_effects_MP:
                self.addChannelsVray(job, mainMP, render_data)
            elif job.renderer == "Arnold":
                self.addChannelsArnold(job, mainMP, render_data)


        if not mainMP.isValid():
            # no need to go through the multipass channels
            is_multipass = False

            if is_mp_single:
                # the reason why we have no pass is the output file is multilayer
                job.imageName = job.imageName.replace("<Channel_intern>", "unresolved")
                if job.renderer == "Redshift":
                    # add direct save AOVs
                    self.addChannelsRedshift(job, mainMP, render_data, direct_only=True)
            else:
                # Apparently, this scene has no Multipass available, no need to set the channel for the kso plugin
                job.channel = ""

        LOGGER.debug("imageName: before correction " + job.imageName)
        job.imageName = applyPathCorrections(job.imageName, separate_digit=not (is_multipass and not is_mp_single))

        if self.hasAlpha:
            regularImageName = "RGBA"
        else:
            regularImageName = "RGB"
        if job.renderer == "Arnold":
            regularImageName = "RGBA"
        LOGGER.debug("2 - imageName is: " + job.imageName)

        c4dVersionMajor = int(c4d.GetC4DVersion() / 1000)

        if not is_multipass or is_mp_single:
            if self.hasAlpha:
                job.imageName = job.imageName.replace("<Channel_intern>", "rgba")
            else:
                job.imageName = job.imageName.replace("<Channel_intern>", "rgb")
            job.imageName = job.imageName.replace("<Channel_name>", regularImageName)
            if not job.Arnold_DriverOut:
                job.imageName, job.imageFormat = self.getNameFormat(job, job.imageName, job.imageFormat)
        else:
            # filenameComb = ""
            # fileext = ""
            if is_regular and not is_multipass:
                if self.hasAlpha:
                    channelName = "rgba"
                else:
                    channelName = "rgb"
                channelDescription = regularImageName
                filenameComb =job.imageName
                fileext = job.imageFormat
                LOGGER.debug("fileext reg: " + fileext)
            else:
                channelName = mainMP.channel_name
                channelDescription = mainMP.channel_description

                if not channelName:
                    filenameComb = job.imageName
                elif c4dVersionMajor > 18 and any(tok in render_data[c4d.RDATA_MULTIPASS_FILENAME] for tok in ("$userpass", "$pass")):
                    # starting from R19, channel is not added to filename if already present
                    filenameComb = job.imageName
                elif render_data[c4d.RDATA_MULTIPASS_SUFFIX]:
                    # if job.imageName[-1].endswith("_"):
                    #     suffix = "<ValueVar " + channelName + "@>"
                    # else:
                    #     suffix = "<ValueVar _" + channelName + "@>"

                    filenameComb = job.imageName + "<ValueVar _" + channelName + "@>"
                else:
                    # if job.imageName.startswith("_"):
                    #     prefix = "<ValueVar " + channelName + "@>"
                    # else:
                    #     prefix = "<ValueVar _" + channelName + "@>"

                    filedir, filename = os.path.split(job.imageName)
                    filenameComb = os.path.join(filedir, "<ValueVar " + channelName + "_@>" + filename)

                fileext = job.imageFormatMultiPass
                LOGGER.debug("fileext mp: " + fileext)
            channelDescription = channelDescription.replace(" ", "_")
            filenameComb = filenameComb.replace("<Channel_intern>", "<ValueVar " + channelName + "@$pass>")
            filenameComb = filenameComb.replace("<Channel_name>", "<ValueVar " + channelDescription + "@$userpass>")

            if not job.Arnold_DriverOut:
                filenameComb, fileext = self.getNameFormat(job, filenameComb, fileext)
                if fileext:
                    job.imageFormat = fileext

            job.imageName = filenameComb
            job.imageFormat = fileext

        LOGGER.debug("3 - imageName is: " + job.imageName)

        if (render_data[c4d.RDATA_STEREO] and (render_data[c4d.RDATA_STEREO_CALCRESULT]==c4d.RDATA_STEREO_CALCRESULT_S)):
            curMaxChannels = job.maxChannels
            tempName = job.imageName
            tempName = tempName.replace(self.languageStrings['STEREO_ANA_COL_RIGHT'], self.languageStrings['STEREO_ANA_COL_LEFT'])
            job.channelFileName.append(tempName)
            job.channelExtension.append(job.imageFormat)
            job.maxChannels += 1
            for po in range(0, curMaxChannels):
                tempName = job.channelFileName[po]
                tempName = tempName.replace(self.languageStrings['STEREO_ANA_COL_RIGHT'], self.languageStrings['STEREO_ANA_COL_LEFT'])
                job.channelFileName.append(tempName)
                job.channelExtension.append(job.channelExtension[po])
                job.maxChannels += 1

        if render_data[c4d.RDATA_STEREO]:
            tempName = job.imageName
            if render_data[c4d.RDATA_STEREO_SAVE_FOLDER]:
                tempName = tempName.replace(addStereoString + "/", "<removeVar " + addStereoString + "/" + ">")
            else:
                tempName = tempName.replace(addStereoString + "_", "<removeVar " + addStereoString + "_" + ">")
            job.imageName=tempName

        if job._imageNamingID == c4d.RDATA_NAMEFORMAT_0:
            # name0000.ext
            job.imageFramePadding = 4
        elif job._imageNamingID == c4d.RDATA_NAMEFORMAT_1:
            # name0000
            job.imageFramePadding = 4
        elif job._imageNamingID == c4d.RDATA_NAMEFORMAT_2:
            # name.0000
            job.imageFramePadding = 4
        elif job._imageNamingID == c4d.RDATA_NAMEFORMAT_3:
            # name000.ext
            job.imageFramePadding = 3
        elif job._imageNamingID == c4d.RDATA_NAMEFORMAT_4:
            # name000
            job.imageFramePadding = 3
        elif job._imageNamingID == c4d.RDATA_NAMEFORMAT_5:
            # name.0000
            job.imageFramePadding = 3
        elif job._imageNamingID == c4d.RDATA_NAMEFORMAT_6:
            # name.0000.ext
            job.imageFramePadding = 4

        if job.renderer == "Arnold":  # this function requires job.imageName
            self.addDriverChannelsArnold(job)

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
        CinemaPath = os.path.join(CinemaPath, "resource", "modules", "newman")

        if not os.path.isdir(CinemaPath):
            CinemaPath = os.path.join(os.path.dirname(c4d.storage.GeGetPluginPath()), "resource", "modules", "c4d_manager")

        CinemaPath = os.path.join(CinemaPath, "strings_" + str(language), "c4d_strings.str")

        if os.path.isfile(CinemaPath):
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
        else:
            LOGGER.warning(f"Language file 1 not found: {CinemaPath}")

        CinemaPath = os.path.dirname(c4d.storage.GeGetPluginPath())
        CinemaPath = os.path.join(CinemaPath, "resource", "modules", "c4dplugin")

        if not os.path.isdir(CinemaPath):
            CinemaPath = os.path.join(os.path.dirname(c4d.storage.GeGetPluginPath()), "resource", "modules", "c4d_base")
                                  
        CinemaPath = os.path.join(CinemaPath, "strings_" + str(language), "c4d_strings.str")

        if os.path.isfile(CinemaPath):
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
        else:
            LOGGER.warning(f"Language file 2 not found: {CinemaPath}")

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
        print("rrSubmit %rrVersion%")
        del self.job[:]
        self.job.append(rrJob())

        doc_changed = doc.GetChanged()

        # read current render settings
        self.getLanguage()
        self.renderSettings = doc.GetActiveRenderData()

        # collects some data and populates the job with initial settings
        self.hasAlpha = self.renderSettings[c4d.RDATA_ALPHACHANNEL]
        self.isRegular = self.renderSettings[c4d.RDATA_SAVEIMAGE] and (len(self.renderSettings[c4d.RDATA_PATH]) > 0)
        self.isMP = self.renderSettings[c4d.RDATA_MULTIPASS_SAVEIMAGE] and self.renderSettings[c4d.RDATA_MULTIPASS_ENABLE]  # is Multipass enabled?
        self.isMPSinglefile = self.renderSettings[c4d.RDATA_MULTIPASS_SAVEONEFILE] and self.renderSettings[c4d.RDATA_MULTIPASS_SAVEFORMAT] in MULTILAYER_FORMATS

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
            
            1029525: "Octane",
            1029988: "Arnold",
            1019782: "vray",
            1035287: "cycles",
        }

        try:
            renderers[c4d.RDATA_RENDERENGINE_CINEMAN] = "CineMan"
        except AttributeError:
            # Cineman was removed in C4D 2024
            pass
        
        try:
            # Redshift attr was added in C4D 2024
            renderers[c4d.RDATA_RENDERENGINE_REDSHIFT] = "Redshift"
        except AttributeError:
            # Fallback to plugin ID
            renderers[1036219] = "Redshift"

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

        setSeq(self.job[0], self.renderSettings)
        self.setImageFormat()
        self.setFileout()

        if len(self.job[0].imageName) == 0 or self.job[0].imageName == "<IMS>" :
            # output not set
            gui.MessageDialog('Output Path not set, please check Render Setting')
            return False

        take_manager = TakeManager(self, doc)
        take_manager.add_takes()

        if self.multiCameraMode:
            self.addCameras(doc)

        if self.takeData.GetCurrentTake() != backupCurrentTake:
            self.takeData.SetCurrentTake(backupCurrentTake)

        if doc_changed:
            rvalue = gui.QuestionDialog("Save Scene?")
            if rvalue:
                c4d.documents.SaveDocument(doc, self.job[0].sceneFilename, c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST, c4d.FORMAT_C4DEXPORT)
        elif doc.GetChanged():
            # we have changed the scene while collecting, we should save
            c4d.documents.SaveDocument(doc, self.job[0].sceneFilename, c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST, c4d.FORMAT_C4DEXPORT)

        self.submitToRR(self.job, False, PID=None, WID=None)

        return True


class RRSubmitAssExport(RRSubmitBase, c4d.plugins.CommandData):
    """Launch rrSubmitter for export .ass job"""
    def Execute(self, doc):
        print("rrSubmit %rrVersion%")

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

        take_manager = TakeManager(self.job, doc, self.renderSettings, is_archive=True)
        take_manager.add_takes()
        self.submitToRR(self.job, False, PID=None, WID=None)

        self.takeData.SetCurrentTake(backupCurrentTake)
        return True


if __name__ == '__main__':
    # Note: Using "#$0" in front of the name to sort menu entries (according to C4D docs) does not work with macOS + R23
    result = plugins.RegisterCommandPlugin(PLUGIN_ID, "rrSubmit", 0, None, "rrSubmit", RRSubmit())
    result = plugins.RegisterCommandPlugin(PLUGIN_ID_CAM, "rrSubmit - Select Camera...", 0, None, "rrSubmit - Select Camera...", RRSubmit(multi_cam=True))
    result = plugins.RegisterCommandPlugin(PLUGIN_ID_ASS, "rrSubmit - Export Arnold .ass files", 0, None,  "rrSubmit - Export Arnold .ass files", RRSubmitAssExport())
