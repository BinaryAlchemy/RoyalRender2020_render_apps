# Render script for 3dsmax
#  %rrVersion%
#  Copyright (c)  Holger Schoenberger - Binary Alchemy

import datetime
import time
import sys
import logging
import MaxPlus
import os

logFile_available=False
changeElementFilename=True


def flushLog():
    pass


def logMessageGen(lvl, msg, tries):
    try:
        if (len(lvl)==0):
            if (logFile_available):
                logger = logging.getLogger()
                logging.info(datetime.datetime.now().strftime("' %H:%M.%S") + " rrMax      : " + str(msg))
                logger.handlers[0].close()
            #print(datetime.datetime.now().strftime("' %H:%M.%S") + " rrMax      : " + str(msg))
        else:
            if (logFile_available):
                logger = logging.getLogger()
                logging.info(datetime.datetime.now().strftime("' %H:%M.%S") + " rrMax - " + str(lvl) + ": " + str(msg))
                logger.handlers[0].close()
            #print(datetime.datetime.now().strftime("' %H:%M.%S") + " rrMax - " + str(lvl) + ": " + str(msg))
    except IOError:
        if (tries<3):
            time.sleep(0.35)
            logMessageGen(lvl, msg, tries+1)
        
        

def logMessage(msg):
    logMessageGen("",msg,1)

def logMessageSET(msg):
    logMessageGen("SET",msg,1)

def logMessageDebug(msg):
    if (True):
        logMessageGen("DBG", msg,1)

def logMessageError(msg):
    logMessageGen("ERR", str(msg)+"\n\n",1)
    logMessageGen("ERR", "Error reported, aborting render script",1)
    flushLog();
    sys.exit();
    #raise NameError("\nError reported, aborting render script\n")    


def argValid(argValue):
    return ((argValue!= None) and (len(str(argValue))>0))
    

class argParser:
    def getParam(self,argFindName):
        import ConfigParser
        argFindName=argFindName.lower()
        try:
            argValue = self.config.get('Max', argFindName)
        except ConfigParser.NoOptionError:
            return ""
        if (argValue== None):
            return ""
        argValue=argValue.strip()
        if (argValue.startswith("*")):
            return ""
        if (argValue.lower()=="true"):
            argValue=True
        elif (argValue.lower()=="false"):
            argValue=False
        logMessage("Flag  "+argFindName.ljust(15)+": '"+str(argValue)+"'");
        return argValue
        
        
    def readArguments(self):
        import ConfigParser
        self.config = ConfigParser.RawConfigParser()
        configFilename=os.environ['TEMP']+"\\kso_3dsmax.ini"
        logMessage("configFilename: "+configFilename);
        self.config.read(configFilename )
        self.SName=self.getParam("Scene")
        self.RendererMode=self.getParam("RendererMode")
        self.Renderer=self.getParam("Renderer")
        self.KSOMode=self.getParam("KSOMode")
        self.KSOPort=self.getParam("KSOPort")
        self.RPMPass=self.getParam("RPMPass")
        self.StateSet=self.getParam("StateSet")
        self.FName=self.getParam("FName")
        self.FNameVar=self.getParam("FNameVar")
        self.FExt=self.getParam("FExt")
        self.FPadding=self.getParam("FPadding")
        self.FNameChannelAdd=self.getParam("FNameChannelAdd")
        self.FrStart=self.getParam("SeqStart")
        self.FrEnd=self.getParam("SeqEnd")
        self.FrStep=self.getParam("SeqStep")
        self.FrOffset=self.getParam("SeqOffset")
        self.Camera=self.getParam("Camera")
        self.ResX=self.getParam("ResX")
        self.ResY=self.getParam("ResY")
        self.IgnoreError=self.getParam("IgnoreErr")
        self.RegionX1=self.getParam("RegionX1")
        self.RegionX2=self.getParam("RegionX2")
        self.RegionY1=self.getParam("RegionY1")
        self.RegionY2=self.getParam("RegionY2")
        self.RenderThreads=self.getParam("RenderThreads")
        self.PyModPath=self.getParam("PyModPath")
        self.logFile=self.getParam("LogFile")
        self.ElementsFolder=self.getParam("ElementsFolder")
        self.VRayMemLimit=self.getParam("VRayMemLimit")
        self.VRayMemLimitPercent=self.getParam("VRayMemLimitPercent")
        self.ClientTotalMemory=self.getParam("ClientTotalMemory")
        self.GBuffer=self.getParam("GBuffer")
                
        

   
    
##############################################################################
#MAIN "FUNCTION":
##############################################################################
timeStart=datetime.datetime.now()
logMessageDebug('----------------------startup-----------------')
arg=argParser()
arg.readArguments()
if (not argValid(arg.logFile)):
    arg.logFile= os.environ['TEMP']+"\\rrMaxRender.log"
logging.basicConfig(filename=arg.logFile,level=logging.INFO,format='%(message)s')
logger = logging.getLogger()
logger.handlers[0].flush()
logger.handlers[0].close()
logFile_available=True
logMessage("###########################################################################")
flushLog()

if (argValid(arg.PyModPath)):
    import sys
    sys.path.append(arg.PyModPath)


logMessage( "Loading Scene '" + str(arg.SName)+"'...")
fm = MaxPlus.FileManager
if not fm.Open(str(arg.SName), True, True, True):
    logMessageError("Unable to open scene file")


if (argValid(arg.StateSet)):
    logMessageSET("pass to '" + str(arg.StateSet) +"'")
    MaxPlus.Core.EvalMAXScript("sceneStateMgr.restoreAllParts \""+arg.StateSet+"\"")
#else:
    #arg.StateSet= Check if an state set is active
    #logMessage("Using current pass '" + arg.StateSet +"'")
        
if (argValid(arg.RPMPass)):
    logMessageSET("RPM pass to '" + str(arg.RPMPass) +"'")
    MaxPlus.Core.EvalMAXScript("RPass_nr =0;  for i= 1 to RPMdata.GetPassCount() do  (  if ("+arg.RPMPass+"==RPMdata.GetPassName(i))    then RPass_nr=i  );  if RPass_nr>0    then RPMData.RMRestValues RPass_nr    else quitMax #noPrompt")
   
    


timeEnd=datetime.datetime.now()
timeEnd=timeEnd - timeStart;
logMessage("Scene load time: "+str(timeEnd)+"  h:m:s.ms")
logMessage("Scene init done, starting to simulate... ")
flushLog()

cmdLine= ( 
	"--If there are selected simulators, use only thosen\n"
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
   

MaxPlus.Core.EvalMAXScript(cmdLine)
logMessage("Finished simulating... ")
flushLog()
