#python
# -*- coding: cp1252 -*-
######################################################################
#
# Royal Render Render script for Cinema4D
# Author:  Royal Render, Paolo Acampora
# Version %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy
#
######################################################################

import datetime
import time
import sys
import c4d
import os


# LOGGING

def flushLog():
    sys.stdout.flush()
    sys.stderr.flush()

def logMessageGen(lvl, msg):
    if (len(lvl)==0):
        print(datetime.datetime.now().strftime("' %H:%M.%S") + " rrC4D      : " + str(msg))
    else:
        print(datetime.datetime.now().strftime("' %H:%M.%S") + " rrC4D - " + str(lvl) + ": " + str(msg))

def logMessage(msg):
    logMessageGen("", msg)

def logMessageSET(msg):
    logMessageGen("SET", msg)

def logMessageDebug(msg):
    #logMessageGen("DBG", msg)
    pass

def logMessageWarning(msg):
    logMessageGen("WRN", msg)

def logMessageError(msg):
    logMessageGen("ERR", str(msg)+"\n\n")
    logMessageGen("ERR", "Error reported, aborting render script")
    c4d.CallCommand(12104, 12104)  # Quit


# Parsing

def argValid(argValue):
    return (argValue!= None) and (len(str(argValue)) > 0)

class argParser:
    def getParam(self,argFindName):
        argFindName=argFindName.lower()
        for a in range(0,  len(sys.argv)):
            if ((sys.argv[a].lower()==argFindName) and (a+1<len(sys.argv))):
                argValue=sys.argv[a+1]
                if (argValue.lower()=="true"):
                    argValue=True
                elif (argValue.lower()=="false"):
                    argValue=False
                else:  # decode special characters to string accepted by c4d
                    argValue = argValue.decode(sys.getfilesystemencoding()).encode('utf8')
                logMessage("Flag  "+argFindName.ljust(15)+": '"+str(argValue)+"'");
                return argValue
        return ""

    def readArguments(self):
        self.sceneFile=self.getParam("-Scene")
        self.FrStart=self.getParam("-FrStart")
        self.FrEnd=self.getParam("-FrEnd")
        self.FrStep=self.getParam("-FrStep")
        self.FName=self.getParam("-FName")
        self.FNameVar=self.getParam("-FNameVar")
        self.FExt=self.getParam("-FExt")
        self.camera=self.getParam("-camera")
        self.threads=self.getParam("-threads")
        self.verbose=self.getParam("-verbose")
        self.width=self.getParam("-width")
        self.height=self.getParam("-height")
        self.KSOMode=self.getParam("-KSOMode")
        self.KSOPort=self.getParam("-KSOPort")
        self.take=self.getParam("-c4dtake")
        self.PyModPath=self.getParam("-PyModPath")
        self.logFile=self.getParam("-LogFile")
        self.RegionLeft=self.getParam("-RegionLeft")
        self.RegionRight=self.getParam("-RegionRight")
        self.RegionTop=self.getParam("-RegionTop")
        self.RegionBtm=self.getParam("-RegionBtm")
        self.Channel=self.getParam("-Channel")
        self.FPadding=self.getParam("-FPadding")
        self.renderer=self.getParam("-renderer")
        self.exportmode=self.getParam("-rendererExportMode")
        self.avFrameTime=self.getParam("-avFrameTime")
        self.noFrameLoop=self.getParam("-noFrameLoop")
        self.sceneOS=self.getParam("-sceneOS")

        # replace RR tokens left for compatibility
        arg.FNameVar = self.FNameVar.replace("<Camera>", self.camera)


# Rendering

def allForwardSlashes(filepath):
    return os.path.normpath(filepath).replace('\\', '/')


def convertFilepath(filepath, fromOS, toOS):
    filepath = allForwardSlashes(filepath)  # Conversion paths use forward slash
    if fromOS == rrOS.Windows:  # case insensitive
        filepath_lw = filepath.lower()
        conv_idx = next((i for i, v in enumerate(fromOS) if filepath_lw.startswith(v.lower())), None)
    else:
        conv_idx = next((i for i, v in enumerate(fromOS) if filepath.startswith(v)), None)

    if conv_idx is None:
        logMessageWarning("No conversion found for '{0}'".format(filepath))
        return

    filepath_new = toOS[conv_idx] + filepath[len(fromOS[conv_idx]):]
    return filepath_new


class ArnoldSymbols():
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
        C4DAIN_DRIVER_DEEPEXR: C4DAIP_DRIVER_EXR_FILENAME,
        C4DAIN_DRIVER_EXR: C4DAIP_DRIVER_EXR_FILENAME,
        C4DAIN_DRIVER_JPEG: C4DAIP_DRIVER_JPEG_FILENAME,
        C4DAIN_DRIVER_PNG: C4DAIP_DRIVER_PNG_FILENAME,
        C4DAIN_DRIVER_TIFF: C4DAIP_DRIVER_TIFF_FILENAME
    }

    # res/description/ainode_volume.h
    C4DAIP_VOLUME_FILENAME = 1869200172

    # Message IDs
    C4DTOA_MSG_TYPE = 1000
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


def GetArnoldRenderSettings():
    rdata = doc.GetActiveRenderData()

    # find the active Arnold render settings
    videopost = rdata.GetFirstVideoPost()
    while videopost:
        if videopost.GetType() == ArnoldSymbols.ARNOLD_RENDERER:
            return videopost
        videopost = videopost.GetNext()

    # create a new one when does not exist
    if videopost is None:
        c4d.CallCommand(ArnoldSymbols.ARNOLD_RENDERER_COMMAND)

        videopost = rdata.GetFirstVideoPost()
        while videopost:
            if videopost.GetType() == ArnoldSymbols.ARNOLD_RENDERER:
                return videopost
            videopost = videopost.GetNext()

    return None


def arnoldConvertSearchPaths(fromOS, toOS):
    """Convert search paths in arnold system settings (procedural, plugin, texture)"""
    arn_settings = GetArnoldRenderSettings()

    # arnold search paths (procedural, plugin, texture)
    for setting_id in (
            c4d.C4DAIP_OPTIONS_PROCEDURAL_SEARCHPATH,
            c4d.C4DAIP_OPTIONS_PLUGIN_SEARCHPATH,
            c4d.C4DAIP_OPTIONS_TEXTURE_SEARCHPATH
    ):
        search_path = arn_settings[setting_id]
        if not search_path:
            continue

        search_path_new = convertFilepath(search_path, fromOS, toOS)
        if search_path_new:
            logMessage("C4DtoA prefs: Convert path {0} to {1}".format(search_path, search_path_new))
            arn_settings[setting_id] = search_path_new


def arnoldConvertProcedural(ob, fromOS, toOS):
    proc_path = ob[c4d.C4DAI_PROCEDURAL_PATH]
    proc_path_new = convertFilepath(proc_path, fromOS, toOS)

    if proc_path_new:
        logMessage("C4DtoA proc: Convert path {0} to {1}".format(proc_path, proc_path_new))
        ob[c4d.C4DAI_PROCEDURAL_PATH] = proc_path_new


def arnoldConvertVolume(ob, fromOS, toOS):
    volume_path = ob[ArnoldSymbols.C4DAIP_VOLUME_FILENAME]
    volume_path_new = convertFilepath(volume_path, fromOS, toOS)

    if volume_path_new:
        logMessage("C4DtoA proc: Convert path {0} to {1}".format(volume_path, volume_path_new))
        ob[ArnoldSymbols.C4DAIP_VOLUME_FILENAME] = volume_path_new
        ob[ArnoldSymbols.C4DAIP_VOLUME_FILENAME] = volume_path_new  # you need to set volume path twice: the first time numbers are converted to '#'


def arnoldLinkedTexShader(ob, attr_code):
    """Color Texture via ShaderLink GUI"""
    shaderLinkBc = ob[ArnoldSymbols.C4DAI_SHADERLINK_CONTAINER]
    if not shaderLinkBc:
        return

    shaderLinkData = shaderLinkBc.GetContainerInstance(attr_code)
    if not shaderLinkData:
        return

    shaderLinkType = shaderLinkData.GetInt32(ArnoldSymbols.C4DAI_SHADERLINK_TYPE)
    if not shaderLinkType:
        return

    if shaderLinkType == ArnoldSymbols.C4DAI_SHADERLINK_TYPE__TEXTURE:
        return shaderLinkData.GetLink(ArnoldSymbols.C4DAI_SHADERLINK_TEXTURE, doc)


def arnoldConvertLight(ob, fromOS, toOS):
    photo_light_path = ob[ArnoldSymbols.C4DAIP_PHOTOMETRIC_LIGHT_FILENAME]
    if photo_light_path:
        light_path_new = convertFilepath(photo_light_path, fromOS, toOS)

        if light_path_new:
            logMessage("C4DtoA light: Convert path {0} to {1}".format(photo_light_path, light_path_new))
            ob[ArnoldSymbols.C4DAIP_PHOTOMETRIC_LIGHT_FILENAME] = light_path_new

    data = ob.GetDataInstance()
    nodeId = data.GetInt32(c4d.C4DAI_LIGHT_TYPE)

    try:
        attr_code = ArnoldSymbols.light_color_attr[nodeId]
    except KeyError:
        pass
    else:
        lightColShader = arnoldLinkedTexShader(ob, attr_code)
        if lightColShader:
            shadertreeConvertTex(lightColShader, fromOS, toOS)


def arnoldConvertSky(ob, fromOS, toOS):
    sky_shader = arnoldLinkedTexShader(ob, ArnoldSymbols.C4DAIP_SKYDOME_LIGHT_COLOR)
    if sky_shader and sky_shader.GetType() == c4d.Xbitmap:
        logMessageDebug("C4DtoA sky: found shader " + sky_shader.GetName())
        shadertreeConvertTex(sky_shader, fromOS, toOS)


def arnoldConvertDriver(ob, fromOS, toOS):
    driver_type = ob[c4d.C4DAI_DRIVER_TYPE]
    if driver_type != ArnoldSymbols.C4DAIN_DRIVER_C4D_DISPLAY:  # DRIVER_C4D_DISPLAY has no custom main output

        try:
            save_attr = ArnoldSymbols.driver_save_attr[driver_type]
        except KeyError:
            logMessageWarning("invalid path attribute for driver of type " + driver_type)
            return

        path_parameter = c4d.DescID(
            c4d.DescLevel(save_attr),
            c4d.DescLevel(1)
        )

        type_parameter = c4d.DescID(
            c4d.DescLevel(save_attr),
            c4d.DescLevel(2)
        )

        save_type = ob.GetParameter(type_parameter, c4d.DESCFLAGS_GET_0)

        if save_type in (ArnoldSymbols.C4DAI_SAVEPATH_TYPE__CUSTOM, ArnoldSymbols.C4DAI_SAVEPATH_TYPE__CUSTOM_WITH_NAME):
            save_path = ob.GetParameter(path_parameter, c4d.DESCFLAGS_GET_0)
            if save_path:
                save_path_new = convertFilepath(save_path, fromOS, toOS)
                if save_path_new:
                    logMessage("C4DtoA driver: Convert path {0} to {1}".format(save_path, save_path_new))
                    ob.SetParameter(path_parameter, save_path_new, c4d.DESCFLAGS_GET_0)

    # TODO: custom path for each AOV


def arnoldConvertShader(material, fromOS, toOS):
    """Perform operations on Arnold Shader Networks. Return true if a scene update is needed afterwards"""
    # message based query
    msg = c4d.BaseContainer()
    msg.SetInt32(ArnoldSymbols.C4DTOA_MSG_TYPE, ArnoldSymbols.C4DTOA_MSG_QUERY_SHADER_NETWORK)
    material.Message(c4d.MSG_BASECONTAINER, msg)

    numShaders = msg.GetInt32(ArnoldSymbols.C4DTOA_MSG_RESP1)

    trigger_update = False

    for i in xrange(0, numShaders):
        shader = msg.GetLink(10000 + i)
        if not shader:
            continue

        data = shader.GetOpContainerInstance()

        if shader.GetOperatorID() == ArnoldSymbols.ARNOLD_SHADER_GV:
            nodeId = data.GetInt32(ArnoldSymbols.C4DAI_GVSHADER_TYPE)
            if nodeId == ArnoldSymbols.C4DAIN_IMAGE:
                filename = data.GetFilename(ArnoldSymbols.C4DAIP_IMAGE_FILENAME)
                filename_new = convertFilepath(filename, fromOS, toOS)

                if filename_new:
                    logMessage("C4DtoA Shader: Convert path {0} to {1}".format(filename, filename_new))
                    shader.SetParameter(ArnoldSymbols.C4DAIP_IMAGE_FILENAME, filename_new, c4d.DESCFLAGS_SET_0)
                    trigger_update = True

                continue

        if shader.GetOperatorID() == ArnoldSymbols.ARNOLD_C4D_SHADER_GV:
            nodeId = data.GetInt32(ArnoldSymbols.C4DAI_GVC4DSHADER_TYPE)
            if nodeId == c4d.Xbitmap:
                # the C4D shader is attached to the GV node
                c4d_shader = shader.GetFirstShader()

                if c4d_shader is not None:
                    shadertreeConvertTex(c4d_shader, fromOS, toOS)

    return trigger_update


def arnoldConvertObjectPaths(ob, fromOS, toOS):
    while ob:
        type_id = ob.GetType()

        # arnold .ass files
        if type_id == ArnoldSymbols.ARNOLD_PROCEDURAL:
            arnoldConvertProcedural(ob, fromOS, toOS)
        # arnold .ies files
        elif type_id == ArnoldSymbols.ARNOLD_LIGHT:
            arnoldConvertLight(ob, fromOS, toOS)
        # arnold Sky
        elif type_id == ArnoldSymbols.ARNOLD_SKY:
            arnoldConvertSky(ob, fromOS, toOS)
        # arnold Volume
        elif type_id == ArnoldSymbols.ARNOLD_VOLUME:
            arnoldConvertVolume(ob, fromOS, toOS)
        # arnold driver
        elif type_id == ArnoldSymbols.ARNOLD_DRIVER:
            if ob[c4d.ID_BASEOBJECT_GENERATOR_FLAG] == 0:  # disabled in c4d
                ob = ob.GetNext()
                continue

            if ob[c4d.C4DAI_DRIVER_ENABLE_AOVS] == 0:  # disabled via arnold attrs
                ob = ob.GetNext()
                continue

            arnoldConvertDriver(ob, fromOS, toOS)

        if ob.GetDown():
            arnoldConvertObjectPaths(ob.GetDown(), fromOS, toOS)

        ob = ob.GetNext()


def arnoldConvertPaths(fromOS, toOS):
    logMessageDebug("Arnold paths conversion")
    arnoldConvertSearchPaths(fromOS, toOS)

    mat = doc.GetFirstMaterial()
    trigger_update = False

    while (mat):
        if mat.GetType() == ArnoldSymbols.ARNOLD_SHADER_NETWORK:
            trigger_update = arnoldConvertShader(mat, fromOS, toOS)
        mat = mat.GetNext()

    arnoldConvertObjectPaths(doc.GetFirstObject(), fromOS, toOS)

    if trigger_update:
        c4d.EventAdd()


def shadertreeConvertTex(shader, fromOS, toOS):
    """Look for texture paths to convert, iterate through shaders recursively"""
    while shader:
        # If it's a bitmap, we'll look at the filename
        if shader.GetType() == c4d.Xbitmap:
            filename = shader[c4d.BITMAPSHADER_FILENAME]
            filename_new = convertFilepath(filename, fromOS, toOS)

            if filename_new:
                logMessage("Convert path {0} to {1}".format(filename, filename_new))
                shader[c4d.BITMAPSHADER_FILENAME] = filename_new

        # Check for child shaders & recurse
        if shader.GetDown():
            shadertreeConvertTex(shader.GetDown(), fromOS, toOS)
        # Get the Next Shader
        shader = shader.GetNext()


def alembicConvertBasicAttrs(ob, fromOS, toOS):
    if ob[c4d.ALEMBIC_OVERRIDE_FOR_RENDERING] and not ob[c4d.ALEMBIC_USE_ORIGINAL_PATH]:
        abc_attrs = (c4d.ALEMBIC_PATH, c4d.ALEMBIC_PATH_FOR_RENDERING)
    else:
        abc_attrs = (c4d.ALEMBIC_PATH,)
    for abc_attr in abc_attrs:
        abc_path = ob[abc_attr]
        if not abc_path:
            continue

        abc_new = convertFilepath(abc_path, fromOS, toOS)
        if abc_new:
            logMessage("ABC: Convert path {0} to {1}".format(abc_path, abc_new))
            ob[abc_attr] = abc_new



def alembicConvertPaths(ob, fromOS, toOS):
    while ob:
        if ob.GetType() == c4d.Oalembicgenerator:
            alembicConvertBasicAttrs(ob, fromOS, toOS)

        abc_tag = ob.GetTag(c4d.Talembicmorphtag)
        if abc_tag:
            abc_path = abc_tag[c4d.ALEMBIC_MT_PATH]
            if abc_path:
                abc_new = convertFilepath(abc_path, fromOS, toOS)

                if abc_new:
                    logMessage("ABC tag: Convert path {0} to {1}".format(abc_path, abc_new))
                    abc_tag[c4d.ALEMBIC_MT_PATH] = abc_new

        # Check for child alembic & recurse
        if ob.GetDown():
            alembicConvertPaths(ob.GetDown(), fromOS, toOS)

        ob = ob.GetNext()


def doCrossOSPathConversionC4d(arg):
    logMessageDebug("Cross OS conversion")
    if not argValid(arg.sceneOS):
        logMessageDebug("No OS conversion enabled")
        return

    arg.sceneOS = int(arg.sceneOS)
    ourOS = rrScriptHelper.getOS()

    if ourOS == arg.sceneOS:
        logMessageDebug("No OS conversion necessary")
        return


    # get conversion table
    osConvert = rrScriptHelper.rrOSConversion()
    osConvert.loadSettings()
    fromOS, toOS = osConvert.getTable(arg.sceneOS, True)

    if len(fromOS) == 0:
        logMessageWarning("No OS conversion entries found")
        return

    # convert c4d objects:
    alembicConvertPaths(doc.GetFirstObject(), fromOS, toOS)

    # convert texture paths
    mat = doc.GetFirstMaterial()
    while (mat):
        shd = mat.GetFirstShader()
        shadertreeConvertTex(shd, fromOS, toOS)
        mat = mat.GetNext()

    if arg.renderer.lower() == "arnold":
        arnoldConvertPaths(fromOS, toOS)


def c4d_ext_id(ext):
    """Return cinema4D filter id for given extension

    c4d_ext_id(".jpg") = 1104  # c4d.FILTER_JPG
    """
    if ext.lower() == "pct":
        ext = "PICT"
    filter_attr = ext.upper().replace(".", "FILTER_")
    return getattr(c4d, filter_attr)

def c4d_pass_id(channel):
    """Return cinema4D filter id for given pass

    c4d_pass_id("Diffuse") = 3  # c4d.VPBUFFER_DIFFUSE
    """

    channel = channel.upper()
    channel.replace(" ", "_")
    channel.replace("MATERIAL", "MAT")
    vbuf_attr = "VPBUFFER_" + channel.upper()
    return getattr(c4d, vbuf_attr)


def searchTakes_recursiveLoop(parentTake, take_name):
    """Returns take with given name, looks recursively"""
    if parentTake.GetName() == take_name:
        return parentTake

    childTake = parentTake.GetDown()
    while childTake:
        if childTake.GetName() == take_name:
            return childTake
        jobtake= searchTakes_recursiveLoop(childTake, take_name)
        if jobtake:
            return jobtake
        childTake = childTake.GetNext()

def arnold_ass_export(fr_start, fr_end, fr_step):
    global arg
    global doc

    fr_start = int(fr_start)
    fr_end = int(fr_end)
    fr_step = int(fr_step)

    ARNOLD_ASS_EXPORT = 1029993
    logMessage("Exporting .ass to " + arg.FNameVar + arg.FExt)

    options = c4d.BaseContainer()
    options.SetFilename(0, arg.FNameVar + ".ass")
    if (arg.FExt.find(".gz")>0):
        options.SetInt32(1, True)  # export .gz file
    options.SetInt32(6, fr_start)  # start frame
    options.SetInt32(7, fr_end)  # end frame
    options.SetInt32(8, fr_step)  # step

    doc.GetSettingsInstance(c4d.DOCUMENTSETTINGS_DOCUMENT).SetContainer(ARNOLD_ASS_EXPORT, options)

    c4d.documents.SetActiveDocument(doc)  # required for ass export
    c4d.CallCommand(ARNOLD_ASS_EXPORT)


def tiled_checkRedshift_compatibility(arg, rd):
    _vp = rd.GetFirstVideoPost()
    while _vp:
        rs_vp = None  # Redshift VideoPost

        if _vp.CheckType(1036219):  # Redshift ID
            rs_vp = _vp
            break
        _vp = _vp.GetNext()

    if not rs_vp:
        return

    ID_CUSTOM_UI_AOV = 1036235  # Redshift AOVs ID
    num_AOV = rs_vp[c4d.REDSHIFT_RENDERER_AOV_COUNT]
    for i in xrange(num_AOV):
        aov_idx = c4d.REDSHIFT_RENDERER_AOV_LAYER_FIRST + i
        aov_attrs = c4d.DescLevel(aov_idx, ID_CUSTOM_UI_AOV, 0)
        aov_param = c4d.DescLevel(c4d.REDSHIFT_AOV_ENABLED, c4d.DTYPE_BOOL, 0)
        enabled = rs_vp.GetParameter(c4d.DescID(aov_attrs, aov_param), c4d.DESCFLAGS_GET_0)

        if not enabled:
            continue

        aov_param = c4d.DescLevel(c4d.REDSHIFT_AOV_FILE_ENABLED, c4d.DTYPE_BOOL, 0)
        direct_save = rs_vp.GetParameter(c4d.DescID(aov_attrs, aov_param), c4d.DESCFLAGS_GET_0)

        if direct_save:
            aov_param = c4d.DescLevel(c4d.REDSHIFT_AOV_NAME, c4d.DTYPE_STRING, 0)
            aov_name = rs_vp.GetParameter(c4d.DescID(aov_attrs, aov_param), c4d.DESCFLAGS_GET_0)
            if not aov_name:
                aov_param = c4d.DescLevel(c4d.REDSHIFT_AOV_TYPE, c4d.DTYPE_LONG, 0)
                aov_type = rs_vp.GetParameter(c4d.DescID(aov_attrs, aov_param), c4d.DESCFLAGS_GET_0)

                aov_name = next((attr for attr in dir(c4d) if attr.startswith('REDSHIFT_AOV_TYPE_') and getattr(c4d, attr) == aov_type), str(aov_type))

            logMessageError(
                "Cannot use 'Direct Output' in combination with 'Tiled Frame' for AOV '{0}'\n"
                "Please resubmit disabling either 'Tiled Frame' for the job or 'Direct Output' for the AOVs".format(
                    aov_name if aov_name else 'NOT FOUND'
                )
            )


def tiled_checkOctane_compatibility(arg, rd):
    _vp = rd.GetFirstVideoPost()
    oc_vp = None  # Octane VideoPost

    while _vp:
        if _vp.CheckType(1029525):  # Octane ID
            oc_vp = _vp
            break
        _vp = _vp.GetNext()
    if not oc_vp:
        return

    oc_vp[c4d.VP_RENDERREGION] = True
    oc_vp[c4d.VP_REGION_X1] = float(arg.RegionLeft) / arg.width
    oc_vp[c4d.VP_REGION_Y1] = float(arg.RegionTop) / arg.width
    oc_vp[c4d.VP_REGION_X2] = float(rd[c4d.RDATA_RENDERREGION_RIGHT]) / arg.width
    oc_vp[c4d.VP_REGION_Y2] = float(rd[c4d.RDATA_RENDERREGION_BOTTOM]) / arg.width

    logMessageDebug("Tile borders:\n\tleft: {0}, top: {1}, right: {2}, bottom: {3}".format(
        oc_vp[c4d.VP_REGION_X1], oc_vp[c4d.VP_REGION_Y1], oc_vp[c4d.VP_REGION_X2], oc_vp[c4d.VP_REGION_Y2])
    )

    if oc_vp[c4d.SET_PASSES_ENABLED]:
        if oc_vp[c4d.SET_PASSES_SAVEPATH]:
            logMessageError("Cannot use 'Tile Frame'in combination with Octane render passes 'File' output.\n"
                            "Please, resubmit either disabling 'Tiled Frame'\n or with a blank 'File' entry "
                            "in Octane 'Render Passes' settings (enable 'Show passes' instead)")



def setRenderParams(doc, arg):
    try:
        if argValid(arg.take):
            takeData = doc.GetTakeData()
            mainTake = takeData.GetMainTake()
            if takeData.GetCurrentTake().GetName() != arg.take:
                logMessage("Looking for take {0}".format(arg.take))
                jobtake = searchTakes_recursiveLoop(mainTake, arg.take)
                if jobtake:
                    logMessage("Setting current take to {0}".format(arg.take))
                    takeData.SetCurrentTake(jobtake)
                else:
                    logMessageError("Take {0} not found in scene".format(arg.take))
                    return False

        rd = doc.GetActiveRenderData()
        rd[c4d.RDATA_GLOBALSAVE] = True

        if arg.exportmode:
            #do not change output filename as the .ass file is our output filename for the job
            pass
        elif not argValid(arg.Channel):
            logMessage("INFO: setRenderParams: main outpout only")
            #main output only
            rd[c4d.RDATA_SAVEIMAGE]= True
            rd[c4d.RDATA_PATH] = arg.FNameVar
            try:
                if argValid(arg.FExt):
                    rd[c4d.RDATA_FORMAT] = c4d_ext_id(arg.FExt)
            except AttributeError:
                logMessage("Couldn't set output image format to {0}".format(arg.FExt))
                return False
            logMessage("INFO: Multipass is: "+str(rd[c4d.RDATA_MULTIPASS_ENABLE]))
            logMessage("INFO: Multipass save image is: "+str(rd[c4d.RDATA_MULTIPASS_SAVEIMAGE]))
            logMessage("INFO: Multipass filename is: "+str(rd[c4d.RDATA_MULTIPASS_FILENAME]))

        elif (arg.Channel=="Reg_Multi"):
            #main and multipass output
            #submitter plugin has read the multipass output as filename, not the main output
            logMessage("INFO: setRenderParams: main and multipass output")
            rd[c4d.RDATA_SAVEIMAGE]= True
            rd[c4d.RDATA_MULTIPASS_ENABLE]= True
            rd[c4d.RDATA_MULTIPASS_SAVEIMAGE] = True
            # rd[c4d.RDATA_MULTIPASS_SUFFIX] = True
            rd[c4d.RDATA_PATH] = arg.FNameVar
            rd[c4d.RDATA_MULTIPASS_FILENAME] = arg.FNameVar
            try:
                if argValid(arg.FExt):
                    rd[c4d.RDATA_FORMAT] = c4d_ext_id(arg.FExt)
            except AttributeError:
                logMessage("Couldn't set output image format to {0}".format(arg.FExt))
                return False

        elif (arg.Channel=="MultiPass"):
            logMessage("INFO: setRenderParams: all multipass output")
            rd[c4d.RDATA_SAVEIMAGE]=False
            rd[c4d.RDATA_MULTIPASS_ENABLE]= True
            rd[c4d.RDATA_MULTIPASS_SAVEIMAGE] = True
            # rd[c4d.RDATA_MULTIPASS_SUFFIX] = True
            rd[c4d.RDATA_MULTIPASS_FILENAME] = arg.FNameVar
            try:
                if argValid(arg.FExt):
                    rd[c4d.RDATA_MULTIPASS_SAVEFORMAT] = c4d_ext_id(arg.FExt)
            except AttributeError:
                logMessage("Couldn't set output image format to {0}".format(arg.FExt))
                return False

        else:
            logMessage("INFO: setRenderParams: one single multipass output")
            #a specific pass was set to render
            rd[c4d.RDATA_SAVEIMAGE]=False
            rd[c4d.RDATA_MULTIPASS_ENABLE]= True
            rd[c4d.RDATA_MULTIPASS_SAVEIMAGE] = True
            rd[c4d.RDATA_MULTIPASS_SUFFIX] = True
            rd[c4d.RDATA_MULTIPASS_FILENAME] = arg.FNameVar
            try:
                if argValid(arg.FExt):
                    rd[c4d.RDATA_MULTIPASS_SAVEFORMAT] = c4d_ext_id(arg.FExt)
            except AttributeError:
                logMessage("Couldn't set output image format to {0}".format(arg.FExt))
                return False
            # check for already enabled passes
            pass_exists = False
            mp = rd.GetFirstMultipass()
            while mp:
                if mp.GetName().lower() == arg.Channel.lower():
                    pass_exists = True
                    if mp.GetBit(c4d.BIT_VPDISABLED):
                        mp.ToggleBit(c4d.BIT_VPDISABLED)  # make sure pass is active
                elif not mp.GetBit(c4d.BIT_VPDISABLED):
                    mp.ToggleBit(c4d.BIT_VPDISABLED)  # disable other passes
                mp = mp.GetNext()

            if not pass_exists:
                new_pass = c4d.BaseList2D(c4d.Zmultipass)
                try:
                    new_pass.GetDataInstance()[c4d.MULTIPASSOBJECT_TYPE] = c4d_pass_id(arg.Channel)
                except AttributeError:
                    logMessageError("Couldn't find pass element for {0}".format(arg.Channel))
                    return False
                rd.InsertMultipass(new_pass)

        rd[c4d.RDATA_SIZEUNIT] = 0  # Pixels
        if argValid(arg.width):
            arg.width = int(arg.width)
            rd[c4d.RDATA_XRES] = arg.width
        else:
            arg.width = rd[c4d.RDATA_XRES]
        if argValid(arg.height):
            arg.height = int(arg.height)
            rd[c4d.RDATA_YRES] = arg.height
        else:
            arg.height = rd[c4d.RDATA_YRES]

        arg.width = round(arg.width, 3)
        arg.height = round(arg.height, 3)

        if argValid(arg.RegionLeft):
            # RR supplies region coordinates, while C4D uses borders size
            rd[c4d.RDATA_RENDERREGION] = True
            rd[c4d.RDATA_RENDERREGION_LEFT] = int(arg.RegionLeft)
            rd[c4d.RDATA_RENDERREGION_TOP] = int(arg.RegionTop)
            rd[c4d.RDATA_RENDERREGION_RIGHT] = int(arg.width -1 - int(arg.RegionRight))
            rd[c4d.RDATA_RENDERREGION_BOTTOM] = int(arg.height -1 - int(arg.RegionBtm))
            logMessage("renderRegions: {0}, {1}, {2}, {3}".format(rd[c4d.RDATA_RENDERREGION_LEFT],
                                                                  rd[c4d.RDATA_RENDERREGION_TOP],
                                                                  rd[c4d.RDATA_RENDERREGION_RIGHT],
                                                                  rd[c4d.RDATA_RENDERREGION_BOTTOM]))

            if arg.renderer.lower() == "redshift":
                tiled_checkRedshift_compatibility(arg, rd)
            elif arg.renderer.lower() == "octane":
                tiled_checkOctane_compatibility(arg, rd)

        if argValid(arg.camera):
            cam = doc.SearchObject(arg.camera)
            if cam and cam.GetType() != c4d.OBJECT_STAGE:
                doc.GetRenderBaseDraw().SetSceneCamera(cam, True)

        return True
    except Exception as e:
        logMessageError(str(e))
        return False


def renderFrames(FrStart, FrEnd, FrStep):
    global arg
    global doc

    FrStart = int(FrStart)
    FrEnd = int(FrEnd)
    FrStep = int(FrStep)

    rd = doc.GetActiveRenderData()
    fps = doc.GetFps()

    logMessage("Image res: X:"+str(arg.width)+"   Y: "+str(arg.height))
    rd[c4d.RDATA_FRAMESEQUENCE] = c4d.RDATA_FRAMESEQUENCE_MANUAL
    rflags = c4d.RENDERFLAGS_EXTERNAL | c4d.RENDERFLAGS_NODOCUMENTCLONE | c4d.RENDERFLAGS_SHOWERRORS

    localNoFrameLoop = arg.noFrameLoop
    if (not localNoFrameLoop):
        if arg.avFrameTime == 0:
            localNoFrameLoop = arg.renderer in ("redshift", "Octane")
        elif arg.avFrameTime < 60:
            localNoFrameLoop = True
        elif arg.avFrameTime < 140:
            localNoFrameLoop = arg.renderer in ("redshift", "Octane")

    try:
        if argValid(arg.FExt):

            if localNoFrameLoop:
                logMessage( "Rendering Frames (no frame loop): " + str(FrStart) + "-" + str(FrEnd))
                rd[c4d.RDATA_FRAMEFROM] = c4d.BaseTime(FrStart, fps)
                rd[c4d.RDATA_FRAMETO] = c4d.BaseTime(FrEnd, fps)
                rd[c4d.RDATA_FRAMESTEP] = FrStep

                flushLog()
                beforeFrame=datetime.datetime.now()

                if rd[c4d.RDATA_ALPHACHANNEL]:
                    logMessageDebug("bmp MultipassBitmap +alpha")
                    bmp = c4d.bitmaps.MultipassBitmap(int(arg.width), int(arg.height), c4d.COLORMODE_RGB)
                    bmp.AddChannel(True, True)
                else:
                    logMessageDebug("bmp MultipassBitmap rgb")
                    bmp = c4d.bitmaps.MultipassBitmap(int(arg.width), int(arg.height), c4d.COLORMODE_RGB)

                res = c4d.documents.RenderDocument(doc, rd.GetData(), bmp, rflags)
                bmp.FlushAll()
                del bmp

                if res == c4d.RENDERRESULT_OK:
                    logMessage("Render Successful")
                else:
                    msg = "error rendering document: "
                    if res == c4d.RENDERRESULT_OUTOFMEMORY:
                        msg += "Not enough memory."
                    elif res == c4d.RENDERRESULT_ASSETMISSING:
                        msg += "Assets (textures etc.) are missing"
                    elif res == c4d.RENDERRESULT_SAVINGFAILED:
                        msg += "Failed to save."
                    elif res == c4d.RENDERRESULT_USERBREAK:
                        msg += "User stopped the processing."
                    elif res == c4d.RENDERRESULT_GICACHEMISSING:
                        msg += "GI cache is missing."
                    else:
                        msg += "Unknown"
                    logMessageError(msg)
                    return

                nrofFrames= (FrEnd-FrStart)/FrStep +1
                afterFrame=datetime.datetime.now()
                afterFrame=afterFrame-beforeFrame;
                afterFrame=afterFrame/nrofFrames
                logMessage("Frame Time : "+str(afterFrame)+"  h:m:s.ms.  Frames Rendered: "+str(FrStart)+"-"+str(FrEnd))
                logMessage(" ")
                flushLog()
            else:
                logMessage( "Rendering Frames : " + str(FrStart) + "-" + str(FrEnd))
                for fr in xrange(FrStart, FrEnd + 1, FrStep):
                    kso_tcp.writeRenderPlaceholder_nr(arg.FName, fr, arg.FPadding, arg.FExt)
                    logMessage( "Rendering Frame #" + str(fr) +" ...")
                    doc.SetTime(c4d.BaseTime(fr, fps))
                    rd[c4d.RDATA_FRAMEFROM] = c4d.BaseTime(fr, fps)
                    rd[c4d.RDATA_FRAMETO] = c4d.BaseTime(fr, fps)
                    rd[c4d.RDATA_FRAMESTEP] = FrStep
                    flushLog()
                    beforeFrame=datetime.datetime.now()

                    bmp = c4d.bitmaps.MultipassBitmap(int(arg.width), int(arg.height), c4d.COLORMODE_RGB)
                    if rd[c4d.RDATA_ALPHACHANNEL]:
                        logMessageDebug("bmp MultipassBitmap +alpha")
                        bmp.AddChannel(True, True)
                    else:
                        logMessageDebug("bmp MultipassBitmap rgb")
                        #bmp = c4d.bitmaps.BaseBitmap()
                        #bmp.Init(x=int(arg.width), y=int(arg.height))

                    res = c4d.documents.RenderDocument(doc, rd.GetData(), bmp, rflags)

                    bmp.FlushAll()
                    del bmp

                    if res == c4d.RENDERRESULT_OK:
                        logMessage("Render Successful")
                    else:
                        msg = "error rendering document: "
                        if res == c4d.RENDERRESULT_OUTOFMEMORY:
                            msg += "Not enough memory."
                        elif res == c4d.RENDERRESULT_ASSETMISSING:
                            msg += "Assets (textures etc.) are missing"
                        elif res == c4d.RENDERRESULT_SAVINGFAILED:
                            msg += "Failed to save."
                        elif res == c4d.RENDERRESULT_USERBREAK:
                            msg += "User stopped the processing."
                        elif res == c4d.RENDERRESULT_GICACHEMISSING:
                            msg += "GI cache is missing."
                        else:
                            msg += "Unknown"
                        logMessageError(msg)
                        return

                    nrofFrames=1
                    afterFrame=datetime.datetime.now()
                    afterFrame=afterFrame-beforeFrame;
                    afterFrame=afterFrame/nrofFrames
                    logMessage("Frame Time : "+str(afterFrame)+"  h:m:s.ms.  Frame Rendered #" + str(fr) )
                    logMessage(" ")
                    flushLog()
        else:
            logMessage( "Rendering Movie...")
            bmp = c4d.bitmaps.MultipassBitmap(int(arg.width), int(arg.height), c4d.COLORMODE_RGB)
            doc.SetTime(c4d.BaseTime(FrStart, fps))
            rd[c4d.RDATA_FRAMEFROM] = c4d.BaseTime(FrStart, fps)
            rd[c4d.RDATA_FRAMETO] = c4d.BaseTime(FrEnd, fps)
            rd[c4d.RDATA_FRAMESTEP] = FrStep
            flushLog()
            beforeFrame=datetime.datetime.now()
            res = c4d.documents.RenderDocument(doc, rd.GetData(), bmp, rflags)

            if res == c4d.RENDERRESULT_OK:
                pass
            else:
                msg = "error rendering document: "
                if res == c4d.RENDERRESULT_OUTOFMEMORY:
                    msg += "Not enough memory."
                elif res == c4d.RENDERRESULT_ASSETMISSING:
                    msg += "Assets (textures etc.) are missing"
                elif res == c4d.RENDERRESULT_SAVINGFAILED:
                    msg += "Failed to save."
                elif res == c4d.RENDERRESULT_USERBREAK:
                    msg += "User stopped the processing."
                elif res == c4d.RENDERRESULT_GICACHEMISSING:
                    msg += "GI cache is missing."
                else:
                    msg += "Unknown"
                logMessageError(msg)
                return

            bmp.FlushAll()
            del bmp

            nrofFrames= (FrEnd-FrStart)/FrStep +1
            afterFrame=datetime.datetime.now()
            afterFrame=afterFrame-beforeFrame;
            afterFrame=afterFrame/nrofFrames
            logMessage("Average time per frame : "+str(afterFrame)+"  h:m:s.ms.  ")
            logMessage(" ")
            flushLog()

    except Exception as e:
        logMessageError(str(e))

def render_default():
    global arg
    if arg.renderer=="arnold" and arg.exportmode:
        arnold_ass_export(arg.FrStart, arg.FrEnd, arg.FrStep)
    else:
        renderFrames(arg.FrStart, arg.FrEnd, arg.FrStep)

def ksoRenderFrame(FrStart, FrEnd, FrStep):
    if arg.renderer=="arnold" and arg.exportmode:
        arnold_ass_export(FrStart, FrEnd, FrStep)
    else:
        renderFrames(FrStart, FrEnd, FrStep)

    logMessage("rrKSO Frame(s) done #" + str(FrEnd) + " ")
    logMessage(" " * 60)
    logMessage(" " * 60)
    logMessage(" " * 60)
    flushLog()


# KSO
def rrKSOStartServer():
    global arg
    try:
        logMessage("rrKSO startup...")
        if (arg.KSOPort == None) or (len(str(arg.KSOPort)) <= 0):
            arg.KSOPort = 7774
        HOST, PORT = "localhost", int(arg.KSOPort)
        server = kso_tcp.rrKSOServer((HOST, PORT), kso_tcp.rrKSOTCPHandler)
        flushLog()
        logMessage("rrKSO server started")
        server.print_port()
        flushLog()
        kso_tcp.rrKSONextCommand = ""
        while server.continueLoop:
            try:
                logMessageDebug("rrKSO waiting for new command...")
                server.handle_request()
                time.sleep(1) # handle_request() seem to return before handle() completed execution
            except Exception, e:
                logMessageError(e)
                server.continueLoop= False
                import traceback
                logMessageError(traceback.format_exc())
                return
            logMessage("rrKSO NextCommand ______________________________________________________________________________________________")
            logMessage("rrKSO NextCommand '" + kso_tcp.rrKSONextCommand+"'")
            logMessage("rrKSO NextCommand ______________________________________________________________________________________________")
            flushLog()
            if len(kso_tcp.rrKSONextCommand) > 0:
                if (kso_tcp.rrKSONextCommand == "ksoQuit()") or (kso_tcp.rrKSONextCommand == "ksoQuit()\n"):
                    server.continueLoop = False
                    kso_tcp.rrKSONextCommand = ""
                else:
                    exec kso_tcp.rrKSONextCommand
                    kso_tcp.rrKSONextCommand = ""
        logMessage("rrKSO closed")
    except Exception as e:
        logMessageError(str(e))

def render_KSO():
    rrKSOStartServer()

def render_default():
    global arg
    renderFrames(arg.FrStart,arg.FrEnd,arg.FrStep)


# Init
def init_c4d():
    """Parse command line arguments, setup logging, load scene, setup render
    Return False if no scene argument has been passed, False otherwise"""

    logMessage("Start cinema4D render setup. %rrVersion%")
    timeStart = datetime.datetime.now()

    global arg
    arg = argParser()
    arg.readArguments()

    if not argValid(arg.noFrameLoop):
        arg.noFrameLoop = False
    if not argValid(arg.avFrameTime):
        arg.avFrameTime = 0
    else:
        arg.avFrameTime= int(arg.avFrameTime)

    if argValid(arg.sceneFile):
        logMessage("loading scene file...")

        arg.sceneFile = os.path.normpath(arg.sceneFile)

        load_flags = c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS |\
                     c4d.SCENEFILTER_PROGRESSALLOWED | c4d.SCENEFILTER_DIALOGSALLOWED |\
                     c4d.SCENEFILTER_NONEWMARKERS

        global doc
        doc = c4d.documents.LoadDocument(arg.sceneFile, load_flags, None)
        if not doc:
            logMessageError("Failed to load file {0}".format(arg.sceneFile))
            return False

        timeEnd = datetime.datetime.now()
        timeEnd -= timeStart
        logMessage("Scene load time: " + str(timeEnd) + "  h:m:s.ms")
    else:
        print "no -scene parameter given, exiting rrKSO plugin"
        return False

    if argValid(arg.PyModPath):
        logMessage("Append python search path with '" + arg.PyModPath+"'")
        sys.path.append(arg.PyModPath)
        global kso_tcp
        global rrScriptHelper
        global rrOS

        import kso_tcp
        import rrScriptHelper
        from rrScriptHelper import rrOS
        doCrossOSPathConversionC4d(arg)

    if not setRenderParams(doc, arg):
        return False

    logMessage("Scene init done, starting to render... ")

    if arg.KSOMode and argValid(arg.KSOMode):
        render_KSO()
    else:
        render_default()

    return True


def PluginMessage(id, data):
    """Receive messages sent by Cinema4D or other plugins via GePluginMessage()"""
    if id == c4d.C4DPL_COMMANDLINEARGS:  # command line arguments received into sys.argv
        return True if init_c4d() else False

    if id == c4d.C4DPL_PROGRAM_STARTED:
        logMessage("Cinema4D application started")
        return True

    if id == c4d.C4DPL_STARTACTIVITY:
        logMessage("all PluginStart() methods called")
        return True

    return False


def PluginEnd():
    logMessage("Closing rrKSO plugin")
