# Royal Render Plugin script for Nuke 13
# Author: Royal Render, Holger Schoenberger, Binary Alchemy
# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy
# #win: rrInstall_Copy: \plugins\
# #win: rrInstall_Change_File:        \plugins\menu.py, before "# Help menu", "m =  menubar.addMenu(\"RRender\");\nm.addCommand(\"Submit Comp\", \"nuke.load('rrSubmit_Nuke_13'), rrSubmit_Nuke()\")\nm.addCommand(\"Submit Copycat\", \"nuke.load('rrSubmit_Nuke_13'), rrSubmit_Nuke_Copycat()\")\nm.addCommand(\"Submit Shotgun Nodes (convert at render time)\", \"nuke.load('rrSubmit_Nuke_13'), rrSubmit_Nuke_Shotgun()\")\nm.addCommand(\"Submit Shotgun Nodes (convert local)\", \"nuke.load('rrSubmit_Nuke_13'), rrSubmit_Nuke_Shotgun_convert()\")\n\n"

# #linux: rrInstall_Copy: \plugins\
# #linux: rrInstall_Change_File:        \plugins\menu.py, before "# Help menu", "m =  menubar.addMenu(\"RRender\");\nm.addCommand(\"Submit Comp\", \"nuke.load('rrSubmit_Nuke_13'), rrSubmit_Nuke()\")\nm.addCommand(\"Submit Copycat\", \"nuke.load('rrSubmit_Nuke_13'), rrSubmit_Nuke_Copycat()\")\nm.addCommand(\"Submit Shotgun Nodes (convert at render time)\", \"nuke.load('rrSubmit_Nuke_13'), rrSubmit_Nuke_Shotgun()\")\nm.addCommand(\"Submit Shotgun Nodes (convert local)\", \"nuke.load('rrSubmit_Nuke_13'), rrSubmit_Nuke_Shotgun_convert()\")\n\n"

# #mac: rrInstall_Copy: /MacOS/plugins/
# #mac: rrInstall_Change_File:        /MacOS/plugins/menu.py, before "# Help menu", "m =  menubar.addMenu(\"RRender\");\nm.addCommand(\"Submit Comp\", \"nuke.load('rrSubmit_Nuke_13'), rrSubmit_Nuke()\")\nm.addCommand(\"Submit Copycat\", \"nuke.load('rrSubmit_Nuke_13'), rrSubmit_Nuke_Copycat()\")\nm.addCommand(\"Submit Shotgun Nodes (convert at render time)\", \"nuke.load('rrSubmit_Nuke_13'), rrSubmit_Nuke_Shotgun()\")\nm.addCommand(\"Submit Shotgun Nodes (convert local)\", \"nuke.load('rrSubmit_Nuke_13'), rrSubmit_Nuke_Shotgun_convert()\")\n\n"



import nuke
import os
import sys
import tempfile

from xml.etree.ElementTree import ElementTree, Element, SubElement


#####################################################################################
# This function has to be changed if an app should show info and error dialog box   #
#####################################################################################

def writeInfo(msg):
    print(msg)
    #nuke.message(msg)

def writeError(msg):
#    print(msg)
    nuke.message(msg)


##############################################
# JOB CLASS                                  #
##############################################


class rrJob(object):
         
    def __init__(self):
        self.clear()
    
    def clear(self):
        self.version = ""
        self.software = ""
        self.renderer = ""
        self.RequiredLicenses = ""
        self.sceneName = ""
        self.sceneDatabaseDir = ""
        self.seqStart = 0
        self.seqEnd = 100
        self.seqStep = 1
        self.seqFileOffset = 0
        self.seqFrameSet = ""
        self.imageWidth = 99
        self.imageHeight = 99
        self.imageDir = ""
        self.imageFileName = ""
        self.imageFramePadding = 4
        self.imageExtension = ""
        self.imagePreNumberLetter = ""
        self.imageSingleOutput = False
        self.imageStereoR = ""
        self.imageStereoL = ""
        self.sceneOS = ""
        self.camera = ""
        self.layer = ""
        self.channel = ""
        self.maxChannels = 0
        self.channelFileName = []
        self.channelExtension = []
        self.isActive = False
        self.sendAppBit = ""
        self.preID = ""
        self.waitForPreID  = ""
        self.CustomA  = ""
        self.CustomB  = ""
        self.CustomC  = ""
        self.LocalTexturesFile  = ""
        self.ColorSpaceConfigFile = ""
        self.ColorSpace = ""
        self.ColorSpace_View = ""

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
        text = str(text)
        if sys.version_info.major == 2:
            text = text if type(text) is unicode else text.decode("utf8")
        sub.text = text
        return sub
    

    def writeToXMLstart(self, submitOptions ):
        rootElement = Element("rrJob_submitFile")
        rootElement.attrib["syntax_version"] = "6.0"
        self.subE(rootElement, "DeleteXML", "1")
        self.subE(rootElement, "SubmitterParameter", submitOptions)
        # YOU CAN ADD OTHER NOT SCENE-INFORMATION PARAMETERS USING THIS FORMAT:
        # self.subE(jobElement,"SubmitterParameter","PARAMETERNAME=" + PARAMETERVALUE_AS_STRING)
        return rootElement

    def writeToXMLJob(self, rootElement):

        jobElement = self.subE(rootElement, "Job", "")
        self.subE(jobElement, "rrSubmitterPluginVersion", "%rrVersion%")
        self.subE(jobElement, "Software", self.software)
        self.subE(jobElement, "Renderer", self.renderer)
        self.subE(jobElement, "RequiredLicenses", self.RequiredLicenses)
        self.subE(jobElement, "Version", self.version)
        self.subE(jobElement, "Scenename", self.sceneName)
        self.subE(jobElement, "SceneDatabaseDir", self.sceneDatabaseDir)
        self.subE(jobElement, "IsActive", self.isActive)
        self.subE(jobElement, "SeqStart", self.seqStart)
        self.subE(jobElement, "SeqEnd", self.seqEnd)
        self.subE(jobElement, "SeqStep", self.seqStep)
        self.subE(jobElement, "SeqFileOffset", self.seqFileOffset)
        self.subE(jobElement, "SeqFrameSet", self.seqFrameSet)
        self.subE(jobElement, "ImageWidth", int(self.imageWidth))
        self.subE(jobElement, "ImageHeight", int(self.imageHeight))
        self.subE(jobElement, "ImageDir", self.imageDir)
        self.subE(jobElement, "Imagefilename", self.imageFileName)
        self.subE(jobElement, "ImageFramePadding", self.imageFramePadding)
        self.subE(jobElement, "ImageExtension", self.imageExtension)
        self.subE(jobElement, "ImageSingleOutput", self.imageSingleOutput)
        self.subE(jobElement, "ImagePreNumberLetter", self.imagePreNumberLetter)
        self.subE(jobElement, "ImageStereoR", self.imageStereoR)
        self.subE(jobElement, "ImageStereoL", self.imageStereoL)
        self.subE(jobElement, "SceneOS", self.sceneOS)
        self.subE(jobElement, "Camera", self.camera)
        self.subE(jobElement, "Layer", self.layer)
        self.subE(jobElement, "Channel", self.channel)
        self.subE(jobElement, "SendAppBit", self.sendAppBit)
        self.subE(jobElement, "PreID", self.preID)
        self.subE(jobElement, "WaitForPreID", self.waitForPreID)
        self.subE(jobElement, "CustomA", self.CustomA)
        self.subE(jobElement, "CustomB", self.CustomB)
        self.subE(jobElement, "CustomC", self.CustomC)
        self.subE(jobElement, "LocalTexturesFile", self.LocalTexturesFile)
        self.subE(jobElement, "ColorSpaceConfigFile", self.ColorSpaceConfigFile)
        self.subE(jobElement, "ColorSpace", self.ColorSpace)
        self.subE(jobElement, "ColorSpace_View", self.ColorSpace_View)
        for c in range(0,self.maxChannels):
           self.subE(jobElement,"ChannelFilename",self.channelFileName[c])
           self.subE(jobElement,"ChannelExtension",self.channelExtension[c])
        return True



    def writeToXMLEnd(self, f,rootElement):
        xml = ElementTree(rootElement)
        self.indent(xml.getroot())

        if f is None:
            print("No valid file has been passed to the write function")
            try:
                f.close()
            except:
                pass
            return False

        xml.write(f)
        f.close()

        return True



##############################################
# Global Functions                           #
##############################################

def getRR_Root():
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
    writeError("This plugin was not installed via rrWorkstationInstaller!")

def getRRSubmitterPath():
    ''' returns the rrSubmitter filename '''
    rrRoot = getRR_Root()
    if ((sys.platform.lower() == "win32") or (sys.platform.lower() == "win64")):
        rrSubmitter = rrRoot+"\\win__rrSubmitter.bat"
    elif (sys.platform.lower() == "darwin"):
        rrSubmitter = rrRoot+"/bin/mac64/rrStartLocal rrSubmitter "
    else:
        rrSubmitter = rrRoot+"/lx__rrSubmitter.sh"
    return rrSubmitter

def getRRSubmitterconsolePath():
    ''' returns the rrSubmitter filename '''
    rrRoot = getRR_Root()
    if ((sys.platform.lower() == "win32") or (sys.platform.lower() == "win64")):
        rrSubmitter = rrRoot+"\\bin\\win64\\rrStartLocal rrSubmitterconsole "
    elif (sys.platform.lower() == "darwin"):
        rrSubmitter = rrRoot+"/bin/mac64/rrStartLocal rrSubmitterconsole "
    else:
        rrSubmitter = rrRoot+"/bin/lx64/rrStartLocal rrSubmitterconsole "
    return rrSubmitter
    

def getOSString():
    if ((sys.platform.lower() == "win32") or (sys.platform.lower() == "win64")):
        return "win"
    elif (sys.platform.lower() == "darwin"):
        return "osx"
    else:
        return "lx"

    
def submitJobsToRR(jobList, submitOptions, nogui=False, own_terminal=False):
    if (len(jobList))==0:
        writeError("Error - No Nuke node for submission found")
        return
    tmpFile = tempfile.NamedTemporaryFile(mode='w+b',
                                          prefix="rrSubmitNuke_",
                                          suffix=".xml",
                                          delete=False)

    xmlObj= jobList[0].writeToXMLstart(submitOptions)
    for submitjob in jobList:
        submitjob.writeToXMLJob(xmlObj)
    ret = jobList[0].writeToXMLEnd(tmpFile, xmlObj)
    if ret:
        #writeInfo("Job written to " + tmpFile.name)
        pass
    else:
        writeError("Error - There was a problem writing the job file to " + tmpFile.name)
    commandline=""
    if nogui:
        commandline=getRRSubmitterconsolePath() + "  \"" + tmpFile.name + "\"" + ' -Wait'
    else:
        commandline= getRRSubmitterPath()+"  \""+tmpFile.name+"\""
        commandline= r"E:\programmierung\RoyalRender2020\project\_debug\bin\win64\rrSubmitter.exe"+"  \""+tmpFile.name+"\""

    if own_terminal:
        if sys.platform.lower().startswith("win"):
            commandline = 'START "rrSubmitter" CMD /C ' + commandline

    #writeInfo("Executing "+commandline)
    os.system(commandline)



###########################################
# OpenColorIO                             #
###########################################

def get_ocio_config_file(root_node):
    try:
        return os.environ['OCIO']
    except KeyError:
        pass

    current_config = root_node['OCIO_config'].value()

    if  current_config == 'custom':
        return root_node['customOCIOConfigPath'].value()

    nuke_exe_dir = os.path.dirname(sys.executable)

    config_path = os.path.join(nuke_exe_dir, "plugins", "OCIOConfigs", "configs", current_config)

    if os.path.isdir(config_path):
        config_file = os.path.join(config_path, "config.ocio")
        if os.path.isfile(config_file):
            return config_file.replace(nuke_exe_dir, "<rrBaseAppPath><isMac /MacOS>")

    config_file = config_path + ".ocio"
    if os.path.isfile(config_file):
        return config_file.replace(nuke_exe_dir, "<rrBaseAppPath><isMac /MacOS>")

    return ""




###########################################
# Read Nuke file                          #
###########################################

def rrSubmit_fillGlobalSceneInfo(newJob):
    root_node = nuke.root()

    newJob.version = nuke.NUKE_VERSION_STRING
    newJob.software = "Nuke"
    newJob.sceneOS = getOSString()
    newJob.sceneName = root_node.name()
    newJob.sceneDatabaseDir = root_node.knob("project_directory").getValue()
    newJob.seqStart = root_node.firstFrame()
    newJob.seqEnd = root_node.lastFrame()
    newJob.imageFileName = ""

    if nuke.usingOcio():
        newJob.ColorSpaceConfigFile = get_ocio_config_file(root_node)
        newJob.ColorSpace_View = root_node['monitorOutLUT'].value()

def rrSubmit_NukeXRequired():
    n = nuke.allNodes()
    for i in n:
        if (i.Class().find(".furnace.")>=0):
            return True
        if (i.Class().find("CameraTracker")>=0):
            return True
        if (i.Class().find("CopyCat")>=0):
            return True
    return False

def rrSubmit_addPluginLicenses(jobList):
    n = nuke.allNodes()
    plugins=""
    for i in n:
        if (i.Class().find(".sapphire.")>=0):
            plugins=plugins+"Sapphire;"
            break;
    for i in n:
        if (i.Class().find("pgBokeh")>=0):
            plugins=plugins+"pgBokeh;"
            break;
    for i in n:
        if (i.Class().find(".revisionfx.rsmb")>=0):
            plugins=plugins+"Reelsmart;"
            break;
    for i in n:
        if (i.Class().find(".myPlugin.")>=0):
            plugins=plugins+"MyPlugin;"
            break;
            
    if (rrSubmit_NukeXRequired()):
        plugins=plugins+"nukeX;"
        
    if (len(plugins)>0):
        for job in jobList:
            job.RequiredLicenses=plugins


def isGroup(node):
    gizmo = isinstance(node, nuke.Group)
    return gizmo

def isScriptedOutput(pathScripted, gizmo):
    pathScripted=pathScripted.lower()
    if ( (pathScripted.find("root.name")>=0) or (pathScripted.find("root().name")>=0) ):
        return True
    if (gizmo and (pathScripted.find("[value")>=0)):
        return True
    return False
       
        
def getAllWriteNodes():
    #nuke.allNodes() does not return nodes inside gizmos
    allNo=nuke.allNodes()
    writeNo=[]
    for gz in allNo:
        if isGroup(gz):
            with gz:
                gList = nuke.allNodes('Write') + nuke.allNodes('DeepWrite')
                for gnode in gList:
                    if (gnode['disable'].value()):
                        continue
                    pathScripted=gnode['file'].value()
                    if ((pathScripted== None) or (len(pathScripted)<3)):
                        continue                    
                    writeNo.append(gz)
                    break
    writeNo=writeNo+ nuke.allNodes('Write') + nuke.allNodes('DeepWrite')
    return writeNo
    

def rrSubmit_CreateAllJob(jobList, noLocalSceneCopy):
    newJob= rrJob()
    rrSubmit_fillGlobalSceneInfo(newJob)
    nList = getAllWriteNodes()
    mainNode = True
    nViews=nuke.views()
    useStereoFlag=False
    if (len(nViews)==2):
        useStereoFlag=True
        newJob.imageStereoR=nViews[0]
        newJob.imageStereoL=nViews[1]
        
    for node in nList:
        if (node['disable'].value()):
            continue
        pathScripted=""
        writeNode = node
        if isGroup(node):
            with node:
                gList = nuke.allNodes('Write') + nuke.allNodes('DeepWrite')
                for gnode in gList:
                    if (gnode['disable'].value()):
                        continue
                    pathScripted=gnode['file'].value()
                    if ((pathScripted== None) or (len(pathScripted)<3)):
                        continue
                    writeNode = gnode
                    if (isScriptedOutput(pathScripted,True)):
                        noLocalSceneCopy[0]=True
        else:
            pathScripted=writeNode['file'].value()
            if ((pathScripted== None) or (len(pathScripted)<3)):
                continue
        if (mainNode):
            if (writeNode['use_limit'].value()):
                newJob.seqStart = writeNode['first'].value()
                newJob.seqEnd = writeNode['last'].value()
                try:
                    newJob.seqStep = writeNode['frame_step'].value()
                except:
                    newJob.seqStep =1
            newJob.imageFileName= nuke.filename(writeNode)
            if (newJob.seqStart==newJob.seqEnd and (newJob.imageFileName.find("#")<0)):
                newJob.imageSingleOutput = True
            if (useStereoFlag):
                if (newJob.imageFileName.find("%V")>=0):
                    newJob.imageFileName = newJob.imageFileName.replace("%V","<Stereo>")
                elif (newJob.imageFileName.find("%v")>=0):
                    newJob.imageFileName = newJob.imageFileName.replace("%v","<Stereo>")
                    newJob.imageStereoR=newJob.imageStereoR[0]
                    newJob.imageStereoL=newJob.imageStereoL[0]
                else:
                    useStereoFlag=False

            try:
                data_type = writeNode['datatype'].value()
            except NameError:
                # No OCIO format
                pass
            else:
                if not writeNode['raw'].value() and writeNode['transformType'].value() == 'colorspace' and data_type in ('16 bit half', '32 bit float'):
                    newJob.ColorSpace = writeNode['colorspace'].value()

            mainNode = False
        else:
            newJob.maxChannels= newJob.maxChannels + 1
            if (useStereoFlag):
                newJob.channelFileName.append(nuke.filename(writeNode).replace("%V","<Stereo>").replace("%v","<Stereo>"))
            else:
                newJob.channelFileName.append(nuke.filename(writeNode).replace("%v",nViews[0][0]).replace("%V",nViews[0]))
            newJob.channelExtension.append("")
    
    if (len(newJob.imageFileName)==0):
        return

    if (not useStereoFlag):
        if ( (newJob.imageFileName.find("%V")>=0) or (newJob.imageFileName.find("%v")>=0)):
            for vn in range(1, len(nViews)):
                newJob.maxChannels= newJob.maxChannels + 1
                newJob.channelFileName.append(newJob.imageFileName.replace("%v",nViews[vn][0]).replace("%V",nViews[vn]))
                newJob.channelExtension.append("")
            newJob.imageFileName = newJob.imageFileName.replace("%v",nViews[0][0]).replace("%V",nViews[0])

    #if there is an .avi outout, place it as main output to RR knows that this job can only be send to one client at once
    for C in range(0, newJob.maxChannels):
        if (newJob.channelFileName[C].endswith(".avi") or newJob.channelFileName[C].endswith(".mov")):
            tempName=newJob.channelFileName[C]
            newJob.channelFileName[C]=newJob.imageFileName
            newJob.imageFileName=tempName
            break
    newJob.layer= "** All **"
    newJob.isActive = True
    jobList.append(newJob)


def rrSubmit_CreateSingleJobs_Node(jobList,noLocalSceneCopy, node):
        nViews=nuke.views()
        if (node['disable'].value()):
            return
        pathScripted=""
        writeNode = node
        writeNodeName = writeNode['name'].value()
        if isGroup(node):
            with node:
                gList = nuke.allNodes('Write') + nuke.allNodes('DeepWrite')
                for gnode in gList:
                    if (gnode['disable'].value()):
                        continue
                    pathScripted=gnode['file'].value()
                    if ((pathScripted== None) or (len(pathScripted)<3)):
                        continue
                    writeNode = gnode
                    if (isScriptedOutput(pathScripted,True)):
                        noLocalSceneCopy[0]=True
        else:
            pathScripted=writeNode['file'].value()
            if ((pathScripted== None) or (len(pathScripted)<3)):
                return
        newJob= rrJob()
        rrSubmit_fillGlobalSceneInfo(newJob)
        useStereoFlag=False
        if (len(nViews)==2):
            useStereoFlag=True
            newJob.imageStereoR=nViews[0]
            newJob.imageStereoL=nViews[1]
        if (writeNode['use_limit'].value()):
            newJob.seqStart = writeNode['first'].value()
            newJob.seqEnd = writeNode['last'].value()
            try: 
                newJob.seqStep = writeNode['frame_step'].value()
            except:
                newJob.seqStep =1
        newJob.imageFileName= nuke.filename(writeNode)
        if ((newJob.imageFileName== None) or  (len(newJob.imageFileName)<3)):
            return
        if (newJob.seqStart==newJob.seqEnd and (newJob.imageFileName.find("#")<0)):
            newJob.imageSingleOutput = True
            
        if (useStereoFlag):
            if (newJob.imageFileName.find("%V")>=0):
                newJob.imageFileName = newJob.imageFileName.replace("%V","<Stereo>")
            elif (newJob.imageFileName.find("%v")>=0):
                newJob.imageFileName = newJob.imageFileName.replace("%v","<Stereo>")
                newJob.imageStereoR=newJob.imageStereoR[0]
                newJob.imageStereoL=newJob.imageStereoL[0]
            else:
                useStereoFlag=False
        elif ( (newJob.imageFileName.find("%V")>=0) or (newJob.imageFileName.find("%v")>=0)):
            for vn in range(1, len(nViews)):
                newJob.maxChannels= newJob.maxChannels + 1
                newJob.channelFileName.append(newJob.imageFileName.replace("%v",nViews[vn][0]).replace("%V",nViews[vn]))
                newJob.channelExtension.append("")
            newJob.imageFileName = newJob.imageFileName.replace("%v",nViews[0][0]).replace("%V",nViews[0])
        newJob.layer= writeNodeName
        newJob.isActive = False
        jobList.append(newJob)


def rrSubmit_AreWriteNodesSelected():
    nList = getAllWriteNodes()
    nViews=nuke.views()
    for node in nList:
        if (node['selected'].value()==True):
            return True
    return False



def rrSubmit_CreateSingleJobs(jobList,noLocalSceneCopy, submitSelectedOnly):
    nList = getAllWriteNodes()
    nViews=nuke.views()
    for node in nList:
        if (node['disable'].value()):
            continue
        if (submitSelectedOnly and (node['selected'].value()==False)):
            continue        
        pathScripted=""
        writeNode = node
        writeNodeName = writeNode['name'].value()
        if isGroup(node):
            with node:
                gList = nuke.allNodes('Write') + nuke.allNodes('DeepWrite')
                for gnode in gList:
                    if (gnode['disable'].value()):
                        continue
                    pathScripted=gnode['file'].value()
                    if ((pathScripted== None) or (len(pathScripted)<3)):
                        continue
                    writeNode = gnode
                    if (isScriptedOutput(pathScripted,True)):
                        noLocalSceneCopy[0]=True
        else:
            pathScripted=writeNode['file'].value()
            if ((pathScripted== None) or (len(pathScripted)<3)):
                continue
        newJob= rrJob()
        rrSubmit_fillGlobalSceneInfo(newJob)
        useStereoFlag=False
        if (len(nViews)==2):
            useStereoFlag=True
            newJob.imageStereoR=nViews[0]
            newJob.imageStereoL=nViews[1]
        if (writeNode['use_limit'].value()):
            newJob.seqStart = writeNode['first'].value()
            newJob.seqEnd = writeNode['last'].value()
            try:
                newJob.seqStep = writeNode['frame_step'].value()
            except:
                newJob.seqStep =1
           
        newJob.imageFileName= nuke.filename(writeNode)
        if ((newJob.imageFileName== None) or  (len(newJob.imageFileName)<3)):
            continue
        if (newJob.seqStart==newJob.seqEnd and (newJob.imageFileName.find("#")<0)):
            newJob.imageSingleOutput = True
            
        if (useStereoFlag):
            if (newJob.imageFileName.find("%V")>=0):
                newJob.imageFileName = newJob.imageFileName.replace("%V","<Stereo>")
            elif (newJob.imageFileName.find("%v")>=0):
                newJob.imageFileName = newJob.imageFileName.replace("%v","<Stereo>")
                newJob.imageStereoR=newJob.imageStereoR[0]
                newJob.imageStereoL=newJob.imageStereoL[0]
            else:
                useStereoFlag=False
        elif ( (newJob.imageFileName.find("%V")>=0) or (newJob.imageFileName.find("%v")>=0)):
            for vn in range(1, len(nViews)):
                newJob.maxChannels= newJob.maxChannels + 1
                newJob.channelFileName.append(newJob.imageFileName.replace("%v",nViews[vn][0]).replace("%V",nViews[vn]))
                newJob.channelExtension.append("")
            newJob.imageFileName = newJob.imageFileName.replace("%v",nViews[0][0]).replace("%V",nViews[0])
        newJob.layer= writeNodeName
        newJob.isActive = False

        try:
            data_type = writeNode['datatype'].value()
        except NameError:
            # No OCIO format
            pass
        else:
            if not writeNode['raw'].value() and writeNode['transformType'].value() == 'colorspace' and data_type in ('16 bit half', '32 bit float'):
                newJob.ColorSpace = writeNode['colorspace'].value()

        jobList.append(newJob)

def getAllCopycatNodes():
    #nuke.allNodes() does not return nodes inside gizmos
    allNo=nuke.allNodes()
    writeNo=[]
    for gz in allNo:
        if isGroup(gz):
            with gz:
                gList = nuke.allNodes('CopyCat') 
                for gnode in gList:
                    if (gnode['disable'].value()):
                        continue
                    writeNo.append(gz)
                    break
    writeNo= writeNo + nuke.allNodes('CopyCat')
    return writeNo
    

def rrSubmit_CreateSingleJobs_Copycat(jobList,noLocalSceneCopy):
    nList = getAllCopycatNodes()
    nViews=nuke.views()
    for node in nList:
        if (node['disable'].value()):
            continue
        writeNode = node
        writeNodeName = writeNode['name'].value()
        if isGroup(node):
            with node:
                gList = nuke.allNodes('CopyCat')
                for gnode in gList:
                    if (gnode['disable'].value()):
                        continue
                    writeNode = gnode
                    if (isScriptedOutput(pathScripted,True)):
                        noLocalSceneCopy[0]=True
        newJob= rrJob()
        rrSubmit_fillGlobalSceneInfo(newJob)
        useStereoFlag=False
           
        newJob.imageFileName= node['dataDirectory'].value()
        if ((newJob.imageFileName== None) or  (len(newJob.imageFileName)<3)):
            continue
        newJob.imageFileName= newJob.imageFileName + "/execOnce.file"
        newJob.imageSingleOutput = True

        newJob.layer= writeNodeName
        newJob.isActive = True
        newJob.renderer= "Copycat"
        jobList.append(newJob)


def rrSubmit_Nuke_Copycat(own_terminal=False):
    print ("rrSubmit %rrVersion%")
    nuke.scriptSave()
    CompName = nuke.root().name()
    if ((CompName==None) or (len(CompName)==0)):
        writeError("Nuke comp not saved!")
        return
    jobList= []
    noLocalSceneCopy= [False]
    rrSubmit_CreateSingleJobs_Copycat(jobList,noLocalSceneCopy)
    submitOptions=""
    if (noLocalSceneCopy[0]):
        submitOptions=submitOptions+"AllowLocalSceneCopy=0~0 "
    submitOptions=submitOptions+" CONukeX=1~1 "
    rrSubmit_addPluginLicenses(jobList)
    submitJobsToRR(jobList, submitOptions, own_terminal=own_terminal)


def rrSubmit_CreateSingleJobs_shotgun(jobList,noLocalSceneCopy):
    modPath= getRR_Root()+"/plugins/python_modules"
    sys.path.append(modPath)
    import sgtk
    eng = sgtk.platform.current_engine()
    app = eng.apps["tk-nuke-writenode"]
    nList = app.get_write_nodes()
    nViews=nuke.views()
    for nod in nList:
        if (nod['disable'].value()):
            continue
        newJob= rrJob()
        rrSubmit_fillGlobalSceneInfo(newJob)
        useStereoFlag=False
        if (len(nViews)==2):
            useStereoFlag=True
            newJob.imageStereoR=nViews[0]
            newJob.imageStereoL=nViews[1]
        newJob.imageFileName= app.get_node_render_path(nod)
        if ((newJob.imageFileName== None) or  (len(newJob.imageFileName)<3)):
            continue
        if (newJob.seqStart==newJob.seqEnd and (newJob.imageFileName.find("#")<0)):
            newJob.imageSingleOutput = True
            
        if (useStereoFlag):
            if (newJob.imageFileName.find("%V")>=0):
                newJob.imageFileName = newJob.imageFileName.replace("%V","<Stereo>")
            elif (newJob.imageFileName.find("%v")>=0):
                newJob.imageFileName = newJob.imageFileName.replace("%v","<Stereo>")
                newJob.imageStereoR=newJob.imageStereoR[0]
                newJob.imageStereoL=newJob.imageStereoL[0]
            else:
                useStereoFlag=False
        elif ( (newJob.imageFileName.find("%V")>=0) or (newJob.imageFileName.find("%v")>=0)):
            for vn in range(1, len(nViews)):
                newJob.maxChannels= newJob.maxChannels + 1
                newJob.channelFileName.append(newJob.imageFileName.replace("%v",nViews[vn][0]).replace("%V",nViews[vn]))
                newJob.channelExtension.append("")
            newJob.imageFileName = newJob.imageFileName.replace("%v",nViews[0][0]).replace("%V",nViews[0])
        newJob.layer= app.get_node_name(nod)
        newJob.renderer= "shotgun"
        newJob.isActive = False
        jobList.append(newJob)



def rrSubmit_Nuke_Shotgun(own_terminal=False):
    print ("rrSubmit %rrVersion%")
    nuke.scriptSave()
    CompName = nuke.root().name()
    if ((CompName==None) or (len(CompName)==0)):
        writeError("Nuke comp not saved!")
        return
    jobList= []
    noLocalSceneCopy= [False]
    rrSubmit_CreateSingleJobs_shotgun(jobList,noLocalSceneCopy)
    submitOptions=""
    if (noLocalSceneCopy[0]):
        submitOptions=submitOptions+"AllowLocalSceneCopy=0~0 "
    if (rrSubmit_NukeXRequired()):
        submitOptions=submitOptions+" CONukeX=1~1 "
    rrSubmit_addPluginLicenses(jobList)
    submitJobsToRR(jobList, submitOptions, own_terminal=own_terminal)

      
def start_sg_nuke_engine():
    """
    Initialize Shotgun Toolkit from the given context
    path and start the engine. For more info check:
    https://support.shotgunsoftware.com/entries/95440797#Render%20Farm%20Integration%201
    returns: Nuke SGTK Instance
    """
    work_area_path= nuke.root().name()
    import sgtk
    tk = sgtk.sgtk_from_path(work_area_path)
    tk.synchronize_filesystem_structure()
    ctx = tk.context_from_path(work_area_path)
    # Attempt to start the engine for this context
    engine = sgtk.platform.start_engine('tk-nuke', tk, ctx)
    writeInfo('Shotgun Toolkit Nuke engine was initialized.')
    return engine   
    
    
def rrSubmit_Nuke_Shotgun_convert():
    print ("rrSubmit %rrVersion%")
    modPath= getRR_Root()+"/plugins/python_modules"
    sys.path.append(modPath)
    #test to import sgtk first 
    try:
        import sgtk
    except ImportError:
        writeInfo('Fail to import Shotgun Toolkit!') 
        
    nuke.scriptSave()
    
    #try save a new comp file before converting nodes
    CompName = nuke.root().name()
    if ((CompName==None) or (len(CompName)==0)):
        writeError("Nuke comp not saved!")
        return
    compFileNameOrg= nuke.root().name()     
    newPath= os.path.dirname(compFileNameOrg)
    newPath= newPath + "/rr/"
    if not os.path.exists(newPath):
        os.makedirs(newPath)    
    newFileName= newPath + os.path.basename(compFileNameOrg)
    nuke.scriptSaveAs(filename=newFileName, overwrite=1)
    
    #file saved, now convert nodes and save again
    eng = sgtk.platform.current_engine()
    app = eng.apps["tk-nuke-writenode"]
    app.convert_to_write_nodes()
    # For function implementation check:
    # https://github.com/shotgunsoftware/tk-nuke-writenode/blob/master/python/tk_nuke_writenode/handler.py  
    nuke.scriptSave()
        
    #default submit
    rrSubmit_Nuke()
    nuke.root().setModified(False)
    #Nuke does not open scripts in the same window any more. NO matter if changed or not, so close it
    nuke.scriptClose()

    nuke.scriptOpen(compFileNameOrg)
    


def rrSubmit_Nuke(own_terminal=False):
    print ("rrSubmit %rrVersion%")
    nuke.scriptSave()
    CompName = nuke.root().name()
    if ((CompName==None) or (len(CompName)==0)):
        writeError("Nuke comp not saved!")
        return
    jobList= []
    noLocalSceneCopy = [False]
    submitSelectedOnly = rrSubmit_AreWriteNodesSelected()
    if not submitSelectedOnly:
        rrSubmit_CreateAllJob(jobList, noLocalSceneCopy)
    rrSubmit_CreateSingleJobs(jobList, noLocalSceneCopy, submitSelectedOnly)
    submitOptions=""
    if (noLocalSceneCopy[0]):
        submitOptions=submitOptions+"AllowLocalSceneCopy=0~0 "
    if (rrSubmit_NukeXRequired()):
        submitOptions=submitOptions+" CONukeX=1~1 "
    rrSubmit_addPluginLicenses(jobList)
    submitJobsToRR(jobList, submitOptions, own_terminal=own_terminal)
          

def rrSubmit_Nuke_Node(node, startFrame=-1, endFrame=-1, nogui=False, own_terminal=False):
    print ("rrSubmit %rrVersion%")
    nuke.scriptSave()
    CompName = nuke.root().name()
    if ((CompName==None) or (len(CompName)==0)):
        writeError("Nuke comp not saved!")
        return
    jobList= []
    noLocalSceneCopy= [False]
    rrSubmit_CreateSingleJobs_Node(jobList,noLocalSceneCopy, node)
    submitOptions=""
    if (noLocalSceneCopy[0]):
        submitOptions=submitOptions+"AllowLocalSceneCopy=0~0 "
    if (rrSubmit_NukeXRequired()):
        submitOptions=submitOptions+" CONukeX=1~1 "
    rrSubmit_addPluginLicenses(jobList)
    if (startFrame>=0):
        for job in jobList:
            job.seqStart=startFrame
            job.seqEnd=endFrame
            writeInfo ("rrSubmit - override job sequence to " + str(job.seqStart) + "-" + str(job.seqEnd))
    submitJobsToRR(jobList, submitOptions, nogui=nogui, own_terminal=own_terminal)

