#python
# -*- coding: cp1252 -*-
######################################################################
#
# Royal Render Render script for Houdini
# Author:  Royal Render, Holger Schoenberger, Binary Alchemy
# Version %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy
# 
######################################################################

import datetime
import time
import sys
import os


if sys.version_info.major == 2:
    range = xrange
   
def logMessageGen(lvl, msg):
    if (len(lvl)==0):
        print(datetime.datetime.now().strftime("' %H:%M.%S") + " rrHoudini      : " + str(msg))
    else:
        print(datetime.datetime.now().strftime("' %H:%M.%S") + " rrHoudini - " + str(lvl) + ": " + str(msg))

def logMessage(msg):
    logMessageGen("",msg)
    
def logMessageDebug( msg):
    if (False):
        logMessageGen("DGB", msg)

def logMessageSET(msg):
    logMessageGen("SET",msg)

def flushLog():
    sys.stdout.flush()        
    sys.stderr.flush()    

def logMessageError(msg, doRaise):
    msg= str(msg).replace("\\n","\n")
    logMessageGen("ERR", str(msg)+"\n")
    import traceback
    logMessageGen("ERR",traceback.format_exc()+"\n")    
    flushLog()
    if doRaise:
        raise NameError("\nError reported, aborting render script\n")


def argValid(argValue):
    return ((argValue!= None) and (len(str(argValue))>0))

def switchTake(takeName):
    houVersion= hou.applicationVersion()
    logMessage("Houdini version: "+str(houVersion[0])+" "+str(houVersion))
    if (houVersion[0]>17):
        if (takeName=="Main"):
            logMessageSET("scene take to main (master) take")
            hou.takes.setCurrentTake(hou.takes.rootTake())
        else:
            logMessageSET("scene take to " + takeName)
            hou.takes.setCurrentTake(hou.takes.findTake(takeName))
    else:
       logMessageSET("scene take to " + takeName)
       hou.hscript("takeset "+takeName) #replaced by hou.takes.setCurrentTake() since version ??
    #hou.hscript("set -g WEDGE ="+takeName)
   

def switchWedge(arg):
    wedgeSplit= arg.wedge.split('*')
    if (len(wedgeSplit)!=2):
        logMessageError("Unable to split wedge setting "+arg.wedge+" into node and index", True)
        return
    wedgeIndex= int(wedgeSplit[1])
    wedgeRop = hou.node( wedgeSplit[0] )
    arg.wedgeRop= wedgeRop
    if wedgeRop == None:
        logMessageError("Wedge node \"" + wedgeSplit[0] + "\" does not exist", True )
        return
    logMessageSET("wedge "+wedgeSplit[0] +" to index "+str(wedgeIndex))
    wedgeRop.parm('random').set(0)
    wedgeRop.parm('wedgenum').set(wedgeIndex)
    wedgeRop.parm('wrange').set("single")
    # playbar does not exist in batch, therefore we cannot use this command.....   framerange= hou.playbar.timelineRange()
    #startFrame= hou.hscriptExpression("$FSTART")
    #logMessageSET("Current frame to start frame  "+str(startFrame) +" to update sims with wedge change.")
    #hou.setFrame(startFrame)
    
    

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
                logMessage("Flag  "+argFindName.ljust(15)+": '"+str(argValue)+"'")
                return argValue
        return ""
    
    def readArguments(self):
        self.renderer= self.getParam("-renderer")
        self.rendererExportMode=self.getParam("-exportmode")
        self.sceneFile=self.getParam("-scene")
        self.FrStart=self.getParam("-FrStart")
        self.FrEnd=self.getParam("-FrEnd")
        self.FrStep=self.getParam("-FrStep")
        self.ropName=self.getParam("-rop")
        if (not argValid(self.ropName)):
            self.ropName=self.getParam("-layer")
        self.FName=self.getParam("-FName")
        self.FRefName=self.getParam("-FRefName")
        self.FExt=self.getParam("-FExt")
        self.FPadding=self.getParam("-FPadding")
        self.FSingleFile=self.getParam("-FSingleFile")
        self.camera=self.getParam("-camera")
        self.threads=self.getParam("-threads")
        self.verbose=self.getParam("-verbose")
        self.tile=self.getParam("-tile")
        self.totalTiles=self.getParam("-totalTiles")
        self.width=self.getParam("-width")
        self.height=self.getParam("-height")
        self.KSOMode=self.getParam("-KSOMode")
        self.KSOPort=self.getParam("-KSOPort")
        self.take=self.getParam("-take")
        self.PyModPath=self.getParam("-PyModPath")
        self.renderDemo=self.getParam("-renderDemo")
        self.gpuBits=self.getParam("-gpuBits")
        self.syncDeepFileName=self.getParam("-syncDeepFileName")
        self.wedge=self.getParam("-wedge")
        self.avFrameTime=self.getParam("-avFrameTime")
        self.allFramesAtOnce=self.getParam("-noFrameLoop")
        self.SkipExisting=self.getParam("-SkipExisting")
        self.ignoreLoadIssues=self.getParam("-ignoreLoadIssues")
        self.subFrames=self.getParam("-subFrames")
        self.unlockAssets=self.getParam("-unlockAssets")
        self.ignoreROPDependencies=self.getParam("-ignoreROPDependencies")
        




def formatExceptionInfo(maxTBlevel=5):
         import traceback
         cla, exc, trbk = sys.exc_info()
         excName = cla.__name__
         try:
             excArgs = exc.__dict__["args"]
         except KeyError:
             excArgs = ""
         excTb = traceback.format_tb(trbk, maxTBlevel)
         return (excName, excArgs, excTb)


def setParmException(node, parmName, value):
    try:
        node.parm(parmName).deleteAllKeyframes()
    except:
        logMessage("Error: Unable to delete keyframes of "+ node.name() + "." + parmName + " !")
    try:
        arg.rop.parm(parmName).set(value )
    except Exception as e:
        logMessage("Error: Unable to change '"+ node.name() +"."+ parmName + "' to " + str(value) + " ! "+str(e))    


    
def setROPValue(paramdesc, parmName, value, logError=True):
    global arg
    logMessageSET("ROP " + paramdesc + " to " + str(value))
    try:
        arg.rop.parm(parmName).deleteAllKeyframes()
    except Exception as e:
        if (logError):
            logMessage("Error: Unable to delete keyframes of  "+ paramdesc +" in "+ arg.rop.name() + " ! "+str(e))
    try:
        arg.rop.parm(parmName).set(value)
    except Exception as e:
        if (logError):
            logMessage("Error: Unable to change "+ paramdesc +" in "+ arg.ropName +" ! "+str(e))    


def renderFrames_sub(localFrStart,localFrEnd,localFrStep, imgRes):
    beforeFrame = datetime.datetime.now()
    flushLog()
    global arg
    frameRange = (localFrStart,localFrEnd,localFrStep)
    rrIgnoreInputs=False
    if (argValid(arg.ignoreROPDependencies)):
        rrIgnoreInputs=True
    
    if (argValid(arg.wedge)):
        arg.rop.parm('trange').set("normal")
        arg.rop.parm('f1').deleteAllKeyframes()
        arg.rop.parm('f2').deleteAllKeyframes()
        arg.rop.parm('f3').deleteAllKeyframes()        
        arg.rop.parm('f1').set(frameRange[0])
        arg.rop.parm('f2').set(frameRange[1])
        arg.rop.parm('f3').set(frameRange[2])
        if (argValid(arg.verbose) and arg.verbose):
            arg.wedgeRop.render( res=imgRes, verbose=True, output_progress=True, method=hou.renderMethod.FrameByFrame)
        else:
            arg.wedgeRop.render( res=imgRes, method=hou.renderMethod.FrameByFrame)
    elif (type(arg.rop)==hou.RopNode):
        #logMessage("Output node is a ROP node")
        if (argValid(arg.verbose) and arg.verbose):
            arg.rop.render(frame_range=frameRange, res=imgRes, verbose=True, output_progress=True, method=hou.renderMethod.FrameByFrame, ignore_inputs=rrIgnoreInputs )
        else:
            arg.rop.render(frame_range=frameRange, res=imgRes, method=hou.renderMethod.FrameByFrame, ignore_inputs=rrIgnoreInputs)
        
    elif (arg.rop.isNetwork()):
        logMessage("Output node is a network node of type '"+str(arg.rop.type()) + "', searching for children ROP nodes to render...")
        rop_children= arg.rop.children()
        for child in rop_children:
            if (type(child)==hou.RopNode):
                logMessage("Rendering ROP node '"+str(child.name()) + "' of type '"+str(child.type().name())+"'")
                if (argValid(arg.verbose) and arg.verbose):
                    child.render(frame_range=frameRange, res=imgRes, verbose=True, output_progress=True, method=hou.renderMethod.FrameByFrame, ignore_inputs=rrIgnoreInputs)
                else:
                    child.render(frame_range=frameRange, res=imgRes, method=hou.renderMethod.FrameByFrame, ignore_inputs=rrIgnoreInputs)
    else:
        logMessage("Warning: Unknown node type '"+str(type(arg.rop))+"', trying to render anyway")
        if (argValid(arg.verbose) and arg.verbose):
            arg.rop.render(frame_range=frameRange, res=imgRes, verbose=True, output_progress=True, method=hou.renderMethod.FrameByFrame, ignore_inputs=rrIgnoreInputs)
        else:
            arg.rop.render(frame_range=frameRange, res=imgRes, method=hou.renderMethod.FrameByFrame, ignore_inputs=rrIgnoreInputs)
    nrofFrames = ((localFrEnd - localFrStart) / localFrStep) + 1
    nrofFrames = int (nrofFrames)
    afterFrame = datetime.datetime.now()
    afterFrame -= beforeFrame
    if (nrofFrames==1):
        logMessage("Frame Time : "+str(afterFrame)+"  h:m:s.ms.  Frame Rendered #" + str(localFrStart) )
    else:
        afterFrame /= nrofFrames
        logMessage("Frame {0} - {1}, {2} ({3} frames) done. Average frame time: {4}  h:m:s.ms".format(localFrStart, localFrEnd, localFrStep, nrofFrames, afterFrame))
    logMessage(" ")
    flushLog()


def renderFrames(FrStart,FrEnd,FrStep):
    global arg
    FrStart=int(FrStart)
    FrEnd=int(FrEnd)
    FrStep=int(FrStep)

    localAllFramesAtOnce = arg.allFramesAtOnce
    if (not localAllFramesAtOnce):
        #logMessage("not localAllFramesAtOnce   TRUE")
        #logMessage("arg.renderer is  "+ str(arg.renderer))
        if (arg.avFrameTime == 0):
            localAllFramesAtOnce = arg.renderer in ("redshift", "Octane", "opengl")
        elif (arg.avFrameTime < 60):
            localAllFramesAtOnce = True
        elif (arg.avFrameTime < 140):
            localAllFramesAtOnce = arg.renderer in ("redshift", "Octane", "opengl")

    try:
        imgRes = ()
        if (argValid(arg.width) and argValid(arg.height)):
            imgRes = (int(arg.width),int(arg.height))

        mainFileName = arg.FRefName
        mainFileName = mainFileName.replace("/$AOV", "")
        mainFileName = mainFileName.replace(".$AOV", "")
        localFrStep= FrStep
        
        if (arg.subFrames > 1 ):
            localFrStep= 1.0 / float(arg.subFrames)
            if (FrStep != 1): 
                #e.g. preview render
                localAllFramesAtOnce= False

        if localAllFramesAtOnce:
            localFrEnd= FrEnd 
            if (localFrStep < 1.0):
                localFrEnd= float(localFrEnd+1) - localFrStep
            logMessage("Rendering Frames #{0}-{1}, step {2} ...".format(FrStart, localFrEnd, localFrStep))

            renderFrames_sub(FrStart,localFrEnd,localFrStep,imgRes)

        else:
            for fr in range(FrStart,FrEnd+1,FrStep):
                if (not argValid(arg.SkipExisting) or not (arg.SkipExisting)):
                    kso_tcp.writeRenderPlaceholder_nr(mainFileName, fr, arg.FPadding, arg.FExt)
                localFrEnd= fr
                if (localFrStep < 1.0):
                    localFrEnd= float(localFrEnd + 1) - localFrStep
                if (arg.subFrames>1):
                    logMessage( "Rendering Frames #" + str(fr) + " - #" + str(localFrEnd) + ", " + str(arg.subFrames) + " subFrames ...")
                else:
                    logMessage( "Rendering Frame #" + str(fr) + " ...")
 
                renderFrames_sub(fr,localFrEnd,localFrStep,imgRes)

    except Exception as e:
        logMessageError(str(e), True)

    



def ksoRenderFrame(FrStart,FrEnd,FrStep ):
    renderFrames(FrStart,FrEnd,FrStep)
    flushLog()
    logMessage("rrKSO Frame(s) done #"+str(FrEnd)+" ")
    logMessage("                                                            ")
    logMessage("                                                            ")
    logMessage("                                                            ")
    flushLog()
    



def rrKSOStartServer():
    global arg
    try:
        logMessage("rrKSO startup...")
        if ((arg.KSOPort== None) or (len(str(arg.KSOPort))<=0)):
            arg.KSOPort=7774
        HOST, PORT = "localhost", int(arg.KSOPort)
        server = kso_tcp.rrKSOServer((HOST, PORT), kso_tcp.rrKSOTCPHandler)
        flushLog()
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
                logMessageError(e, True)
                server.continueLoop= False
                import traceback
                logMessageError(traceback.format_exc(), True)
            logMessage("                                                            ")
            logMessage("                                                            ")
            logMessage("rrKSO NextCommand ______________________________________________________________________________________________")
            logMessage("rrKSO NextCommand '"+ kso_tcp.rrKSONextCommand+"'")   
            logMessage("rrKSO NextCommand ______________________________________________________________________________________________")
            flushLog()
            if (len(kso_tcp.rrKSONextCommand)>0):
                if ((kso_tcp.rrKSONextCommand=="ksoQuit()") or (kso_tcp.rrKSONextCommand=="ksoQuit()\n")):
                    server.continueLoop=False
                    kso_tcp.rrKSONextCommand=""
                else:
                    exec (kso_tcp.rrKSONextCommand)
                    kso_tcp.rrKSONextCommand=""
        logMessage("rrKSO closed")
    except NameError as e:
        logMessage(str(e)+"\n")        
    except Exception as e:
        logMessageError(str(e), True)


def render_KSO():
    rrKSOStartServer()
        
def render_default():
    global arg
    renderFrames(arg.FrStart,arg.FrEnd,arg.FrStep)

def rrGetDirName(dir):
    #logMessage("************rrGetDirName***********************\n" + dir)
    PD= '/'
    if (len(dir)<3):
        return dir
    endedWithPD= False
    if (dir[len(dir)-1] == PD):
        dir = dir[:len(dir)-1]
        endedWithPD= True
    
    driveEnd = 0 #linux has root slash at pos 0: /
    if (dir[1] == PD): #UNC PATH has root slash at 1 and second "folder" is part of the "drive" \\fileserver\drive
        driveEnd = dir.find(PD, 2)
        driveEnd = dir.find(PD, driveEnd+1)
        if (driveEnd<0):
            dir+= PD
            return dir
    elif (dir[1] == ':'):  #windows drive E:/
        driveEnd = 2
    p = dir.rfind(PD)
    if (p >= driveEnd):
        dir = dir[:p]
    elif (p < 0): #filename only or drive only
        if not endedWithPD:
            return ""
    dir+= PD
    #logMessage("result: " + dir)
    return dir

def rrReplaceUpLevel(dir):
    dir= os.path.normpath(dir)
    dir= dir.replace('\\','/')
    return dir

def addFrameNumber_and_Log(outFileName):
    global arg
    if (arg.FSingleFile):
        outFileName= arg.FName + arg.FExt
    elif (arg.subFrames>1):
        outFileName= outFileName +"$FF" + arg.FExt
    else: 
        outFileName= outFileName +"$F"+str(arg.FPadding) + arg.FExt
    logMessageSET("output name to "+outFileName)
    return outFileName
    

def applyRendererOptions_default():
    global arg
    logMessage("Rendering with default renderer")
    if argValid(arg.threads) and not arg.rendererExportMode:
        try:
            arg.rop.parm('vm_usemaxthreads').set(0)
            arg.rop.parm('vm_threadcount').set(int(arg.threads))
        except (hou.LoadWarning, AttributeError) as e:
            logMessage("Error: Unable to set thread count")
            logMessage(e)
    if (argValid(arg.camera)):
        setROPValue("camera", "camera", arg.camera, True)
    if (argValid(arg.take)):
        setROPValue("take", "take", arg.take, True)
    outFileName=arg.FName
    if (argValid(arg.totalTiles) and (int(arg.totalTiles)>1)):
        arg.rop.parm('vm_tile_render').set(1)
        arg.rop.parm('vm_tile_count_y').set(1)
       
        logMessageSET("vm_tile_count_x "+str(arg.totalTiles))
        arg.rop.parm('vm_tile_count_x').set(int(arg.totalTiles))
        logMessageSET("vm_tile_index "+str(arg.tile))
        arg.rop.parm('vm_tile_index').set(int(arg.tile))
        if (outFileName.endswith('.')):
            outFileName=outFileName+'.'
    flushLog()
    outFileName= addFrameNumber_and_Log(outFileName)
    if (arg.rendererExportMode):
        arg.rop.parm('soho_outputmode').set(1)
        arg.rop.parm('soho_diskfile').set(outFileName)
        #debugOutputName = arg.rop.parm('soho_diskfile').eval()
        #logMessageSET("output name to "+debugOutputName+ "(evaluated)")        
        logMessage("Not touching image output; which is set to "+ str(arg.rop.parm('vm_picture').eval()))
    else:
        arg.rop.parm('soho_outputmode').set(0)
        orgDirName0= rrGetDirName( arg.rop.parm('vm_picture').eval() )
        arg.rop.parm('vm_picture').set(outFileName)
        newDirName0= rrGetDirName( arg.rop.parm('vm_picture').eval() )

        orgDirName0 = rrReplaceUpLevel(orgDirName0)
        newDirName0 = rrReplaceUpLevel(newDirName0)
        logMessage(" main output orgDirName was " + orgDirName0)
        logMessage(" main output newDirName is  " + newDirName0)
        orgDirName1= rrGetDirName(orgDirName0)
        orgDirName2= rrGetDirName(orgDirName1)
        orgDirName3= rrGetDirName(orgDirName2)
        newDirName1= rrGetDirName(newDirName0)
        newDirName2= rrGetDirName(newDirName1)
        newDirName3= rrGetDirName(newDirName2)

        try:
            layOutput = arg.rop.parm('vm_dcmfilename').unexpandedString()
            logMessage(layOutput + ": deep layer output was:    " + layOutput)
            layOutput = layOutput.replace("$F","09876543211")
            arg.rop.parm('vm_cryptolayeroutput' + layOutput).set(layOutput)
            layOutput = arg.rop.parm('vm_cryptolayeroutput' + layOutput).eval()
            layOutput = rrReplaceUpLevel(layOutput) 
            layOutput = layOutput.replace("09876543211", "$F")
            logMessage(layOutput + ": deep layer output resolved:  " + layOutput)
            
            layOutput = layOutput.replace(orgDirName0,newDirName0)
            layOutput = layOutput.replace(orgDirName1,newDirName1)
            layOutput = layOutput.replace(orgDirName2,newDirName2)
            layOutput = layOutput.replace(orgDirName3,newDirName3)
            arg.rop.parm('vm_dcmfilename').set(layOutput)
            logMessage(layOutput + ": deep layer output set to:       " + layOutput)
            flushLog()
            
        except:
            pass

        try:
            cryptolayerCount= arg.rop.parm('vm_cryptolayers').eval()
            if (cryptolayerCount>0 and orgDirName0!=None and orgDirName0!=newDirName0 ):
                logMessage(str(cryptolayerCount)+ " Cryptolayers. Changing to local render out... ")
                
                for l in range(0, cryptolayerCount):
                    hasDiffOutput = arg.rop.parm('vm_cryptolayeroutputenable'+str(l+1)).eval() == 1
                    if (hasDiffOutput):
                        layOutput = arg.rop.parm('vm_cryptolayeroutput'+str(l+1)).unexpandedString()
                        logMessage(str(l) + ": crypto layer output was:    " + layOutput)
                        layOutput = layOutput.replace("$F","09876543211")
                        arg.rop.parm('vm_cryptolayeroutput'+str(l+1)).set(layOutput)
                        layOutput = arg.rop.parm('vm_cryptolayeroutput'+str(l+1)).eval()
                        layOutput = rrReplaceUpLevel(layOutput) 
                        layOutput = layOutput.replace("09876543211", "$F")
                        logMessage(str(l) + ": crypto layer output resolved:  " + layOutput)
                        
                        layOutput = layOutput.replace(orgDirName0,newDirName0)
                        layOutput = layOutput.replace(orgDirName1,newDirName1)
                        layOutput = layOutput.replace(orgDirName2,newDirName2)
                        layOutput = layOutput.replace(orgDirName3,newDirName3)
                        arg.rop.parm('vm_cryptolayeroutput'+str(l+1)).set(layOutput)
                        logMessage(str(l) + ": crypto layer output set to:       " + layOutput)
                        flushLog()
        except:
            pass

def applyRendererOptions_createUSD():
    global arg
    logMessage("Exporting USD files")
    if (argValid(arg.camera)):
        setROPValue("camera", "camera", arg.camera, True)
    if (argValid(arg.take)):
        setROPValue("take", "take", arg.take, True)
    outFileName= addFrameNumber_and_Log(arg.FName)
    arg.rop.parm('lopoutput').set(outFileName)
    try:
        if (not arg.FSingleFile):
            arg.rop.parm('fileperframe').set(1)
        #else:     
            #arg.rop.parm('fileperframe').set(0)  required for file per frame, BUT OPTIONAL for single .usd files.
    except:
        pass
    
def applyRendererOptions_USD():
    global arg
    logMessage("Rendering USD/LOP")
    if (argValid(arg.camera)):
        setROPValue("camera", "camera", arg.camera, True)
    if (argValid(arg.take)):
        setROPValue("take", "take", arg.take, True)
    outFileName= addFrameNumber_and_Log(arg.FName)
    setFirst=True
    setSecond=True
    try:
        arg.rop.parm('outputimage').set(outFileName)
    except:
        setFirst=False
    try:
        arg.rop.parm('picture').set(outFileName)
    except:
        setSecond=False
    if (not setFirst and not setSecond):
        raise NameError("Error: Unable to set output filename!")

    
def applyRendererOptions_openGl():
    global arg
    logMessage("Rendering with openGL renderer")
    if (argValid(arg.camera)):
        setROPValue("camera", "camera", arg.camera, True)
    if (argValid(arg.take)):
        setROPValue("take", "take", arg.take, True)
    outFileName= addFrameNumber_and_Log(arg.FName)
    arg.rop.parm('picture').set(outFileName)

  
def applyRendererOptions_geometry():
    global arg
    logMessage("Rendering with geometry exporter")
    if (argValid(arg.take)):
        logMessageSET("ROP take to "+arg.take)
        try:
            arg.rop.parm('take').set(arg.take)
        except:
            logMessage("Error: Unable to change take in "+ arg.ropName +" !")
    outFileName= addFrameNumber_and_Log(arg.FName)
    setROPValue("Output", 'sopoutput' , outFileName, True)

def applyRendererOptions_alembic(singleFile):
    global arg
    logMessage("Rendering with alembic exporter")
    if (argValid(arg.take)):
        logMessageSET("ROP take to "+arg.take)
        try:
            arg.rop.parm('take').set(arg.take)
        except:
            logMessage("Error: Unable to change take in "+ arg.ropName +" !")
    outFileName=arg.FName
    if singleFile:
        arg.FSingleFile= True
        arg.allFramesAtOnce= True
        outFileName= outFileName
        logMessageSET("output name to "+outFileName)
        arg.rop.parm('render_full_range').set(1)
    else:
        outFileName= addFrameNumber_and_Log(outFileName)
        arg.rop.parm('render_full_range').set(0)
    arg.rop.parm('filename').set(outFileName)
    
    
def applyRendererOptions_Arnold():
    global arg
    logMessage("Rendering with Arnold")
    if (argValid(arg.camera)):
        setROPValue("camera", "camera", arg.camera, True)
    if (argValid(arg.take)):
        setROPValue("take", "take", arg.take, True)
    if (arg.renderDemo):
        arg.rop.parm('ar_abort_on_license_fail').set(0)
        arg.rop.parm('ar_skip_license_check').set(1)
    else:
        arg.rop.parm('ar_abort_on_license_fail').set(1)
        arg.rop.parm('ar_skip_license_check').set(0)
    
    outFileName= addFrameNumber_and_Log(arg.FName)
        
    if (arg.rendererExportMode):
        setROPValue("Archive Export", "ar_ass_export_enable", 1)
        setROPValue("Archive Filename", "ar_ass_file", outFileName)
        logMessage("Not touching image output; which is set to "+ str(arg.rop.parm('ar_picture').eval()))
    else:
        setROPValue("Archive Export", "ar_ass_export_enable", 0)
        setROPValue("Output Filename", 'ar_picture', outFileName)
    
    
    
def applyRendererOptions_PRman():
    try:
        import about
        rfh_path = os.environ['RFHTREE']
        version = about._rfhReadVersion(os.path.join(rfh_path, about._rfhGetVersion(), 'etc', 'buildid.txt'))
        logMessage("Rendering with "+str(version["versionStr"]))
    except:
        return False
        logMessage("Rendering with PRman (unidentified version)")

    global arg
    if (argValid(arg.camera)):
        setROPValue("camera", "camera", arg.camera, True)
    if (argValid(arg.take)):
        setROPValue("take", "take", arg.take, True)
    try:
        device=arg.rop.parm('ri_device_0').eval()
        if (device=="it"):
            logMessage("WARNING: ROP device is set to frameviewer 'it'. This does not render any files! Changing to 'openexr'...")
            arg.rop.parm('ri_device_0').set("openexr")
    except:
        pass
            
    outFileName= addFrameNumber_and_Log(arg.FName)
    if (arg.rendererExportMode):
        setROPValue("Archive Export", "rib_outputmode", 1, False)
        setROPValue("Archive Export", "diskfile", 1, False)
        setROPValue("Archive Filename", "soho_diskfile", outFileName)
        logMessage("Info: Not touching image output")
    else:
        setROPValue("Archive Export", "rib_outputmode", 0, False) #Houdini ROP
        setROPValue("Archive Export", "diskfile", 0, False) #prman v23 ROP
        setROPValue("Archive Filename", "ri_display", outFileName, False) #Houdini ROP
        setROPValue("Archive Filename", "ri_display_0", outFileName, False) #prman v23 ROP


def applyRendererOptions_VRay():
    global arg
    logMessage("Rendering with VRay")
    if (argValid(arg.camera)):
        setROPValue("camera", "camera", arg.camera, True)
    if (argValid(arg.take)):
        setROPValue("take", "take", arg.take, True)
    if (arg.rendererExportMode):
        arg.rop.parm('render_export_mode').set("2")
        archiveName=""
        if (arg.FSingleFile):
            archiveName= arg.FName + arg.FExt
            logMessageSET("archive output name to "+archiveName)
        else:
            archiveName= addFrameNumber_and_Log(arg.FName)
        arg.rop.parm('render_export_filepath').set(archiveName)
        logMessage("Not touching image output; which is set to "+ str(arg.rop.parm('SettingsOutput_img_file_path').eval()))
    else:
        arg.rop.parm('render_export_mode').set("0")
        outFileName= addFrameNumber_and_Log(arg.FName)
        arg.rop.parm('SettingsOutput_img_file_path').set( outFileName)
    
    
def applyRendererOptions_Redshift():
    global arg
    logMessage("Rendering with Redshift")
    hou.hscript("Redshift_disableRaiseExceptionOnRenderError")
    arg.rop.parm('RS_outputEnable').set(1)
    arg.rop.parm('RS_renderToMPlay').set(0)
    if (argValid(arg.camera)):
        setROPValue("camera", "camera", arg.camera, False) #deprecated
    if (argValid(arg.camera)):
        setROPValue("camera", "RS_renderCamera", arg.camera)
    if (argValid(arg.take)):
        setROPValue("take", "take", arg.take)
    if (argValid(arg.gpuBits)):
        logMessageSET("GPUs to be used: "+arg.gpuBits)
        hou.hscript("Redshift_setGPU -s "+arg.gpuBits) 
    if (arg.renderDemo):
        setROPValue('AbortOnLicenseFail', 'AbortOnLicenseFail', 0)
    else:
        setROPValue('AbortOnLicenseFail', 'AbortOnLicenseFail', 1)
        
    outFileName= addFrameNumber_and_Log(arg.FName)
    if (arg.rendererExportMode):
        if (argValid(arg.SkipExisting)):
            if (arg.SkipExisting):
                setROPValue('Skip Existing Frames', 'RS_archive_skipFiles', 1)
            else:
                setROPValue('Skip Existing Frames', 'RS_archive_skipFiles', 0)
        else:
            setROPValue('Skip Existing Frames', 'RS_archive_skipFiles', 0)
        setROPValue('Enable Archive', 'RS_archive_enable', 1)
        arg.rop.parm('RS_archive_file').set(outFileName)
        logMessage("Not touching image output; which is set to "+ str(arg.rop.parm('RS_outputFileNamePrefix').eval()))
    else:
        if (argValid(arg.SkipExisting)):
            if (arg.SkipExisting):
                setROPValue('Skip Existing Frames', 'RS_outputSkipRendered', 1)
            else:
                setROPValue('Skip Existing Frames', 'RS_outputSkipRendered', 0)
        else:
            setROPValue('Skip Existing Frames', 'RS_outputSkipRendered', 0)
        setROPValue('Enable Archive', 'RS_archive_enable', 0)
        setROPValue("Output Filename", 'RS_outputFileNamePrefix',outFileName)
        setROPValue("Output File Format", 'RS_outputFileFormat',arg.FExt)

def list_parents(targetnode):
    nparents = len(targetnode.path().split("/"))-2
    parentlist = []
    for n in range(nparents,0,-1):
        parentX = targetnode
        for o in range(n):
            parentX = parentX.parent()
        parentlist.append(parentX)
    return parentlist

def unlock_assets(ropNode):
    logMessage("Unlocking parent assets of ROP node.")
    try:
        parentlist = list_parents(ropNode)
        for parent in parentlist:
            parent.allowEditingOfContents()
    except: 
        logMessage("Error: Unable unlock parent assets of ROP node!")


#main function:
try:
    logMessage("Script %rrVersion%" )
    logMessage("Python version: "+str(sys.version))
    flushLog()
    timeStart=datetime.datetime.now()
    global arg
    arg=argParser()
    arg.readArguments()
    
    if (argValid(arg.PyModPath)):
        import sys
        logMessage("Append python search path with '" +arg.PyModPath+"'" )
        sys.path.append(arg.PyModPath)
    global kso_tcp
    import kso_tcp
    kso_tcp.USE_LOGGER= False
    kso_tcp.USE_DEFAULT_PRINT= True        
    kso_tcp.rrKSO_logger_init()
    if (not argValid(arg.rendererExportMode)):
        arg.rendererExportMode=False
    if (not argValid(arg.FPadding)):
        arg.FPadding=1
    if (not argValid(arg.FRefName)):
        arg.FRefName=arg.FName
    if argValid(arg.subFrames):
        arg.subFrames= int(arg.subFrames)
    else:
        arg.subFrames= 1
    if (arg.subFrames < 1):
        arg.subFrames= 1
    if (not argValid(arg.FSingleFile)):
        arg.FSingleFile= False
    if arg.FSingleFile:
        arg.allFramesAtOnce= True       
        
    logMessage("Allowing to overwrite $JOB by the rrJobs rrEnv." )   
    hou.allowEnvironmentToOverwriteVariable("JOB",True)

    if (not argValid(arg.ignoreLoadIssues)):
        arg.ignoreLoadIssues = False


    if (arg.ignoreLoadIssues):
        logMessage("loading scene file, ignoring load warnings..." )
    else:
        logMessage("loading scene file..." )
        
    flushLog()
    try:
        hou.hipFile.load( arg.sceneFile, True, arg.ignoreLoadIssues )
    except hou.LoadWarning as e:
        logMessageError( "Error loading scene: Load Warning\n"+str(e), (not arg.ignoreLoadIssues))
    except hou.OperationFailed as e:
        logMessageError( "Error loading scene: 'hou.hipFile.load' operation failed \n"+str(e), (not arg.ignoreLoadIssues))
    except Exception as e:
        logMessageError( "Error loading scene: \n"+str(e), True)
        
    if (argValid(arg.take)):
        switchTake("Main") #we have to switch to the main take to be able to change render settings
        arg.FName= arg.FName.replace("<Channel>",arg.take)
        arg.FName= arg.FName.replace("<AOV>",arg.take)
        arg.FRefName= arg.FRefName.replace("<Channel>",arg.take)
        arg.FRefName= arg.FRefName.replace("<AOV>",arg.take)
    else:
        arg.FName= arg.FName.replace("<Channel>","")
        arg.FName= arg.FName.replace("<AOV>","")
        arg.FRefName= arg.FRefName.replace("<Channel>","")
        arg.FRefName= arg.FRefName.replace("<AOV>","")
        
    arg.FName= arg.FName.replace("<Stereo>","")
    arg.FRefName= arg.FRefName.replace("<Stereo>","")

        
    
    arg.rop = hou.node( arg.ropName )
    if (argValid(arg.unlockAssets) and arg.unlockAssets):
        unlock_assets(arg.rop)
    
    if arg.rop is None:
        logMessageError("Node \"" + arg.ropName + "\" does not exist" , True)
    else:
        logMessage("Rendering rop:   name:"+arg.rop.name()+"   node type:"+arg.rop.type().name())
                
    logMessage("renderer "+str(arg.renderer))
    if (arg.renderer=="arnold"):
        applyRendererOptions_Arnold()
    elif (arg.renderer=="redshift"):
        applyRendererOptions_Redshift()
    elif (arg.renderer=="usd"):
        applyRendererOptions_USD()
    elif (arg.renderer=="createUSD"):
        applyRendererOptions_createUSD()
    elif (arg.renderer=="vray"):
        applyRendererOptions_VRay()
    elif (arg.renderer=="prman"):
        applyRendererOptions_PRman()
    elif (arg.renderer=="opengl"):
        applyRendererOptions_openGl()
    elif (arg.renderer=="geometry"):
        applyRendererOptions_geometry()
    elif (arg.renderer=="alembic"):
        applyRendererOptions_alembic(arg.FSingleFile)
    elif (arg.renderer=="alembic-singlefile"):
        applyRendererOptions_alembic(arg.FSingleFile)
    else:
        arg.renderer= "mantra"
        applyRendererOptions_default()
        
    if (argValid(arg.take)):
        switchTake(arg.take)
        
        
    if (argValid(arg.wedge)):
        switchWedge(arg)

    if (not argValid(arg.allFramesAtOnce)):
        arg.allFramesAtOnce= False
    if (not argValid(arg.avFrameTime)):
        arg.avFrameTime= 0
    else:
        arg.avFrameTime= int(arg.avFrameTime)

    timeEnd=datetime.datetime.now()
    timeEnd=timeEnd - timeStart;
    logMessage("Scene load time: "+str(timeEnd)+"  h:m:s.ms")
    logMessage("Scene init done, starting to render... ")
    flushLog()

    if (argValid(arg.KSOMode) and arg.KSOMode):
        render_KSO()
    else:
        render_default()

except NameError as e:
    logMessage(str(e)+"\n")      
except Exception as e:
    logMessageError( str(e)+"\n", True)
