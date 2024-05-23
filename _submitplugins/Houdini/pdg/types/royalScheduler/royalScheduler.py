# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy

# python script to reload this python module in Houdini after a script change:
# import pdg; pdg.TypeRegistry.types().registeredType(pdg.registeredType.Scheduler, "royalscheduler").reload()


LOG_FUNCTION_ENTER_EXIT= False


import json
import os
import socket
import sys
import traceback
import logging
import tempfile
import os
from datetime import datetime

import hou
import pdg
from pdg.utils import expand_vars
from pdg.job.callbackserver import CallbackServerMixin
from pdg.scheduler import PyScheduler
from pdg.job.eventdispatch import EventDispatchMixin
from pdg.utils.mq import MQUtility, MQInfo, MQState, MQUsage, MQSchedulerMixin
from pdgutils import PDGNetMQRelay, mqGetError, mqCreateMessage, PDGNetMessageType
#from pdg.scheduler import submitGraphAsJob
from pdg.utils import expand_vars



sharedPath=os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../shared"))
sys.path.append(sharedPath)
import royalCommands as rrCmds
try:
    logger = rrCmds.getLogger()
except:
    print("#######################################")
    print("Error: Unable to get rrCmds.getLogger()")
    print(os.path.abspath(rrCmds.__file__))
    print("#######################################")
import royalDefs as rrDefs


def houdiniMajorVersion_Int():
    version= hou.applicationVersion()
    if (len(version)>0):
        version=version[0]
    else:
        version=18
        
    logger.debug("Houdini version is {}".format(version))
    return version


_jobTypeNone=0
_jobTypeHoudini=1
_jobTypePython=2

_typePython_SplitJobs = ["tracker.py", "placeholder"]
_typePython_IsServerJob = ["tracker.py", "placeholder2"]

class houdiniTask2rrJobMapper_node():
    
    def __init__(self, work_item, workJobType, scheduler):
        self.rrJobID= 0
        self.rrJobIDStr= "---"
        self.changed= False
        self.newFramesActive= False
        self.everFramesActive= False
        self.hNodeName= ""
        self.topNodeName= ""
        self.hjobType= _jobTypeNone
        self.hjobTypeDetailed= ""
        self.hjobPythonSingle = False
        self.hjobIsServer = False
        self.activeFrames= []
        self.minFrame= -1
        self.maxFrame= 0
        self.minFrameChanged= False
        self.maxFrameChanged= False
        self.wasSubmitted = False
        self.envListVar = [] 
        self.envListValue = [] 
        self.customListVar = [] 
        self.customListValue = [] 
        self.doneList=[]
        self.renderingList=[]
        
        
        
        self.hNodeName= work_item.node.name
        self.hjobType= workJobType
        self.hjobTypeDetailed= self.getDetailedJobType(work_item)
        if (workJobType==_jobTypePython):
            for cmd in _typePython_SplitJobs:
                self.hjobPythonSingle= self.hjobPythonSingle or (cmd in work_item.command)
            for cmd in _typePython_IsServerJob:
                self.hjobIsServer= self.hjobIsServer or (cmd in work_item.command)
        self.addEnv("PDG_ITEM_ID", "<FN>");
        itemName= str(work_item.name)
        itemName= itemName[: len(itemName) - len(str(work_item.id)) ] 
        itemName= itemName + "<PDG_ITEM_ID>"
        self.addEnv("PDG_ITEM_NAME", itemName);
        self.addEnv("PDG_RESULT_SERVER", scheduler.workItemResultServerAddr() );
        self.addEnv("[BSlashConvert] PDG_SHARED_TEMP", scheduler.tempDir(False));
        self.addEnv("[BSlashConvert] PDG_TEMP", scheduler.tempDir(False) );
        self.addEnv("[BSlashConvert] PDG_SCRIPTDIR", scheduler.scriptDir(False));
        self.addEnv("[BSlashConvert] PDG_DIR", scheduler.workingDir(False));
        self.baseDir = scheduler.workingDir(False)

        self.addEnv("PDG_ITEM_LABEL", itemName);
        #self.addEnv("PDG_ITEM_ID", str(work_item.id));
        #self.addEnv("PDG_INDEX", str(work_item.index));
        #self.addEnv("PDG_INDEX4", '{:04d}'.format(work_item.index));
        #self.addEnv("PDG_JOBID", "1");
        #self.addEnv("PDG_JOBID_VAR", 'PDG_JOBID');

        self.cmdFlags = work_item.command
        self.cmdFlags= self.cmdFlags.replace("__PDG_PYTHON__", "")
        self.cmdFlags= self.cmdFlags.replace("__PDG_HYTHON__", "")
        self.cmdFlags= self.cmdFlags.replace("\"\"", "")
        self.cmdFlags= self.cmdFlags.replace("__PDG_SCRIPTDIR__", "<OSEnv <PD/PDG_SCRIPTDIR>>")
        self.cmdFlags= self.cmdFlags.strip()
        #self.addEnv("RR_PDG_COMMAND", self.cmdFlags);
        self.addCustomVar("CommandLine", self.cmdFlags)

        pythonVer= str(sys.version_info.major) + "." +  str(sys.version_info.minor)
        self.addCustomVar("CustomHPyVerP", pythonVer)
        pythonVer= str(sys.version_info.major) + str(sys.version_info.minor)
        self.addCustomVar("CustomHPyVer", pythonVer)
        
        
        logger.debug("Create Task2rrJobMapper_node: {}: type:{} {} PythonSingle:{}".format(self.hNodeName, self.hjobType, self.hjobTypeDetailed, self.hjobPythonSingle) )
        
    def getDetailedJobType(self, work_item):
        topnode = work_item.node.topNode()
        toptype = topnode.type().name()
        if toptype == 'ropfetch':
            roppath = topnode.parm('roppath')
            if (roppath != None):
                ropnode = hou.node(roppath.eval())
                if ropnode:
                    return ropnode.type().name()
        return toptype
        
    def addEnv(self, var, value):
        self.envListVar.append(var)
        self.envListValue.append(value)
        logger.debug("Adding env var {} {} = {} {}".format(str(var), type(var), str(value), type(value) ))
        
    def addCustomVar(self, var, value):
        self.customListVar.append(var)
        self.customListValue.append(value)
        
    def addID(self, work_item):
        if (self.maxFrame < work_item.id):
            self.changed= True
            self.maxFrame= work_item.id
            self.maxFrameChanged= True
        if ((self.minFrame==-1) or self.minFrame > work_item.id):
            self.changed= True
            self.minFrame= work_item.id
            self.minFrameChanged= True
        return True
        
    def activateID(self, work_item):
        self.activeFrames.append(work_item.id)
        self.newFramesActive= True
        self.everFramesActive= True
        self.addID(work_item)# In case something has changed. But it makes no difference as the activeFrames is the only important thing from now on
        #logger.debug("activateID: Added new frame {} {} -{}:  {}".format(self.rrJobIDStr, self.hNodeName, self.hjobType, work_item.id))
        return True
    

class houdiniTask2rrJobMapper():

    #This class is used to find the Houdini task in RR
    #Each task is a frame in a job with a layer named like the node
    def __init__(self):
        self.clear()
        self.newJobAdded= False
        
        
    def clear(self):
        self.nodes= []
        rrCmds.restartJobID()
        self.last_sendActivateToRR= 0
        self.last_getFrameStatusFromRR= 0
        self.jobPassword=""
        
    
    def hasJobs(self):
        return (len(self.nodes)>0)
        
    def getWorkItemType(self, work_item):
        if ("__PDG_HYTHON__" in work_item.command):
            return _jobTypeHoudini
        if ("__PDG_PYTHON__" in work_item.command):
            return _jobTypePython
        return _jobTypeNone
        
    def addWork(self, work_item, scheduler):
        workJobType=  self.getWorkItemType(work_item)
        foundIt= -1;
        for i in range(len(self.nodes)):
            if ((self.nodes[i].hNodeName == work_item.node.name) and (self.nodes[i].hjobType == workJobType)
                    and (not self.nodes[i].hjobPythonSingle or (self.nodes[i].minFrame== work_item.id  ) )):
                foundIt=i
                
        if (foundIt == -1):
            newNode= houdiniTask2rrJobMapper_node(work_item, workJobType, scheduler)
            self.nodes.append(newNode)
            foundIt= len(self.nodes)-1
            self.newJobAdded=True
            
        return self.nodes[foundIt].addID(work_item)
        
    def activateWork(self, work_item, scheduler):
        workJobType=  self.getWorkItemType(work_item)
        foundIt= -1;
        for i in range(len(self.nodes)):
            if ((self.nodes[i].hNodeName == work_item.node.name) and (self.nodes[i].hjobType == workJobType)
                    and (not self.nodes[i].hjobPythonSingle or (self.nodes[i].minFrame== work_item.id  ) )):
                foundIt=i
                
        if (foundIt == -1):
            newNode= houdiniTask2rrJobMapper_node(work_item, workJobType, scheduler)
            self.nodes.append(newNode)
            foundIt= len(self.nodes)-1
            self.newJobAdded=True
            #logger.debug("activateWork: job {}: type:{} ID: {}".format(self.nodes[foundIt].hNodeName, self.nodes[foundIt].hjobType, work_item.id))
            
        return self.nodes[foundIt].activateID(work_item)
        
    def printInfo(self):
        logger.info("---------------")
        logger.info("houdiniTask2rrJobMapper: nodeCount {}".format(len(self.nodes)))
        for i in range(len(self.nodes)):
            logger.info("{}: type:{} {} minFrame:{}  maxFrame:{} frameAddCount:{} ".format(self.nodes[i].hNodeName, self.nodes[i].hjobType, self.nodes[i].hjobTypeDetailed,  self.nodes[i].minFrame, self.nodes[i].maxFrame, len(self.nodes[i].activeFrames)   ) )
        logger.info("---------------")
        
    def sortByIndex(self):
        #not required, but it is nice to have the jobs in rrControl in the right order
        #good old bubblesort! :-)
        for i in range(len(self.nodes)-1, 1, -1):
            for j in range(0, i):
                if (self.nodes[j].minFrame < self.nodes[j+1].minFrame):
                    self.nodes[j+1], self.nodes[j] = self.nodes[j], self.nodes[j+1]
        
        
    def submitJobs(self, scheduler):
        if (not self.newJobAdded):
            return
        if self.jobPassword=="":
            self.jobPassword= rrCmds.getRandomPW() #required in case job commands are blocked for anonymous users
        rrCmds.setJobCommandPassword(self.jobPassword) #used for all job commands from now on

        newJobListIDs= []
        rrCmds.clearSubmissionList()
        renderApp= rrCmds.createRenderApp()
        renderApp.name="Houdini"
        renderApp.setVersionBoth(hou.applicationVersionString())
        renderApp.rendererName="PDG"  
        self.newJobAdded= False
        
        for i in range(len(self.nodes)):
            if (not self.nodes[i].changed):
                continue
                
            if (self.nodes[i].rrJobID == 0):
                newJobListIDs.append(i)
                newJob= rrCmds.createJob(hou.hipFile.path(), rrDefs.plugin_version_str)
                newJob.setCommandPassword(self.jobPassword)
                newJob.layer= self.nodes[i].hNodeName
                if self.nodes[i].hjobIsServer:
                    renderApp.rendererName="pyServer"  
                    newJob.layer="PDG Server"
                    newJob.customDataAppend_Str("rrSubmitterParameter", ' "Priority=1~80" ' )
                elif (self.nodes[i].hjobType==_jobTypePython):
                    renderApp.rendererName="PDGpy"  
                else:
                    renderApp.rendererName="PDG"  
                
                newJob.renderApp= renderApp
                newJob.imageDir= self.nodes[i].baseDir
                #newJob.imageFileName= "no_check.file"
                newJob.seqStart=  self.nodes[i].minFrame
                newJob.seqEnd=  self.nodes[i].maxFrame
                newJob.seqFrameSet= rrCmds.frameSetBinaryLock_name()
                
                #logger.debug("Difference env var/value\n{}\n{}".format(self.nodes[i].envListVar, self.nodes[i].envListValue ))
                if (len(self.nodes[i].envListVar)!= len(self.nodes[i].envListValue)):
                    logger.error("Difference env var/value\n{}\n{}".format(self.nodes[i].envListVar, self.nodes[i].envListValue ))
                
                envList= ""
                for iv in range(len(self.nodes[i].envListVar)):
                    envList= envList + self.nodes[i].envListVar[iv] + "=" + self.nodes[i].envListValue[iv] + "~~~"
                envList= envList+  scheduler.jobEnvList
                newJob.customDataAppend_Str("rrEnvList", envList )
                logger.debug("Add Job:  envList  {} ".format(envList))
                for iv in range(len(scheduler.jobVarName)):
                    newJob.customDataAppend_Str(scheduler.jobVarName[iv], scheduler.jobVarValue[iv] )                    
                for iv in range(len(self.nodes[i].customListVar)):
                    newJob.customDataAppend_Str(self.nodes[i].customListVar[iv], self.nodes[i].customListValue[iv] )
                newJob.customDataAppend_Str("rrSubmitterParameter", scheduler.jobSettings )
                logger.debug("Add Job:  scheduler.jobSettings  {} ".format(scheduler.jobSettings))
                
                if "rrJobProject" in os.environ:
                     newJob.customDataAppend_Str("rrSubmitterParameter", ' "CompanyProjectName=0~' + os.environ["rrJobProject" ] +  '" ' )
                if "rrJobUser" in os.environ:
                     newJob.customDataAppend_Str("rrSubmitterParameter", ' "UserName=0~' + os.environ["rrJobUser" ] +  '" ' )
                if "rrJobCustomSequence" in os.environ:
                     newJob.customDataAppend_Str("rrSubmitterParameter", ' "CustomSeQName=0~' + os.environ["rrJobCustomSequence" ] +  '" ' )
                if "rrJobCustomShot" in os.environ:
                     newJob.customDataAppend_Str("rrSubmitterParameter", ' "CustomSHotName=0~' + os.environ["rrJobCustomShot" ] +  '" ' )
                if "rrJobCustomVersion" in os.environ:
                     newJob.customDataAppend_Str("rrSubmitterParameter", ' "CustomVersionName=0~' + os.environ["rrJobCustomVersion" ] +  '" ' )
                
                    
                #logger.debug("Add Job: {}   {} start:{} end:{}\n{}".format( newJob.renderApp.rendererName,  newJob.layer, newJob.seqStart,  newJob.seqEnd, envList))
                #logger.debug("Add Job: {}  {}   {} start:{} end:{}".format(newJob.sceneName , newJob.renderApp.rendererName,  newJob.layer, newJob.seqStart,  newJob.seqEnd))
                logger.debug("Add Job:  {}   {} start:{} end:{}".format(newJob.renderApp.rendererName,  newJob.layer, newJob.seqStart,  newJob.seqEnd))
                rrCmds.addJob(newJob)
                
        if (len(newJobListIDs)>0):
            if (scheduler.exportXML):
                xmlFilename= rrCmds.getXmlTempFile("rrSubmitHoudini")
                if rrCmds.exportXML(xmlFilename):
                    logger.info("Exported as xml file "+xmlFilename)
                    for i in range(len(self.nodes)):
                        self.nodes[i].changed= False 
                else:
                    logger.error("Unable to export as xml file "+xmlFilename)
            else:
                if (not rrCmds.submitJobList()):
                    logger.error("Unable to submit jobs! {}".format(rrCmds.getErrorString()))
                    return False
                else:
                    
                    jobIDList=""
                    sendIndex=-1
                    for i in range(len(self.nodes)):
                        if (not self.nodes[i].changed):
                            continue
                        sendIndex= sendIndex + 1
                        if (sendIndex > rrCmds.jobsSendCount()-1):
                            sendIndex = sendIndex - 1
                            logger.error("More jobs than the number of jobs submitter???")
                        self.nodes[i].rrJobID= rrCmds.jobsSendID(sendIndex)
                        self.nodes[i].rrJobIDStr= rrCmds.jobsID2Str(self.nodes[i].rrJobID)
                        jobIDList= jobIDList + self.nodes[i].rrJobIDStr + ", "
                        self.nodes[i].changed= False 
                    logger.info("Submited {} jobs! {}".format(len(newJobListIDs),jobIDList ))
            rrCmds.clearSubmissionList()
        else:
            logger.debug("No jobs to submit!")
            
        return True
        
    def sendActivateToRR_waitTimeOver(self, delay):                
        timeOver= False
        if (self.last_sendActivateToRR==0):
            timeOver= True
        else:
            now= datetime.now() 
            difference = (now - self.last_sendActivateToRR)
            diff_seconds = difference.total_seconds()
            if (diff_seconds > delay):
                timeOver= True
        if timeOver:
            self.last_sendActivateToRR= datetime.now() 
        return timeOver
            
    def getFrameStatusFromRR_waitTimeOver(self, delay):                
        timeOver= False
        if (self.last_getFrameStatusFromRR==0):
            timeOver= True
        else:
            now= datetime.now() 
            difference = (now - self.last_getFrameStatusFromRR)
            diff_seconds = difference.total_seconds()
            if (diff_seconds > delay):
                timeOver= True
        if timeOver:
            self.last_getFrameStatusFromRR= datetime.now() 
        return timeOver
        
            
    def sendActivateToRR(self):
        if (not self.sendActivateToRR_waitTimeOver(10)):
            return
        #logger.debug("jobUpdateActivate:...")
        for i in range(len(self.nodes)):
            if (self.nodes[i].newFramesActive):
                binFrameSet= rrCmds.getBinaryFrameSet()
                binFrameSet.setStartFileFrame(self.nodes[i].minFrame)
                for fr in self.nodes[i].activeFrames:
                    binFrameSet.setFrame(fr, True)
                logger.info("jobUpdateActivate: activating frames for job {} {}: {}".format(self.nodes[i].rrJobID,self.nodes[i].rrJobIDStr, self.nodes[i].activeFrames))
                if (not rrCmds.send_addBinaryFrameSet(self.nodes[i].rrJobID , binFrameSet)):
                    logger.warning("jobUpdateActivate: Unable to activate frames for job {} {}: {}".format(self.nodes[i].rrJobID,self.nodes[i].rrJobIDStr, self.nodes[i].activeFrames))
                
                self.nodes[i].newFramesActive=False
                self.nodes[i].activeFrames=[]
                
            
    def disableAbortAllJobs(self):
        for i in range(len(self.nodes)):
            logger.info("Disabling & Aborting job {}".format(self.nodes[i].rrJobIDStr))
            rrCmds.abortNDisableJob(self.nodes[i].rrJobID)
        pass
    
        
        
        
        



class RoyalScheduler( CallbackServerMixin, PyScheduler):

    def __init__(self, scheduler, name):
        PyScheduler.__init__(self, scheduler, name)
        CallbackServerMixin.__init__(self, False)
        self.parmprefix = 'rr'
        self.h2rrMap=houdiniTask2rrJobMapper()
        self.jobsCreated = False
        self.exportXML= False
        self.useCallBackServer = True
        self.jobSettings=""
        self.jobVarName=[]
        self.jobVarValue=[]
        self.jobEnvList=""
        


    @classmethod
    def templateName(cls):
        return 'royalScheduler'

    def readGlobalUISettings(self):
        schedulerVerbose= self["rr_schedulerVerbose"].evaluateString()
        if (schedulerVerbose=="error"):
            logger.setLevel(logging.DEBUG)
        elif (schedulerVerbose=="warning"):
            logger.setLevel(logging.WARNING)
        elif (schedulerVerbose=="info"):
            logger.setLevel(logging.INFO)
        elif (schedulerVerbose=="debug"):
            logger.setLevel(logging.DEBUG)
        
        submitterVerbose= self["rr_submissionVerbose"].evaluateString()
        if (submitterVerbose=="none"):
            rrCmds.setVerboseLevel(0)
        elif (submitterVerbose=="error"):
            rrCmds.setVerboseLevel(1)
        elif (submitterVerbose=="warning"):
            rrCmds.setVerboseLevel(2)
        elif (submitterVerbose=="info"):
            rrCmds.setVerboseLevel(3)
        elif (submitterVerbose=="progress"):
            rrCmds.setVerboseLevel(4)
        elif (submitterVerbose=="debug"):
            rrCmds.setVerboseLevel(10)
        elif (submitterVerbose=="debugjobs"):
            rrCmds.setVerboseLevel(13)
        self.exportXML = self['rr_exportAsXML'].evaluateInt() > 0
        
        self.jobSettings=""
        L_jobSettings= self["job_settings"].evaluateString()
        for setting in L_jobSettings.split(";"):
            self.jobSettings=self.jobSettings+ ' "' + setting + '" '
        
        self.jobVarName=[]
        self.jobVarValue=[]
        L_jobVariables= self["job_variables"].evaluateString()
        for var in L_jobVariables.split(";"):
            equalSign= var.find("=")
            if (equalSign>0):
                varname = var[:equalSign]
                varvalue = var[equalSign+1:]
                varname= varname.strip()
                varvalue= varvalue.strip()
                varname = "Custom{}".format(varname)
                self.jobVarName.append(varname)
                self.jobVarValue.append(varvalue)
       
        self.jobEnvList=""
        L_Env= self["env_vars"].evaluateString()
        for var in L_Env.split(";"):
            equalSign= var.find("=")
            if (equalSign>0):
                varname = var[:equalSign]
                varvalue = var[equalSign+1:]
                varname= varname.strip()
                varvalue= varvalue.strip()
                self.jobEnvList= self.jobEnvList + "{}={}~~~".format(varname, varvalue)
                
                
    @classmethod
    def templateBody(cls):
        return json.dumps({
            "name": "royalScheduler",
            "parameters" : [
                {
                    "name" : "rr_pdg_jobname",
                    "label" : "Job Name",
                    "type" : "String",
                    "size" : 1,
                },          
                {
                    "name" : "rr_exportAsXML",
                    "type" : "Integer",
                    "size" : 1,
                    "value" : 0,
                },
                {
                    "name" : "rr_schedulerVerbose",
                    "label" : "Scheduler Verbose",
                    "type" : "String",
                    "size" : 1,
                    "value" : "warning"
                },               
                {
                    "name" : "rr_submissionVerbose",
                    "label" : "rrSubmitter Verbose",
                    "type" : "String",
                    "size" : 1,
                    "value" : "warning"
                },               
                
            ]
        })


    def applicationBin(self, name, work_item):
        """
        [virtual] Returns the path to the given application
        """
        #not used RR
        if name == 'python':
            return "<Exe><../>python" + str(sys.version_info.major) + str(sys.version_info.minor) + "/python"
        elif name == 'hython':
            return "<Exe>" 


    def onStart(self):
        """
        Called by PDG when scheduler is first created. Can be used to acquire resources that persist between cooks.
        Called by SubmitAsJob as well
        """
        logger.debug('-------------------onStart-------------------')
        return True


    def onStop(self):
        """
        Called by PDG when scheduler is cleaned up. Can be used to release resources. Note that this method may not be called in some cases when Houdini is shut down.
        """
        logger.debug('-------------------onStop-------------------')
        self.h2rrMap.disableAbortAllJobs()
        if (self.useCallBackServer):
            self.stopCallbackServer()
        if LOG_FUNCTION_ENTER_EXIT:
            logger.debug('-------------------onStop--EXIT-----------------')
        return True


    def onStartCook(self, static, cook_set):
        try:
            """
            This callback is called when a PDG cook starts, after static generation.
            """
            self.readGlobalUISettings()
            logger.info('   \n'
                        '##########################################################\n'
                        'onStartCook\n')
            self.h2rrMap.disableAbortAllJobs()
            self.h2rrMap.clear()
            self.jobsCreated=False

            pdg_workingdir = self["pdg_workingdir"].evaluateString()
            self.setWorkingDir(pdg_workingdir, pdg_workingdir)
            local_ip="";
            if (self.useCallBackServer):
                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
                if not self.isCallbackServerRunning():
                    self.startCallbackServer()      
                    logger.info("onStartCook:  workItemResultServerAddr '{}'".format(self.workItemResultServerAddr()))                
                    logger.info("onStartCook:  hostname '{}'".format(hostname))                
                    logger.info("onStartCook:  local_ip '{}'".format(local_ip))                
        except:
            logger.error("\n   onStartCook  Exception.\n")
            logger.error(str(traceback.format_exc()))
            return False
        if LOG_FUNCTION_ENTER_EXIT:
            logger.debug('-------------------onStartCook--EXIT-----------------')

        return True

    def workItemResultServerAddr(self):
        if LOG_FUNCTION_ENTER_EXIT:
            logger.debug('-------------------workItemResultServerAddr-------------------')
        try:
            serverName = super().workItemResultServerAddr()
            
            local_ip="";
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            if (len(local_ip)>0 and local_ip!="127.0.0.1"):
                address, port = serverName.split(':')
                serverName= local_ip + ":" +  port
        except:
            logger.error("\n   workItemResultServerAddr Exception.\n")
            logger.error(str(traceback.format_exc()))
            return False            
        if LOG_FUNCTION_ENTER_EXIT:
            logger.debug('-------------------workItemResultServerAddr--EXIT-----------------')
        return serverName

    def onStopCook(self, cancel):
        """
        Called when cooking completes or is canceled. 
        If cancel is True there will likely be jobs still running. 
        In that case the scheduler should cancel them and block until they are actually canceled. 
        This is also the time to tear down any resources that are set up in onStartCook. 
        """
        logger.info('------------------- onStopCook: cancel = ' + str(cancel))

        if cancel:
            self.h2rrMap.disableAbortAllJobs()
        if (self.useCallBackServer):
            self.stopCallbackServer()            
        if LOG_FUNCTION_ENTER_EXIT:
            logger.debug('-------------------onStopCook--EXIT-----------------')

        return True


    def onSchedule(self, work_item):
        """
        This callback is evaluated when the given pdg.WorkItem is ready to be executed. 
        The scheduler should create the necessary job spec for their farm scheduler and submit it if possible.
        """
        if LOG_FUNCTION_ENTER_EXIT:       
            #logger.debug("------------------- onSchedule:  {};{};{};{}".format(work_item.node.name, work_item.id, work_item.index, work_item.command))
            logger.debug('------------------- onSchedule input: {} - {}'.format(work_item.node.name, work_item.name))
        #if len(work_item.command) == 0:
         #   return pdg.scheduleResult.CookSucceeded
            

        # Ensure directories exist and serialize the work item
        self.createJobDirsAndSerializeWorkItems(work_item)

        #Houdini sends 60 tasks per second by default
        #We collect them and send a pack of tasks for each node in onTick() every x seconds
        if not self.h2rrMap.activateWork(work_item, self):
            if LOG_FUNCTION_ENTER_EXIT:
                logger.debug('-------------------onSchedule--EXIT1-----------------')
            return pdg.scheduleResult.Failed

        if LOG_FUNCTION_ENTER_EXIT:
            logger.debug('-------------------onSchedule--EXIT2-----------------')
        return pdg.scheduleResult.Succeeded


    def onScheduleStatic(self, dependencies, dependents, ready_items):
        """
        I first thought about adding it for Tops with less than 200 tasks
        Then I read:
        "For the above reasons we do not recommend attempting to generate fully static jobs from PDG graphs."
        https://www.sidefx.com/docs/houdini/tops/custom_scheduler.html#staticcook
        """

    def onTick(self):
        """
        This callback is called periodically when the graph is cooking.
        The callback is generally used to check the state of running work items. 
        This is also the only safe place to cancel an ongoing cook.   

        The period of this callback is controlled with the PDG node parameter pdg_tickperiod, 
        and the maximum number of ready item onSchedule callbacks between ticks is controlled 
        by the node parameter pdg_maxitems. For example by default the tick period is 0.5s 
        and the max items per tick is 30. This means that onSchedule will be called a maximum of 60 times per second. 
        Adjusting these values can be useful to control the load on the farm scheduler.
        """
        if LOG_FUNCTION_ENTER_EXIT:
            logger.debug('-------------------onTick-------------------')
        
        
        #we pre-generate the jobs. 
        #This way we do not have to change the frame range every time.
        #And the artist has a better overview in RR.
        #Even if some tasks of a node are not submitted, it is stil only one job in RR.
        #Disadvatage: There are some nodes in TOP that are not submitted at all
        #
        #Improvement: Keep the job collection, but submit them only if tasks are activeated for the node
        
        if not self.jobsCreated:
            try:
                #dependencyGraph(expand_partitions=False) => tuple of dict 
                #Returns the static dependency graph for work items that would normally be processed by this scheduler. 
                #The graph is represented as a tuple containing a map of work item->dependencies, work item->dependents and a list of items currently ready to cook.
                #The expand_partitions argument configures whether partitions should be expanded into a flat dependency graph containing only regular work items, or kept in the tuple.
                #requires cookWorkItems() to be executed first
                dependencies, dependents, ready = self.dependencyGraph(False)
                
                logger.debug("onTick: lCount {}".format(len(dependents.items())))
                if (len(dependents.items())==0):
                    logger.debug("onTick: return SchedulerBusy")
                    return pdg.tickResult.SchedulerBusy
                
                logger.debug("onTick: loop dependents.items()")
                for wo_it, children in dependents.items():
                    if (wo_it.name!=wo_it.label):
                        logger.debug("onTick:  *  {};{};{};{}; {}".format(wo_it.name, wo_it.label, wo_it.id, wo_it.index, wo_it.command))
                    else: 
                        #logger.debug("onTick:  *  {};         ;{};{}; {}".format(wo_it.name, wo_it.id, wo_it.index, wo_it.command))
                        pass
                    self.h2rrMap.addWork(wo_it, self)
                logger.debug("onTick: loop dependents.items() done")
                
                self.h2rrMap.sortByIndex()
                self.h2rrMap.printInfo()

                if (not self.h2rrMap.submitJobs(self)):
                    return pdg.tickResult.SchedulerCancelCook                
                self.jobsCreated= True

                if (self.exportXML):
                    if LOG_FUNCTION_ENTER_EXIT:
                        logger.debug('-------------------onTick--EXIT1-----------------')
                    return pdg.tickResult.SchedulerCancelCook                

                if LOG_FUNCTION_ENTER_EXIT:
                    logger.debug('-------------------onTick--EXIT2-----------------')
                return pdg.tickResult.SchedulerBusy
                
            except:
                logger.error("\n   onTick 'not self.jobsCreated' Exception.\n")
                logger.error(str(traceback.format_exc()))
                return pdg.tickResult.SchedulerCancelCook
             
             
        #send tasks that Houdini has activated 
        try:
            self.h2rrMap.sendActivateToRR()
        except:
            logger.error("\n   onTick 'jobUpdateActivate' Exception.\n")
            logger.error(str(traceback.format_exc()))
            return pdg.tickResult.SchedulerCancelCook


        #retrieve the status of all jobs with active tasks
        try:
            if (self.h2rrMap.getFrameStatusFromRR_waitTimeOver(10)):
                frDone=0
                frRendering=0
                frAll=0 
                frActivated=0  
                for i in range(len(self.h2rrMap.nodes)):
                    if (self.h2rrMap.nodes[i].everFramesActive):
                        frStatusList=  rrCmds.sendrequest_FrameList(self.h2rrMap.nodes[i].rrJobID)
                        #logger.debug("onTick getFrameStatusFromRR  {} {}   frCount:{}".format(self.h2rrMap.nodes[i].rrJobID,self.h2rrMap.nodes[i].rrJobIDStr,frStatusList.frameCount()))  
                        frAll= frAll + frStatusList.frameCount()
                        for i in range(0, frStatusList.frameCount()):
                            if (frStatusList.idxValid(i)):
                                frActivated= frActivated+1
                                rrFrame_HoudiniIndex= frStatusList.idxToFrame(i)
                                if (frStatusList.idxIsRendering(i)):
                                    self.onWorkItemStartCook(rrFrame_HoudiniIndex, -1)
                                    #if not (rrFrame_HoudiniIndex in self.h2rrMap.nodes[i].renderingList):
                                     #   self.h2rrMap.nodes[i].renderingList.append(rrFrame_HoudiniIndex)
                                    frRendering= frRendering +1
                                elif frStatusList.idxStatusClientReturned(i):
                                    self.onWorkItemSucceeded(rrFrame_HoudiniIndex, -1, 1)
                                    #if not (rrFrame_HoudiniIndex in self.h2rrMap.nodes[i].doneList):
                                     #   self.h2rrMap.nodes[i].doneList.append(rrFrame_HoudiniIndex)
                                    frDone= frDone+1
                                    
                logger.info("onTick getFrameStatusFromRR frAll:{} frActivated:{} frRendering:{} frDone:{} ".format(frAll,frActivated,frRendering,frDone))        
            
            
        except:
            logger.error("\n   onTick 'getFrameStatusFromRR' Exception.\n")
            logger.error(str(traceback.format_exc()))
            return pdg.tickResult.SchedulerCancelCook

                
        #We do not limit the number of jobs to submit, therefore always ready
        #logger.debug("      onTick return SchedulerReady")
        
        #a way to tell the rrClient that this app is still running.
        #Creates a 3sec CPU peak every 120 seconds
        rrCmds.aliveCpuPeak()
        
        if LOG_FUNCTION_ENTER_EXIT:
            logger.debug('-------------------onTick--EXIT3-----------------')
        return pdg.tickResult.SchedulerReady


    def submitAsJob(self, graph_file, node_path):
        """
        Called by pressing the 'Submit as Job' button on the scheduler node
        UI.  Creates a job which cooks that TOP graph using hython.
        """
        self.readGlobalUISettings()
        logger.debug("submitAsJob({},{})".format(graph_file, node_path))
        
        self.h2rrMap.disableAbortAllJobs()
        rrCmds.clearSubmissionList()
    
        renderApp= rrCmds.createRenderApp()
        renderApp.name="Houdini"
        renderApp.setVersionBoth(hou.applicationVersionString())
        renderApp.rendererName="PDG_All"  
        
        
        newJob= rrCmds.createJob(hou.hipFile.path(),"H2RR_%rrVersion%")
        newJob.layer= node_path
        newJob.renderApp= renderApp
        newJob.imageDir= os.path.dirname(hou.hipFile.path())
        newJob.seqStart=1
        newJob.seqEnd=1
        pythonVer= str(sys.version_info.major) + "." +  str(sys.version_info.minor)
        newJob.customDataAppend_Str("CustomHPyVerP", pythonVer )
        pythonVer= str(sys.version_info.major) + str(sys.version_info.minor)
        newJob.customDataAppend_Str("CustomHPyVer", pythonVer )
        
        envList= ""
        envList= envList+  self.jobEnvList
        newJob.customDataAppend_Str("rrEnvList", envList )
        for iv in range(len(self.jobVarName)):
            newJob.customDataAppend_Str(self.jobVarName[iv], self.jobVarValue[iv] )                    
        newJob.customDataAppend_Str("rrSubmitterParameter", self.jobSettings )
                
        
        rrCmds.addJob(newJob)
        if (self.exportXML):
            xmlFilename= rrCmds.getXmlTempFile("rrSubmitHoudini")
            if rrCmds.exportXML(xmlFilename):
                logger.info("Exported as xml file "+xmlFilename)
            else:
                logger.error("Unable to export as xml file "+xmlFilename)
        else:
            if (not rrCmds.submitJobList_withUI()):
                logger.error("Unable to submit jobs! {}".format(rrCmds.getErrorString()))
            else:
                logger.info("Submitted 1 job!")
        
        if (houdiniMajorVersion_Int() >= 20):
            return "", "" # we not not offer url links nor JobID
        else:
            return "" # we not not offer url links 


    
