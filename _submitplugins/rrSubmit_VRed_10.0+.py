#python
# -*- coding: cp1252 -*-
######################################################################
#
# Royal Render Plugin script for VRed
# Author:  Paolo Acampora
# Last change: %rrVersion%
# Copyright (c)  Holger Schoenberger - Binary Alchemy
# #win:     rrInstall_Copy: <USERPROFILE>\Documents\Autodesk\VRED-<ExeVersionMajor>.<ExeVersionMinor>\ScriptPlugins\
#
######################################################################

import copy
import logging
import os
import sys
import tempfile

from subprocess import call
from xml.etree.ElementTree import ElementTree, Element, SubElement
from PySide2 import QtWidgets

import vrController
import vrFileIO
import vrRenderSettings
import vrCamera
import vrScenegraph
import vrVariantSets
import vrVredUi

##############################################
# GLOBAL LOGGER                              #
##############################################

LOGGER = logging.getLogger('rrSubmit')
# reload plugin creates another handler, so remove all at script start
for h in list(LOGGER.handlers):
    LOGGER.removeHandler(h)
LOGGER.setLevel(logging.INFO)
# LOGGER.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
LOGGER.addHandler(ch)


##############################################
# GLOBAL FUNCTIONS                           #
##############################################
def isWin():
    return sys.platform.startswith("win")


def rrGetRR_Root():
    if 'RR_ROOT' in os.environ:
        return os.environ['RR_ROOT']
    HCPath = "%"
    if (sys.platform.lower() == "win32") or (sys.platform.lower() == "win64"):
        HCPath = "%RRLocationWin%"
    elif sys.platform.lower() == "darwin":
        HCPath = "%RRLocationMac%"
    else:
        HCPath = "%RRLocationLx%"
    if HCPath[0] != "%":
        return HCPath
    LOGGER.warning(
        "No RR_ROOT environment variable set!\n Please execute rrWorkstationInstaller and restart the machine.")
    return ""


def getRRSubmitter():
    """ return the rrSubmitter filename """
    if isWin():
        rrSubmitter = "\\win__rrSubmitter.bat"
    else:
        rrSubmitter = "/bin/mac64/rrSubmitter.app/Contents/MacOS/startlocal.sh"
    return rrSubmitter


def getRRSubmitterConsole():
    """ return the rrSubmitterconsole filename """
    if isWin():
        rrSubmitterConsole = "\\bin\\win64\\rrSubmitterconsole.exe"
    else:
        rrSubmitterConsole = "/bin/mac64/rrSubmitterConsole.app/Contents/MacOS/startlocal.sh"
    return rrSubmitterConsole


def vredMainWindow(id):
    from shiboken2 import wrapInstance
    return wrapInstance(id, QtWidgets.QMainWindow)

##############################################
# JOB CLASS                                  #
##############################################

class rrJob(object):
    """Contains the submission settings
    """

    def __init__(self):
        self.clear()

    def clear(self):
        # Set default values
        self.camera = ""
        self.channel = ""
        self.channelExtension = []
        self.channelFileName = []
        self.CustomA = ""
        self.CustomB = ""
        self.CustomC = ""
        self.imageDir = ""
        self.ImageStereoR = "Right"
        self.ImageStereoL = "Left"
        self.imageFormat = ""
        self.imageFramePadding = 5
        self.imageHeight = 99
        self.imageName = ""
        self.imagePreNumberLetter = ""
        self.imageSingleOutput = False
        self.imageWidth = 99
        self.isActive = False
        self.isTiledMode = False
        self.layer = ""
        self.layerName = ""
        self.LocalTexturesFile = ""
        self.maxChannels = 0
        self.osString = ""
        self.preID = ""
        self.renderer = ""
        self.RequiredLicenses = ""
        self.sceneDatabaseDir = ""
        self.sceneName = ""
        self.sceneOS = ""
        self.sendAppBit = ""
        self.seqEnd = 0
        self.seqFileOffset = 0
        self.seqFrameSet = ""
        self.seqStart = 0
        self.seqStep = 1
        self.software = "VRed"
        self.versionInfo = ""
        self.sceneFilename = ""
        self.waitForPreID = ""

    def indent(self, elem, level=0):
        """Formats the "elem" xml element with correct indentation
        ( from infix.se (Filip Solomonsson) )

        :param elem: xml element to format
        :param level: starting indentation
        :return: success
        """
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

    @staticmethod
    def subE(parent, tag, text):
        """Create sub-element of element 'r',
        tags it with 'e' and assign text 'e'

        :param parent: parent element
        :param tag: sub-element tag
        :param text: sub-element text

        :return: sub-element
        """
        sub = SubElement(parent, tag)
        sub.text = str(text)
        return sub

    def writeToXMLstart(self):
        """Create root element for the submission xml

        :return: root element
        """
        rootElement = Element("rrJob_submitFile")
        rootElement.attrib["syntax_version"] = "6.0"
        self.subE(rootElement, "DeleteXML", "1")
        self.subE(rootElement, "decodeUTF8", "_")
        return rootElement

    def writeToXMLJob(self, rootElement):
        """Fill the xml with job settings

        :param rootElement: xml root element
        :return: success
        """

        # YOU CAN ADD OTHER NOT SCENE-INFORMATION PARAMETERS USING THIS FORMAT:
        # self.subE(rootElement,"SubmitterParameter","PARAMETERNAME=" + PARAMETERVALUE_AS_STRING)

        if self.isTiledMode:
            self.subE(rootElement, "SubmitterParameter", "TileFrame=0~0")
            self.subE(rootElement, "SubmitterParameter", "PPAssembleTiles=0~1")

        jobElement = self.subE(rootElement, "Job", "")
        self.subE(jobElement, "rrSubmitterPluginVersion", "%rrVersion%")
        self.subE(jobElement, "Camera", self.camera)
        self.subE(jobElement, "Channel", self.channel)
        self.subE(jobElement, "ImageExtension", self.imageFormat)
        self.subE(jobElement, "ImageFilename", self.imageName)
        self.subE(jobElement, "ImageStereoL", self.ImageStereoL)
        self.subE(jobElement, "ImageStereoR", self.ImageStereoR)
        self.subE(jobElement, "ImageFramePadding", self.imageFramePadding)
        self.subE(jobElement, "ImageHeight", int(self.imageHeight))
        self.subE(jobElement, "ImageWidth", int(self.imageWidth))
        self.subE(jobElement, "ImageSingleOutputFile", int(self.imageSingleOutput))
        self.subE(jobElement, "IsActive", self.isActive)
        self.subE(jobElement, "Layer", self.layerName)
        self.subE(jobElement, "Renderer", self.renderer)
        self.subE(jobElement, "SceneName", self.sceneFilename)
        self.subE(jobElement, "SceneOS", self.osString)
        self.subE(jobElement, "SeqEnd", self.seqEnd)
        self.subE(jobElement, "SeqStart", self.seqStart)
        self.subE(jobElement, "SeqStep", self.seqStep)
        self.subE(jobElement, "Software", self.software)
        self.subE(jobElement, "Version", self.versionInfo)
        for c in range(0, self.maxChannels):
            self.subE(jobElement, "ChannelFilename", self.channelFileName[c])
            self.subE(jobElement, "ChannelExtension", self.channelExtension[c])

        return True

    def writeToXMLEnd(self, f, rootElement):
        """Save rootElement to file f

        :param f: destination file
        :param rootElement: xml root element
        :return: success
        """
        xml = ElementTree(rootElement)
        self.indent(xml.getroot())

        if f is not None:
            xml.write(f, encoding="utf-8")
            LOGGER.debug("XML written to " + f.name)
            f.close()
        else:
            print("No valid file has been passed to the function")
            try:
                f.close()
            except:
                pass
            return False
        return True


##############################################
# RR SUBMIT                                  #
##############################################

def submitRR(filename):
    """ call rrSubmit and load the job settings file

    :param filename: xml file to submit
    """
    call(rrGetRR_Root() + getRRSubmitter() + " " + filename)
    return True


def submitRRConsole(filename, PID=None, WID=None):
    """ call rrSubmitterconsole and load the job settings file

    :param filename: xml file to submit
    :param PID: PreID, A value between 0 and 255. Each job gets the Pre ID attached as small letter to the main ID
    :param WID: WaitForPreID, When the job is received, the server checks for other jobs from the machine
    """
    if WID is not None:
        call(rrGetRR_Root() + getRRSubmitterConsole(), filename, "-PID", PID, "-WID", WID)
    elif PID is not None:
        call(rrGetRR_Root() + getRRSubmitterConsole(), filename, "-PID", PID)
    else:
        call(rrGetRR_Root() + getRRSubmitterConsole(), filename)
    return True

class SaveDialog(QtWidgets.QMessageBox):
    def __init__(self, parent=None):
        super(SaveDialog, self).__init__(parent)
        self.setText('Document has changed.')
        self.setInformativeText('Save Scene?')
        self.setIcon(QtWidgets.QMessageBox.Question)
        self.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)


def submitToRR(submitjobs, useConsole, PID=None, WID=None):
    """writes XML Job file into a temporary file, then loads it
    either into rrSubmitter or rrSubmitterconsole

    :param submitjobs: list of jobs to submit
    :param useConsole: use rrSubmitterconsole when True
    :param PID: PreID, A value between 0 and 255. Each job gets the Pre ID attached as small letter to the main ID
    :param WID: WaitForPreID, When the job is received, the server checks for other jobs from the machine
    :return: success
    """

    tmpDir = tempfile.gettempdir()
    xmlObj = submitjobs[0].writeToXMLstart()

    tmpFile = open(tmpDir + os.sep + "rrTmpSubmitVRed.xml", "w")

    # No documentModified() in the API, we'll check the window title
    mw = vredMainWindow(vrVredUi.getMainWindow())
    filetitle, _ = mw.windowTitle().rsplit(" - Autodesk", 1)

    if filetitle.endswith("*"):  # Document modified
        dialog = SaveDialog(mw)
        ret = dialog.exec_()
        if ret == QtWidgets.QMessageBox.Yes:
            vrFileIO.save(vrFileIO.getFileIOFilePath())

    # Send XML to RR Submitter
    for jobLyr in submitjobs:
        LOGGER.debug("submit job  " + str(jobLyr.imageName))
        jobLyr.writeToXMLJob(xmlObj)

    ret = submitjobs[0].writeToXMLEnd(tmpFile, xmlObj)
    if ret:
        LOGGER.debug("Job written to " + tmpFile.name)
    else:
        LOGGER.warning("There was a problem writing the job file to " + tmpFile.name)
        return False
    if useConsole:
        return submitRRConsole(tmpFile.name, PID, WID)
    else:
        return submitRR(tmpFile.name)


def submitCurrentScene(multicam=False, variants=False, stereo=False, console=False):
    """Harvest settings and invoke submitToRR "

    :param multicam: if True, a job for camera is submitted
    :param console: if True, don't show submission window
    :return: 0 == success, 1 == cancel; If no value is returned, success is assumed
    """
    print("rrSubmit %rrVersion%")
    jobs = [rrJob()]
    jobs[0].sceneFilename = vrFileIO.getFileIOFilePath()
    jobs[0].versionInfo = vrController.getVredVersion()
    jobs[0].camera = vrCamera.getActiveCameraNode().getName()

    filename, fileext = os.path.splitext(vrRenderSettings.getRenderFilename())

    is_anim = vrRenderSettings.getRenderAnimation()

    if is_anim:
        is_movie = bool(vrRenderSettings.getRenderAnimationFormat())
        if vrRenderSettings.getRenderUseClipRange() and not is_movie:  # clip range
            dlg = QtWidgets.QMessageBox()
            dlg.setText('"Use Clip Range" is selected')
            dlg.setInformativeText('Clip Range cannot be used in submission, Start and stop Frame will be used instead')
            dlg.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel)
            dlg.setIcon(QtWidgets.QMessageBox.Warning)
            ret = dlg.exec_()
            if ret == QtWidgets.QMessageBox.Cancel:
                print("Submission aborted")
                return

        jobs[0].seqStart = vrRenderSettings.getRenderStartFrame()
        jobs[0].seqEnd = vrRenderSettings.getRenderStopFrame()
        jobs[0].seqStep = vrRenderSettings.getRenderFrameStep()

        if is_movie:
            jobs[0].imageSingleOutput = True
            jobs[0].imageFramePadding = 0
    else:
        jobs[0].imageSingleOutput = True
        jobs[0].imageFramePadding = 0

    jobs[0].imageName = filename
    jobs[0].imageFormat = fileext
    jobs[0].imageWidth = vrRenderSettings.getRenderPixelWidth()
    jobs[0].imageHeight = vrRenderSettings.getRenderPixelHeight()

    if isWin():
        jobs[0].osString = "win"
    else:
        jobs[0].osString = "mac"

    if stereo:
        if not any(param in jobs[0].imageName for param in (["<Stereo>", "[Stereo]"])):
            jobdir, jobimg = os.path.split(jobs[0].imageName)
            jobs[0].imageName = os.path.join(jobdir, "<Stereo>", jobimg)
        if "[Stereo]" in jobs[0].imageName:
            jobs[0].imageName = jobs[0].imageName.replace("[Stereo]", "<Stereo>")

        leftjob = copy.deepcopy(jobs[0])
        leftjob.imageName = jobs[0].imageName.replace("<Stereo>", "<ImageStereoL>")
        jobs[0].imageName = jobs[0].imageName.replace("<Stereo>", "<ImageStereoR>")
        jobs.append(leftjob)

    if variants:
        var_jobs = []
        for job in jobs:
            if "<Layer>" not in job.imageName:
                jobdir, jobimg = os.path.split(job.imageName)
                lay_img_name = os.path.join(jobdir, "<Layer>", jobimg)

            varsets = vrVariantSets.getVariantSets()
            for varset in varsets:
                newJob = copy.deepcopy(job)
                newJob.layerName = varset
                newJob.imageName = lay_img_name
                var_jobs.append(newJob)

        jobs += var_jobs

    add_dash = is_anim and not is_movie

    if vrRenderSettings.getUseRenderPasses():
        channels = vrRenderSettings.getRenderPasses()

        if channels:
            # VRed does not render the main pass
            first_chan = channels.pop(0)

            for job in jobs:
                filename, fileext = os.path.splitext(job.imageName)

                job.channel = first_chan
                ch_base = "{0}-{1}"
                if add_dash:
                    ch_base += "-"

                job.imageName = ch_base.format(filename, "<Channel>")
                for chan in channels:
                    ch_name = ch_base.format(filename, chan)
                    job.channelFileName.append(ch_name)
                    job.channelExtension.append(fileext)
                    job.maxChannels += 1

            add_dash = False  # channels are dashed already

    if add_dash:
        for job in jobs:
            job.imageName += "-"

    if multicam:  # add cameras
        cam_jobs = []
        for node in vrScenegraph.getAllNodes():
            # different views can have different frame ranges
            if node.getType() != "UberCamera":
                continue

            camera = node.getName()
            if camera == jobs[0].camera:
                continue

            for job in jobs:
                newJob = copy.deepcopy(job)
                newJob.camera = camera
                if "<Camera>" not in newJob.imageName:
                    jobdir, jobimg = os.path.split(newJob.imageName)
                    newJob.imageName = os.path.join(jobdir, "<Camera>_" + jobimg)

                cam_jobs.append(newJob)

        jobs += cam_jobs

    submitToRR(jobs, useConsole=console, PID=None, WID=None)


class RRmenu():
    def __init__(self, main_win):
        self.mw = main_win

        self.stereobox = QtWidgets.QAction('enable stereo', main_win, checkable=True)
        self.cambox = QtWidgets.QAction('enable cameras', main_win, checkable=True)

        self.submitAction = QtWidgets.QAction(main_win.tr("Submit Job"), main_win)
        self.submitVarAction = QtWidgets.QAction(main_win.tr("Submit Job, select Variant States"), main_win)

        self.submitAction.triggered.connect(self.submit)
        self.submitVarAction.triggered.connect(self.submitVariants)

        self.menu = QtWidgets.QMenu(main_win.tr("RRender"), main_win)
        self.menu.addAction(self.stereobox)
        self.menu.addAction(self.cambox)
        self.menu.addAction(self.submitAction)
        self.menu.addAction(self.submitVarAction)

        # insert new menu before Help.
        actions = main_win.menuBar().actions()
        for action in actions:
            if action.text() == main_win.tr("&Help"):
                main_win.menuBar().insertAction(action, self.menu.menuAction())
                break

    def __del__(self):
        self.mw.menuBar().removeAction(self.menu.menuAction())

    def submit(self):
        submitCurrentScene(multicam=self.cambox.isChecked(), stereo=self.stereobox.isChecked() ,console=False)

    def submitVariants(self):
        # needs to be another function, or it won't be garbage collected
        submitCurrentScene(multicam=self.cambox.isChecked(), variants=True, stereo=self.stereobox.isChecked(), console=False)


rrMenu = RRmenu(vredMainWindow(VREDMainWindowId))
