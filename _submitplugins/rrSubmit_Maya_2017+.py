# -*- coding: cp1252 -*-
######################################################################
#
# Royal Render Plugin script for Maya 
# Author:  Royal Render, Holger Schoenberger and Kirill Kovalevskiy, Binary Alchemy
# Last change: %rrVersion%
# Copyright (c)  Holger Schoenberger - Binary Alchemy
# #win:     rrInstall_Env: MAYA_PLUG_IN_PATH, Directory
# #linux:   rrInstall_Env: MAYA_PLUG_IN_PATH, Directory
# #mac:     rrInstall_Copy:         /MacOS/plug-ins
# 
######################################################################

import os
import sys
import re
import tempfile
import subprocess
import copy

from xml.etree.ElementTree import ElementTree, Element, SubElement

import maya.OpenMaya as OpenMaya
import maya.OpenMayaMPx as OpenMayaMPx
import maya.cmds as cmds
import maya.mel
import maya.utils as mu
import maya.app.renderSetup.model.renderSetup as renderSetup

if sys.version_info.major == 2:
    range = xrange
    FileNotFoundError = OSError
else:
    from pathlib import Path
    def unichr(x):
        return str(x)


#Classes:
# rrDelightRenderPass
#    if 3delight is used for rendering, as 3delight has its own passes
# rrMayaLayer
#    get and hold all information about maya layer 
# rrsceneInfo
#    basic information about the scene
# rrPlugin
#    the main class that is called. the funciton doIt is the main function executed
#
#
#

def printDebug(msg):
    if (False):
        print(msg)

# option menus
FR_SET_OPTION = None


def is_ui_mode():
    gMainWindow = maya.mel.eval('$tmpVar=$gMainWindow')
    try:
        cmds.setParent(gMainWindow)
    except:
        return False
    return True


def rrWriteLog(msg):
    if is_ui_mode():
        cmds.confirmDialog(message=msg, button=['Abort'])
    else:
        print(msg)


def getSceneFps():
    FpsName= cmds.currentUnit(query=True, time=True)

    fps_names = {
        "game": 15.0,
        "film": 24.0,
        "pal": 25.0,
        "ntsc": 30.0,
        "show": 48.0,
        "palf": 50.0,
        "ntscf": 60.0,
        "millisec": 1000,
        "sec": 1.0,
        "min": 1.0/60.0,
        "hour": 1.0/60.0/60.0,
    }

    if FpsName in fps_names:
        return fps_names[FpsName]

    if FpsName.endswith("fps"):
        return float(FpsName.rstrip("fps"))

    return 25.0


def initGlobalVars():
    global _rrGL_mayaVersion
    global _rrGL_mayaVersionMinor
    global _rrGL_mayaVersionMinorStr
    _rrGL_mayaVersion = cmds.about(apiVersion=True)
    if (_rrGL_mayaVersion>10000000):
        _rrGL_mayaVersionMinor= _rrGL_mayaVersion % 10000
        _rrGL_mayaVersion= int(_rrGL_mayaVersion/10000)
        _rrGL_mayaVersionMinorStr= str(_rrGL_mayaVersionMinor).zfill(4)
    else:
        _rrGL_mayaVersionMinor=_rrGL_mayaVersion % 100
        _rrGL_mayaVersion=int(_rrGL_mayaVersion/100)
        _rrGL_mayaVersionMinorStr= str(_rrGL_mayaVersionMinor).zfill(2)
    global _rrGL_hasRenderSetup
    _rrGL_hasRenderSetup= False
    prefNewSystemEnabled= cmds.optionVar( q='renderSetupEnable' )
    if (prefNewSystemEnabled):
        if (_rrGL_mayaVersion>2016 or (_rrGL_mayaVersion==2016 and _rrGL_mayaVersionMinor>=50)):
            renderSetupCount   = len( cmds.ls( type="renderSetupLayer" ) )  #New 
            renderLayerCount   = len( cmds.ls( type="renderLayer" ) )  #Old 
            renderLayerCount= renderLayerCount - renderSetupCount  -1
            printDebug("New layer system count: "+str(renderSetupCount))          
            printDebug("Legacy layer count: "+str(renderLayerCount))
            _rrGL_hasRenderSetup= (renderSetupCount>0 or renderLayerCount<=0)

    global _rrGL_sceneFPSConvert
    _rrGL_sceneFPSConvert= getSceneFps() 
    if (_rrGL_hasRenderSetup):
        _rrGL_sceneFPSConvert= _rrGL_sceneFPSConvert / 6000.0
    printDebug("Scene FPS convert: "+str(_rrGL_sceneFPSConvert)+"   "+str(1.0/_rrGL_sceneFPSConvert))
    
    global _rrGL_RenderLayer_Current_Name
    global _rrGL_RenderLayer_MasterOverrides
    _rrGL_RenderLayer_Current_Name= cmds.editRenderLayerGlobals( query=True, currentRenderLayer=True )
    _rrGL_RenderLayer_MasterOverrides= cmds.listConnections( "defaultRenderLayer.adjustments", p=True, c=True)    
    
    
       
def rrOptions_GetValue(name, typeName, defaultValue, askForValue):
    if not cmds.objExists('RoyalRender_Options'):
        cmds.spaceLocator(n='RoyalRender_Options')
        cmds.setAttr("RoyalRender_Options.visibility", False)
        
    if not cmds.objExists( 'RoyalRender_Options.' + name):
        if (typeName == "filename"):
            cmds.addAttr("RoyalRender_Options", shortName=name, longName=name, dataType="string")
        else:
            cmds.addAttr("RoyalRender_Options", shortName=name, longName=name, dataType=typeName)
            
        if ((typeName == "filename") or (typeName == "string")):
            cmds.setAttr('RoyalRender_Options.' + name, defaultValue, type="string")
        else:
            cmds.setAttr('RoyalRender_Options.' + name, defaultValue, type=typeName)                
                        
        if (askForValue):
            res = cmds.promptDialog(title=name, message="Please enter " + name,
                                    button=['OK', 'Cancel'], defaultButton='OK',
                                    cancelButton="Cancel", dismissString='Cancel',
                                    text= str(defaultValue) )
            if res == "OK":
                newValue = cmds.promptDialog(query=True, text=True)
                if ((typeName == "filename") or (typeName == "string")):
                    cmds.setAttr('RoyalRender_Options.' + name, newValue, type="string")
                else:
                    cmds.setAttr('RoyalRender_Options.' + name, int(newValue), type=typeName)                
            
    return cmds.getAttr('RoyalRender_Options.' + name)


def rrOptions_SetValue(name, typeName, value):
    if not cmds.objExists('RoyalRender_Options'):
        cmds.spaceLocator(n='RoyalRender_Options')
        cmds.setAttr("RoyalRender_Options.visibility", False)
        
    if not cmds.objExists( 'RoyalRender_Options.' + name):
        if (typeName == "filename"):
            cmds.addAttr("RoyalRender_Options", shortName=name, longName=name, dataType="string")
        else:
            cmds.addAttr("RoyalRender_Options", shortName=name, longName=name, dataType=typeName)
            
    if ((typeName == "filename") or (typeName == "string")):
        cmds.setAttr('RoyalRender_Options.' + name, value, type="string")
    else:
        cmds.setAttr('RoyalRender_Options.' + name, value)                
                    
    return cmds.getAttr('RoyalRender_Options.' + name)
            
 
        
        

class rrDelightRenderPass:
    def __init__(self):
        self.name = ''
        self.camera =''
        self.seqStart = 1
        self.seqEnd = 100
        self.seqStep=1
        self.imageWidth=100
        self.imageHeight=100
        self.imageFileName=""
        self.imageFramePadding=1
        self.imageDir=""
        self.imageExtension=""
        self.imagePreNumberLetter=""
        self.ImageSingleOutputFile=False
        self.tmpId = 0
        self.preID = 0
        self.version= 0
        self.waitForPreID = 0
        self.channelFilenames = []
        self.channelExts = []
        self.renderer = "_3delight"
        self.software= "Maya"
        self.shortcodeAttrs = {'<ext>':self.getExtension,
                               '<scene>':self.getScene,
                               '<project>':self.getProject,
                               '<pass>':self.getPass,
                               '<camera>':self.getCamera,
                               '<output_variable>':self.getVariable
                               }
        
    def getProject(self):
        return cmds.workspace(q=True,fn=True)

    def getVariable(self):
        return cmds.getAttr(self.name+'.displayOutputVariables['+str(self.tmpId)+']')
    
    def getCamera(self):
        return self.camera
                
    def getPass(self):
        return self.name
                
    def getExtension(self):
        return cmds.getAttr(self.name+'.displayDrivers['+str(self.tmpId)+']')
    
    def getScene(self):
        return cmds.file(q=True,sn=True,shn=True).split('.')[0]
    
    def getLayer(self):
        current = cmds.editRenderLayerGlobals( query=True, currentRenderLayer=True )
        if current == "defaultRenderLayer":
            return "masterLayer"
        return current
    
    def getPassSettings(self,dpass):
        self.name = dpass
        if not self.findConnections(self.camera, dpass+'.camera'):
            print ('No camera selected in Pass: '+dpass+'!')

        if not cmds.getAttr(dpass+'.animation'):
            rrWriteLog("Animation checkbox is not on for pass:\n\n  " + dpass + "\n")
            return False

        #CONVERT TO INTS
        self.seqStart = int(cmds.getAttr(dpass+'.startFrame'))
        self.seqEnd = int(cmds.getAttr(dpass+'.endFrame'))
        self.seqStep = int(cmds.getAttr(dpass+'.increment'))
        
        res = cmds.getAttr(dpass+'.resolution')
        self.imageWidth = res[0][0]
        self.imageHeight = res[0][1]
        
        if not self.getRenderable(dpass):
            rrWriteLog('No Renderable Displays!')
            return False
        
#        get channels
        
        return True

    
    def findConnections(self,setting,plug):
        tmp = cmds.listConnections(plug,sh=True)
        if (tmp == None):
            return False
        if (len(tmp) == 0):
            return False
        setting = tmp[0]
        return True
    
    #EVAL SHORTCODES    
    def evalShortcodes(self,path,variable):
        #replace short codes                
        for k,v in self.shortcodeAttrs.iteritems():
            path = path.replace(k,v())
        
        #replace env vars                
        for k,v in os.environ.iteritems():
            path = path.replace('${'+k+'}',v)

        path = path.replace("<aov>",variable)
            
        paths = os.path.split(path)
        self.imageDir = paths[0]
        if paths[1] == '':
            rrWriteLog('Needs Image Filename!')
            return False
        
        
        tokens = paths[1].split('.')
        tokens.append(paths[0])
        return tokens
    
    
    def getRenderable(self,dpass):
        #print("get renderable")
        ImageperiodInExt= cmds.getAttr('defaultRenderGlobals.periodInExt')
        useLayerFileOutput = False
        try:
            max = cmds.getAttr(dpass+'.displayRenderables',s=True)
        except ValueError:
            max = cmds.getAttr(dpass + '.layerFileOutput', s=True)
            useLayerFileOutput = True
        primary = True
        for i in range(0,max):
            self.tmpId = i
            if useLayerFileOutput:
                renderable = cmds.getAttr(dpass + '.layerFileOutput[' + str(i) + ']')
            else:
                renderable = cmds.getAttr(dpass+'.displayRenderables['+str(i)+']')

            if renderable == 1:
                path = cmds.getAttr(dpass+'.displayFilenames['+str(i)+']')
                variable = cmds.getAttr(dpass+'.displayOutputVariables['+str(i)+']')
                variable= variable.replace("color aov_","")
                tokens = self.evalShortcodes(path,variable)

                if primary:
                    self.imageExtension = '.'+tokens[-2]
                    self.imageFileName = tokens[0]
                    if ((self.imageFileName[len(self.imageFileName)-1]) == '#'):
                        self.imageFileName= self.imageFileName[:len(self.imageFileName)-1]
                    primary = False
                else:
                    channelFile=tokens[-1]+os.sep+tokens[0]
                    if ((channelFile[len(channelFile)-1]) == '#'):
                        channelFile= channelFile[:len(channelFile)-1]
                    self.channelFilenames.append(channelFile)
                    self.channelExts.append('.'+tokens[-2])

        if primary:
            return False
        
        return True
    
    
    def __str__(self):
        return ' '.join(['Image Dir',self.imageDir,'Image Extension',self.imageExtension,'Image File',self.imageFileName])


def get_attr_in_RenderSetup_loopCollection(qAtrib, obj, objectName, objString, printLog ):  
    colList= obj.getCollections()
    if printLog and (len(colList)>0):
        printDebug ("     "+objString+": override collections: "+str(len(colList)))
    for col in colList:
        overrides= col.getOverrides()
        if printLog:
            if len(overrides)>0:
                printDebug ("     "+"     "+ objString+": collection " +str(col.name())+"  overrides "+str(len(overrides)))
        for oride in overrides:
            if (oride.typeName()=="absUniqueOverride"):
                oName= oride.targetNodeName()+"."+oride.attributeName()
                if (oName == qAtrib):
                    if printLog:
                        printDebug ("     "+"     "+str(oride.name())+"    absUniqueOverride  " + oride.targetNodeName()+"."+oride.attributeName())
                    if (oride.isEnabled()):
                        if printLog:
                            printDebug ("     "+"     "+"isEnabled  "+str(oride.getAttrValue()))
                        return oride.getAttrValue(), True , True     
            elif (oride.typeName()=="absOverride"):
                if (qAtrib.endswith("."+oride.attributeName())):
                    if printLog:
                        printDebug ("     "+"     "+str(oride.name())+"    absOverride "+oride.attributeName()+ "    "+str(col.getSelector().names()))
                    if (str(col.getSelector().names()).find(objectName)>0):
                        if printLog:
                            printDebug ("     "+"     "+"absOverride for OBject found "+oride.attributeName())
                        if (oride.isEnabled()):
                            if printLog:
                                printDebug("     "+"     "+"isEnabled  "+str(oride.getAttrValue()))
                            return oride.getAttrValue(), True   , True   
    return 0, True, False 
        
        
def get_attr_in_RenderSetup_loopCollectionB(qAtrib, obj, objectName, objString, printLog ):    
    colList= obj.getCollections()
    #print ( objString+": ######## "+str(len(colList)))
    for col in colList:
        overrides= col.getOverrides()
        #if len(overrides)>0:
            #print ( objString+": collection " +str(col.name())+"  overrides "+str(len(overrides)))
        for oride in overrides:
            if (oride.typeName()=="absUniqueOverride"):
                #print "     "+str(oride.name())+"    absUniqueOverride  " + oride.targetNodeName()+"."+oride.attributeName()
                oName= oride.targetNodeName()+"."+oride.attributeName()
                if (oName == qAtrib):
                    if (oride.isEnabled()):
                        oride.setSelfEnabled(False)
                        retVal= cmds.getAttr(qAtrib)
                        oride.setSelfEnabled(True)
                        #print "    isEnabled  "+str(retVal)
                        return retVal, False , True     
            elif (oride.typeName()=="absOverride"):
                #print "     "+str(oride.name())+"    absOverride "+oride.attributeName()+ "    "+str(col.getSelector().names())
                if (qAtrib.endswith("."+oride.attributeName())):
                    if (str(col.getSelector().names()).find(objectName)>0):
                        #print "     absOverride for OBject found "+oride.attributeName()
                        if (oride.isEnabled()):
                            oride.setSelfEnabled(False)
                            retVal= cmds.getAttr(qAtrib)
                            oride.setSelfEnabled(True)
                            #print "    isEnabled  "+str(retVal)
                            return retVal, False , True     
    return 0, True, False         
        
        
def get_attr_in_RenderSetup(qAtrib, qLayer):
    objectName= ""
    if (qAtrib.find('.')>0):
        objectName= qAtrib[:qAtrib.find('.')]
    if (not objectName.startswith('|')):
        objectName='|'+objectName
    printLog= False
    #if (qAtrib.find('aiAOV')<0) and (qAtrib.find('Arnold')<0): 
    #    printLog= True
    #if (qAtrib.find('Frame')>0): 
     #   printLog= True
    if printLog:
        printDebug ("Attrib to find: " + qLayer.name() + "  " + str(qAtrib))
    #import maya.app.renderSetup.model.renderSetup as renderSetup
    rs = renderSetup.instance() 
    layerActive= rs.getVisibleRenderLayer()   
    #check if the current applied value is the one we want
    if (qLayer == layerActive):
        return cmds.getAttr(qAtrib), False    
    #check if our layer has an override
    rLayers = rs.getRenderLayers()
    for layer in rLayers:
        if (layer != qLayer):
            continue
        #TODO: replace with     allOverrides= maya.app.renderSetup.model.utils.getOverridesRecursive(layer)     for oride in allOverrides:
        value, override, foundItem= get_attr_in_RenderSetup_loopCollection(qAtrib, layer,objectName,layer.name(), printLog )
        if (foundItem):
            return value, override
        colList= layer.getCollections()
        for col in colList:
            value, override, foundItem= get_attr_in_RenderSetup_loopCollection(qAtrib, col,objectName,layer.name()+" - "+col.name(), printLog )
            if (foundItem):
                return value, override
            
    #check if the current scene layer (not the current in this script) has an override applied to it:
    for layer in rLayers:
        if (layer != layerActive):
            continue
        value, override, foundItem= get_attr_in_RenderSetup_loopCollectionB(qAtrib, layer,objectName,layer.name(), printLog )
        if (foundItem):
            return value, override
        colList= layer.getCollections()
        for col in colList:
            value, override, foundItem= get_attr_in_RenderSetup_loopCollectionB(qAtrib, col,objectName,layer.name()+" - "+col.name(), printLog )
            if (foundItem):
                return value, override
    #there are no overrides for this one
    return cmds.getAttr(qAtrib), False          
        
def get_attr_in_LegacyLayer(qAtrib, qLayer):
    #printDebug("get_attr_in_LegacyLayer "+str(qAtrib)+"   "+str(qLayer))
    if qLayer == 'masterLayer':
        qLayer = 'defaultRenderLayer'
    global _rrGL_RenderLayer_Current_Name
    if (qLayer == _rrGL_RenderLayer_Current_Name):
        return cmds.getAttr(qAtrib), False   
    overrideFound = False
    retValue = 0
    global _rrGL_RenderLayer_MasterOverrides
    if (_rrGL_RenderLayer_MasterOverrides != None):
        for o in range(0, int(len(_rrGL_RenderLayer_MasterOverrides) / 2)):
            OWhat=_rrGL_RenderLayer_MasterOverrides[o*2+1]
            _rrGL_RenderLayer_MasterOverrides[o*2]=_rrGL_RenderLayer_MasterOverrides[o*2].replace(".plug",".value")
            OValue=cmds.getAttr(_rrGL_RenderLayer_MasterOverrides[o*2])
            if (OWhat==qAtrib):
                retValue= OValue
                overrideFound = True
            
    layerOverrides= cmds.listConnections( qLayer+".adjustments", p=True, c=True)
    #printDebug("get_attr_in_LegacyLayer "+str(layerOverrides))
    if (layerOverrides != None):
        for o in range(0, int(len(layerOverrides) / 2)):
            OWhat=layerOverrides[o*2+1]
            layerOverrides[o*2]=layerOverrides[o*2].replace(".plug",".value")
            OValue=cmds.getAttr(layerOverrides[o*2])
            if (OWhat==qAtrib):
                #printDebug("get_attr_in_LegacyLayer "+str(OWhat)+" "+str(OValue))
                retValue= OValue
                overrideFound = True
    if (overrideFound):
        return retValue, True
    return cmds.getAttr(qAtrib), False          


class rrMayaLayer:
    def __init__(self):
        self.renderSetupObj= None
        self.name=""
        self.camera=""
        self.renderer=""
        self.RequiredLicenses=""
        self.IsActive=False
        self.seqStart=1
        self.seqEnd=100
        self.seqStep=1
        self.seqFileOffset=0
        self.imageWidth=100
        self.imageHeight=100
        self.imageFileName=""
        self.imageFramePadding=1
        self.imageDir=""
        self.imageExtension=""
        self.imagePreNumberLetter=""
        self.ImageSingleOutputFile=False
        self.channelName=""
        self.maxChannels=0
        self.channelFileName=[]
        self.channelExtension=[]
        self.tempModifyExtension=False
        self.tempModifyByframe=1.0
        self.tempModifyStart=1
        self.tempImageExtension="unknown"
        self.tempExtensionPadding=1
        self.tempVersionTag=""
        self.tempIsGI=False
        self.tempIsGI2=False
        self.tempGIFileName=""
        self.tempCamNames = []
        self.tempCamRenderable = []
        self.nbRenderableCams=0
        self.rendererVersion=""
        self.customScriptFile=""
        self.preID = 0
        self.waitForPreID = 0
        self.sceneName=""
        self.software= "Maya"
        self.version= 0
        return


        

 
         
    
    def get_attr(self, qAtrib):
        global _rrGL_hasRenderSetup
        value=0
        wasoverride= False
        if (_rrGL_hasRenderSetup):
            value, wasoverride = get_attr_in_RenderSetup(qAtrib, self.renderSetupObj)
        else:
            value, wasoverride = get_attr_in_LegacyLayer(qAtrib, self.name)
        return value
                    
    def get_attr_wasOverride(self, qAtrib):
        global _rrGL_hasRenderSetup
        if (_rrGL_hasRenderSetup):
            return get_attr_in_RenderSetup(qAtrib, self.renderSetupObj)
        else:
            return get_attr_in_LegacyLayer(qAtrib, self.name)

    def CalcImageExtension(self):
        printDebug("CalcImageExtension   "+self.renderer)
        if (self.renderer=="renderMan"):
            imfKeyPlugin=self.get_attr("rmanFinalOutputGlobals0.rman__riopt__Display_type")
            rmanImages = maya.mel.eval('rman getPrefAsArray ImageFormatQuantizationTable;')
            for img in range(1, len(rmanImages)-1):
                if (rmanImages[img]==imfKeyPlugin):
                    self.tempImageExtension= rmanImages[img-1]
                    if (self.tempImageExtension.find("(")>=0):
                        self.tempImageExtension=self.tempImageExtension[self.tempImageExtension.find("(")+1:]
                        if (self.tempImageExtension.find(")")>=0):
                            self.tempImageExtension=self.tempImageExtension[:self.tempImageExtension.find("(")]
                            return
            self.tempImageExtension=".unknown"
            return

        if (self.renderer=="redshift"):
            imgFormatID= int(self.get_attr('redshiftOptions.imageFormat'))
            if (imgFormatID==0):
                self.tempImageExtension="iff"
            elif (imgFormatID==0):
                self.tempImageExtension="iff"
            elif (imgFormatID==1):
                self.tempImageExtension="exr"
            elif (imgFormatID==2):
                self.tempImageExtension="png"
            elif (imgFormatID==3):
                self.tempImageExtension="tga"
            elif (imgFormatID==4):
                self.tempImageExtension="jpg"
            elif (imgFormatID==5):
                self.tempImageExtension="tif"
            return
         
        imgFormatID=int(self.get_attr('defaultRenderGlobals.imageFormat'))   
        imfKeyPlugin=self.get_attr("defaultRenderGlobals.imfPluginKey")        
        #MRay, Maya Software, maxwell, arnold:
        if (imgFormatID== 60):
            self.tempImageExtension="swf"
        elif (imgFormatID== 61):
            self.tempImageExtension="ai"
        elif (imgFormatID== 62):
            self.tempImageExtension="svg"
        elif (imgFormatID== 63):
            self.tempImageExtension="swft"
        elif (imgFormatID== 50):
            mayaimfPlugInExt = maya.mel.eval('$rrTempimfPlugInExt = $imfPlugInExt;')
            mayaimfPlugInKey = maya.mel.eval('$rrTempimfPlugInKey = $imfPlugInKey;')
            for i in range(0, len(mayaimfPlugInKey)):
                if (mayaimfPlugInKey[i]==imfKeyPlugin):
                    self.tempImageExtension=mayaimfPlugInKey[i]
        elif (imgFormatID== 51):
            self.tempImageExtension=imfKeyPlugin
        else:
            self.tempImageExtension = maya.mel.eval('getImfImageExt()')
            
        if (self.renderer=="mentalRay"):
            if (self.tempImageExtension=="sgi"):
                self.tempImageExtension="rgb"
            if (self.tempImageExtension=="tifu"):
                self.tempImageExtension="tif"
            if (self.tempImageExtension=="qntntsc"):
                self.tempImageExtension="yuv"
            if (self.tempImageExtension=="qntpal"):
                self.tempImageExtension="yuv"
        if (self.tempImageExtension=="jpeg"):
            self.tempImageExtension="jpg"
        if (self.renderer=="maxwell"):
            if (imgFormatID== 31):
                self.tempImageExtension="exr"
            elif (imgFormatID== 35):
                self.tempImageExtension="hdr"
            elif (imgFormatID== 36):
                self.tempImageExtension="jp2"
        if (self.renderer=="arnold"):
            mtoaVersion = self.rendererVersion 
            mtoaVersion = mtoaVersion[:1]
            if (mtoaVersion<"3"):
                if (self.tempImageExtension=="jpg"):
                    self.tempImageExtension="jpeg"
            if (self.tempImageExtension=="deepexr"):
                self.tempImageExtension="exr"
        if (self.renderer=="_3delight"):
            if (self.tempImageExtension=="tiff"):
                self.tempImageExtension="tif"
        if (self.renderer=="MayaKrakatoa"):
            if int(self.get_attr('MayaKrakatoaRenderSettings.forceEXROutput')) == 1:
                self.tempImageExtension="exr"


    #add Arnold AOV to layer
    def addAOVToLayer(self):
        if (self.get_attr('defaultArnoldRenderOptions.aovMode')==0):
            return
        if (self.get_attr('defaultArnoldDriver.mergeAOVs')==1):
            return
        #name = self.name
        #if self.name == 'masterLayer':
         #   name = 'defaultRenderLayer'
        passes = cmds.ls(type='aiAOV')
        if passes == None or len(passes) == 0:
            return
        for p in passes:
            if((cmds.nodeType(p)=='aiAOV') and (self.get_attr(p+'.enabled') == 1)):
                self.channelFileName.append(self.imageFileName.replace('<Channel>', self.get_attr(p+'.name')))
                self.channelExtension.append(self.imageExtension)
                self.maxChannels +=1

    #add Redshift AOV to layer
    def addRedshiftAOVToLayer(self):
        if (self.get_attr('redshiftOptions.aovGlobalEnableMode')==0):
            return
        combineWithBeauty= self.get_attr('redshiftOptions.exrForceMultilayer')==1
        passes = cmds.ls(type='RedshiftAOV')
        if passes == None or len(passes) == 0:
            return
        printDebug("AOV self.imageDir   "+self.imageDir+" self.imageFileName "+self.imageFileName)
        if (len(self.imageDir)==0):
            orgFileSplit= self.imageFileName
        else:
            orgFileSplit= self.imageDir+ "/" + self.imageFileName
        orgFileSplit= orgFileSplit.rpartition('/')
        orgFileSplitDir= orgFileSplit[0]
        orgFileSplitName= orgFileSplit[2]
        if (orgFileSplitName.endswith('.')):
            orgFileSplitName = orgFileSplitName[:-1]
        
        printDebug("AOV1 orgFileSplit   "+orgFileSplitDir+"   "+orgFileSplitName)                

        #Find Redshift beauty AOV as this disables the main output.
        #And set it as RR job main output
        #But we have to keep the original file prefix of the render settings (same as <BeautyPath>/<BeautyFile>)  in job.ImageNameVariables
        beautyAovIdx = -1
        for p in passes:
            aovType= cmds.getAttr(p+'.aovType')
            if (self.get_attr(p+'.enabled') == 1 and aovType=="Beauty"):
                beautyAovIdx=p
                aovName= self.get_attr(p+'.name')
                filePrefix = self.get_attr(p+'.filePrefix')
                filePrefix = filePrefix.strip()
                if (len(filePrefix)==0):
                    continue
                filePrefix= filePrefix.replace('\\','/')
                filePrefix= filePrefix.replace("<RenderPass>","<Channel>")
                newFileName=""
                printDebug("AOV2   "+filePrefix+"   "+newFileName)                
                if (filePrefix.startswith("<BeautyPath>/")):
                    newFileName +=  orgFileSplitDir + "/"
                    filePrefix = filePrefix[len("<BeautyPath>/"):]
                if (filePrefix.startswith("<BeautyPath>")):
                    newFileName +=  orgFileSplitDir
                    filePrefix = filePrefix[len("<BeautyPath>"):]
                printDebug("AOV3   "+filePrefix+"   "+newFileName)
                filePos= filePrefix.find("<BeautyFile>")
                if (filePos >= 0):
                    if (filePos>0):
                        newFileName += "<RemoveVar " + filePrefix[:filePos] + ">"
                        filePrefix = filePrefix[filePos:]
                    newFileName += orgFileSplitName
                    filePrefix = filePrefix[len("<BeautyFile>"):]
                printDebug("AOV4   "+filePrefix+"   "+newFileName)
                filePrefix= filePrefix.replace("<BeautyFile>",orgFileSplitName)
                redVersion = self.rendererVersion
                if (redVersion<"3.0.65"):
                    self.channelName= aovName
                    newFileName += "<RemoveVar " + filePrefix + ">"
                filePrefix=""
                printDebug("AOV5   "+filePrefix+"   "+newFileName)
                printDebug("AOV6 beauty found  "+newFileName)
                self.imageFileName= newFileName + "."
                self.imageDir=""
                break
        
        for p in passes:
            if (p==beautyAovIdx):
                continue
            if (self.get_attr( p+'.enabled') == 1):
                aovType= cmds.getAttr(p+'.aovType')
                if (aovType!="Cryptomatte" and combineWithBeauty):
                    continue
                aovName= self.get_attr( p+'.name')
                filePrefix = self.get_attr( p+'.filePrefix')
                filePrefix = filePrefix.strip()
                printDebug("AOV7   "+aovType+"   "+aovName+"   filePrefix:"+str(filePrefix))
                if (len(filePrefix)==0):
                    filePrefix= orgFileSplitDir+'/'+orgFileSplitName
                    if (filePrefix[len(filePrefix)-1]!="."):
                        filePrefix += "."
                else:
                    filePrefix += "."
                    printDebug("AOV8 add   "+aovName+": "+filePrefix)                
                    filePrefix= filePrefix.replace('\\','/')
                    filePrefix= filePrefix.replace("<BeautyPath>",orgFileSplitDir)
                    filePrefix= filePrefix.replace("<BeautyFile>",orgFileSplitName)
                    filePrefix= filePrefix.replace("<RenderPass>", "<IMS>"+aovName)   
                printDebug("AOV9 add   "+aovName+": "+filePrefix)                
                self.channelFileName.append(filePrefix)
                self.channelExtension.append(self.imageExtension)
                self.maxChannels +=1
                

    #add MRay Render Passes to layer
    def addChannelsToLayer(self):
        name = self.name
        if self.name == 'masterLayer':
            name = 'defaultRenderLayer'
        passes = cmds.listConnections(name+'.renderPass')
        if passes == None or len(passes) == 0:
            return
        for p in passes:
            if ((cmds.nodeType(p)=="renderPass") and (self.get_attr(p+'.renderable') == 1)):
                self.channelFileName.append(self.imageFileName.replace('<Channel>',p))
                self.channelExtension.append(self.imageExtension)
                self.maxChannels +=1



    def getImageOut_imageFilePrefix(self):
        maya.mel.eval('renderSettings -fin -lyr "'+self.name+'";') # workaround for batch mode to load python command we execute next
        RenderOut= cmds.renderSettings( ign=True,lyr=self.name)        
        RenderOut= RenderOut[0]
        #printDebug("     getImageOut_imageFilePrefix   RenderOut "+RenderOut)
        RenderOut=RenderOut.replace("\\","/")
        FNsplitter=""
        self.imageFramePadding=0
        if (RenderOut.find("%0n")>=0):
            FNsplitter="%0n"
            self.imageFramePadding=1
        if (RenderOut.find("%1n")>=0):
            FNsplitter="%1n"
            self.imageFramePadding=1
        if (RenderOut.find("%2n")>=0):
            FNsplitter="%2n"
            self.imageFramePadding=2
        if (RenderOut.find("%3n")>=0):
            FNsplitter="%3n"
            self.imageFramePadding=3
        if (RenderOut.find("%4n")>=0):
            FNsplitter="%4n"
            self.imageFramePadding=4
        if (RenderOut.find("%5n")>=0):
            FNsplitter="%5n"
            self.imageFramePadding=5
        if (RenderOut.find("%6n")>=0):
            FNsplitter="%6n"
            self.imageFramePadding=6
        if (RenderOut.find("%7n")>=0):
            FNsplitter="%7n"
            self.imageFramePadding=7
        if (RenderOut.find("%8n")>=0):
            FNsplitter="%8n"
            self.imageFramePadding=8
        if (RenderOut.find("%9n")>=0):
            FNsplitter="%9n"
            self.imageFramePadding=9
            
        if (len(FNsplitter)>0):
            Splitted=RenderOut.split(FNsplitter,1)
            self.imageFileName=Splitted[0]
            self.imageExtension=Splitted[1]
            if ((self.renderer=="renderMan") and (self.imagePreNumberLetter=="_")):
                if (self.name=="masterLayer"):
                    self.imageFileName+="__"
                else:
                    self.imageFileName+="_"
        else:
            self.imageFileName=RenderOut
            self.imageExtension=""
            
        #printDebug("     getImageOut_imageFilePrefix   self.imageFileName "+self.imageFileName)
        self.replaceMayaVariablesWithRR()            
        #printDebug("     getImageOut_imageFilePrefix   self.imageFileName "+self.imageFileName)

        isUNC= (len(self.imageFileName)>2 and (self.imageFileName[0]=="/") and (self.imageFileName[1]=="/"))
        self.imageFileName=self.imageFileName.replace("//","/")
        if (isUNC):
            self.imageFileName='/'+self.imageFileName
        if ((self.renderer=="arnold") and (self.get_attr('defaultArnoldRenderOptions.aovMode')!=0) and (self.get_attr('defaultArnoldDriver.mergeAOVs')!=1) and (self.imageFileName.find("<Channel>")<0)):
            if (len(os.path.dirname(self.imageFileName))>0):
                self.imageFileName=os.path.dirname(self.imageFileName)+"/<Channel>/"+os.path.basename(self.imageFileName)
            else:
                self.imageFileName="<Channel>/"+self.imageFileName

        if (self.imageFileName.find("<Channel>")>=0):
            if (self.renderer=="mentalRay") :
                self.channelName="MasterBeauty"
            elif (self.renderer=="arnold"):
                self.channelName="beauty"
            elif (self.renderer=="redshift"):
                self.channelName=""
            else:
                self.imageFileName= self.imageFileName.replace("<Channel>","")
                
        printDebug("     getImageOut_imageFilePrefix   self.imageFileName "+self.imageFileName)
        

    def replaceMayaVariablesWithRR(self):
        self.imageFileName=self.imageFileName.strip()
        self.imageFileName=self.imageFileName.replace("%/l","<Layer>/")
        self.imageFileName=self.imageFileName.replace("%l","<Layer>")
        self.imageFileName=self.imageFileName.replace("<layer>","<Layer>")
        self.imageFileName=self.imageFileName.replace("<RenderLayer>","<Layer>")
        self.imageFileName=self.imageFileName.replace("<renderLayer>","<Layer>") #lowercase 'R' is not recognized by Maya, but by Redshift
        self.imageFileName=self.imageFileName.replace("<RenderPass>","<Channel>")
        self.imageFileName=self.imageFileName.replace("%/c","<Camera>/")
        self.imageFileName=self.imageFileName.replace("%c","<Camera>")
        self.imageFileName=self.imageFileName.replace("<camera>","<Camera>")
        self.imageFileName=self.imageFileName.replace("%/s","<SceneFile>/")
        self.imageFileName=self.imageFileName.replace("%s","<SceneFile>")
        self.imageFileName=self.imageFileName.replace("<Scene>","<SceneFile>")
        self.imageFileName=self.imageFileName.replace("<scene>","<SceneFile>")
        self.imageFileName=self.imageFileName.replace("<channel>","<Channel>")
        self.imageFileName=self.imageFileName.replace("<aov>","<Channel>")
        self.imageFileName=self.imageFileName.replace("<ext>",self.tempImageExtension)
        self.imageFileName=self.imageFileName.replace("%e",self.tempImageExtension)
        self.imageFileName=self.imageFileName.replace("<Extension>",self.tempImageExtension)
        self.imageFileName=self.imageFileName.replace("<Version>",self.tempVersionTag)
        self.imageFileName=self.imageFileName.replace("%v",self.tempVersionTag)
        self.imageFileName=self.imageFileName.replace("%/v",self.tempVersionTag+"/")
        
        self.imageExtension= self.imageExtension.replace("%e",self.tempImageExtension)
        self.imageExtension= self.imageExtension.replace("<Extension>",self.tempImageExtension)        


    def getImageOut(self,sceneInfo,isLayerRendering):
        printDebug ("getImageOut()")
        ImageperiodInExt= self.get_attr('defaultRenderGlobals.periodInExt')
        if (ImageperiodInExt==0):
            self.imagePreNumberLetter=""
        elif (ImageperiodInExt==1):
            self.imagePreNumberLetter="."
        elif (ImageperiodInExt==2):
            self.imagePreNumberLetter="_"


        #get resolved image file prefix
        self.getImageOut_imageFilePrefix()
        if (isLayerRendering and (self.imageFileName.lower().find("<layer>")<0)):
            self.imageFileName= os.path.dirname(self.imageFileName) + "<Layer>/" + os.path.basename(self.imageFileName)
            
        
        #Now add the base path to the file prefix
        self.imageDir= cmds.workspace(fre="images")
        #if (self.renderer=="renderMan"):
         #   self.imageDir= maya.mel.eval('rman workspace GetDir rfmImages 1;')
            
            
        isRelative=True
        if (len(self.imageFileName)>1):
            self.imageFileName=self.imageFileName.replace("\\","/")
            if ((self.imageFileName[0]=="/" and (self.imageFileName[1]!="<")) or (self.imageFileName[1]==":")):
                isRelative=False
                self.imageDir=""
        if (isRelative):
            printDebug("getImageOut - imageFileName isRelative(1), add "+self.imageDir)
            if (len(self.imageDir)>1):
                self.imageDir= self.imageDir.replace("\\","/")
                if ((self.imageDir[0]=="/") or (self.imageDir[1]==":")):
                    isRelative=False
        else:
            printDebug ("getImageOut - imageFileName isAbsolute")
        if (isRelative):
            printDebug ("getImageOut - imageFileName isRelative(2), add "+sceneInfo.DatabaseDir)
            self.imageDir= sceneInfo.DatabaseDir + self.imageDir
            self.imageDir+= "/"

        
        #mentalcoreGlobals does it differently:
        if (cmds.objExists ( "mentalcoreGlobals" ) and (int(self.get_attr ('mentalcoreGlobals.enable'))==1 )):
            outMode = int(self.get_attr ('mentalcoreGlobals.file_mode'))
            if (outMode!=2):
                ImageperiodInExt= self.get_attr('defaultRenderGlobals.periodInExt')
                if (ImageperiodInExt!=1):
                    rrWriteLog('You have to use name.#.ext for MentalCore!')
                    return False
                filepath=""
                filename=""
                (filepath, filename)= os.path.split(self.imageFileName)
                self.channelName="beauty"
                filepath=filepath+"/<Channel-removeVar>/"
                if (filename[len(filename)-1]=="."):
                    filename=filename[:len(filename)-1]
                    filename=filename+"_<Channel-removeVar>."
                else:
                    filename=filename+"_<Channel-removeVar>"
                self.imageFileName=filepath+filename
        printDebug("getImageOut - imageDir "+self.imageDir+"   imageFileName  "+self.imageFileName)
        return True

 
    #Get all cameras,  with layer overrides
    def getLayerCamera(self):
        self.tempCamRenderable= []
        self.tempCamNames= []
        cameraList=cmds.ls(ca=True)
        for cam in cameraList:
            self.tempCamNames.append(cam)
            if (self.get_attr(cam+'.renderable')):
                self.tempCamRenderable.append(True)
            else:
                self.tempCamRenderable.append(False)
                
        self.nbRenderableCams=0
        for c in range(0, len(self.tempCamNames)):
            if (self.tempCamRenderable[c]):
                self.nbRenderableCams=self.nbRenderableCams+1
            
        
        #convert CameraShape into camera name:
        for c in range(0, len(self.tempCamRenderable)):
            if (self.tempCamRenderable[c]):
                transformNode = cmds.listRelatives(self.tempCamNames[c],parent=True)
                transformNode=transformNode[0]
                if (self.tempCamNames[c].find(transformNode+"|")>=0):
                    transformNode= "|"+transformNode
                if ((self.renderer=="_3delight") or (self.renderer=="renderMan" and (self.rendererVersion[:2]>21))):
                    self.camera= self.tempCamNames[c]
                else:
                    self.camera= transformNode
                
        
                
    
                    
    def getLayerRenderer(self):
        self.renderer= self.get_attr('defaultRenderGlobals.currentRenderer')
        if (self.renderer=="renderManRIS"):
            self.renderer = "renderMan"
        if (self.renderer=="renderman"):
            self.renderer = "renderMan"
            
        if (self.renderer=="arnold"):
            self.rendererVersion=cmds.pluginInfo( 'mtoa', query=True, version=True )
        if (self.renderer=="vray"):
            self.rendererVersion=cmds.pluginInfo( 'vrayformaya', query=True, version=True )
            if (self.rendererVersion=="Next"):
                self.rendererVersion= cmds.vray('version')
        if (self.renderer=="renderMan"):
            self.rendererVersion=cmds.pluginInfo( 'RenderMan_for_Maya', query=True, version=True )
            verBuildSeperator= self.rendererVersion.find('@')
            if (verBuildSeperator>0):
                self.rendererVersion= self.rendererVersion[:verBuildSeperator]
                self.rendererVersion= self.rendererVersion.strip()
        if (self.renderer=="redshift"):
            self.rendererVersion=cmds.pluginInfo( 'redshift4maya', query=True, version=True )
        if (self.renderer=="_3delight"):
            global _rrGL_mayaVersion
            self.rendererVersion=cmds.pluginInfo( "3delight_for_maya"+str(_rrGL_mayaVersion), query=True, version=True )


    def getLayerSettings_Renderman22(self,sceneInfo,isLayerRendering):
        printDebug ("rrSubmit - getImageOut_renderman22")
        self.imageWidth= int(self.get_attr('defaultResolution.width'))
        self.imageHeight= int(self.get_attr('defaultResolution.height'))
        self.tempModifyExtension=(self.get_attr('defaultRenderGlobals.modifyExtension')==True)
        self.tempModifyStart=int(self.get_attr('defaultRenderGlobals.startExtension'))
        self.tempModifyByframe=self.get_attr('defaultRenderGlobals.byExtension')
        self.ImageSingleOutputFile=False

        if ( self.tempModifyExtension):
            self.seqFileOffset=self.tempModifyStart-1
            if (self.tempModifyByframe!=1.0):
                rrWriteLog("No 'By Frame' renumbering allowed!\n Value: "+str(self.tempModifyByframe)+"  Layer: "+self.name+"\n")
                return False
                
        isRelativeOutputDir=False
        self.imageDir=""
        self.imageFileName= self.get_attr('rmanGlobals.imageOutputDir') +"/"+ self.get_attr('rmanGlobals.imageFileFormat')
        printDebug("     getImageOut_renderman22   self.imageFileName "+self.imageFileName)
        if (not isLayerRendering):
            self.imageFileName= self.imageFileName.replace("<layer>","")
        if (self.imageFileName.startswith("<ws>")):
            isRelativeOutputDir=True
            self.imageFileName= self.imageFileName[5:]
        printDebug("     getImageOut_renderman22   self.imageFileName "+self.imageFileName)
        self.imageFileName= self.imageFileName.replace("<version>",str(self.get_attr('rmanGlobals.version')))
        self.imageFileName= self.imageFileName.replace("<take>",str(self.get_attr('rmanGlobals.take')))
 
        
        self.imageFileName=self.imageFileName.replace("\\","/")
        FNsplitter=""
        self.imageFramePadding=0
        if (self.imageFileName.find("<f0>")>=0):
            FNsplitter="<f0>"
            self.imageFramePadding=1
        if (self.imageFileName.find("<f1>")>=0):
            FNsplitter="<f1>"
            self.imageFramePadding=1
        if (self.imageFileName.find("<f2>")>=0):
            FNsplitter="<f2>"
            self.imageFramePadding=2
        if (self.imageFileName.find("<f3>")>=0):
            FNsplitter="<f3>"
            self.imageFramePadding=3
        if (self.imageFileName.find("<f4>")>=0):
            FNsplitter="<f4>"
            self.imageFramePadding=4
        if (self.imageFileName.find("<f5>")>=0):
            FNsplitter="<f5>"
            self.imageFramePadding=5
        if (self.imageFileName.find("<f6>")>=0):
            FNsplitter="<f6>"
            self.imageFramePadding=6
        if (self.imageFileName.find("<f7>")>=0):
            FNsplitter="<f7>"
            self.imageFramePadding=7
        if (self.imageFileName.find("<f8>")>=0):
            FNsplitter="<f8>"
            self.imageFramePadding=8
        if (self.imageFileName.find("<f9>")>=0):
            FNsplitter="<f9>"
            self.imageFramePadding=9
            
        if (len(FNsplitter)>0):
            splitted=self.imageFileName.split(FNsplitter,1)
            self.imageFileName=splitted[0]
            self.imageExtension=splitted[1]
        else:
            self.imageFileName= self.imageFileName
            self.imageExtension=""
            
        printDebug("     getImageOut_renderman22   self.imageFileName "+self.imageFileName)
        printDebug("     getImageOut_renderman22   self.imageExtension "+self.imageExtension)

        isUNC= (len(self.imageFileName)>2 and (self.imageFileName[0]=="/") and (self.imageFileName[1]=="/"))
        self.imageFileName=self.imageFileName.replace("//","/")
        if (isUNC):
            self.imageFileName='/'+self.imageFileName
        

        if ((not isRelativeOutputDir) and len(self.imageFileName)>1):
            self.imageFileName=self.imageFileName.replace("\\","/")
            if ((self.imageFileName[0]=="/" and (self.imageFileName[1]!="<")) or (self.imageFileName[1]==":")):
                isRelativeOutputDir=False
            else:
                isRelativeOutputDir=True
        if (isRelativeOutputDir):
            #print ("rrSubmit - getImageOut - imageFileName imageDir, add "+sceneInfo.DatabaseDir)
            self.imageDir=sceneInfo.DatabaseDir+self.imageDir
            self.imageDir+="/"
            
        printDebug("     getImageOut_renderman22   self.imageFileName "+self.imageFileName)
        printDebug("     getImageOut_renderman22   self.imageExtension "+self.imageExtension)
        
        
        
        self.channelName="" 
        if (self.get_attr("rmanDefaultDisplay.enable")==1):
            self.channelName="beauty"
            aovExt=cmds.listConnections('rmanDefaultDisplay.displayType')
            aovExt=aovExt[0]
            if (aovExt.find("exr")>0):
                aovExt="exr"
            elif (aovExt.find("png")>0):
                aovExt="png"
            elif (aovExt.find("targa")>0):
                aovExt="tga"
            elif (aovExt.find("tiff")>0):
                aovExt="tif"
            elif (aovExt.find("texture")>0):
                aovExt="tex"
            else:
                aovExt="exr"
            self.imageExtension= self.imageExtension.replace("<ext>",aovExt)
            

        aovList = cmds.ls(type='rmanDisplay', sns=True)
        if aovList == None or len(aovList) == 0:
            self.imageExtension= self.imageExtension.replace("<ext>","exr")        
            self.replaceMayaVariablesWithRR()  
            if (self.imageFileName.find("<Channel>")>=0):
                self.channelName="beauty"    
            return
            
        aovList = [aovList[i] for i in range(0, len(aovList), 2) if aovList[i + 1] == ':']
        for aovName in aovList:
            if (aovName=="rmanDefaultDisplay"):
                continue
            if((self.get_attr(aovName+'.enable') == 1)):
                aovExt=cmds.listConnections(aovName+'.displayType')
                aovExt=aovExt[0]
                if (aovExt.find("exr")>0):
                    aovExt="exr"
                elif (aovExt.find("png")>0):
                    aovExt="png"
                elif (aovExt.find("targa")>0):
                    aovExt="tga"
                elif (aovExt.find("tiff")>0):
                    aovExt="tif"
                elif (aovExt.find("texture")>0):
                    aovExt="tex"
                else:
                    aovExt="exr"

                if (len(self.channelName)==0):
                    self.channelName=aovName
                    self.imageExtension= self.imageExtension.replace("<ext>",aovExt) 
                else:
                    self.channelFileName.append(self.imageFileName.replace('<aov>', aovName))
                    self.channelExtension.append("."+aovExt)
                    self.maxChannels +=1
                
        printDebug("     getImageOut_renderman22   self.imageFileName "+self.imageFileName)
        printDebug("     getImageOut_renderman22   self.imageExtension "+self.imageExtension)
        self.replaceMayaVariablesWithRR()            
        printDebug("     getImageOut_renderman22   self.imageFileName "+self.imageFileName)
        printDebug("     getImageOut_renderman22   self.imageExtension "+self.imageExtension)
            
            
        self.imageExtension= self.imageExtension.replace("<Extension>","exr")  
        
        return True
        
        
            

    # gather all information from a layer
    def getLayerSettings_VRay(self,sceneInfo,isLayerRendering):
        self.imageWidth= int(self.get_attr('vraySettings.width'))
        self.imageHeight= int(self.get_attr('vraySettings.height'))
        self.imageFramePadding=self.get_attr('vraySettings.fileNamePadding')
        self.imageFileName=self.get_attr('vraySettings.fileNamePrefix')
        self.imageExtension=self.get_attr('vraySettings.imageFormatStr')
        self.imagePreNumberLetter='.'
        #self.camera=self.get_attr('vraySettings.batchCamera')
        self.tempIsGI= self.get_attr('vraySettings.giOn')
        self.tempIsGI2= ( (self.get_attr('vraySettings.imap_mode')==6) or (self.get_attr('vraySettings.imap_mode')==1))
        self.tempGIFileName=self.get_attr('vraySettings.imap_autoSaveFile')

        self.ImageSingleOutputFile=False
        if ((self.imageFileName==None) or (len(self.imageFileName)<=1)):
            self.imageFileName= sceneInfo.SceneName
            self.imageFileName=self.imageFileName.replace("\\","/")
            if (self.imageFileName.find("/")>=0):
                splitted=self.imageFileName.split("/")
                self.imageFileName=splitted[len(splitted)-1]
            if (self.imageFileName.find(".")>=0):
                splitted=self.imageFileName.split(".")
                self.imageFileName=""
                for i in range(0, len(splitted)-1):
                    if (i>0):
                        self.imageFileName= self.imageFileName + "."
                    self.imageFileName= self.imageFileName + splitted[i]

                    
        if ((self.imageExtension==None) or (len(self.imageExtension)==0)):
            self.imageExtension="png"
        self.imageExtension= "."+ self.imageExtension
        
        noChannels= False
        if ((self.imageExtension==".exr (multichannel)")):
            self.imageExtension=".exr"
            self.imagePreNumberLetter=""
            self.renderer=="vray_mexr"
            noChannels= True
        if ((self.imageExtension==".exr (deep)")):
            self.imageExtension=".exr"
        if ((self.imageExtension==".vrimg")):
            self.imagePreNumberLetter=""
            self.renderer=="vray_mexr"
            noChannels= True
        if ((self.camera==None) or (len(self.camera)==0)):
            self.camera=""
        if ((self.tempIsGI) and (self.tempIsGI2)):
            self.imageFileName=self.tempGIFileName
            self.imageExtension=""
            self.imagePreNumberLetter=""
            self.renderer="vray_prepass"
            if ((self.imageFileName==None) or (len(self.imageFileName)==0)):
                rrWriteLog("No Vray Irradiancee Map File set.\n(Change mode to 'Animation(render)', set the filename, change mode back to pre-pass)\n Layer: "+Layer+"\n")
                return False
            if (self.imageFileName.lower().find(".vrmap")>=0):
                splitted=self.imageFileName.split(".vrmap")
                self.imageFileName=splitted[0]
                self.imageExtension=".vrmap"

        rgbaOut_Subfolder=self.get_attr('vraySettings.relements_separateRGBA')
        if (int(rgbaOut_Subfolder)==1):
            rrWriteLog("Please disable the setting\n  Render Settings/ Render Elements/ Separate RGBA.\n This is not yet supported in RR.\n")
            return False

        self.replaceMayaVariablesWithRR()
        self.imageFileName=self.imageFileName.replace("<Channel>","")

        if (self.renderer=="vray_prepass"):
            self.imageFileName= self.imageFileName + self.imagePreNumberLetter
            self.imageDir=""
        else:
            if (isLayerRendering and (self.imageFileName.lower().find("<layer>")<0)):
                self.imageFileName=os.path.dirname(self.imageFileName)+"<Layer>/"+os.path.basename(self.imageFileName)
            if ((self.nbRenderableCams>1) and (self.imageFileName.lower().find("<camera>")<0)):
                self.imageFileName=os.path.dirname(self.imageFileName)+"<Camera>/"+os.path.basename(self.imageFileName)
            if (len(self.imageFileName)>1):
                self.imageFileName=self.imageFileName.replace("\\","/")
            imageFileName_nopre=self.imageFileName
            imageDirName_nopre=self.imageFileName
            posDir=self.imageFileName.find("/")
            if (posDir>0):
                imageFileName_nopre= os.path.basename(imageFileName_nopre)
                imageDirName_nopre= os.path.dirname(imageDirName_nopre)+ "/"
            else:
                imageDirName_nopre=""

            self.imageFileName= self.imageFileName + self.imagePreNumberLetter

            self.imageDir= cmds.workspace(fre="images")
            isRelative=True
            if (len(self.imageFileName)>1):
                self.imageFileName=self.imageFileName.replace("\\","/")
                if ((self.imageFileName[0]=="/") or (self.imageFileName[1]==":")):
                    isRelative=False
                    self.imageDir=""
            if (isRelative):
                if (len(self.imageDir)>1):
                    self.imageDir=self.imageDir.replace("\\","/")
                    if ((self.imageDir[0]=="/") or (self.imageDir[1]==":")):
                        isRelative=False
            if (isRelative):
                self.imageDir=sceneInfo.DatabaseDir+ self.imageDir
                self.imageDir+="/"
            vrayElemSeperateFolders= self.get_attr('vraySettings.relements_separateFolders')
            vrayElemSep= self.get_attr('vraySettings.fileNameRenderElementSeparator')
            vrayElements= maya.mel.eval('$rrTempExisting = vrayRenderElementsExisting();')
            if (not noChannels):
                for elem in vrayElements:
                    if (self.get_attr(elem+'.enabled')):
                        suffix=elem
                        suffix=suffix.replace(" ","")
                        suffix=suffix.replace("_","")
                        suffix=suffix.replace("-","")
                        suffix= suffix[:1].lower() + suffix[1:]
                        attribs=cmds.listAttr( elem, ud=True, a=False, s=False )
                        for attr in attribs:
                            if (attr.find("_name_")>0):
                                overridename=cmds.getAttr(elem+"." + attr)
                                printDebug(str(suffix)+"  "+str(overridename)+"  "+str(type(overridename)))
                                if (isinstance(overridename,int)):
                                    continue
                                if (len(overridename) > 0):
                                    suffix= overridename
                        if (vrayElemSeperateFolders):
                            self.channelFileName.append(imageDirName_nopre+suffix+"/"+imageFileName_nopre+vrayElemSep+suffix+self.imagePreNumberLetter)
                        else:
                            self.channelFileName.append(imageDirName_nopre+imageFileName_nopre+vrayElemSep+suffix+self.imagePreNumberLetter)
                        self.channelExtension.append(self.imageExtension)
                        self.maxChannels +=1

        return True


    # gather all information from a layer
    def getLayerSettings_sub(self,sceneInfo,isLayerRendering):
        self.imageWidth= int(self.get_attr('defaultResolution.width'))
        self.imageHeight= int(self.get_attr('defaultResolution.height'))
        self.tempModifyExtension=(self.get_attr('defaultRenderGlobals.modifyExtension')==True)
        self.tempModifyStart=int(self.get_attr('defaultRenderGlobals.startExtension'))
        self.tempModifyByframe=self.get_attr('defaultRenderGlobals.byExtension')
        self.tempExtensionPadding= self.get_attr('defaultRenderGlobals.extensionPadding')
        self.ImageSingleOutputFile=False
        self.CalcImageExtension()
        printDebug("self.tempImageExtension   "+self.tempImageExtension)

        if not self.get_attr('defaultRenderGlobals.putFrameBeforeExt'):
            rrWriteLog("Extension before frames not allowed!\n Please use an output format that ends with an extension.\n Layer: "+self.name+"\n")
            return False

        if ( self.tempModifyExtension):
            self.seqFileOffset=self.tempModifyStart-1
            if (self.tempModifyByframe!=1.0):
                rrWriteLog("No 'By Frame' renumbering allowed!\n Value: "+str(self.tempModifyByframe)+"  Layer: "+self.name+"\n")
                return False

        if (not self.getImageOut(sceneInfo,isLayerRendering)):
            rrWriteLog ("rrSubmit - getLayerSettings_sub '"+ self.name +"' getImageOut failed")
            return False

        if (self.renderer == 'mentalRay'):
            self.addChannelsToLayer()
        if (self.renderer == 'arnold'):
            self.addAOVToLayer()
            isAssExport= self.get_attr('defaultArnoldRenderOptions.renderType')
            isAssExport= (isAssExport==1)
            if (isAssExport):
                self.imageDir=  "<Database>ass_export/"
                self.imageFileName= "<SceneFile>/<Layer>_<Camera>." 
                self.imageExtension=".ass.gz"
                self.renderer="arnold-exportAss"
        if (self.renderer == "redshift"):
            self.addRedshiftAOVToLayer()
        return True        

    # gather all information from a layer
    def getLayerSettings(self,sceneInfo,isLayerRendering):
        printDebug ("rrSubmit - getLayerSettings '"+ self.name +"'")
        self.tempVersionTag = self.get_attr('defaultRenderGlobals.renderVersion')
        if ((self.tempVersionTag==None) or (len(self.tempVersionTag)==0)):
            self.tempVersionTag=""

        self.getLayerRenderer()
        self.getLayerCamera()
        
        isAnimation= self.get_attr('defaultRenderGlobals.animation')
        if (isAnimation != 1 and self.renderer != "_3delight"):
            self.ImageSingleOutputFile=True
            rrWriteLog("Still frames not allowed!\n Please use a sequence with one frame.\n Layer: "+self.name+"\n")
            return False
        
        #Get frame range
        global _rrGL_sceneFPSConvert
        value, overridden = self.get_attr_wasOverride('defaultRenderGlobals.startFrame')
        self.seqStart= int(value)
        if (overridden):
            self.seqStart= int(value * _rrGL_sceneFPSConvert + 0.001 )
        printDebug("    startFrame:  t:"+str(value)+"  f:"+str(self.seqStart) +" wasoverriden: " +str(overridden))
            
        value, overridden = self.get_attr_wasOverride('defaultRenderGlobals.endFrame')
        self.seqEnd= int(value)
        if (overridden):
            self.seqEnd= int(value * _rrGL_sceneFPSConvert + 0.001 )
            
        value, overridden = self.get_attr_wasOverride('defaultRenderGlobals.byFrameStep')
        self.seqStep= int(value)
        #if (overridden):
        #    self.seqStep= int(value * _rrGL_sceneFPSConvert + 0.001 )
        #printDebug("    byFrameStep:  t:"+str(value)+"  f:"+str(self.seqStep) +" wasoverriden: " +str(overridden))

             
        
        #get all render setting information 
        returnSuc=False
        if (self.renderer=="vray"):
            returnSuc= self.getLayerSettings_VRay(sceneInfo,isLayerRendering)  
        elif (self.renderer=="renderMan" and (self.rendererVersion[:2]>21)): 
            returnSuc= self.getLayerSettings_Renderman22(sceneInfo,isLayerRendering)  
        else:
            returnSuc= self.getLayerSettings_sub(sceneInfo,isLayerRendering)
        if (returnSuc == False):
            return False

        #this message is never shown as we replace lowercase renderlayer before
        if ("<renderLayer>" in self.imageFileName):
            rrWriteLog("You are using <renderLayer> in your filename.\nMaya support uppercase <RenderLayer> only.\nMaya might add an unwanted subfolder <RenderLayer>.\n\n(Please review the resolved filename in the render dialog)")
            return False
        
        #print (self.name+ "    "+self.camera+ " is renderable" )
        #If there are more than one rederable cam, then RR should not set the -cam flag at render time
        if (self.nbRenderableCams>1):
            for c in range(0, len(self.tempCamRenderable)):
                if (self.tempCamRenderable[c]):
                    self.nbRenderableCams=self.nbRenderableCams+1
                    transformNode = cmds.listRelatives(self.tempCamNames[c],parent=True)
                    transformNode=transformNode[0]
                    if (self.renderer=="mayaSoftware") or (self.renderer=="redshift") or (self.renderer=="vray"):
                        if (self.tempCamNames[c].find(transformNode+"|")>=0):
                            transformNode= "_"+transformNode
                    if (self.camera!=transformNode):
                        self.channelFileName.append(self.imageFileName.replace('<Camera>',transformNode))
                        self.channelExtension.append(self.imageExtension)
                        self.maxChannels +=1
            self.camera=self.camera + " MultiCam"
        if ((self.camera.find(":")>0) and (self.imageFileName.lower().find("<camera>")<0)):
            self.camera=""
        if (self.renderer=="mayaSoftware") or (self.renderer=="redshift") or (self.renderer=="vray"):
            self.imageFileName=self.imageFileName.replace('<Camera>','<CameraKeepVBar>')
        if ((len(self.camera)>150) and (self.camera.find(":")>0)):
            splitted=self.camera.split(":")
            self.camera=splitted[len(splitted)-1]
            
        if (self.renderer=="renderMan" and (self.rendererVersion[:2] <= 21)):
            self.renderer=="renderMan21"
        
        return True




   
                

class rrsceneInfo:
    def __init__(self):
        self.MayaVersion=""
        self.SceneName=""
        self.DatabaseDir=""
        self.RequiredLicenses=""
        self.ColorSpace = ""
        self.ColorSpace_View = ""
        self.ColorSpaceConfigFile = ""
            
    def getsceneInfo(self):
        self.DatabaseDir=cmds.workspace( q=True, rd=True )
        self.SceneName=cmds.file( q=True, location=True )

        global _rrGL_mayaVersion
        global _rrGL_mayaVersionMinorStr  

        self.MayaVersion =  str(_rrGL_mayaVersion)+"."+str(_rrGL_mayaVersionMinorStr)
        if (str(cmds.pluginInfo( query=True, listPlugins=True )).find('Yeti')>0):
            nodes= cmds.ls( type='pgYetiGroom' ) + cmds.ls( type='pgYetiMaya' ) + cmds.ls( type='pgYetiMayaFeather' )
            if (len(nodes)>0):
                self.RequiredLicenses=self.RequiredLicenses+"/Yeti;"
        
        self.ColorSpace = cmds.colorManagementPrefs(q=True, renderingSpaceName=True)
        self.ColorSpaceConfigFile = cmds.colorManagementPrefs(q=True, configFilePath=True)
        self.ColorSpace_View = cmds.colorManagementPrefs(q=True, viewTransformName=True)

        self.ColorSpaceConfigFile = self.ColorSpaceConfigFile.replace("<MAYA_RESOURCES>", OpenMaya.MGlobal.getAbsolutePathToResources()) 
        mayaPath=cmds.internalVar(mayaInstallDir=True)
        if (len(mayaPath)>0):
            self.ColorSpaceConfigFile = self.ColorSpaceConfigFile.replace(cmds.internalVar(mayaInstallDir=True), "<rrBaseAppPath>") 


def rrGetRR_Root():
        if ('RR_ROOT' in os.environ):
            return os.environ['RR_ROOT'].strip("\r")
        HCPath="%"
        if ((sys.platform.lower() == "win32") or (sys.platform.lower() == "win64")):
            HCPath="%RRLocationWin%"
        elif (sys.platform.lower() == "darwin"):
            HCPath="%RRLocationMac%"
        else:
            HCPath="%RRLocationLx%"
        if HCPath[0]!="%":
            return HCPath
        rrWriteLog("No RR_ROOT environment variable set!\n Please execute rrWorkstationInstaller and restart the machine.")
        return""


class rrPlugin(OpenMayaMPx.MPxCommand):
    def __init__(self):
        OpenMayaMPx.MPxCommand.__init__(self)
        self.RR_ROOT=""
        self.RR_ROOT=rrGetRR_Root()
        self.TempFileName=""
        self.maxLayer=0
        self.layer=[]
        self.cameras=[]
        self.passes = []
        self.sceneInfo = rrsceneInfo()
        self.multiCameraMode= False
        self.locTexFile=""
        self.frameSet=""
        return

    @staticmethod
    def creator():
        return OpenMayaMPx.asMPxPtr( rrPlugin() )


    #get list of all cameras in scene
    def getAllCameras(self):
        cameraList=cmds.ls(ca=True)
        for cam in cameraList:
            transformNode = cmds.listRelatives(cam,parent=True)
            transformNode=transformNode[0]
            if ((transformNode!="front") and (transformNode!="top") and (transformNode!="side")):
                if (self.layer[0].renderer=="_3delight"):
                    self.cameras.append(cam)                        
                else:
                    self.cameras.append(transformNode)


    def rrWriteNodeStr(self,fileID,name,text):
        #print ("    <"+name+">  "+text+"   </"+name+">")
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        text = text.replace("\"", "&quot;")
        text = text.replace("'", "&apos;")
        text = text.replace(unichr(228), "&#228;")
        text = text.replace(unichr(246), "&#246;")
        text = text.replace(unichr(252), "&#252;")
        text = text.replace(unichr(223), "&#223;")
        try:
            fileID.write("    <"+name+">  "+text+"   </"+name+">\n")
        except:
            rrWriteLog("Unable to write attribute '"+name+"' = '"+text+"'")


    #write list of all textures used into localtex file
    def writeTextureList(self):
        self.locTexFile=self.sceneInfo.SceneName
        if (self.locTexFile.find(".ma")>=0):
            self.locTexFile= self.locTexFile.replace(".ma",".localtex")
        elif (self.locTexFile.find(".mb")>=0):
            self.locTexFile= self.locTexFile.replace(".mb",".localtex")
        else:
            self.locTexFile=self.locTexFile+".localtex"
        fileID=0
        fileID = file(self.locTexFile, "w")
        fileID.write("<RR_LocalTextures syntax_version=\"6.0\">\n")
        if ((sys.platform.lower() == "win32") or (sys.platform.lower() == "win64")):
            self.rrWriteNodeStr(fileID,"SceneOS", "win")
        elif (sys.platform.lower() == "darwin"):
            self.rrWriteNodeStr(fileID,"SceneOS", "mac")
        else:
            self.rrWriteNodeStr(fileID,"SceneOS", "lx")
        self.rrWriteNodeStr(fileID,"Software", "Maya")
        self.rrWriteNodeStr(fileID,"DatabaseDir", self.sceneInfo.DatabaseDir)
        texList=cmds.ls(type='file')
        for tex in texList:
            fileID.write("<File>\n")
            texFileName=str(self.get_attr(tex+'.fileTextureName'))
            if (texFileName.startswith(self.sceneInfo.DatabaseDir)):
                texFileName=texFileName.replace(self.sceneInfo.DatabaseDir,self.sceneInfo.DatabaseDir+"/")
            self.rrWriteNodeStr(fileID,"Original", texFileName )
            fileID.write("</File>\n")
        fileID.write("</RR_LocalTextures>\n")
        fileID.close()
        if ((sys.platform.lower() == "win32") or (sys.platform.lower() == "win64")):
            os.system("\""+self.RR_ROOT+"\\bin\\win64\\rrSubmitterconsole.exe\"  "+self.locTexFile)
        elif (sys.platform.lower() == "darwin"):
            os.system("\""+self.RR_ROOT+"/bin/mac64/rrSubmitterconsole.app/Contents/MacOS/rrSubmitterconsole\"  "+self.locTexFile)
        else:
            os.system("\""+self.RR_ROOT+"/bin/lx64/rrSubmitterconsole\"  "+self.locTexFile)


    #get all 3delight passes
    def getAllPasses(self):
        self.passes= []
        passes = maya.mel.eval('DRP_getAllRenderPasses()')
        if passes == None or len(passes) == 0:
            print ('No passes found!')
            return False

        for p in passes:
            #print ("Parsing pass"+p)
            hpass = rrDelightRenderPass()
            if not hpass.getPassSettings(p):
                return False
            
            self.passes.append(hpass)
            #print (str(hpass))
        
        return True


    def getPhoenixSim(self):
        try:
            import pymel.core as pm
        except:
            print("pymel module not found! It was not enabled during Maya installation")
            return False   

        sel = pm.ls(sl = True)
        if ((len(sel)==0) or (cmds.objectType( cmds.listRelatives(sel[0].name()), isType='PhoenixFDSimulator' ) == False)):
            print("Please select the PhoenixFDSimulator object(s)")
            return False
        self.maxLayer=0
        for i in range(0, len(sel)):
            if (not cmds.objectType( cmds.listRelatives(sel[i].name()), isType='PhoenixFDSimulator' )):
                continue
            self.maxLayer+=1
            self.layer.append(rrMayaLayer())
            self.layer[self.maxLayer-1].sceneName= self.sceneInfo.SceneName
            self.layer[self.maxLayer-1].version= self.sceneInfo.MayaVersion
            self.layer[self.maxLayer-1].name=sel[i]
            self.layer[self.maxLayer-1].renderer="PhoenixFD"
            self.layer[self.maxLayer-1].IsActive=True
            self.layer[self.maxLayer-1].imageFileName=sel[i].getShape().getAttr("outPathResolved")
            self.layer[self.maxLayer-1].seqStep = 1
            self.layer[self.maxLayer-1].seqStart = sel[i].getShape().getAttr("startFrame")
            self.layer[self.maxLayer-1].seqEnd = sel[i].getShape().getAttr("stopFrame")
            if (self.layer[self.maxLayer-1].seqStart==0):
                self.layer[self.maxLayer-1].seqStart=cmds.playbackOptions( query=True, minTime= True)
            if (self.layer[self.maxLayer-1].seqEnd==0):
                self.layer[self.maxLayer-1].seqEnd=cmds.playbackOptions( query=True, maxTime= True)
        return True            

            
    def getAlembicObj(self):
        try:
            import pymel.core as pm
        except:
            print("pymel module not found! It was not enabled during Maya installation")
            return False   
        sel = pm.ls(sl = True)
        if (len(sel)==0):
            print("No object(s) selectetd")
            return False
        self.maxLayer=0
        for i in range(0, len(sel)):
            self.maxLayer+=1
            self.layer.append(rrMayaLayer())
            self.layer[self.maxLayer-1].sceneName= self.sceneInfo.SceneName
            self.layer[self.maxLayer-1].version= self.sceneInfo.MayaVersion
            self.layer[self.maxLayer-1].name=sel[i]
            self.layer[self.maxLayer-1].renderer="Alembic"
            self.layer[self.maxLayer-1].IsActive=True
            self.layer[self.maxLayer-1].imageFileName=cmds.workspace(fre="alembicCache")
            if (len(self.layer[self.maxLayer-1].imageFileName)==0):
                self.layer[self.maxLayer-1].imageFileName=cmds.workspace(fre="diskCache")
                if (len(self.layer[self.maxLayer-1].imageFileName)!=0):
                    self.layer[self.maxLayer-1].imageFileName=self.layer[self.maxLayer-1].imageFileName+"/alembic"
            if (len(self.layer[self.maxLayer-1].imageFileName)==0):
                self.layer[self.maxLayer-1].imageFileName="cache/alembic"
            self.layer[self.maxLayer-1].imageFileName=self.layer[self.maxLayer-1].imageFileName.replace("\\","/")
            if ((self.layer[self.maxLayer-1].imageFileName[0]!="/") and (self.layer[self.maxLayer-1].imageFileName[1]!=":")):
                self.layer[self.maxLayer-1].imageFileName=self.sceneInfo.DatabaseDir+self.layer[self.maxLayer-1].imageFileName
            self.layer[self.maxLayer-1].imageFileName=self.layer[self.maxLayer-1].imageFileName+"/"+sel[i]+".abc"
            self.layer[self.maxLayer-1].seqStep = 1
            self.layer[self.maxLayer-1].seqStart=cmds.playbackOptions( query=True, minTime= True)
            self.layer[self.maxLayer-1].seqEnd=cmds.playbackOptions( query=True, maxTime= True)
            self.layer[self.maxLayer-1].ImageSingleOutputFile=True
        return True            


    def getBakeObj(self):
        try:
            import pymel.core as pm
        except:
            print("pymel module not found! It was not enabled during Maya installation")
            return False   
        selection = pm.ls(selection=True)

        # Check if user have something selected
        if (len(selection) == 0):
            cmds.warning("Select one or multiple objects to bake")
            return False

        try:
            bake_options = pm.PyNode('vrayDefaultBakeOptions')
        # Might not exist catch the exception
        except pm.MayaNodeError:
            cmds.warning(
                "vrayDefaultBakeOptions does not exist. "
                "Please create one from the main menu "
                "Lighting/Shading -> Show default V-Ray bake options"
            )
            return False

        # Get some global bake settings
        filename_prefix = bake_options.getAttr('filenamePrefix')

        # Get some VRay settings
        image_format = pm.getAttr("vraySettings.imageFormatStr")
        if not image_format:
            cmds.warning(
                "'Image Format' not set in render settings or not updated: "
                "Please change its value in the Render Settings and then change it back")
            return False

        self.maxLayer = 0

        for node in selection:

            children = node.listRelatives(children=True)
            if len(children) > 1:
                print (
                    "[-] %s group has multiple shapes attached to it. Skepped!"
                    % node.name()
                )
                continue
            elif len(children) == 0:
                print("[-] %s  has no children" % node.name())
                child = node
            else:
                child = children[0]

            # Make sure that our child is a mesh node
            if child.type() != 'mesh':
                print (
                    "[-] %s object skipped since it does not contains a mesh object. "
                    "Make sure that you made your selection in the viewport and not in outliner."
                    % node.name()
                )
                continue

            self.maxLayer += 1
            self.layer.append(rrMayaLayer())
            self.layer[self.maxLayer-1].sceneName= self.sceneInfo.SceneName
            self.layer[self.maxLayer-1].version= self.sceneInfo.MayaVersion
            self.layer[self.maxLayer-1].name = node.name()
            self.layer[self.maxLayer-1].renderer = "VrayBake"
            self.layer[self.maxLayer-1].IsActive = True

            output_path = self.layer[self.maxLayer-1].imageFileName
            output_path = cmds.workspace(fre="images")

            if len(output_path) == 0:
                output_path = cmds.workspace(fre="images")
                if len(output_path) != 0:
                    output_path = output_path + "/images"

            if len(output_path) == 0:
                output_path = "images/bake"

            output_path = output_path.replace("\\", "/")

            # If output path has no root set it relative to project
            if output_path[0] != "/" and output_path[1] != ":":
                output_path = self.sceneInfo.DatabaseDir + output_path

            # Output file path and name but with no file extension
            output_path = output_path + "/" + filename_prefix + "-"  + child.name()
            # We split the file path and its extension in order to prevent RR
            # trimming leading digits on the file name
            self.layer[self.maxLayer-1].imageFileName = output_path
            self.layer[self.maxLayer-1].imageExtension = "." + image_format

            self.layer[self.maxLayer-1].seqStep = 1

            # Set frame range from maya global settings
            self.layer[self.maxLayer-1].seqStart = cmds.getAttr("defaultRenderGlobals.startFrame")
            self.layer[self.maxLayer-1].seqEnd = cmds.getAttr("defaultRenderGlobals.endFrame")

            # self.layer[self.maxLayer-1].ImageSingleOutputFile=True

        # Make sure that at least one
        # object was added for submission
        if self.maxLayer:
            return True
        else:
            return False

            

    #get all render layers
    def getAllLayers(self):
        printDebug("rrSubmit - getAllLayers")
        global _rrGL_hasRenderSetup
        isLayerRendering= False
        
        rs= ""
        if (_rrGL_hasRenderSetup):
            rs = renderSetup.instance() 
            rLayers = rs.getRenderLayers()
        else:
            rLayers=cmds.listConnections( "renderLayerManager", t="renderLayer")
        isLayerRendering= (len(rLayers)>1) 
        
        printDebug("rrSubmit - "+str(len(rLayers))+" Maya layers found")
        
        #Get MasterLayer Info
        self.maxLayer=1
        self.layer.append(rrMayaLayer())
        self.layer[0].sceneName= self.sceneInfo.SceneName
        self.layer[0].version= self.sceneInfo.MayaVersion
        self.layer[0].name="masterLayer"
        self.layer[0].IsActive= (cmds.getAttr('defaultRenderLayer.renderable')==True)

        if (_rrGL_hasRenderSetup):
            self.layer[0].renderSetupObj= rs.getDefaultRenderLayer()
        if (not (self.layer[0].getLayerSettings(self.sceneInfo,isLayerRendering))):
            print ("rrSubmit - unable to read settings of layer 'defaultRenderLayer'")
            return False
        
        
		
        #now get all layer:
        if (len(rLayers)>0):
            for layer in rLayers:
                renderSetupObj=""
                layerName=""
                if (_rrGL_hasRenderSetup):
                    renderSetupObj= layer
                    layerName= layer.name()
                else:
                    layerName= layer
                    
                if (layerName== "defaultRenderLayer"):
                    continue
                
                self.maxLayer+=1
                self.layer.append(rrMayaLayer())
                self.layer[self.maxLayer-1].sceneName= self.sceneInfo.SceneName
                self.layer[self.maxLayer-1].version= self.sceneInfo.MayaVersion
                self.layer[self.maxLayer-1].name= layerName
                self.layer[self.maxLayer-1].renderSetupObj= renderSetupObj
                
                if (_rrGL_hasRenderSetup):
                    self.layer[self.maxLayer-1].IsActive= layer.isRenderable()
                else:
                    self.layer[self.maxLayer-1].IsActive= (cmds.getAttr(layerName+'.renderable')==True)

                if (not (self.layer[self.maxLayer-1].getLayerSettings(self.sceneInfo,isLayerRendering))):
                    print ("rrSubmit - unable to read settings of layer "+ self.layer[self.maxLayer-1].name)
                    return False
                    
                #Maya 2017 update 2+ fix:
                mayaUpd2_layerName= maya.mel.eval('exists("renderLayerDisplayName")')!=0
                if (mayaUpd2_layerName):
                    mayaUpd2_layerName=False #first check completed, we have the required new maya version
                    #now check if we have the right renderer version
                    if (self.layer[self.maxLayer-1].renderer=="arnold" or self.layer[self.maxLayer-1].renderer=="mayaSoftware" ):
                        mayaUpd2_layerName=True
                    elif (self.layer[self.maxLayer-1].renderer=="redshift"):
                        redVersion=self.layer[self.maxLayer-1].rendererVersion
                        if (redVersion>="2.0.88"):
                            mayaUpd2_layerName=True
                    elif (self.layer[self.maxLayer-1].renderer=="vray"):
                        renVersion=self.layer[self.maxLayer-1].rendererVersion
                        if (renVersion>="3.53" or renVersion>="3.52.03"):
                            mayaUpd2_layerName=True
                    elif (self.layer[self.maxLayer-1].renderer=="renderMan" and (self.layer[self.maxLayer-1].rendererVersion[:2]>21)):          
                        mayaUpd2_layerName=True
                if (mayaUpd2_layerName):
                    if (self.layer[self.maxLayer-1].name.startswith("rs_")):
                        self.layer[self.maxLayer-1].name= self.layer[self.maxLayer-1].name[3:]
                else:
                    if (_rrGL_hasRenderSetup):
                        self.layer[self.maxLayer-1].name= "rs_" + self.layer[self.maxLayer-1].name
                        
                    
        if (self.maxLayer==1) and (self.layer[0].imageFileName.lower().find("<layer>")<0):
            self.layer[0].name=""
            
        printDebug("rrSubmit - "+str(self.maxLayer)+" Maya jobs added to submission")
        
        return True


    def arnoldUsd(self):      
    
        #remove all non-arnold Render Layer
        for L in reversed(range(0, self.maxLayer)):
            if self.layer[L].renderer == "arnold":
                continue
            self.layer.remove(self.layer[L])                
            self.maxLayer= self.maxLayer-1
            
        if (self.maxLayer==0):
            return False
        
        #Read USD export filename
        usdFileName= rrOptions_GetValue("USD_exportFileName", "filename", "<MayaProject>/USD/<Scene>_<Layer><Version>/<Scene>_<Layer><Version>.####.usdz", True)
        
        dbDir=  self.sceneInfo.DatabaseDir
        sceneName=  Path(self.sceneInfo.SceneName).stem
        usdFileName= usdFileName.replace("<MayaProject>",dbDir)
        usdFileName= usdFileName.replace("<mayaproject>",dbDir)
        usdFileName= usdFileName.replace("<Scene>",sceneName)
        usdFileName= usdFileName.replace("<scene>",sceneName)
        
        
        #Dublicate all jobs
        layerCount= self.maxLayer
        for L in range(0, layerCount):
            self.layer[L].renderSetupObj= None
            self.layer.append(copy.deepcopy(self.layer[L]))
            self.maxLayer= self.maxLayer +1
             
            usdFileName_Layer= usdFileName;
            usdFileName_Layer= usdFileName_Layer.replace("<layer>", self.layer[L].name)
            usdFileName_Layer= usdFileName_Layer.replace("<Layer>", self.layer[L].name)
            usdFileName_Layer= usdFileName_Layer.replace("<version>", self.layer[L].tempVersionTag)
            usdFileName_Layer= usdFileName_Layer.replace("<Version>", self.layer[L].tempVersionTag)
 
            #Export USD job:
            self.layer[L].imageDir=""
            self.layer[L].imageExtension=""
            self.layer[L].imageFileName= usdFileName_Layer
            self.layer[L].renderer="arnold-CreateUSD"
            self.layer[L].preID=L
            
            #Render USD Job:
            usdFileName_Layer= usdFileName_Layer.replace("######","<FN6>")
            usdFileName_Layer= usdFileName_Layer.replace("#####","<FN5>")
            usdFileName_Layer= usdFileName_Layer.replace("####","<FN4>")
            usdFileName_Layer= usdFileName_Layer.replace("###","<FN3>")
            usdFileName_Layer= usdFileName_Layer.replace("##","<FN2>")
            usdFileName_Layer= usdFileName_Layer.replace("#","<FN1>")
            
            jID= self.maxLayer -1
            self.layer[jID].preID=jID
            self.layer[jID].waitForPreID=L
            self.layer[jID].sceneName= usdFileName_Layer
            self.layer[jID].software= "Arnold"
            self.layer[jID].renderer= ""
            self.layer[jID].version= self.layer[jID].rendererVersion
            self.layer[jID].rendererVersion= self.sceneInfo.MayaVersion
 
        return True



    def askFrameset(self, message="Enter Frames:"):
        defaultValue="{0:.0f}-{1:.0f}".format(cmds.getAttr("defaultRenderGlobals.startFrame"),
                                              cmds.getAttr("defaultRenderGlobals.endFrame"))
        frameSet= rrOptions_GetValue("FrameSet", "string", defaultValue, False);
        res = cmds.promptDialog(title="RR Frameset", message=message,
                                button=['OK', 'Cancel'], defaultButton='OK',
                                cancelButton="Cancel", dismissString='Cancel',
                                text= frameSet )

        if res == "OK":
            frameSet = cmds.promptDialog(query=True, text=True)
            match = re.match("[0-9]+([,\-][0-9]+)*", frameSet)
            if match and match.span()[-1] == len(frameSet):
                self.frameSet = frameSet
                rrOptions_SetValue("FrameSet", "string", frameSet)
            else:
                self.askFrameset(message="Enter Frames: only numbers separated by dash or commas allowed"
                                         "\ni.e. 1-5,10,20")



    # from infix.se (Filip Solomonsson)
    def indent(self, elem, level=0):
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

    def subE(self, r, e, text):
        sub = SubElement(r, e)
        if sys.version_info.major == 2:
            if type(text) == unicode:
                sub.text = text
            else:
                sub.text = str(text).decode("utf-8")
        else:
            sub.text = str(text)
        return sub

    def writeToXMLstart(self, submitOptions ):
        rootElement = Element("rrJob_submitFile")
        rootElement.attrib["syntax_version"] = "6.0"
        self.subE(rootElement, "DeleteXML", "1")
        self.subE(rootElement, "SubmitterParameter", submitOptions)
        # YOU CAN ADD OTHER NOT SCENE-INFORMATION PARAMETERS USING THIS FORMAT:
        # self.subE(rootElement,"SubmitterParameter","PARAMETERNAME=" + PARAMETERVALUE_AS_STRING)
        if cmds.optionVar( exists='renderSetup_includeAllLights' ) and (cmds.optionVar(q='renderSetup_includeAllLights') == 0):
            self.subE(rootElement,"SubmitterParameter","COnoIncludeAllLights=1~1")
        return rootElement



    def writeToXMLEnd(self, f, rootElement):
        xml = ElementTree(rootElement)
        self.indent(xml.getroot())

        if f is None:
            print("No valid file has been passed to the write function")
            try:
                f.close()
            except:
                pass
            return False

        xml.write(f, encoding="utf-8", xml_declaration=True)
        f.close()

        return True

   

    def rrWritePassToFile(self,rootElement, Layer, DPass, sceneInfo,camera,LocalTextureFile):
        jobElement = self.subE(rootElement, "Job", "")
        self.subE(jobElement, "rrSubmitterPluginVersion", "%rrVersion%-2017")
        if ((sys.platform.lower() == "win32") or (sys.platform.lower() == "win64")):
            self.subE(jobElement,"SceneOS", "win")
        elif (sys.platform.lower() == "darwin"):
            self.subE(jobElement,"SceneOS", "mac")
        else:
            self.subE(jobElement,"SceneOS", "lx")
        self.subE(jobElement,"Software", "Maya")
        self.subE(jobElement,"Version", sceneInfo.MayaVersion)
        self.subE(jobElement,"Scenename", sceneInfo.SceneName)
        self.subE(jobElement,"SceneDatabaseDir", sceneInfo.DatabaseDir)
        self.subE(jobElement,"ColorSpace", sceneInfo.ColorSpace)
        self.subE(jobElement,"ColorSpace_View", sceneInfo.ColorSpace_View)
        self.subE(jobElement,"ColorSpaceConfigFile", sceneInfo.ColorSpaceConfigFile)
        self.subE(jobElement,"Renderer", DPass.renderer)
        self.subE(jobElement,"RequiredLicenses", sceneInfo.RequiredLicenses)
        self.subE(jobElement,"Camera",camera)
        self.subE(jobElement,"Layer", Layer)
        self.subE(jobElement,"Channel", DPass.name)
        self.subE(jobElement,"IsActive",True)
        self.subE(jobElement,"SeqStart",DPass.seqStart)
        self.subE(jobElement,"SeqEnd",DPass.seqEnd)
        self.subE(jobElement,"SeqStep",DPass.seqStep)
        self.subE(jobElement,"SeqFileOffset",0)
        self.subE(jobElement,"SeqFrameSet",self.frameSet)
        self.subE(jobElement,"ImageWidth",DPass.imageWidth)
        self.subE(jobElement,"ImageHeight",DPass.imageHeight)
        self.subE(jobElement,"ImageDir",DPass.imageDir)
        self.subE(jobElement,"ImgFilename",DPass.imageFileName)
        self.subE(jobElement,"ImageExtension",DPass.imageExtension)
    #        self.subE(jobElement,"ImagePreNumberLetter",Layer.imagePreNumberLetter)
        self.subE(jobElement,"ImageFramePadding",4)
    #        self.subE(jobElement,"ImageSingleOutputFile",Layer.ImageSingleOutputFile)
        for c in range(0,len(DPass.channelFilenames)):
           self.subE(jobElement,"ChannelFilename",DPass.channelFilenames[c])
           self.subE(jobElement,"ChannelExtension",DPass.channelExts[c])
        self.subE(jobElement,"LocalTexturesFile",LocalTextureFile)
        if (len(Layer.customScriptFile)>0):
            self.subE(jobElement,"CustomScriptFile",Layer.customScriptFile)
        
        
    def rrWriteLayerToFile(self,rootElement,Layer, channel,sceneInfo,camera,LocalTextureFile):
        #print("\n\n")
        #print LayerID
        jobElement = self.subE(rootElement, "Job", "")
        self.subE(jobElement, "rrSubmitterPluginVersion", "%rrVersion%-2017")
        if ((sys.platform.lower() == "win32") or (sys.platform.lower() == "win64")):
            self.subE(jobElement,"SceneOS", "win")
        elif (sys.platform.lower() == "darwin"):
            self.subE(jobElement,"SceneOS", "mac")
        else:
            self.subE(jobElement,"SceneOS", "lx")
        self.subE(jobElement,"Software", Layer.software)
        self.subE(jobElement,"Version", Layer.version)
        self.subE(jobElement,"SceneName", Layer.sceneName)
        self.subE(jobElement,"SceneDatabaseDir", sceneInfo.DatabaseDir)
        self.subE(jobElement,"ColorSpace", sceneInfo.ColorSpace)
        self.subE(jobElement,"ColorSpace_View", sceneInfo.ColorSpace_View)
        self.subE(jobElement,"ColorSpaceConfigFile", sceneInfo.ColorSpaceConfigFile)
        self.subE(jobElement,"Renderer", Layer.renderer)
        self.subE(jobElement,"rendererVersion",Layer.rendererVersion)
        self.subE(jobElement,"RequiredLicenses", sceneInfo.RequiredLicenses)
        self.subE(jobElement,"Camera",camera)
        self.subE(jobElement,"Layer", Layer.name)
        self.subE(jobElement,"Channel", channel)
        self.subE(jobElement,"IsActive",Layer.IsActive)
        self.subE(jobElement,"SeqStart",Layer.seqStart)
        self.subE(jobElement,"SeqEnd",Layer.seqEnd)
        self.subE(jobElement,"SeqStep",Layer.seqStep)
        self.subE(jobElement,"SeqFileOffset",Layer.seqFileOffset)
        self.subE(jobElement,"SeqFrameSet",self.frameSet)
        self.subE(jobElement,"ImageWidth",Layer.imageWidth)
        self.subE(jobElement,"ImageHeight",Layer.imageHeight)
        self.subE(jobElement,"ImageDir",Layer.imageDir)
        self.subE(jobElement,"ImgFilename",Layer.imageFileName)
        self.subE(jobElement,"ImageExtension",Layer.imageExtension)
        self.subE(jobElement,"ImagePreNumberLetter",Layer.imagePreNumberLetter)
        self.subE(jobElement,"ImageFramePadding",Layer.imageFramePadding)
        self.subE(jobElement,"ImageSingleOutputFile",Layer.ImageSingleOutputFile)
        for c in range(0,Layer.maxChannels):
            self.subE(jobElement,"ChannelFilename",Layer.channelFileName[c])
            self.subE(jobElement,"ChannelExtension",Layer.channelExtension[c])
        self.subE(jobElement,"LocalTexturesFile",LocalTextureFile)
        if (len(Layer.customScriptFile)>0):
            self.subE(jobElement,"CustomScriptFile",Layer.customScriptFile)
        if (Layer.preID >0):
            self.subE(jobElement,"PreID", Layer.preID)
        if (Layer.waitForPreID >0):
            self.subE(jobElement,"WaitForPreID", Layer.waitForPreID)

    #write all information (layer/passes) into RR job file
    def writeAllLayers(self, UIMode):
        submitOptions = ""
        tmp_prefix = "rrSubmitMaya_"
        tmp_suffix = ".xml"
        tmpFile = tempfile.NamedTemporaryFile(mode='w+b',
                                              prefix=tmp_prefix,
                                              suffix=tmp_suffix,
                                              delete=False)

        self.TempFileName = tmpFile.name
        xmlObj= self.writeToXMLstart(submitOptions)

        if self.multiCameraMode:
            self.getAllCameras()
            for cam in self.cameras:
                for L in range(0, self.maxLayer):
                    if self.layer[L].renderer == "_3delight":
                        if not self.getAllPasses():
                            return False
                        for p in self.passes:
                            self.rrWritePassToFile(xmlObj, self.layer[L].name, p, self.sceneInfo, cam, self.locTexFile)
                    else:
                        self.rrWriteLayerToFile(xmlObj, self.layer[L], self.layer[L].channelName, self.sceneInfo, cam, self.locTexFile)
        else:        
            for L in range(0, self.maxLayer):
                if self.layer[L].renderer == "_3delight":
                    if not self.getAllPasses():
                        return False
                    for p in self.passes:
                        self.rrWritePassToFile(xmlObj, self.layer[L].name, p, self.sceneInfo, p.camera, self.locTexFile)
                else:
                    self.rrWriteLayerToFile(xmlObj, self.layer[L], self.layer[L].channelName, self.sceneInfo, self.layer[L].camera, self.locTexFile)

        ret = self.writeToXMLEnd(tmpFile, xmlObj)
        if not ret:
            rrWriteLog("Error - There was a problem writing the job file to " + tmpFile.name)
            return
        if not UIMode:
            # we strip the random name from the file when the plugin is invoked from the command line:
            # the scene parser plugin expects the file to be named just
            # "rrSubmitMaya_.xml"
            # FIXME: we should be able to return the filename to the scene parser plugin
            original_path = self.TempFileName
            tmp_dir, tmp_name = os.path.split(original_path)
            self.TempFileName = os.path.join(tmp_dir, tmp_prefix + tmp_suffix)
            try:
                os.unlink(self.TempFileName)
            except FileNotFoundError:
                pass
            os.rename(original_path, self.TempFileName)


    #call the submitter
    def submitLayers(self):
        exePath=""
        cmdFlags=""
        if ((sys.platform.lower() == "win32") or (sys.platform.lower() == "win64")):
            exePath=self.RR_ROOT+"\\win__rrSubmitter.bat"
            cmdFlags=self.TempFileName
        elif (sys.platform.lower() == "darwin"):
            exePath=self.RR_ROOT+"/bin/mac64/rrStartLocal"
            cmdFlags="rrSubmitter  "+self.TempFileName
        else:
            exePath=self.RR_ROOT+"/lx__rrSubmitter.sh"
            cmdFlags=self.TempFileName
        #print ("Executing: '"+exePath+"'  "+cmdFlags)
        if not os.path.isfile(exePath):
            rrWriteLog("RR executable not found or cannot be accessed!\n "+exePath+" \n")
        
        cmdLine="\""+exePath+"\"  "+cmdFlags
        
        rr_env= os.environ.copy()
        envCount= len(list(rr_env))
        ie=0
        while (ie<envCount):
            envVar= list(rr_env)[ie]
            if envVar.startswith("QT_"):
                del rr_env[envVar]
                envCount= envCount -1
            else:
                ie= ie+1


        subprocess.Popen(cmdLine, close_fds=True, env=rr_env)

        
            

    ########################################
    #      Main function 
    ########################################
    def doIt(self, arglist):
        printDebug('---------------------------------------------------------------------------')
        printDebug('###########################################################################')
        print ("rrSubmit %rrVersion%-2017+")
        
        initGlobalVars()

        #check if we are in console batch mode
        UIMode = is_ui_mode()
        
        # Ask for scene save:
        if (UIMode and (cmds.file(q=True, mf=True))):  # //Ignore ifcheck
            ConfirmResult=(cmds.confirmDialog(message="Scene should be saved before network rendering.\n Save scene?", button=['Yes','No','Cancel'], defaultButton='Yes', cancelButton='Cancel', dismissString='Cancel'))
            if (ConfirmResult=="Cancel"):
                return True
            elif (ConfirmResult=="Yes"):
                cmds.file(s=True)
                
        #get information about the scene:
        self.sceneInfo.getsceneInfo()
        if (self.sceneInfo.SceneName=="unknown"):
            if (UIMode):
                cmds.confirmDialog(message="Scene was never saved!\n", button=['Abort'])
            return True

        #check if this function was called with parameters:
        self.multiCameraMode= False
        self.phoenixFD= False
        self.alembicSelection= False
        self.bakeSelection= False
        self.pickPythonFile= False
        self.exportArnoldUsd= False
        if ((arglist.length()>0) and arglist.asBool(0)):
            self.multiCameraMode= True
        if ((arglist.length()>1) and arglist.asBool(1)):
            self.writeTextureList()
        if ((arglist.length()>2) and arglist.asBool(2)):
            self.phoenixFD= True
        if ((arglist.length()>3) and arglist.asBool(3)):
            self.alembicSelection= True
        if ((arglist.length()>4) and arglist.asBool(4)):
            self.bakeSelection= True
        if ((arglist.length()>5) and arglist.asBool(5)):
            self.pickPythonFile= True
        if ((arglist.length()>6) and arglist.asBool(6)):
            self.exportArnoldUsd= True

        #get all layers:
        if (self.phoenixFD):
            printDebug("rrSubmit - About to get phoenixFD objects")
            if (not self.getPhoenixSim()):
                return False
        elif (self.alembicSelection):
            printDebug("rrSubmit - About to get Alembic objects")
            if (not self.getAlembicObj()):
                return False
        elif (self.bakeSelection):
            printDebug("rrSubmit - About to get bake objects")
            if (not self.getBakeObj()):
                return False
        else:
            printDebug("rrSubmit - About to get  Maya layers")
            if (not self.getAllLayers()):
                #print ("rrSubmit - unable to get render/layer information")
                return False
            if (self.exportArnoldUsd):
                if (not self.arnoldUsd()):
                    return False
                

        # frameset
        use_frameset = cmds.menuItem(FR_SET_OPTION, query=True, checkBox=True)
        if use_frameset:
            self.askFrameset()

        if (self.pickPythonFile):
            pyFileName= cmds.fileDialog( dm='*.py', mode=0, title='Please pick your python script...' )
            if (len(pyFileName)==0):
                return False
            for L in range(0, self.maxLayer):
                self.layer[L].IsActive= False
                self.layer[L].renderer="Python"
                self.layer[L].customScriptFile= pyFileName
                self.layer[L].imageFileName= "python"
                self.layer[L].imageExtension=""
            self.layer[0].IsActive= True

            
        #write layers into file:
        #print ("rrSubmit - write layers into file")
        if self.writeAllLayers(UIMode) == False:
            return False

        #call submitter
        #print ("rrSubmit - call submitter")
        if UIMode:
            self.submitLayers()
                




# Initialize the script plug-in
def initializePlugin(mobject):
    if is_ui_mode():
        maya.mel.eval('global string $RRMenuCtrl;')
        maya.mel.eval('if (`menu -exists $RRMenuCtrl `) deleteUI $RRMenuCtrl;')
        maya.mel.eval('$RRMenuCtrl = `menu -p $gMainWindow -to true -l "RRender"`;')
        maya.mel.eval('menuItem -p $RRMenuCtrl -l "Submit scene..." -c "rrSubmit";')
        maya.mel.eval('menuItem -p $RRMenuCtrl -l "Submit scene - Select camera..." -c "rrSubmit true";')
        maya.mel.eval('menuItem -p $RRMenuCtrl -l "Submit scene - Simulate PhoenixFD object" -c "rrSubmit false false true";')
        maya.mel.eval('menuItem -p $RRMenuCtrl -l "Submit scene - Export selected object as alembic cache" -c "rrSubmit false false false true";')
        maya.mel.eval('menuItem -p $RRMenuCtrl -l "Submit scene - VRay Bake Textures" -c "rrSubmit false false false false true";')
        maya.mel.eval('menuItem -p $RRMenuCtrl -l "Submit scene - Pick python script to execute on scene file" -c "rrSubmit false false false false false true";')
        maya.mel.eval('menuItem -p $RRMenuCtrl -l "Submit scene - Export .usd and render with Arnold" -c "rrSubmit false false false false false false true";')

        global FR_SET_OPTION
        FR_SET_OPTION = maya.mel.eval('menuItem -p $RRMenuCtrl -l "Ask for Frameset" -checkBox off;')
    else:
        print("We are running in batch mode")
    
    mplugin = OpenMayaMPx.MFnPlugin(mobject)
    try:
        mplugin.registerCommand( "rrSubmit", rrPlugin.creator )
    except:
        sys.stderr.write( "Failed to register RR commands\n" )
        raise


# Uninitialize the script plug-in
def uninitializePlugin(mobject):
    maya.mel.eval('global string $RRMenuCtrl;')
    maya.mel.eval('if (`menu -exists $RRMenuCtrl `) deleteUI $RRMenuCtrl;')
    mplugin = OpenMayaMPx.MFnPlugin(mobject)
    try:
        mplugin.deregisterCommand("rrSubmit")
    except:
        sys.stderr.write("Failed to unregister RR commands\n")
        raise







