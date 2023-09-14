#  Render script for Maya    
#  Last Change: %rrVersion%
#  Copyright (c)  Holger Schoenberger - Binary Alchemy

import datetime
import time
import sys
import maya.cmds as cmds
import maya.mel
import rrScriptHelper
import os


if sys.version_info.major == 2:
    range = xrange


def flushLog():
    sys.stdout.flush()        
    sys.stderr.flush()    
    
def logMessageGen(lvl, msg):
    if (len(lvl)==0):
        print(datetime.datetime.now().strftime("' %H:%M.%S") + " rrMaya      : " + str(msg))
    else:
        print(datetime.datetime.now().strftime("' %H:%M.%S") + " rrMaya - " + str(lvl) + ": " + str(msg))


def logMessage(msg):
    logMessageGen("",msg)

def logMessageSet(msg):
    logMessageGen("SET",msg)

    
def logMessageDebug( msg):
    if (False):
        logMessageGen("DGB", msg)

def logMessageError(msg):
    logMessageGen("ERROR", str(msg)+"\n\n")
    logMessage("                                   ... ")
    logMessage("                                   ..  ")
    logMessage("                                   ... ")
    time.sleep(2) #some delay as some log messages seem to be cut off
    flushLog()
    raise NameError("\nError reported, aborting render script\n")
    
    
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
    if (_rrGL_mayaVersion>2016 or (_rrGL_mayaVersion==2016 and _rrGL_mayaVersionMinor>=50)):
        renderSetupCount   = len( cmds.ls( type="renderSetupLayer" ) )  #New 
        renderLayerCount   = len( cmds.ls( type="renderLayer" ) )  #Old 
        renderLayerCount= renderLayerCount - renderSetupCount  
        _rrGL_hasRenderSetup= (renderSetupCount>0 or renderLayerCount<=0)
    #logMessage("_rrGL_hasRenderSetup is " + str(_rrGL_hasRenderSetup))
 



def remove_override_in_RenderSetup(qAtrib):
    global _rrGL_hasRenderSetup
    if not _rrGL_hasRenderSetup:
        return
    import maya.app.renderSetup.model.renderSetup as renderSetup
    rs = renderSetup.instance() 
    layerActive= rs.getVisibleRenderLayer()   
    #check if the current layer has an override applied to it:
    allOverrides= maya.app.renderSetup.model.utils.getOverridesRecursive(layerActive)
    for oride in allOverrides:
        if (oride.typeName()=="absUniqueOverride"):
            oName=oride.targetNodeName()+"."+oride.attributeName()
            if (oName == qAtrib):
                oride.setSelfEnabled(False)
                return
        elif (oride.typeName()=="absOverride"):
            if (qAtrib.endswith("."+oride.attributeName())):
                oride.setSelfEnabled(False)    
                return
                    


def setAttr(setParam,setValue):
    if cmds.objExists(setParam):
        maya.mel.eval("removeRenderLayerAdjustmentAndUnlock "+str(setParam)+";")
        remove_override_in_RenderSetup(setParam)
        cmds.setAttr(setParam,setValue)
    else:
        logMessageGen("WRN","Unable to set value. "+str(setParam)+" does not exist!")
        
        
def logSetAttr(setParam,setValue):
    logMessageGen("SET",str(setParam)+" = "+str(setValue))
    setAttr(setParam,setValue)
    flushLog()
        

def logSetAttrType(setParam,setValue,setType):
    logMessageGen("SET",str(setParam)+" = "+str(setValue))
    if cmds.objExists(setParam):
        maya.mel.eval("removeRenderLayerAdjustmentAndUnlock "+str(setParam)+";")
        cmds.setAttr(setParam,setValue, type=setType)
    else:
        logMessageGen("WRN","Unable to set value. "+str(setParam)+" does not exist!")


def logSetAttr2(setParam,setValue,setValueB):
    logMessageGen("SET", str(setParam)+" = "+str(setValue)+", "+str(setValueB))
    if cmds.objExists(setParam):
        maya.mel.eval("removeRenderLayerAdjustmentAndUnlock "+str(setParam)+";")
        cmds.setAttr(setParam,setValue,setValueB)
    else:
        logMessageGen("WRN","Unable to set value. "+str(setParam)+" does not exist!")
        
        
def argValid(argValue):
    return ((argValue!= None) and (len(str(argValue))>0))



def getParam(allArgList, argFindName):
    argFindName=argFindName.lower()
    for argComb in allArgList:
        arg= argComb.split(":")
        if (len(arg)<2):
            continue
        argName=arg[0].strip().lower()
        argValue=arg[1]
        for i in range(2, len(arg)):
            argValue+=":" + arg[i]
        argValue=argValue.strip()
        if (argName==argFindName):
            argValue= rrScriptHelper.replaceXMLEscapedString(argValue)
            argValue= argValue.replace("<Channel>", "<RenderPass>")
            argValue= argValue.replace("<AOV>", "<RenderPass>")
            if (argValue.lower()=="true"):
                argValue=True
            elif (argValue.lower()=="false"):
                argValue=False
            logMessage("Flag  "+argFindName.ljust(15)+": '"+str(argValue)+"'");
            return argValue
    return ""

def isPluginLoaded(pluginName):
    return (str(cmds.pluginInfo( query=True, listPlugins=True )).lower().find(pluginName.lower())>0)
    

def disableAllImageplanes():
    for img_plane in cmds.ls(type='imagePlane'):
        attr_name = '{0}.displayMode'.format(img_plane)
        if cmds.getAttr(attr_name) > 0:
            logMessage('Disabling imageplane ' + img_plane)
            cmds.setAttr(attr_name, 0)


class argParser:
    def readArguments(self,argAll):
        #argAll is *almost* a JSON string, but it is not to keep the commandline cleaner and less error prone
        logMessageDebug(argAll)
        allArgList= argAll.split(",")
        self.Renderer=getParam(allArgList,"Renderer")
        self.KSOMode=getParam(allArgList,"KSOMode")
        self.KSOPort=getParam(allArgList,"KSOPort")
        self.SName=getParam(allArgList,"SName")
        self.Database=getParam(allArgList,"Db")
        self.Layer=getParam(allArgList,"Layer")
        self.FDir=getParam(allArgList,"FDir")
        self.FName=getParam(allArgList,"FName")
        self.FNameNoVar=getParam(allArgList,"FNameNoVar")
        self.FPadding=getParam(allArgList,"FPadding")
        self.FrStart=getParam(allArgList,"FrStart")
        self.FrEnd=getParam(allArgList,"FrEnd")
        self.FrStep=getParam(allArgList,"FrStep")
        self.FrOffset=getParam(allArgList,"FrOffset")
        self.FExt=getParam(allArgList,"FExt")
        self.FExtOverride=getParam(allArgList,"FExtOverride")
        self.FOverrideFormat=getParam(allArgList,"FOverrideFormat")
        self.FSingleOutput=getParam(allArgList,"FSingleOutput")
        self.Camera=getParam(allArgList,"Camera")
        self.Threads=getParam(allArgList,"Threads")
        self.Verbose=getParam(allArgList,"Verbose")
        self.ResX=getParam(allArgList,"ResX")
        self.ResY=getParam(allArgList,"ResY")
        self.RegionX1=getParam(allArgList,"RegionX1")
        self.RegionX2=getParam(allArgList,"RegionX2")
        self.RegionY1=getParam(allArgList,"RegionY1")
        self.RegionY2=getParam(allArgList,"RegionY2")
        self.RenderThreads=getParam(allArgList,"RenderThreads")
        self.RenderDemo=getParam(allArgList,"RenderDemo")
        self.PyModPath=getParam(allArgList,"PyModPath")
        self.AA1=getParam(allArgList,"AA1")
        self.AA2=getParam(allArgList,"AA2")
        self.AA3=getParam(allArgList,"AA3")
        self.AA4=getParam(allArgList,"AA4")
        self.AAseed=getParam(allArgList,"AAseed")
        self.AASamples=getParam(allArgList,"AASamples")
        self.RenderDisplace= getParam(allArgList,"RenderDisplace")
        self.RenderMotionBlur= getParam(allArgList,"RenderMotionBlur")
        self.RenderImagePlanes = getParam(allArgList, "RenderImgPlanes")
        self.ArchiveExportEnabled= getParam(allArgList,"ArchiveExport")
        self.ArchiveExportName= getParam(allArgList,"ArchiveExportName")
        self.OverwriteRenderCmd= getParam(allArgList,"OverwriteRenderCmd")
        self.CudaDevices= getParam(allArgList,"CudaDevices")
        self.sceneOS= getParam(allArgList,"sceneOS")
        self.customScriptFile= getParam(allArgList,"customScriptFile")
        self.noEvaluationManager= getParam(allArgList,"noEvaluationManager")
        self.noIncludeAllLights= getParam(allArgList,"noIncludeAllLights")
        self.avFrameTime= getParam(allArgList,"avFrameTime")
        self.noFrameLoop= getParam(allArgList,"noFrameLoop")        
        self.pathConversionFile= getParam(allArgList,"pathConversionFile")        

globalArg = argParser() #required for KSO rendering


def renderFrames(arg,FrStart,FrEnd,FrStep,FrOffset,Renderer, Layer):
    try:
        if (not argValid(arg.FPadding)):
            arg.FPadding=4
        arg.FPadding= int(arg.FPadding)
        FrStart=int(FrStart)
        FrStart=int(FrStart)
        FrEnd=int(FrEnd)
        FrStep=int(FrStep)
        logMessage("Changing scene frame to frame #"+str(FrStart)+" ...")
        cmds.currentTime( FrStart, edit=True )    
        setAttr('defaultRenderGlobals.byFrameStep',FrStep)
        setAttr('defaultRenderGlobals.byExtension',int(FrStep))
        if (Renderer == "vray"):
            setAttr('vraySettings.frameStep',FrStep)
        maya.mel.eval('setImageSizePercent(-1.)')
        setAttr('defaultRenderGlobals.renderAll',1)
        if (not argValid(arg.FSingleOutput)):
            logSetAttr('defaultRenderGlobals.modifyExtension',1)
        #logMessage("############ Average frame time received from job: "+ str(arg.avFrameTime))
        localNoFrameLoop= arg.noFrameLoop
        if (not localNoFrameLoop): 
            if (arg.avFrameTime == 0):
                localNoFrameLoop= arg.Renderer in ("redshift", "Octane", "mayaHardware2")
            elif (arg.avFrameTime < 60):
                localNoFrameLoop= True
            elif (arg.avFrameTime < 140):
                localNoFrameLoop= arg.Renderer in ("redshift", "Octane", "mayaHardware2")
        
        
        if (localNoFrameLoop):
            frameCount= ((FrEnd - FrStart) / FrStep ) + 1
            logMessage("Starting to render frames "+str(FrStart)+" - "+str(FrEnd)+", "+str(FrStep)+" ("+str(frameCount)+" frames)")
            
            beforeFrame=datetime.datetime.now()
            logSetAttr('defaultRenderGlobals.startFrame',FrStart)
            logSetAttr('defaultRenderGlobals.endFrame',FrEnd)
            setAttr('defaultRenderGlobals.startExtension',int(FrStart)+int(FrOffset))
            if (Renderer == "vray"):
                setAttr('vraySettings.startFrame',FrStart)
                setAttr('vraySettings.endFrame',FrEnd)
            flushLog()
            if (arg.Renderer == "redshift"):
                maya.mel.eval('redshiftBatchRender("")')
            else:
                maya.mel.eval('mayaBatchRenderProcedure(0, "", "'+str(Layer)+'", "'+str(Renderer)+'", "'+arg.batchRenderOptions+'")')
            flushLog()
            afterFrame=datetime.datetime.now()
            afterFrame=afterFrame-beforeFrame
            
            afterFrame= afterFrame / frameCount
            logMessage("Frame "+str(FrStart)+" - "+str(FrEnd)+", "+str(FrStep)+" ("+str(frameCount)+" frames) done. Average frame time: "+str(afterFrame)+"  h:m:s.ms")
            flushLog()
        else:
            for frameNr in range(FrStart,FrEnd+1,FrStep):
                logMessage("Starting to render frame #"+str(frameNr)+" ...")
                if (argValid(arg.FNameNoVar) and (arg.Renderer != "mayaSoftware")):
                    if (Renderer == "vray" and not arg.FNameNoVar.endswith('.')):
                        kso_tcp.writeRenderPlaceholder_nr(arg.FDir+"/"+arg.FNameNoVar+".", frameNr, arg.FPadding, arg.FExt)
                    else:
                        kso_tcp.writeRenderPlaceholder_nr(arg.FDir+"/"+arg.FNameNoVar, frameNr, arg.FPadding, arg.FExt)
                
                beforeFrame=datetime.datetime.now()
                setAttr('defaultRenderGlobals.startFrame',frameNr)
                setAttr('defaultRenderGlobals.endFrame',frameNr)
                setAttr('defaultRenderGlobals.startExtension',int(frameNr)+int(FrOffset))
                if (Renderer == "vray"):
                    setAttr('vraySettings.startFrame',frameNr)
                    setAttr('vraySettings.endFrame',frameNr)
                flushLog()
                if (arg.Renderer == "redshift"):
                    maya.mel.eval('redshiftBatchRender("")')
                else:
                    maya.mel.eval('mayaBatchRenderProcedure(0, "", "'+str(Layer)+'", "'+str(Renderer)+'", "'+arg.batchRenderOptions+'")')
                flushLog()
                afterFrame=datetime.datetime.now()
                afterFrame=afterFrame-beforeFrame
                
                logMessage("Frame #"+str(frameNr)+" done. Frame Time: "+str(afterFrame)+"  h:m:s.ms")
                flushLog()
        
    except Exception as e:
        logMessageError(str(e))

    



def ksoRenderFrame(FrStart,FrEnd,FrStep ):
    global globalArg
    renderFrames(globalArg,FrStart,FrEnd,FrStep, globalArg.FrOffset, globalArg.Renderer, globalArg.Layer)
    flushLog()
    logMessage("rrKSO Frame(s) done #"+str(FrEnd)+" ")
    logMessage("                                                            ")
    logMessage("                                                            ")
    logMessage("                                                            ")
    flushLog()
    



def rrKSOStartServer(arg):
    try:
        logMessage("rrKSO startup...")
        if ((arg.KSOPort== None) or (len(str(arg.KSOPort))<=0)):
            arg.KSOPort=7774
        HOST, PORT = "localhost", int(arg.KSOPort)
        server = kso_tcp.rrKSOServer((HOST, PORT), kso_tcp.rrKSOTCPHandler)
        flushLog()
        time.sleep(0.3)
        logMessage("rrKSO server started")
        server.print_port()
        flushLog()
        kso_tcp.rrKSONextCommand=""
        while server.continueLoop:
            try:
                logMessageDebug("rrKSO waiting for new command...")
                server.handle_request()
                time.sleep(1) # handle_request() seem to return before handle() completed execution
            except Exception as e:
                logMessageError(e)
                server.continueLoop= False;
                import traceback
                logMessageError(traceback.format_exc())
            logMessage("rrKSO NextCommand '"+ kso_tcp.rrKSONextCommand+"'")   
            logMessage("                                                           **   ")
            logMessage("                                                         *wait* ")
            logMessage("                                                           **   ")
            flushLog()
            if (len(kso_tcp.rrKSONextCommand)>0):
                if ((kso_tcp.rrKSONextCommand=="ksoQuit()") or (kso_tcp.rrKSONextCommand=="ksoQuit()\n")):
                    server.continueLoop=False
                    kso_tcp.rrKSONextCommand=""
                else:
                    exec (kso_tcp.rrKSONextCommand)
                    kso_tcp.rrKSONextCommand=""
        logMessage("Closing TCP")    
        server.closeTCP()
        logMessage("rrKSO closed")                    
    except Exception as e:
        logMessageError(str(e))


def render_KSO(arg):
    rrKSOStartServer(arg)
    
    
def render_default(arg):
    renderFrames (arg,arg.FrStart,arg.FrEnd,arg.FrStep,arg.FrOffset,arg.Renderer,arg.Layer)


def render_overwrite(arg):
    cmdline=arg.OverwriteRenderCmd
    cmdline=cmdline.replace("aFrStart",str(arg.FrStart))
    cmdline=cmdline.replace("aFrEnd",str(arg.FrEnd))
    cmdline=cmdline.replace("aFrStep",str(arg.FrStep))
    if (argValid(arg.FDir)):
        cmdline=cmdline.replace("aFDir",str(arg.FDir))
    if (argValid(arg.FName)):
        cmdline=cmdline.replace("aFName",'"'+str(arg.FName)+'"')
    if (argValid(arg.ArchiveExportName)):
        cmdline=cmdline.replace("aArchiveExportName",'"'+str(arg.ArchiveExportName)+'"')
    if (argValid(arg.FrOffset)):
        cmdline=cmdline.replace("aFrOffset",str(arg.FrOffset))
    if (argValid(arg.Renderer)):
        cmdline=cmdline.replace("aRenderer",str(arg.Renderer))
    if (argValid(arg.Layer)):
        cmdline=cmdline.replace("aLayer",str(arg.Layer))
    if (argValid(arg.Camera)):
        cmdline=cmdline.replace("aCamera",str(arg.Camera))
    logMessage("Executing custom mel line "+cmdline)
    ret=maya.mel.eval(cmdline)
    print(ret)
    
def execute_scriptfile(arg):
    try:
        logMessage("Executing custom python code from file "+arg.customScriptFile)
        flushLog()
        if sys.version_info.major == 2:
            execfile(arg.customScriptFile)
        else:
            exec(open(arg.customScriptFile).read())
    except Exception as e:
        logMessageError(str(e))        


    

def setRenderSettings_MayaSoftware(arg):
    try:
        logSetAttr('defaultRenderGlobals.skipExistingFrames',0)
        if (argValid(arg.FOverrideFormat)): 
            maya.mel.eval('setMayaSoftwareImageFormat("'+arg.FOverrideFormat+'")')
        if (argValid(arg.Threads)):
            logSetAttr('defaultRenderGlobals.numCpusToUse',int(arg.Threads))
        if (argValid(arg.AA1)): 
            logSetAttr('defaultRenderQuality.edgeAntiAliasing',int(arg.AA1))
        if (argValid(arg.AA2)): 
            logSetAttr('defaultRenderQuality.shadingSamples',int(arg.AA2))
        if (argValid(arg.AA3)): 
            logSetAttr('defaultRenderQuality.maxShadingSamples',int(arg.AA3))
        if (argValid(arg.AA4)): 
            logSetAttr('defaultRenderQuality.redThreshold',float(arg.AA4))
            logSetAttr('defaultRenderQuality.greenThreshold',float(arg.AA4))
            logSetAttr('defaultRenderQuality.blueThreshold',float(arg.AA4))
            logSetAttr('defaultRenderQuality.coverageThreshold',float(arg.AA4))
        if (argValid(arg.RegionX1)):
            if (not argValid(arg.RegionX2)):    
                arg.RegionX2=19999
            if (not argValid(arg.RegionY1)):    
                arg.RegionY1=0
            if (not argValid(arg.RegionY2)):    
                arg.RegionY2=19999
            maya.mel.eval('setMayaSoftwareRegion('+str(arg.RegionX1)+','+str(arg.RegionX2)+','+str(arg.RegionY1)+','+str(arg.RegionY2)+')')
        if (argValid(arg.RenderMotionBlur)): 
            logSetAttr('defaultRenderGlobals.motionBlur',arg.RenderMotionBlur)
    except Exception as e:
        logMessageError(str(e))        


def setRenderSettings_MRay(arg):
    try:
        logSetAttr('defaultRenderGlobals.skipExistingFrames',0)
        if (argValid(arg.FOverrideFormat)): 
            maya.mel.eval('setMentalRayImageFormat("'+arg.FOverrideFormat+'")')
        if (argValid(arg.Verbose)):
            maya.mel.eval('global int $g_mrBatchRenderCmdOption_VerbosityOn = true; global int $g_mrBatchRenderCmdOption_Verbosity = '+str(arg.Verbose))
        if (argValid(arg.Threads)):
            maya.mel.eval('global int $g_mrBatchRenderCmdOption_NumThreadOn = true; global int $g_mrBatchRenderCmdOption_NumThread = '+str(arg.Threads))
        else:
            maya.mel.eval('global int $g_mrBatchRenderCmdOption_NumThreadAutoOn = true; global int $g_mrBatchRenderCmdOption_NumThreadAuto = true')
        if (argValid(arg.RegionX1)):
            if (not argValid(arg.RegionX2)):    
                arg.RegionX2=19999
            if (not argValid(arg.RegionY1)):    
                arg.RegionY1=0
            if (not argValid(arg.RegionY2)):    
                arg.RegionY2=19999
            maya.mel.eval('setMentalRayRenderRegion('+str(arg.RegionX1)+','+str(arg.RegionX2)+','+str(arg.RegionY1)+','+str(arg.RegionY2)+')')
        if (argValid(arg.RenderDisplace)): 
            logSetAttr('miDefaultOptions.displacementShaders',arg.RenderDisplace)        
        if (argValid(arg.RenderMotionBlur)):
            if (arg.RenderMotionBlur):
                logSetAttr('miDefaultOptions.motionBlur',2)
            else:
                logSetAttr('miDefaultOptions.motionBlur',0)        
        if (argValid(arg.AA1)): 
            logSetAttr('miDefaultOptions.minSamples',int(arg.AA1))
        if (argValid(arg.AA2)): 
            logSetAttr('miDefaultOptions.maxSamples',int(arg.AA2))
        if (argValid(arg.AA3)): 
            logSetAttr('miDefaultOptions.contrastR',float(arg.AA3))
            logSetAttr('miDefaultOptions.contrastR',float(arg.AA3))
            logSetAttr('miDefaultOptions.contrastR',float(arg.AA3))
            logSetAttr('miDefaultOptions.contrastR',float(arg.AA3))
    except Exception as e:
        logMessageError(str(e))

        
def setRenderSettings_VRay(arg):
    try:
        logSetAttr('vraySettings.globopt_cache_bitmaps',1)
    except Exception as e:
        logMessage(str(e))        
    try:
        logSetAttr('defaultRenderGlobals.skipExistingFrames',0)
        logSetAttr('vraySettings.animation',True)
        logSetAttrType('vraySettings.fileNamePrefix',arg.FDir+"/"+arg.FName,"string")        
                
        maya.mel.eval('vrayRegisterRenderer(); vrayCreateVRaySettingsNode();')
        if (argValid(arg.Threads)):
            logSetAttr('vraySettings.sys_max_threads',int(arg.Threads))
        if (argValid(arg.RegionX1)):
            if (not argValid(arg.RegionX2)):    
                arg.RegionX2=19999
            if (not argValid(arg.RegionY1)):    
                arg.RegionY1=0
            if (not argValid(arg.RegionY2)):    
                arg.RegionY2=19999
            maya.mel.eval('vraySetBatchDoRegion('+str(arg.RegionX1)+','+str(arg.RegionX2)+','+str(arg.RegionY1)+','+str(arg.RegionY2)+')')
        if (argValid(arg.ResX)): 
            logSetAttr('vraySettings.width',int(arg.ResX))
        if (argValid(arg.ResY)): 
            logSetAttr('vraySettings.height',int(arg.ResY))
        if (argValid(arg.FPadding)):
            logSetAttr('vraySettings.fileNamePadding',int(arg.FPadding))
        if (argValid(arg.Camera)):
            logSetAttrType('vraySettings.batchCamera',arg.Camera,"string")
        if (argValid(arg.FOverrideFormat)):
            logSetAttrType('vraySettings.imageFormatStr',arg.FOverrideFormat,"string")
        if (argValid(arg.AAseed)):
            logSetAttr('vraySettings.dmcs_randomSeed',int(arg.AAseed))
    except Exception as e:
        logMessageError(str(e))        
    
def setRenderSettings_Arnold(arg):
    try:
        logSetAttr('defaultRenderGlobals.skipExistingFrames',0)
        logSetAttr('defaultArnoldRenderOptions.renderType',0)
        arg.FName=arg.FName.replace("<Layer>","<RenderLayer>");
        arg.FName=arg.FName.replace("<layer>","<RenderLayer>");
        logSetAttrType('defaultRenderGlobals.imageFilePrefix',arg.FDir+"/"+arg.FName,"string")
            
        if (argValid(arg.Threads)):
            logSetAttr('defaultArnoldRenderOptions.threads_autodetect',False)
            logSetAttr('defaultArnoldRenderOptions.threads',int(arg.Threads))
        if (argValid(arg.RenderMotionBlur)): 
            logSetAttr('defaultArnoldRenderOptions.motion_blur_enable',arg.RenderMotionBlur)
        if (argValid(arg.RenderDemo)):
            if (arg.RenderDemo):
                logSetAttr('defaultArnoldRenderOptions.abortOnLicenseFail',False)
                logSetAttr('defaultArnoldRenderOptions.skipLicenseCheck',True)
            else:
                logSetAttr('defaultArnoldRenderOptions.abortOnLicenseFail',True)
                logSetAttr('defaultArnoldRenderOptions.skipLicenseCheck',False)
        if (argValid(arg.RenderDisplace)): 
            logSetAttr('defaultArnoldRenderOptions.ignoreDisplacement',(not arg.RenderDisplace))        
        if (argValid(arg.RenderMotionBlur)):
            logSetAttr('defaultArnoldRenderOptions.ignoreMotionBlur',(not arg.RenderMotionBlur))
        if (argValid(arg.FOverrideFormat)):
            try:
                import pymel.core as pm
                dAD = pm.PyNode('defaultArnoldDriver')
                dAD.ai_translator.set(arg.FOverrideFormat)
            except:
                logMessage("Warning: Unable to change output format. ")
        if (argValid(arg.FExtOverride)):
            try:
                import pymel.core as pm
                dAD = pm.PyNode('defaultArnoldDriver')
                arg.FExtOverride=arg.FExtOverride.lower()
                if (arg.FExtOverride==".exr"):
                    dAD.ai_translator.set("exr")
                elif (arg.FExtOverride==".jpeg"):
                    dAD.ai_translator.set("jpeg")
                elif (arg.FExtOverride==".jpg"):
                    dAD.ai_translator.set("jpeg")
                elif (arg.FExtOverride==".maya"):
                    dAD.ai_translator.set("maya")
                elif (arg.FExtOverride==".png"):
                    dAD.ai_translator.set("png")
                elif (arg.FExtOverride==".tif"):
                    dAD.ai_translator.set("tif")
            except:
                logMessage("Warning: Unable to change output format. ")                
        if (argValid(arg.AA1)): 
            logSetAttr('defaultArnoldRenderOptions.AASamples',int(arg.AA1))
        if (argValid(arg.AA2)): 
            logSetAttr('defaultArnoldRenderOptions.GIDiffuseSamples',int(arg.AA2))
        if (argValid(arg.AA3)): 
            logSetAttr('defaultArnoldRenderOptions.GITransmissionSamples',float(arg.AA3))
            logSetAttr('defaultArnoldRenderOptions.GISpecularSamples',float(arg.AA3))
        if (argValid(arg.AA4)): 
            logSetAttr('defaultArnoldRenderOptions.GISssSamples',float(arg.AA4))
            logSetAttr('defaultArnoldRenderOptions.GIVolumeSamples',float(arg.AA4))
        if (argValid(arg.RegionX1)):
            if (not argValid(arg.RegionX2)):    
                arg.RegionX2=19999
            if (not argValid(arg.RegionY1)):    
                arg.RegionY1=0
            if (not argValid(arg.RegionY2)):    
                arg.RegionY2=19999
            logSetAttr('defaultArnoldRenderOptions.regionMinX',int(arg.RegionX1))
            logSetAttr('defaultArnoldRenderOptions.regionMaxX',int(arg.RegionX2))
            logSetAttr('defaultArnoldRenderOptions.regionMinY',int(arg.RegionY1))
            logSetAttr('defaultArnoldRenderOptions.regionMaxY',int(arg.RegionY2))
        try:
            if (argValid(arg.Verbose)):
                logSetAttr('defaultArnoldRenderOptions.log_verbosity',int(arg.Verbose))
                logSetAttr('defaultArnoldRenderOptions.log_console_verbosity',int(arg.Verbose))
        except Exception as e:
            logMessageError(str(e))
        if (argValid(arg.AAseed)):
            logSetAttrType('defaultArnoldRenderOptions.aiUserOptions','AA_seed '+str(arg.AAseed),"string")
        if argValid(arg.AASamples):
            try:
                samples_multi = float(arg.AASamples)
            except TypeError:
                logMessage(f"Warning: Samples argument given but not a valid float: {arg.AASamples}")
            else:
                if samples_multi != 1.0:
                    new_aa_samples = round(cmds.getAttr("defaultArnoldRenderOptions.AASamples") * samples_multi)
                    logSetAttr('defaultArnoldRenderOptions.AASamples', new_aa_samples)

                    if cmds.getAttr("defaultArnoldRenderOptions.enableAdaptiveSampling"):
                        new_max_samples = round(cmds.getAttr("defaultArnoldRenderOptions.AASamplesMax") * samples_multi)
                        logSetAttr('defaultArnoldRenderOptions.AASamplesMax', new_max_samples)
                    
                    if cmds.getAttr("defaultArnoldRenderOptions.use_sample_clamp"):
                        new_samples_clamp = cmds.getAttr("defaultArnoldRenderOptions.AASampleClamp") * samples_multi
                        logSetAttr('defaultArnoldRenderOptions.AASampleClamp', new_samples_clamp)

    except Exception as e:
        logMessageError(str(e))   


def setRenderSettings_Renderman(arg):
    try:
    
        import rfm2.api.nodes
        rfm2.api.nodes.rman_globals()
        logSetAttr('defaultRenderGlobals.skipExistingFrames',0)
        arg.FName= arg.FName.replace("<Layer>","<RenderLayer>")
        arg.FName= arg.FName.replace("<layer>","<RenderLayer>")
        arg.FName= arg.FName.replace("<RenderPass>","<aov>")
        arg.FName= arg.FName + "<f"+str(arg.FPadding)+">.<ext>"
        logSetAttrType('rmanGlobals.imageOutputDir', arg.FDir,"string")
        logSetAttrType('rmanGlobals.imageFileFormat',arg.FName,"string")
            
        if (argValid(arg.Threads)):
            arg.batchRenderOptions=arg.batchRenderOptions+ " -numThreads " +str(arg.Threads)

        if (argValid(arg.RegionX1)):
            if (not argValid(arg.RegionX2)):    
                arg.RegionX2=1
            if (not argValid(arg.RegionY1)):    
                arg.RegionY1=0
            if (not argValid(arg.RegionY2)):    
                arg.RegionY2=1
            logSetAttr('rmanGlobals.opt_cropWindowEnable',1)
            logSetAttr2('rmanGlobals.opt_cropWindowTopLeft'    , float(arg.RegionX1) , float(arg.RegionY1) )
            logSetAttr2('rmanGlobals.opt_cropWindowBottomRight', float(arg.RegionX2) , float(arg.RegionY2) )
        
    except Exception as e:
        logMessageError(str(e))  
        
        
def setRenderSettings_Redshift(arg):
    try:
        maya.mel.eval('redshiftRegisterRenderer(); redshiftGetRedshiftOptionsNode(true);')
        arg.FName=arg.FName.replace("<Layer>","<RenderLayer>");
        arg.FName=arg.FName.replace("<layer>","<RenderLayer>");
        logSetAttrType('redshiftOptions.imageFilePrefix',arg.FDir+"/"+arg.FName,"string")
        logSetAttr('redshiftOptions.skipExistingFrames',0)
        try:
            availableCuda= maya.mel.eval('rsPreference -q "AllCudaDevices";')
            logMessage("Available Cuda devices: "+availableCuda)
        except Exception as e:
            logMessage("WARNING: Unable to execute function 'rsPreference -q AllCudaDevices;'") 
            logMessage(str(e))                   
        if (argValid(arg.CudaDevices)):
            arg.CudaDevices= arg.CudaDevices.replace(".",",")
            arg.CudaDevices="{"+arg.CudaDevices+"}"
            logMessageSet("CudaDevices to "+str(arg.CudaDevices))
            flushLog()
            try:
                maya.mel.eval('redshiftSelectCudaDevices('+arg.CudaDevices+');')      
            except Exception as e:
                logMessage("ERROR: Unable to execute function 'redshiftSelectCudaDevices("+str(arg.CudaDevices)+");'")
                logMessage(str(e))            
        if (argValid(arg.RenderDemo)):
            if (arg.RenderDemo):
                logSetAttr('redshiftOptions.abortOnLicenseFail',False)
            else:
                logSetAttr('redshiftOptions.abortOnLicenseFail',True)
        if (argValid(arg.Verbose)):
                logSetAttr('redshiftOptions.logLevel',int(arg.Verbose))
        if (argValid(arg.RegionX1)):
            if (not argValid(arg.RegionX2)):    
                arg.RegionX2=19999
            if (not argValid(arg.RegionY1)):    
                arg.RegionY1=0
            if (not argValid(arg.RegionY2)):    
                arg.RegionY2=19999
            maya.mel.eval('setMayaSoftwareRegion('+str(arg.RegionX1)+','+str(arg.RegionX2)+','+str(arg.RegionY1)+','+str(arg.RegionY2)+')')
        
        if argValid(arg.AASamples):
            try:
                samples_multi = float(arg.AASamples)
            except TypeError:
                logMessage(f"Warning: Samples argument given but not a valid float: {arg.AASamples}")
            else:
                if samples_multi != 1.0:
                    if cmds.getAttr("redshiftOptions.enableAutomaticSampling"):
                        logMessage("Warning: Redshift Automatic Sampling is enabled and no override will be applied")
                    else:
                        new_min_samples = max(round(cmds.getAttr("redshiftOptions.unifiedMinSamples") * samples_multi), 1)
                        logSetAttr('redshiftOptions.unifiedMinSamples', new_min_samples)

                        new_max_samples = max(round(cmds.getAttr("redshiftOptions.unifiedMaxSamples") * samples_multi), new_min_samples)
                        logSetAttr('redshiftOptions.unifiedMaxSamples', new_max_samples)

    except Exception as e:
        logMessageError(str(e))      


def printPluginsLoaded():
    loadedPlugins= cmds.pluginInfo( query=True, listPlugins=True  )
    logMessage("Plugins loaded ("+str(len(loadedPlugins))+"): ")
    column=0
    logLine=""
    for plugin in loadedPlugins:
        logLine=logLine+str(plugin)+",  "
        column+=1
        if (column >= 7):
            logMessage("    "+str(logLine))
            column=0
            logLine=""
    logMessage("    "+str(logLine))             

def loadPlugins(arg):    
    #printPluginsLoaded()    
    try:
        maya.mel.eval('loadPlugin AbcImport;')
    except:
        pass
    try:
        maya.mel.eval('loadPlugin modelingToolkit;')
    except:
        pass

    global _rrGL_mayaVersion
    global _rrGL_mayaVersionMinor
    global _rrGL_mayaVersionMinorStr
    logMessage("Maya version: "+str(_rrGL_mayaVersion)+"."+str(_rrGL_mayaVersionMinorStr))

            
    if (_rrGL_mayaVersion>=2014):
#            try:
#                logMessage("Loading FumeFX")
#                maya.mel.eval('loadPlugin FumeFX;')
#            except:
#                pass
        pass

            
    if (arg.Renderer == "arnold"):
        maya.mel.eval('loadPlugin -quiet mtoa;;')      
        version=cmds.pluginInfo( 'mtoa', query=True, version=True )
    try:
        logMessage("MtoA version: "+version)            
        pluginPath=cmds.pluginInfo( 'mtoa', query=True, path=True )
        logMessage("MtoA path: "+pluginPath)        
    except:
        pass
    if (arg.Renderer == "vray"):
        maya.mel.eval('loadPlugin vrayformaya;;')   
        maya.mel.eval('vrayRegisterRenderer();;')  
        version=cmds.pluginInfo( 'vrayformaya', query=True, version=True )
        logMessage("VRay version: "+version)   
        if (version=="Next"):
            version= "Next:  "+cmds.vray('version')
        logMessage("VRay version: "+version)   
        pluginPath=cmds.pluginInfo( 'vrayformaya', query=True, path=True )
        logMessage("VRay path: "+pluginPath)        
        if (_rrGL_mayaVersion>=2014):
            try:
                #logMessage("Loading xgenVRay.")
                #flushLog()
                #maya.mel.eval('loadPlugin xgenToolkit;')
                #maya.mel.eval('loadPlugin xgenVRay;')
                pass
            except:
                pass
        
    if (arg.Renderer == "redshift"):
        maya.mel.eval('loadPlugin redshift4maya;;')   
        version=cmds.pluginInfo( 'redshift4maya', query=True, version=True )
        logMessage("Redshift version: "+version)        
        pluginPath=cmds.pluginInfo( 'redshift4maya', query=True, path=True )
        logMessage("Redshift path: "+pluginPath)        

    if (arg.Renderer == "mentalRay"):
        maya.mel.eval('loadPlugin Mayatomr;;')
        maya.mel.eval('miLoadMayatomr;;')
        maya.mel.eval('miCreateDefaultNodes();;')
        if (_rrGL_mayaVersion>=2014):
            try:
                logMessage("Loading xgenMR.")
                flushLog()
                maya.mel.eval('loadPlugin xgenMR;')
                #maya.mel.eval('loadPlugin xgenToolkit;')
            except:
                pass

    if (arg.Renderer == "renderman"):
        try:
            maya.mel.eval('loadPlugin RenderMan_for_Maya;;')      
            version=cmds.pluginInfo( 'RenderMan_for_Maya', query=True, version=True )
            logMessage("RenderMan_for_Maya version: "+version) 
        except:
            pass
            

def doCrossOSPathConversionMaya(arg):        
    if (argValid(arg.sceneOS)): 
        arg.sceneOS=int(arg.sceneOS)
        ourOS= rrScriptHelper.getOS()
        if (ourOS != arg.sceneOS):
            osConvert= rrScriptHelper.rrOSConversion()
            osConvert.loadSettings()
            fromOS, toOS = osConvert.getTable(arg.sceneOS,True)
            if (len(fromOS)>0):
                cmds.dirmap( en=True )
                for i in range(len(fromOS)):
                    logMessage("Add OS conversion to Maya dirmap:  %-30s  =>  %-30s" % (fromOS[i] , toOS[i]) )
                    cmds.dirmap( m=(fromOS[i], toOS[i]))

def doCrossOSPathConversionMaya_CustomFile(arg, customIniFilename, ID_fromOS, ID_toOS):        
    if (ID_fromOS != ID_toOS):
        osConvert= rrScriptHelper.rrOSConversion()
        osConvert.setIniFile(customIniFilename)
        osConvert.loadSettings()
        fromOS, toOS = osConvert.getTableOS(ID_fromOS, ID_toOS,True)
        if (len(fromOS)>0):
            cmds.dirmap( en=True )
            for i in range(len(fromOS)):
                logMessage("Add OS conversion to Maya dirmap:  %-30s  =>  %-30s" % (fromOS[i] , toOS[i]) )
                cmds.dirmap( m=(fromOS[i], toOS[i]))


def ireplaceStartsWith(text, old, new ):
    idx = 0
    while idx < len(text):
        index_l = text.lower().find(old.lower(), idx)
        if index_l == -1:
            return text
        if index_l > 0:
            return text
        text = text[:index_l] + new + text[index_l + len(old):]
        idx = index_l + len(old)
    return text


def allForwardSlashes(filepath):
    return os.path.normpath(filepath).replace('\\', '/')


def doCrossOSPathConversion_node(nodeTypeName, attribName, fromOS, toOS):  
    nodeList = cmds.ls(type=nodeTypeName)
    if (nodeList!=None):
        #logMessage(nodeTypeName + " list  "+str(type(nodeList))+"     "+str(nodeList))            
        for o in nodeList:
            fileName = cmds.getAttr(o + attribName)

            if (fileName!=None and (len(fileName)>0)):
                fileName = allForwardSlashes(fileName)
                for i in range(len(fromOS)):
                    if (fromOS[i].lower() in fileName.lower()):
                        fileName = ireplaceStartsWith(fileName,fromOS[i], toOS[i])
                        cmds.setAttr(o + attribName, fileName, type = 'string')
                        logMessage('Replaced '+fromOS[i]+' with '+toOS[i]+' in node ' + o+attribName)   

def doCrossOSPathConversion_node_list(nodeTypeName, attribName, fromOS, toOS):  
    nodeList = cmds.ls(type=nodeTypeName)
    if (nodeList!=None):
        #logMessage(nodeTypeName + " list  "+str(type(nodeList))+"     "+str(nodeList))            
        for o in nodeList:
            filesString = cmds.getAttr(o + attribName)

            if (filesString!=None and (len(filesString)>0)):
                wasChanged= False
                filesString = allForwardSlashes(filesString)
                fList=filesString.split(':')
                for i in range(0,len(fList)):
                    if (fList[i]!=None and (len(fList[i])>0)):
                        for i in range(len(fromOS)):
                            if (fromOS[i].lower() in fList[i].lower()):
                                fList[i] = ireplaceStartsWith(fList[i],fromOS[i], toOS[i])
                                wasChanged=True
                if (wasChanged):
                    filesString= ":".join(fList)
                    cmds.setAttr(o + attribName, filesString, type = 'string')
                    logMessage('Replaced node ' + o+attribName + ' to '+filesString)   

						
def doCrossOSPathConversion_node_OnlyWithVariable(nodeTypeName, attribName, fromOS, toOS):  
    nodeList= cmds.ls(type=nodeTypeName)
    if (nodeList!=None):
        #logMessage(nodeTypeName + " list  "+str(type(nodeList))+"     "+str(nodeList))            
        for o in nodeList:
            fileName = cmds.getAttr(o + attribName)

            if (fileName!=None and (len(fileName)>0)):
                fileName = allForwardSlashes(fileName)
                for i in range(len(fromOS)):
                    if (fromOS[i].lower() in fileName.lower()):
                        if '<' in fileName:
                            fileName = ireplaceStartsWith(fileName,fromOS[i], toOS[i])
                            cmds.setAttr(o + attribName, fileName, type = 'string')
                            logMessage('Replaced '+fromOS[i]+' with '+toOS[i]+' in node ' + o+attribName)   


def doCrossOSYetiConversion(fromOS, toOS):
    nodeList = cmds.ls(dag=1, o=1, type='pgYetiMaya')

    if not nodeList:
        return

    for fur in nodeList:
        logMessage('CrossOS, processing Yeti: ' + fur)

        # Get all texture nodes in current Yeti graph
        furTextureNodes = maya.mel.eval('pgYetiGraph -listNodes -type "texture" ' + fur)

        if not furTextureNodes:
            continue

        for furTex in furTextureNodes:
            # Get texture path
            texturePath = maya.mel.eval(
                'pgYetiGraph -node "' + furTex + '" -param "file_name" -getParamValue ' + fur)

            if not texturePath:
                continue

            texturePath = allForwardSlashes(texturePath)

            for i, fromOS_path in enumerate(fromOS):
                if fromOS_path in texturePath:
                    converted_path = ireplaceStartsWith(texturePath, fromOS_path, toOS[i])

                    melString = 'pgYetiGraph -node "{0}" -param "file_name" -setParamValueString "{1}" {2}'.format(furTex, converted_path, fur)
                    maya.mel.eval(melString)
                    logMessage('Replaced "{0}" with "{1}" in node {1}'.format(fromOS_path, toOS[i], fur))

def doCrossOSPathConversion_sub(arg, fromOS, toOS):        
    for i, fromOS_path in enumerate(fromOS):
        fromOS[i] = allForwardSlashes(fromOS_path)

    for i, toOS_path in enumerate(toOS):
        toOS[i] = allForwardSlashes(toOS_path)

    if (len(fromOS)>0):
        print("______________________________________________________ doCrossOSPathConversion() _____________________________________________________________________" )            
        #logMessage("fromOS  is "+str(type(fromOS))+"     "+str(fromOS))            
        #Mayas conversion does not work for texture file nodes of VRay with a <variable> in it
        textureFileList=cmds.ls(type='file')
        #logMessage("textureFileList  is "+str(type(textureFileList))+"     "+str(textureFileList))            
        if (textureFileList!=None):
            for o in textureFileList:
                fileName = cmds.getAttr(o + '.fileTextureName')

                if (fileName!=None and (len(fileName)>0)):
                    fileName = allForwardSlashes(fileName)
                    for i in range(len(fromOS)):
                        if fromOS[i].lower() in fileName.lower():
                            # Test for < character in filename
                            if '<' in fileName:
                                # Store color space
                                colorSpace = cmds.getAttr(o + '.colorSpace')
                                fileName = ireplaceStartsWith(fileName, fromOS[i], toOS[i])
                                # Change texture path
                                cmds.setAttr(o + '.fileTextureName', fileName, type = 'string')
                                # Restore color space
                                cmds.setAttr(o + '.colorSpace', colorSpace, type = 'string')
                                # Print info
                                logMessage('Replaced '+fromOS[i]+' with '+toOS[i]+' in node ' + o)       



        if (isPluginLoaded('xgenToolkit')):
            doCrossOSPathConversion_node('xgmCurveToSpline', '.fileName', fromOS, toOS)  # xgen
            doCrossOSPathConversion_node('xgmSplineCache', '.fileName', fromOS, toOS)  # xgen
        
        if (isPluginLoaded('Boss')):
            doCrossOSPathConversion_node('BossWaveSolver', '.absoluteCacheName', fromOS, toOS)
            doCrossOSPathConversion_node('BossWaveSolver', '.cacheFolder', fromOS, toOS)
            doCrossOSPathConversion_node('BossWaveSolver', '.velocityCacheName', fromOS, toOS)
            doCrossOSPathConversion_node('BossWaveSolver', '.foamCacheName', fromOS, toOS)
            doCrossOSPathConversion_node('BossWaveSolver', '.remappedInputCacheName', fromOS, toOS)

            doCrossOSPathConversion_node('BossSpectralWave', '.absoluteCacheName', fromOS, toOS)
            doCrossOSPathConversion_node('BossSpectralWave', '.cacheFolder', fromOS, toOS)
            doCrossOSPathConversion_node('BossSpectralWave', '.velocityCacheName', fromOS, toOS)
            doCrossOSPathConversion_node('BossSpectralWave', '.foamCacheName', fromOS, toOS)
        
        if ("vray" in arg.Renderer):
            doCrossOSPathConversion_node('VRayVolumeGrid', '.inPath', fromOS, toOS)
            doCrossOSPathConversion_node_OnlyWithVariable('VRayMesh', '.fileName2', fromOS, toOS)
            doCrossOSPathConversion_node_OnlyWithVariable('VRayProxy', '.fileName', fromOS, toOS)
            doCrossOSPathConversion_node_OnlyWithVariable('VRayScene', '.FilePath', fromOS, toOS)

        if ("redshift" in arg.Renderer):
            doCrossOSPathConversion_node('RedshiftProxyMesh', '.fileName', fromOS, toOS)
            
        if ("arnold" in arg.Renderer):
            doCrossOSPathConversion_node('aiVolume', '.filename', fromOS, toOS)
            doCrossOSPathConversion_node_list('defaultArnoldRenderOptions', '.procedural_searchpath', fromOS, toOS)
            doCrossOSPathConversion_node_list('defaultArnoldRenderOptions', '.plugin_searchpath', fromOS, toOS)
            doCrossOSPathConversion_node_list('defaultArnoldRenderOptions', '.texture_searchpath', fromOS, toOS)
            
        if (isPluginLoaded('Yeti')):
            doCrossOSPathConversion_node('pgYetiMaya', '.cacheFileName', fromOS, toOS)
            doCrossOSYetiConversion(fromOS, toOS)
            
        fileNodeList= cmds.ls(type='colorManagementGlobals')
        #logMessage("fileNodeList  is "+str(type(fileNodeList))+"     "+str(fileNodeList))            
        if (fileNodeList!=None):
            for o in fileNodeList:
                fileName = cmds.getAttr(o + '.configFilePath')

                if (fileName!=None and (len(fileName)>0) ):
                    fileName = allForwardSlashes(fileName)
                    for i in range(len(fromOS)):
                        if fromOS[i].lower() in fileName.lower():
                            fileName = ireplaceStartsWith(fileName,fromOS[i], toOS[i])
                            #cmds.setAttr(o + '.configFilePath', fileName, type = 'string')
                            #fileName = cmds.getAttr(o + '.configFilePath')
                            cmds.colorManagementPrefs(e=True, configFilePath=fileName)
                            cmds.colorManagementPrefs(e=True, cmEnabled=True)
                            cmds.colorManagementPrefs(e=True, cmConfigFileEnabled=True)
                            logMessage('Replaced '+fromOS[i]+' with '+toOS[i]+' in colorManagementPrefs')   
        print("______________________________________________________________________________________________________________________________________________________" )  


def doCrossOSPathConversion(arg):        
    if (argValid(arg.sceneOS)): 
        ourOS= rrScriptHelper.getOS()
        if (ourOS != arg.sceneOS):
            osConvert= rrScriptHelper.rrOSConversion()
            osConvert.loadSettings()
            fromOS, toOS = osConvert.getTable(arg.sceneOS,True)
            doCrossOSPathConversion_sub(arg, fromOS, toOS)       
    logMessage("OS conversion done")                                  

def doCrossOSPathConversion_CustomFile(arg, customIniFilename, ID_fromOS, ID_toOS):        
    if (ID_fromOS != ID_toOS):
        osConvert= rrScriptHelper.rrOSConversion()
        osConvert.loadSettings()
        fromOS, toOS = osConvert.getTableOS(ID_fromOS, ID_toOS, True)
        doCrossOSPathConversion_sub(arg, fromOS, toOS)       
    logMessage("OS conversion done '"+customIniFilename)  
 


def checkColorPrefsFile():
    fileNodeList= cmds.ls(type='colorManagementGlobals')
    if (fileNodeList!=None):
        for o in fileNodeList:
            fileName = cmds.getAttr(o + '.configFilePath')
            if (fileName!=None and (len(fileName)>0)):
                if (not "<MAYA_RESOURCES>" in fileName):
                    if not os.path.isfile(fileName):
                        logMessage('Warning: ColorManagement file not found!. It is set to \''+fileName+'\'')   
            logMessage('ColorManagement settings: ')
            logMessage('   cmEnabled:           ' + str(cmds.getAttr(o + '.cmEnabled')) )
            logMessage('   configFileEnabled:   ' + str(cmds.getAttr(o + '.configFileEnabled')) )
            logMessage('   configFilePath:      ' + cmds.getAttr(o + '.configFilePath') )
            logMessage('   viewTransformName:   ' + cmds.getAttr(o + '.viewTransformName') )
            logMessage('   workingSpaceName:    ' + cmds.getAttr(o + '.workingSpaceName') )
            logMessage('   outputTransformName: ' + cmds.getAttr(o + '.outputTransformName') )

                                
def rrYetiChanges(arg):   
    hasYeti= isPluginLoaded('Yeti')
    if (hasYeti):
        yetiNodes= cmds.ls( type='pgYetiGroom' ) + cmds.ls( type='pgYetiMaya' ) + cmds.ls( type='pgYetiMayaFeather' )
        hasYeti= (len(yetiNodes)>0)
    try:
        if (not hasYeti):
            logMessage("Removing potential Yeti commands as there are no yeti nodes");
            melStrg= cmds.getAttr('defaultRenderGlobals.preMel') 
            if (melStrg!=None):
                melStrg=melStrg.replace("pgYetiVRayPreRender","")
                melStrg=melStrg.replace(";;",";")
                cmds.setAttr('defaultRenderGlobals.preMel',melStrg, type="string") 

            melStrg= cmds.getAttr('defaultRenderGlobals.postMel') 
            if (melStrg!=None):
                melStrg=melStrg.replace("pgYetiVRayPostRender","")
                melStrg=melStrg.replace(";;",";")
                cmds.setAttr('defaultRenderGlobals.postMel',melStrg, type="string") 

            melStrg= cmds.getAttr('defaultRenderGlobals.preRenderMel') 
            if (melStrg!=None):
                melStrg=melStrg.replace("pgYetiPrmanFlush","")
                melStrg=melStrg.replace(";;",";")
                cmds.setAttr('defaultRenderGlobals.preRenderMel',melStrg, type="string") 
                
            melStrg= cmds.getAttr('defaultRenderGlobals.postRenderMel') 
            if (melStrg!=None):
                melStrg=melStrg.replace("pgYetiPrmanFlush","")
                melStrg=melStrg.replace(";;",";")
                cmds.setAttr('defaultRenderGlobals.postRenderMel',melStrg, type="string") 
                
            melStrg= cmds.getAttr('defaultRenderGlobals.preRenderLayerMel') 
            if (melStrg!=None):
                melStrg=melStrg.replace("pgYetiPrmanFlush","")
                melStrg=melStrg.replace(";;",";")
                cmds.setAttr('defaultRenderGlobals.preRenderLayerMel',melStrg, type="string") 
                
            melStrg= cmds.getAttr('defaultRenderGlobals.postRenderLayerMel') 
            if (melStrg!=None):
                melStrg=melStrg.replace("pgYetiPrmanFlush","")
                melStrg=melStrg.replace(";;",";")
                cmds.setAttr('defaultRenderGlobals.postRenderLayerMel',melStrg, type="string")                 
        else:
            #changing YETI temp folder to localhosts temp instead of the Maya scene/project folder
            if 'TEMP' in os.environ and 'YETI_TMP' in os.environ:
                tempPath = os.environ['TEMP']
                tempPath = allForwardSlashes(tempPath)
                os.environ['currentYetiTempDirectory'] = tempPath

            melStrg = cmds.getAttr('defaultRenderGlobals.preMel')

            if 'TEMP' in os.environ or 'YETI_TMP' in os.environ:
                if melStrg:
                    melStrg = melStrg.replace("putenv \"YETI_TMP\" \"\\\\\\\\jfpsohostorage\\\\render\\\\yeti_render_data\"","")
                    melStrg = melStrg.replace("pgYetiPreRender", "")
                    melStrg = melStrg.replace(";;", ";")
                    cmds.setAttr('defaultRenderGlobals.preMel', melStrg, type="string")
    except Exception as e:
        logMessage(str(e))  

def rrStart(argAll):
    try:    
        initGlobalVars()
        flushLog()
        logMessage("")
        print("_______________________________________________________ Maya started ____________________________________________________________________" )            
        cmds.cycleCheck(e=False )
        
        timeStart=datetime.datetime.now()
        arg= argParser()
        arg.readArguments(argAll)
        arg.batchRenderOptions= ""

        if (argValid(arg.PyModPath)): 
            import sys
            logMessage("Append python search path with '" +arg.PyModPath+"'" )
            sys.path.append(arg.PyModPath)
        global kso_tcp
        import kso_tcp   
        kso_tcp.USE_LOGGER= False
        kso_tcp.USE_DEFAULT_PRINT= True 
        kso_tcp.rrKSO_logger_init()

        try:
            logMessage("Set Workspace to '" +arg.Database+"'" )
            cmds.workspace(arg.Database, openWorkspace=True )
        except Exception as e:
            logMessageGen("WRN",str(e))

        logMessage("Set image dir to '" +arg.FDir+"'" )
        cmds.workspace(fileRule = ['images', arg.FDir])
        cmds.workspace(fileRule = ['depth', arg.FDir])


        loadPlugins(arg)
        if 'RR_PathConversionFile' in os.environ:
            arg.pathConversionFile = os.environ['RR_PathConversionFile'].strip("\r")
        if argValid(arg.pathConversionFile):
            doCrossOSPathConversionMaya_CustomFile(arg, arg.pathConversionFile, 1, 2)
        doCrossOSPathConversionMaya(arg)
        
        if argValid(arg.noEvaluationManager):
            logMessageSet("Animation Evaluation Manager to 'off' (DG).")
            cmds.evaluationManager(mode="off")
            
        restore_includeAllLights = False
        includeAllLights_default = cmds.optionVar(q='renderSetup_includeAllLights')
        if argValid(arg.noIncludeAllLights):
            logMessageDebug("renderSetup_includeAllLights is set to " + str(includeAllLights_default))
            logMessageSet("renderSetup_includeAllLights to 'off'.")
            cmds.optionVar(iv=('renderSetup_includeAllLights', 0))
            restore_includeAllLights = True
        
        print("______________________________________________________ About to open scene file ___________________________________________________________________" )            
        logMessage("Open Scene file '" +arg.SName+"'   " )
        flushLog()
        cmds.file( arg.SName, f=True, o=True )
        flushLog()
        print("______________________________________________________ Scene opened _____________________________________________________________________" )            

        if (argValid(arg.pathConversionFile)):
            doCrossOSPathConversion_CustomFile(arg, arg.pathConversionFile, 1, 2)
        doCrossOSPathConversion(arg)
        checkColorPrefsFile()
        
        global _rrGL_mayaVersion        
        global _rrGL_mayaVersionMinor

        if argValid(arg.RenderImagePlanes) and not arg.RenderImagePlanes:
            disableAllImageplanes()

        
        if (_rrGL_mayaVersion>2016 or (_rrGL_mayaVersion==2016 and _rrGL_mayaVersionMinor>=50)):
            prefNewSystemEnabled= cmds.optionVar( q='renderSetupEnable' )
            globalVarSet=maya.mel.eval('global int $renderSetupEnableCurrentSession; $tempVar=$renderSetupEnableCurrentSession;')
            renderSetupCount   = len( cmds.ls( type="renderSetupLayer" ) )  #New 
            renderLayerCount   = len( cmds.ls( type="renderLayer" ) ) #Old 
            renderLayerCount= renderLayerCount - renderSetupCount
            logMessage("New Render Setup layer  count: "+str(renderSetupCount))          
            logMessage("Legacy layer count: "+str(renderLayerCount))
            logMessage("New Render Setup preference enabled: "+str(prefNewSystemEnabled))
            logMessage("New Render Setup enabled: "+str(globalVarSet))
            if (renderSetupCount>0): 
                if (prefNewSystemEnabled!=1):
                    logMessageError("The new Render Setup layer system has been disabled via the Maya prefs! Unable to render scene file!")
                    return
                if (globalVarSet!=1):
                    logMessageSet("render layer system to new Render Setup mode");
                    maya.mel.eval('global int $renderSetupEnableCurrentSession; $renderSetupEnableCurrentSession=1;')   
            elif (renderLayerCount>0):
                if (_rrGL_mayaVersion>2018 or (_rrGL_mayaVersion==2018 and _rrGL_mayaVersionMinor>= 300)):
                    logMessageSet("render layer system to old Legacy mode (2018.3+)");
                    try:
                        cmds.mayaHasRenderSetup(edit = True, enableCurrentSession = False)
                    except Exception as e:
                        logMessageGen("WRN",str(e))                    
                elif (globalVarSet!=0):
                    logMessageSet("render layer system to old Legacy mode (<2018.3)");
                    maya.mel.eval('global int $renderSetupEnableCurrentSession; $renderSetupEnableCurrentSession=0;')   
            else:
                if (prefNewSystemEnabled!=1):
                    logMessageError("The new Render Setup layer system has been disabled via the Maya prefs! Unable to render scene file!")
                    return
                if (globalVarSet!=1):
                    logMessageSet("render layer system to new Render Setup mode");
                    maya.mel.eval('global int $renderSetupEnableCurrentSession; $renderSetupEnableCurrentSession=1;')   
 
        
        if (argValid(arg.Layer)): 
            mayaRSUpdated= False
            mayaRSUpdated= maya.mel.eval('exists("renderLayerDisplayName")')!=0;
            if (arg.Layer == "masterLayer"):
                arg.Layer= "defaultRenderLayer"
            RenderLayer=cmds.listConnections( "renderLayerManager", t="renderLayer")
            if (not arg.Layer.upper() in (name.upper() for name in RenderLayer)):
                layerFound= False
                if (mayaRSUpdated):
                    arg.Layer="rs_"+arg.Layer
                    if (arg.Layer.upper() in (name.upper() for name in RenderLayer)):
                        layerFound= True
                if (not layerFound):
                    logMessageError("Requested layer does not exist!" )
                    return
                
            logMessageSet("layer to '" +arg.Layer+"'" )
            maya.mel.eval('setMayaSoftwareLayers("'+arg.Layer+'","" );')
            #above command does only disable the other layers, but for example an .ass export requires the layer to be selected:
            cmds.editRenderLayerGlobals( currentRenderLayer= arg.Layer )
            #set layer to renderable in case someone disabled it in Maya. Some renderer do not start to render in this case (e.g. Redshift)
            cmds.setAttr( arg.Layer + ".renderable", 1 )
                
        rrYetiChanges(arg)
        
        if (not argValid(arg.Renderer)): 
            arg.Renderer=cmds.getAttr('defaultRenderGlobals.currentRenderer')
        logMessage("Renderer is '" + arg.Renderer+"'")


        if (not argValid(arg.FPadding)):
            arg.FPadding=4


        if (not argValid(arg.FSingleOutput)):
            logSetAttrType('defaultRenderGlobals.imageFilePrefix',arg.FName,"string")
            maya.mel.eval('removeRenderLayerAdjustmentAndUnlock defaultRenderGlobals.animation;')
            logSetAttr('defaultRenderGlobals.animation',True)
            maya.mel.eval('removeRenderLayerAdjustmentAndUnlock defaultRenderGlobals.startFrame;')
            maya.mel.eval('removeRenderLayerAdjustmentAndUnlock defaultRenderGlobals.endFrame;')
            maya.mel.eval('removeRenderLayerAdjustmentAndUnlock defaultRenderGlobals.byFrameStep;')
            maya.mel.eval('removeRenderLayerAdjustmentAndUnlock defaultRenderGlobals.modifyExtension;')
            maya.mel.eval('removeRenderLayerAdjustmentAndUnlock defaultRenderGlobals.startExtension;')
            logSetAttr('defaultRenderGlobals.modifyExtension',0)
            if (argValid(arg.FPadding)):
                logSetAttr('defaultRenderGlobals.extensionPadding',int(arg.FPadding))
            if (not argValid(arg.FrOffset)):
                arg.FrOffset=0
            logSetAttr('defaultRenderGlobals.startExtension',int(arg.FrStart)+int(arg.FrOffset))

        
        if (argValid(arg.Camera)): 
            logMessageSet("camera to '" +arg.Camera+"'" )
            maya.mel.eval('makeCameraRenderable("'+arg.Camera+'")')
        cameraList=cmds.ls(ca=True)
        foundRenderCam=False
        for cam in cameraList:
            if (cmds.getAttr(cam+'.renderable')):
                foundRenderCam=True
        if not foundRenderCam:
            logMessage("ERROR: No camera set in render settings!")
            

        if (argValid(arg.Threads)):
            logMessageSet("threads to '" +arg.Threads+"'" )
            cmds.threadCount( n=arg.Threads )

        if (argValid(arg.ResX)): 
            logMessageSet("width to '" +arg.ResX+"'" )
            logSetAttr('defaultResolution.width',int(arg.ResX))
        if (argValid(arg.ResY)): 
            logMessageSet("height to '" +arg.ResY+"'" )
            logSetAttr('defaultResolution.height',int(arg.ResY))


        if (arg.Renderer == "mayaSoftware"):
            setRenderSettings_MayaSoftware(arg)
        elif (arg.Renderer == "mentalRay"):
            setRenderSettings_MRay(arg)
        elif (arg.Renderer == "vray"):
            setRenderSettings_VRay(arg)
        elif (arg.Renderer == "arnold"):
            setRenderSettings_Arnold(arg)
        elif (arg.Renderer == "renderman"):
            setRenderSettings_Renderman(arg)
        elif (arg.Renderer == "redshift"):
            setRenderSettings_Redshift(arg)
      

        maya.mel.eval('setImageSizePercent(-1.)')
        logSetAttr('defaultRenderGlobals.renderAll',1)

        if (not argValid(arg.noFrameLoop)): 
            arg.noFrameLoop= False
        if (not argValid(arg.avFrameTime)):
            arg.avFrameTime= 0
        else:
            arg.avFrameTime= int(arg.avFrameTime)

        arg.FrStart=int(arg.FrStart)
        arg.FrEnd=int(arg.FrEnd)
        arg.FrStep=int(arg.FrStep)
        global globalArg
        globalArg=arg #copy for kso render
        timeEnd=datetime.datetime.now()
        timeEnd=timeEnd - timeStart;
        logMessage("Scene load time: "+str(timeEnd)+"  h:m:s.ms")
        logMessage("Scene init done, starting to render... ")
        flushLog()

        if (argValid(arg.customScriptFile)):
            execute_scriptfile(arg)
        elif (argValid(arg.OverwriteRenderCmd)):
            render_overwrite(arg)
        elif (argValid(arg.KSOMode) and arg.KSOMode): 
            render_KSO(arg)
        else:
            render_default(arg)
            
        logMessage("Render done")
    except Exception as e:
        logMessageError(str(e))
    
    # reset preferences in case they have changed
    if restore_includeAllLights:
        logMessageSet("renderSetup_includeAllLights restored to '{0}'.".format(includeAllLights_default))
        cmds.optionVar( iv=('renderSetup_includeAllLights', includeAllLights_default))
    
    flushLog()
    logMessage("                                      .   ")
    logMessage("                                     ...  ")
    logMessage("                                    ..... ")
    logMessage("                                   ..end..")
    flushLog()
    time.sleep(2) #some delay as some log messages seem to be cut off

print("RR kso_maya.py script  %rrVersion% loaded\n")
flushLog()

