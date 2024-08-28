# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy

import sys
import os
import shutil
import traceback
import tempfile
from datetime import datetime

import logging
# TODO: final logging directory for Royal Render
_TEMP_DIR = tempfile.gettempdir()
_TEMP_NAME = "rrHoudini.log"

# create logger
logger = logging.getLogger("rrS")
# create file handler which logs even debug messages
#fh = logging.FileHandler(os.path.join(_TEMP_DIR, _TEMP_NAME))
# create console handler with a different log level
#fh.setLevel(logging.WARNING)
#fh.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
level = logging.DEBUG if "DEBUG" in os.environ else logging.INFO
ch.setLevel(level)
# create formatter and add it to the handlers
formatter = logging.Formatter("%(asctime)s %(name)s| %(levelname)s:  %(message)s", "%M:%S")
#fh.setFormatter(formatter)
ch.setFormatter(formatter)

# add the handlers to the logger
#logger.addHandler(fh)
logger.addHandler(ch)


def getLogger():
    return logging.getLogger("rrS")


def findRR_Root_Binfolder():
    # findRR_Root adds the RR path as search path for the module
    # This function work only if RR was installed on the machine (as it uses the env var RR_ROOT)
    import platform
    import struct
    is64bit=(struct.calcsize("P") == 8)

    #for beta sites that use some RR9 apps, but farm is still RR8
    if ('RR_ROOT9' in os.environ):
        binPath= os.environ['RR_ROOT9']
    else:
        if not ('RR_ROOT' in os.environ):
            return ""
        binPath=os.environ['RR_ROOT']
    if (os.path.exists(binPath+"/_RR9")):
        binPath= binPath+"/_RR9"
        
    binPath=binPath.replace("\\","/")
    if (sys.platform.lower() == "win32"):
        binPath=binPath + '/bin/win64'
    elif (sys.platform.lower() == "darwin"):
            binPath=binPath + '/bin/mac64'
    else:
        binPath=binPath + '/bin/lx64'
    binPath= binPath.replace("_debug","_release")
    logger.debug("findRR_Root_Binfolder:" + binPath)
    return binPath

def rrSyncCopy(srcname, dstname, errors):
    srcStat= os.stat(srcname)
    if os.path.isfile(dstname):
        dstStat= os.stat(dstname)
    
    
        if (srcStat.st_mtime - dstStat.st_mtime <= 1) and (srcStat.st_size == dstStat.st_size):
            # print("rrSyncTree: same size and time "+srcname)
            return
  
    # print("rrSyncTree: copy file "+srcname)
    # exceptions are handled in parent function
    shutil.copyfile(srcname, dstname)
     
    try:
        shutil.copystat(srcname, dstname)
    except OSError as why:
        # special exceptions NOT handled in parent function
        if WindowsError is not None and isinstance(why, WindowsError):
            # Copying file access times may fail on Windows
            pass
        else:
            errors.extend((srcname, dstname, str(why)))
            
class Error(EnvironmentError):
    pass

def rrSyncTree(src, dst, symlinks=False):
    names = os.listdir(src)
    ignored_names = ('QtGui', 'Qt5Gui', 'QtXml', 'Qt5Xml', 'Qt5Widgets', 
                     'avcodec', 'avformat', 'avutil', 'cuda', 'swscale',
                     'Half', 'Iex', 'IlmImf', 'IlmThread', 'Imath', 'OpenEXR',
                     'libcurl', 'libpng', 'rrJpeg', 'curl', 'rrShared', '7z', 
                     'D3Dcompiler', 'iconengines', 'imageformats',
                     'platforms', 'bearer', 'translations')
    contain_names = ('')
    if sys.platform.lower().startswith("win32"):
        contain_names = ('.dll', '.pyd')
    elif sys.platform.lower() == "darwin":
        contain_names = ('') #QT libs have no extension
    else:
        contain_names = ('.so')
        
    if not os.path.isdir(dst): 
        os.makedirs(dst)
    errors = []
    for name in names:
        if any(s in name for s in ignored_names):
            # print("rrSyncTree: ignoring file (1) "+name)
            continue
        if (len(contain_names)>0) and not any(s in name for s in contain_names):
            # print("rrSyncTree: ignoring file (2) "+name)
            continue
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        try:
            if os.path.isdir(srcname):
                rrSyncTree(srcname, dstname, symlinks, ignore)
            else:
                # Will raise a SpecialFileError for unsupported file types
                rrSyncCopy(srcname, dstname, errors)
        # catch the Error from the recursive rrSyncTree so that we can
        # continue with other files
        except Error as err:
            errors.extend(err.args[0])
        except EnvironmentError as why:
            errors.append((srcname, dstname, str(why)))
        
    if errors:
        raise Error(errors)    
    

def rrModule_createLocalCache(rrBinFolder):
    # Python module files and their required dependenicy libs are locked if they are in use.
    # If you directly use the modules from the RR network folder, you have a constant connection to our fileserver.
    # And you cannot update RR as long as you use this python script.
    # This function copies all required files to your local temp folder.
    import platform
    import struct
    import tempfile
    
    if (len(rrBinFolder)==0):
        return

    #Get the default temp folder 
    tempFolder= tempfile.gettempdir()
    tempFolder= tempFolder.replace("\\","/")
    if (rrBinFolder.endswith("64")):
        tempFolder= tempFolder+ "/rrbin64_py"
    else:
           tempFolder= tempFolder+ "/rrbin_py"
    if (sys.platform.lower() != "win32") :
        tempFolder = tempFolder + "/lib"     
        rrBinFolder = rrBinFolder + "/lib"
    # print ("tempFolder "+tempFolder )
    logger.debug ("rrBinFolder "+rrBinFolder )
    
    if ("RoyalRenderGit_90" in rrBinFolder):
        modPath= rrBinFolder
    else:
        rrSyncTree(rrBinFolder, tempFolder)
        modPath= tempFolder
        if (sys.platform.lower() == "darwin"):
            modPath=modPath + '/python/any'
    if modPath not in sys.path:
        sys.path.append(modPath)
        logger.debug("added module path "+modPath)





#The module should not be loaded if Houdini loads this plugin
#The module should only be loaded if this plugin is used

global rrsched__pyRR_submit_loaded
rrsched__pyRR_submit_loaded= False
global rrSubmitter
global rrJob
global rrSubmitLib

def loadRRmodule():
    global rrsched__pyRR_submit_loaded
    global rrSubmitter
    if (rrsched__pyRR_submit_loaded):
        return rrSubmitter
    rrModule_createLocalCache(findRR_Root_Binfolder())
    global rrSubmitLib
    try:
        if (sys.version_info.major == 2):
            import libpyRR2_submit as rrSubmitLib
            logger.debug("libpyRR2_submit loaded ({})".format(rrSubmitLib.__file__))
            rrsched__pyRR_submit_loaded= True
        elif (sys.version_info.major == 3):
            if (sys.version_info.minor == 7):
                import libpyRR37_submit as rrSubmitLib
                logger.debug("libpyRR37_submit loaded ({})".format(rrSubmitLib.__file__))
                rrsched__pyRR_submit_loaded= True
            elif (sys.version_info.minor == 9):
                import libpyRR39_submit as rrSubmitLib
                logger.debug("libpyRR39_submit loaded ({})".format(rrSubmitLib.__file__))
                rrsched__pyRR_submit_loaded= True
            elif (sys.version_info.minor == 10):
                import libpyRR310_submit as rrSubmitLib
                logger.debug("libpyRR310_submit loaded ({})".format(rrSubmitLib.__file__))
                rrsched__pyRR_submit_loaded= True
            elif (sys.version_info.minor == 11):
                import libpyRR311_submit as rrSubmitLib
                logger.debug("libpyRR311_submit loaded ({})".format(rrSubmitLib.__file__))
                rrsched__pyRR_submit_loaded= True
            elif (sys.version_info.minor == 12):
                import libpyRR312_submit as rrSubmitLib
                logger.debug("libpyRR312_submit loaded ({})".format(rrSubmitLib.__file__))
                rrsched__pyRR_submit_loaded= True
            elif (sys.version_info.minor == 13):
                import libpyRR313_submit as rrSubmitLib
                logger.debug("libpyRR313_submit loaded ({})".format(rrSubmitLib.__file__))
                rrsched__pyRR_submit_loaded= True
            elif (sys.version_info.minor == 14):
                import libpyRR314_submit as rrSubmitLib
                logger.debug("libpyRR314_submit loaded ({})".format(rrSubmitLib.__file__))
                rrsched__pyRR_submit_loaded= True
        if (not rrsched__pyRR_submit_loaded):
            logger.warning("\n Unable to load libpyRR_submit for python version {}.{}.\n"
            .format(sys.version_info.major,sys.version_info.minor))
    except:
         logger.warning("Unable to load libpyRR_submit.\nPython sys.path is: \n "+str(sys.path))
         logger.warning(str(traceback.format_exc()))
         return None
    
    global rrJob
    import rrJob
    rrSubmitter= rrSubmitLib.Submitter()
    return rrSubmitter

#-------------------------------------------------------------------------------------------------------------
#-------------------------------------------------------------------------------------------------------------
#-------------------------------------------------------------------------------------------------------------




def createJob(sceneFileName, pluginVersion):
    loadRRmodule()
    return rrSubmitLib.createEmptyJob2(sceneFileName,pluginVersion)
    pass    
    
def createRenderApp():
    loadRRmodule()
    ra= rrJob._RenderAppBasic() #somehow this does not work within Houdini?
    ra.clear()
    return ra
    
def clearSubmissionList():
    rrSubmitter= loadRRmodule()
    rrSubmitter.deleteAllJobs()
    pass
    
def addJob(newJob):
    rrSubmitter= loadRRmodule()
    rrSubmitter.addJob(newJob)
    pass

def submitJobList():
    rrSubmitter= loadRRmodule()
    return rrSubmitter.submitJobs()
    pass
    
def submitJobList_withUI():
    rrSubmitter= loadRRmodule()
    return rrSubmitter.submitJobs_withUI()
    pass
    
def getXmlTempFile(prefix):    
    now = datetime.now() 
    return os.path.join(tempfile.gettempdir(), prefix+ "_"+ now.strftime("%m%d%H%M%S") +".xml")
    
def exportXML(exportFilename):
    rrSubmitter= loadRRmodule()
    rrJob.exportJobAsXml_MultiStart()
    for jNr in range(0, rrSubmitter.getJobCount()):
        job= rrSubmitter.getJob(jNr)
        rrJob.exportJobAsXml_MultiAdd(job, False)
    if not rrJob.exportJobAsXml_MultiEnd(exportFilename, False, False):
        return False
    else:
        return True
    pass
    
def setLastJobsID(jID):
    rrSubmitter= loadRRmodule()
    rrSubmitter.setLastJobsID(jID)

def restartJobID():
    rrSubmitter= loadRRmodule()
    rrSubmitter.setLastJobsID(0)
    
def frameSetBinaryLock_name():
    loadRRmodule()
    return rrSubmitLib.get_frameSetBinaryLock_name()
    
def setVerboseLevel(level):
    loadRRmodule()
    rrSubmitLib.setVerboseLevel(level)
    
def getBinaryFrameSet():
    loadRRmodule()
    return rrJob._binaryFrameSet()   

def abortNDisableJob(jobID):
    if (jobID==0):
        return True
    rrSubmitter= loadRRmodule()
    return rrSubmitter.send_JobCommand(jobID, 4)  #4 is the same as from module rrJob   rrJob._LogMessage.lDisableAbort
    
def jobsSendCount():
    rrSubmitter= loadRRmodule()
    return rrSubmitter.jobsSendCount()

def jobsSendID(idx):
    rrSubmitter= loadRRmodule()
    return rrSubmitter.jobsSendID(idx)  

def jobsID2Str(ID):
    loadRRmodule()
    return rrJob.jID2Str(ID)

def getRandomPW():
    rrSubmitter= loadRRmodule()
    return rrSubmitter.getRandomPassword()
    
def setJobCommandPassword(password):
    rrSubmitter= loadRRmodule()
    return rrSubmitter.setJobCommandPassword(password)

def send_addBinaryFrameSet(jobID, frameSet):
    if (jobID==0):
        return False
    rrSubmitter= loadRRmodule()
    return rrSubmitter.send_addBinaryFrameSet(jobID, frameSet)    
    
def send_jobCommand(jobID, commandID):
    if (jobID==0):
        return True
    rrSubmitter= loadRRmodule()
    return rrSubmitter.send_JobCommand(jobID, commandID)    

def sendrequest_FrameList(jobID):
    rrSubmitter= loadRRmodule()
    return rrSubmitter.send_getFrameList(jobID)

def sendrequest_jobStatusInfo(jobID):
    rrSubmitter= loadRRmodule()
    return rrSubmitter.send_getJobStatus(jobID)
        

def aliveCpuPeak():
    rrSubmitter= loadRRmodule()
    return rrSubmitter.runCPUPeak(2)
        
def getErrorString():
    rrSubmitter= loadRRmodule()
    return rrSubmitter.errorString()
        