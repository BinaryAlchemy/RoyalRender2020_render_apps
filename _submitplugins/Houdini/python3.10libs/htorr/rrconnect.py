# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy
"""Module to connect to the Royal Render server and to obtain farm specific information like available clients and groups.
"""
#Note : This script requires Royal Render version 9
import sys
import os
import shutil
import traceback

import logging
logger = logging.getLogger("HtoRR")

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
        
    if (sys.platform.lower() == "win32"):
        if (is64bit):
            binPath=binPath + '/bin/win64'
        else:
            binPath=binPath + '/bin/win'
        binPath=binPath.replace("\\","/")
    elif (sys.platform.lower() == "darwin"):
        if (is64bit):
            binPath=binPath + '/bin/mac64'
        else:
            binPath=binPath + '/bin/mac'
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
    ignored_names = ('QtGui','QtXml','avcodec','avformat','avutil','cuda','Half','Iex','IlmImf','IlmThread','Imath','libcurl','libpng','rrJpeg','rrShared','swscale')
    contain_names = ('')
    if (sys.platform.lower() == "win32"):
        contain_names = ('.dll','.pyd')
        
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
        tempFolder= tempFolder+ "/rrbin64"
    else:
           tempFolder= tempFolder+ "/rrbin"
    if (sys.platform.lower() != "win32") :
        tempFolder = tempFolder + "/lib"     
        rrBinFolder = rrBinFolder + "/lib"
    # print ("tempFolder "+tempFolder )
    logger.debug ("rrBinFolder "+rrBinFolder )
    rrSyncTree(rrBinFolder, tempFolder)
    
    modPath= tempFolder
    if (sys.platform.lower() == "darwin"):
        if (sys.version_info.major == 2):
            modPath=modPath + '/python/27'
        else:
            modPath=modPath + '/python/39'
    sys.path.append(modPath)
    logger.debug("added module path "+modPath)




global htorr__pyRR_loaded
htorr__pyRR_loaded= False
global rrLib

def  loadModule_libpyRR2():
    global htorr__pyRR_loaded
    global rrLib
    if (htorr__pyRR_loaded):
        return
    try:
        rrModule_createLocalCache(findRR_Root_Binfolder())
        if (sys.version_info.major == 2):
            import libpyRR2 as rrLib
            logger.debug("libpyRR2 loaded ({})".format(rrLib.__file__))
            htorr__pyRR_loaded= True
        elif (sys.version_info.major == 3):
            if (sys.version_info.minor == 7):
                import libpyRR37 as rrLib
                logger.debug("libpyRR37 loaded ({})".format(rrLib.__file__))
                htorr__pyRR_loaded= True
            elif (sys.version_info.minor == 9):
                import libpyRR39 as rrLib
                logger.debug("libpyRR39 loaded ({})".format(rrLib.__file__))
                htorr__pyRR_loaded= True
            elif (sys.version_info.minor == 10):
                import libpyRR310 as rrLib
                logger.debug("libpyRR310 loaded ({})".format(rrLib.__file__))
                htorr__pyRR_loaded= True
            elif (sys.version_info.minor == 11):
                import libpyRR311 as rrLib
                logger.debug("libpyRR311 loaded ({})".format(rrLib.__file__))
                htorr__pyRR_loaded= True
            elif (sys.version_info.minor == 12):
                import libpyRR312 as rrLib
                logger.debug("libpyRR312 loaded ({})".format(rrLib.__file__))
                htorr__pyRR_loaded= True
            elif (sys.version_info.minor == 13):
                import libpyRR313 as rrLib
                logger.debug("libpyRR313 loaded ({})".format(rrLib.__file__))
                htorr__pyRR_loaded= True
            elif (sys.version_info.minor == 14):
                import libpyRR314 as rrLib
                logger.debug("libpyRR314 loaded ({})".format(rrLib.__file__))
                htorr__pyRR_loaded= True
        if (not htorr__pyRR_loaded):
            logger.warning("\n    Unable to load libpyRR for python version {}.{}.\n    Buttons to get client names do not work.\n".format(sys.version_info.major,sys.version_info.minor))
    except:
         logger.warning("\n    Unable to load libpyRR.\n    Buttons to get client names do not work.\n")
         logger.debug(str(traceback.format_exc()))
         
        

def get_client_groups():
    loadModule_libpyRR2()
    global htorr__pyRR_loaded
    if (not htorr__pyRR_loaded):
        return []
    global rrLib
        
    
    #groupCfgFilename=rrData.getRRFolder_cfgUser()
    #if (len(groupCfgFilename)==0):
    #    logger.error("ERROR: RR folder not found.")
    #    return
    #groupCfgFilename=groupCfgFilename+"clientgroups.ini"
    #groupList=rrData._ClientGroupList()
    #retSuccess= groupList.loadFromFile(groupCfgFilename)
    #if not retSuccess:
    #    logger.error("ERROR: Unable to load file '"+groupCfgFilename+"'. "+groupList.getError())
    #    return
  
    logger.debug("Set up server and login info.")
    tcp = rrLib._rrTCP("")
    rrServer=tcp.getRRServer() #This function works in your company only as it uses the RR_ROOT environment installed by rrWorkstationInstaller
    if (len(rrServer)==0):
        logger.debug (tcp.errorMessage())
    if not tcp.setServer(rrServer, 7773):
        logger.error ("Error setServer: "+ tcp.errorMessage())
        return
        
    #IMPORTANT: If you set a password, then the rrServer enables its authorization check.
    #           This means this user HAS TO to exist in RR.
    #           If you are running this script from your local intranet, you probably do not need a password.
    #           Please see rrHelp section Usage/External Connections/Security

    #tcp.setLogin("MyUser", "")
    if not tcp.connectAndAuthorize():
        logger.error("Error authorizing at the rrServer: " + tcp.errorMessage())
        return [] 
    groupList=tcp.clientGetGroups()


    logger.debug("List of groups loaded ("+str(groupList.count)+" groups)")
    groups = [groupList.clientGroup(gi).getName() for gi in range(groupList.count)]
    for gi in range(groupList.count):
        grp= groupList.clientGroup(gi)
        logger.debug("    " + grp.getName()) 

    return groups

def get_clients():
    loadModule_libpyRR2()
    global htorr__pyRR_loaded
    if (not htorr__pyRR_loaded):
        return []
    ### --------------------------------------------------------------------- INIT
    global rrLib
    logger.debug("Set up server and login info.")
    tcp = rrLib._rrTCP("")
    rrServer=tcp.getRRServer() #This function works in your company only as it uses the RR_ROOT environment installed by rrWorkstationInstaller
    if (len(rrServer)==0):
        logger.debug (tcp.errorMessage())
    if not tcp.setServer(rrServer, 7773):
        logger.error ("Error setServer: "+ tcp.errorMessage())
        return
  
  
    #IMPORTANT: If you set a password, then the rrServer enables its authorization check.
    #           This means this user HAS TO to exist in RR.
    #           If you are running this script from your local intranet, you probably do not need a password.
    #           Please see rrHelp section Usage/External Connections/Security

    #tcp.setLogin("MyUser", "")
    if not tcp.connectAndAuthorize():
        logger.error("Error authorizing at the rrServer: " + tcp.errorMessage())
        return []


    ### --------------------------------------------------------------------- CLIENTS
    logger.debug("\nCheck clients")
    if not tcp.clientGetList():
      logger.error("Error getting clients: " + tcp.errorMessage())
    else:
      clients = tcp.clients
      nbClients = clients.count()
      #logger.error("Number of client found: " + str(nbClients))
      #for i in xrange(0, nbClients):
        #cl = clients.at(i)
        #logger.error("\tCpuUsage %6.2f name: %s" %(cl.CPU_Usage,cl.name) )

    return [clients.at(i).name for i in range(nbClients)]

