# Royal Render Plugin script for Nuke 5+
# Author: Royal Render, Holger Schoenberger, Binary Alchemy
# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy
# rrInstall_Copy: \plugins\
# rrInstall_Change_File_delete: \plugins\menu.py, before "# Help menu", "m =  menubar.addMenu(\"RRender\");\nm.addCommand(\"Submit Comp\", \"nuke.load('rrSubmit_Nuke_5'), rrSubmit_Nuke_5()\")\n\n"   
# rrInstall_Change_File_delete: \plugins\menu.py, before "# Help menu", "m =  menubar.addMenu(\"RRender\");\nm.addCommand(\"Submit Comp\", \"nuke.load('rrSubmit_Nuke_5'), rrSubmit_Nuke()\")\nm.addCommand(\"Submit Shotgun Nodes\", \"nuke.load('rrSubmit_Nuke_5'), rrSubmit_Nuke_Shotgun()\")\n\n"
# rrInstall_Change_File_delete: \plugins\menu.py, before "# Help menu", "m =  menubar.addMenu(\"RRender\");\nm.addCommand(\"Submit Comp\", \"nuke.load('rrSubmit_Nuke_5'), rrSubmit_Nuke()\")\nm.addCommand(\"Submit Shotgun Nodes (convert at renderfarm)\", \"nuke.load('rrSubmit_Nuke_5'), rrSubmit_Nuke_Shotgun()\")\nm.addCommand(\"Submit Shotgun Nodes (convert local)\", \"nuke.load('rrSubmit_Nuke_5'), rrSubmit_Nuke_Shotgun_convert()\")\n\n"
# rrInstall_Change_File:        \plugins\menu.py, before "# Help menu", "m =  menubar.addMenu(\"RRender\");\nm.addCommand(\"Submit Comp\", \"nuke.load('rrSubmit_Nuke_5'), rrSubmit_Nuke()\")\nm.addCommand(\"Submit Shotgun Nodes (convert at render time)\", \"nuke.load('rrSubmit_Nuke_5'), rrSubmit_Nuke_Shotgun()\")\nm.addCommand(\"Submit Shotgun Nodes (convert local)\", \"nuke.load('rrSubmit_Nuke_5'), rrSubmit_Nuke_Shotgun_convert()\")\n\n"

import nuke
import os
import sys
import string
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
        self.subE(jobElement, "SceneName", self.sceneName)
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
        self.subE(jobElement, "ImageFilename", self.imageFileName)
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

    
def submitJobsToRR(jobList, submitOptions, nogui=False, own_terminal=True):
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

    if own_terminal:
        if sys.platform.lower().startswith("win"):
            commandline = "START CMD /C {0}".format(commandline)

    #writeInfo("Executing "+commandline)
    os.system(commandline)



###########################################
# Read Nuke file                          #
###########################################

def rrSubmit_fillGlobalSceneInfo(newJob):
    newJob.version = nuke.NUKE_VERSION_STRING
    newJob.software = "Nuke"
    newJob.sceneOS = getOSString()
    newJob.sceneName = nuke.root().name()
    newJob.sceneDatabaseDir = nuke.root().knob("project_directory").getValue()
    newJob.seqStart = nuke.root().firstFrame()
    newJob.seqEnd = nuke.root().lastFrame()
    newJob.imageFileName = ""

def isGizmo(node):
    gizmo = isinstance(node, nuke.Gizmo)
    return gizmo

def isScriptedOutput(pathScripted, gizmo):
    pathScripted=pathScripted.lower()
    if ( (pathScripted.find("root.name")>=0) or (pathScripted.find("root().name")>=0) ):
        return True
    if (gizmo and (pathScripted.find("[value")>=0)):
        return True
    return False
    
        
def getAllWriteNodes():
    allNo=nuke.allNodes()
    writeNo=[]
    for gz in allNo:
        if isGizmo(gz):
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

    
    

def rrSubmit_CreateAllJob(jobList,noLocalSceneCopy):
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
        if isGizmo(node):
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
                    newJob.imageFileName = string.replace(newJob.imageFileName,"%V","<Stereo>")
                elif (newJob.imageFileName.find("%v")>=0):
                    newJob.imageFileName = string.replace(newJob.imageFileName,"%v","<Stereo>")
                    newJob.imageStereoR=newJob.imageStereoR[0]
                    newJob.imageStereoL=newJob.imageStereoL[0]
                else:
                    useStereoFlag=False
            mainNode = False
        else:
            newJob.maxChannels= newJob.maxChannels + 1
            if (useStereoFlag):
                newJob.channelFileName.append(string.replace(string.replace(nuke.filename(writeNode),"%v","<Stereo>"),"%V","<Stereo>"))
            else:
                newJob.channelFileName.append(string.replace(string.replace(nuke.filename(writeNode),"%v",nViews[0][0]),"%V",nViews[0]))
            newJob.channelExtension.append("")

    if (not useStereoFlag):
        if ( (newJob.imageFileName.find("%V")>=0) or (newJob.imageFileName.find("%v")>=0)):
            for vn in range(1, len(nViews)):
                newJob.maxChannels= newJob.maxChannels + 1
                newJob.channelFileName.append(string.replace(string.replace(newJob.imageFileName,"%v",nViews[vn][0]),"%V",nViews[vn]))
                newJob.channelExtension.append("")
            newJob.imageFileName = string.replace(string.replace(newJob.imageFileName,"%v",nViews[0][0]),"%V",nViews[0])

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
        if isGizmo(node):
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
                newJob.imageFileName = string.replace(newJob.imageFileName,"%V","<Stereo>")
            elif (newJob.imageFileName.find("%v")>=0):
                newJob.imageFileName = string.replace(newJob.imageFileName,"%v","<Stereo>")
                newJob.imageStereoR=newJob.imageStereoR[0]
                newJob.imageStereoL=newJob.imageStereoL[0]
            else:
                useStereoFlag=False
        elif ( (newJob.imageFileName.find("%V")>=0) or (newJob.imageFileName.find("%v")>=0)):
            for vn in range(1, len(nViews)):
                newJob.maxChannels= newJob.maxChannels + 1
                newJob.channelFileName.append(string.replace(string.replace(newJob.imageFileName,"%v",nViews[vn][0]),"%V",nViews[vn]))
                newJob.channelExtension.append("")
            newJob.imageFileName = string.replace(string.replace(newJob.imageFileName,"%v",nViews[0][0]),"%V",nViews[0])
        newJob.layer= writeNodeName
        newJob.isActive = False
        jobList.append(newJob)




def rrSubmit_CreateSingleJobs(jobList,noLocalSceneCopy):
    nList = getAllWriteNodes()
    nViews=nuke.views()
    for node in nList:
        if (node['disable'].value()):
            continue
        pathScripted=""
        writeNode = node
        writeNodeName = writeNode['name'].value()
        if isGizmo(node):
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
                newJob.imageFileName = string.replace(newJob.imageFileName,"%V","<Stereo>")
            elif (newJob.imageFileName.find("%v")>=0):
                newJob.imageFileName = string.replace(newJob.imageFileName,"%v","<Stereo>")
                newJob.imageStereoR=newJob.imageStereoR[0]
                newJob.imageStereoL=newJob.imageStereoL[0]
            else:
                useStereoFlag=False
        elif ( (newJob.imageFileName.find("%V")>=0) or (newJob.imageFileName.find("%v")>=0)):
            for vn in range(1, len(nViews)):
                newJob.maxChannels= newJob.maxChannels + 1
                newJob.channelFileName.append(string.replace(string.replace(newJob.imageFileName,"%v",nViews[vn][0]),"%V",nViews[vn]))
                newJob.channelExtension.append("")
            newJob.imageFileName = string.replace(string.replace(newJob.imageFileName,"%v",nViews[0][0]),"%V",nViews[0])
        newJob.layer= writeNodeName
        newJob.isActive = False
        jobList.append(newJob)



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
                newJob.imageFileName = string.replace(newJob.imageFileName,"%V","<Stereo>")
            elif (newJob.imageFileName.find("%v")>=0):
                newJob.imageFileName = string.replace(newJob.imageFileName,"%v","<Stereo>")
                newJob.imageStereoR=newJob.imageStereoR[0]
                newJob.imageStereoL=newJob.imageStereoL[0]
            else:
                useStereoFlag=False
        elif ( (newJob.imageFileName.find("%V")>=0) or (newJob.imageFileName.find("%v")>=0)):
            for vn in range(1, len(nViews)):
                newJob.maxChannels= newJob.maxChannels + 1
                newJob.channelFileName.append(string.replace(string.replace(newJob.imageFileName,"%v",nViews[vn][0]),"%V",nViews[vn]))
                newJob.channelExtension.append("")
            newJob.imageFileName = string.replace(string.replace(newJob.imageFileName,"%v",nViews[0][0]),"%V",nViews[0])
        newJob.layer= app.get_node_name(nod)
        newJob.renderer= "shotgun"
        newJob.isActive = False
        jobList.append(newJob)



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
        
    if (len(plugins)>0):
        for job in jobList:
            job.RequiredLicenses=plugins

def rrSubmit_NukeXRequired():
    n = nuke.allNodes()
    for i in n:
        if (i.Class().find(".furnace.")>=0):
            return True
    return False






def rrSubmit_Nuke_Shotgun():
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
    submitJobsToRR(jobList,submitOptions)




def rrSubmit_Nuke():
    print ("rrSubmit %rrVersion%")
    nuke.scriptSave()
    CompName = nuke.root().name()
    if ((CompName==None) or (len(CompName)==0)):
        writeError("Nuke comp not saved!")
        return
    jobList= []
    noLocalSceneCopy= [False]
    rrSubmit_CreateAllJob(jobList,noLocalSceneCopy)
    rrSubmit_CreateSingleJobs(jobList,noLocalSceneCopy )
    submitOptions=""
    if (noLocalSceneCopy[0]):
        submitOptions=submitOptions+"AllowLocalSceneCopy=0~0 "
    if (rrSubmit_NukeXRequired()):
        submitOptions=submitOptions+" CONukeX=1~1 "
    rrSubmit_addPluginLicenses(jobList)
    submitJobsToRR(jobList,submitOptions)
      
      
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
    log.info('Shotgun Toolkit Nuke engine was initialized.')
    return engine   
    
def rrSubmit_Nuke_Shotgun_convert():
    print ("rrSubmit %rrVersion%")
    modPath= getRR_Root()+"/plugins/python_modules"
    sys.path.append(modPath)
    #test to import sgtk first 
    try:
        import sgtk
    except ImportError:
        log.info('Fail to import Shotgun Toolkit!') 
        
    nuke.scriptSave()
    
    #try save a new comp file before converting nodes
    CompName = nuke.root().name()
    if ((CompName==None) or (len(CompName)==0)):
        writeError("Nuke comp not saved!")
        return
    compFileNameOrg= nuke.root().name()     
    newPath= os.path.dirname(compFileNameOrg)
    newPath= newPath + "rr/"
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
    nuke.scriptOpen(compFileNameOrg)
    
    

def rrSubmit_Nuke_Node(node, startFrame=-1, endFrame=-1, nogui=False):
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
    submitJobsToRR(jobList,submitOptions,nogui)
    
