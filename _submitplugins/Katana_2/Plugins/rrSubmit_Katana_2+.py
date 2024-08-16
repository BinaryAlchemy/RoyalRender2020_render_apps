######################################################################
#
# Royal Render Plugin script for Katana
# Author:  Anno Schachner, Holger Schoenberger, Paolo Acampora
# Last change: %rrVersion%
#
######################################################################

import os
import sys
import errno
import logging
import tempfile
import datetime
import time
from functools import partial
from xml.etree.ElementTree import ElementTree, Element, SubElement

from Katana import FarmAPI, Callbacks, UI4, RenderingAPI, KatanaFile
from Katana import NodegraphAPI, NodeDebugOutput
import KatanaInfo


################ LOGGING ################

def writeInfo(msg):
    logger = logging.getLogger('RR_SUBMIT')
    logger.info(msg)


def writeError(msg):
    logger = logging.getLogger('RR_SUBMIT')
    logger.error(msg)


def writeWarning(msg):
    logger = logging.getLogger('RR_SUBMIT')
    logger.warning(msg)


def writeDebug(msg):
    logger = logging.getLogger('RR_SUBMIT')
    logger.debug(msg)


#########################################

def onStartup(**kwargs):
    """Add Menu Options"""
    FarmAPI.AddFarmPopupMenuOption('RR submit scene', initExport)
    FarmAPI.AddFarmPopupMenuOption('RR export locally and submit', partial(initExport, local_export=True))

    FarmAPI.AddFarmSettingString('rr_fileName')
    FarmAPI.AddFarmSettingString('rr_outputFolder', hints={'widget': 'assetIdInput',
                                                        'dirsOnly': 'true',
                                                        'acceptDir': 'true'})

    FarmAPI.AddFarmSettingNumber('rr_stepSize', 1)
    FarmAPI.AddFarmSettingNumber('rr_useYetiLic', hints={'widget': 'checkBox'})
    FarmAPI.AddFarmSettingString('rr_comment')


def get_local_path(farm_settings):
    """

    :param farm_settings: RR custom farm settings
    :return: (fileDir, fileName)
    """
    fileDir = farm_settings['rr_outputFolder']

    if not fileDir:
        UI4.Widgets.MessageBox.Warning('Missing output folder',
                                       'Please set <b>rr_outputFolder</b> path on RenderNode')

        writeDebug("exiting because of unset dir")
        return

    fileName = farm_settings['rr_fileName']
    if fileName == '':
        UI4.Widgets.MessageBox.Warning('Warning',
                                       'Please set <b>rr_fileName</b> output on RenderNode')

        writeDebug("exiting because of unset filename")
        return

    return fileDir, fileName


def export_scene_frames(rr_job, render_service):
    """Export scene for stand alon renderer (.rib, .ass, etc.). Exports one file per frame"""
    for current_frame in range(rr_job.seqStart, rr_job.seqEnd + 1):
        NodegraphAPI.SetCurrentTime(current_frame)

        out_file = rr_job.sceneName.replace("<FN4>", "{0:04d}".format(current_frame))
        NodeDebugOutput.WriteRenderOutputForRenderMethod(rr_job.render_method,
                                                         NodegraphAPI.GetNode(rr_job.renderNode),
                                                         render_service, filename=out_file)


def timerInit():
    return datetime.datetime.now()

def timerBreak(timerBefore, where):
    timerAfter= datetime.datetime.now()
    timerAfter= timerAfter-timerBefore
    writeInfo("   "+where+": "+str(timerAfter)+"  h:m:s.ms")
    return datetime.datetime.now()


def initExport(local_export=False):
    """Initialize export. local_export means that you export the .ass files on your machine,
    farm sends the .katana scene to the render farm.

    :param local_export: bool
    :return:
    """
    timerBefore= timerInit()
    writeInfo("RR Katana Submission plugin, %rrVersion%  - {0}".format("local export" if local_export else "farm"))
    render_node_attrs = FarmAPI.GetSortedDependencies()[-1]
    timerBefore=timerBreak(timerBefore, "GetSortedDependencies")
    current_filepath = FarmAPI.GetKatanaFileName()
    timerBefore=timerBreak(timerBefore, "GetKatanaFileName")
    
    if KatanaFile.IsFileDirty():
        result = UI4.Widgets.MessageBox.Warning('Unsaved Changes', 'Save your file', acceptText='Save',
                                                cancelText='Abort')
        if result == 0:  # Save
            KatanaFile.Save(current_filepath)
        else:  # Cancel
            return False
    timerBefore=timerBreak(timerBefore, "IsFileDirty")
    
    if not FarmAPI.IsSceneValid(FarmAPI.NODES_SELECTED):
        warning_msg = FarmAPI.GetWarningMessages()
        error_msg = FarmAPI.GetErrorMessages()

        detailed_text = "\n".join(error_msg)
        detailed_text += "\n"
        detailed_text = "\n".join(warning_msg)

        result = UI4.Widgets.MessageBox.Warning('Scene might be compromised',
                                                'Some validity checks have failed, do you want to submit anyway?',
                                                acceptText='Submit anyway',
                                                cancelText='Abort',
                                                detailedText=detailed_text)
        if result > 0:
            writeError("Abort due to failed Validity Check")
            return False
    timerBefore=timerBreak(timerBefore, "ValidScene")
    
    # create job
    newJob = RRJob()

    if not newJob.set_software(render_node_attrs.renderService, local_export):
        writeError("software info collection failed, aborting")
        return
    timerBefore=timerBreak(timerBefore, "set_software")
    
    if local_export:
        file_dir, file_name = get_local_path(render_node_attrs.customFarmSettings)
        newJob.set_local_scene_export(file_dir, file_name)
    else:
        newJob.sceneName = current_filepath
        
    timerBefore=timerBreak(timerBefore, "get path")

    writeDebug("dependency list: " + str(render_node_attrs))

    comment = render_node_attrs.customFarmSettings['rr_comment']

    if not newJob.set_output(render_node_attrs.outputs):
        writeError("no output path found, aborting")
        return
    if not newJob.set_framerange(render_node_attrs.frameRange):
        writeError("frame range not set or invalid, aborting")
        return

    newJob.sceneDatabaseDir = ""
    newJob.seqStep = render_node_attrs.customFarmSettings['rr_stepSize']
    newJob.seqFileOffset = 0
    newJob.seqFrameSet = ""
    newJob.imagePreNumberLetter = ""
    newJob.imageSingleOutput = False
    newJob.sceneOS = getOSString()
    newJob.camera = ""
    newJob.layer = render_node_attrs.nodeName
    newJob.isActive = False
    newJob.sendAppBit = ""
    newJob.preID = ""
    newJob.waitForPreID = ""
    if len(comment) > 0:
        newJob.CustomB = "comment: {}".format(comment)
    newJob.CustomC = ""
    newJob.LocalTexturesFile = ""
    newJob.rrSubmitVersion = "%rrVersion%"
    newJob.renderNode = render_node_attrs.nodeName
    timerBefore=timerBreak(timerBefore, "Job set")
    
    if local_export:
        # export stand alone scene (.rib, .ass, etc.)
        export_scene_frames(newJob, render_node_attrs.renderService)

    # write xml file
    job_export = JobFileExport(newJob)
    job_info_path = job_export.write_xml_file()

    # submit job
    cmd = '{0} "{1}"'.format(getRRSubmitterPath(), job_info_path)
    timerBefore=timerBreak(timerBefore, "End")
    os.system(cmd)


class RRJob(object):
    def __init__(self):
        self._local_scene_extension = ""
        self._local_render_method = ""
        self._image_size_set = False

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
        self.waitForPreID = ""
        self.CustomA = ""
        self.CustomB = ""
        self.CustomC = ""
        self.LocalTexturesFile = ""
        self.rrSubmitVersion = "%rrVersion%"
        self.packageSize = ""
        self.threadCount = ""
        self.renderNode = ""
        self.rendererVersionName = ""
        self.rendererVersion = ""

    @property
    def export_image_size(self):
        return self._image_size_set

    @property
    def render_method(self):
        return self._local_render_method

    def set_software(self, render_service, is_local, use_yeti=False):
        """Sets software, renderer and version

        :param render_service:
        :param is_local:
        :param use_yeti:
        :return: success
        """

        if not is_local:
            self.software = 'Katana'
            self.version = KatanaInfo.version

        if render_service == 'arnold':
            render_info = RenderingAPI.RendererInfo.GetPlugin('ArnoldRendererInfo')
            self.rendererVersion = render_info.getRegisteredRendererVersion().replace(".X", "")  # e.g. 5.3.X.X -> 5.3
            self.RequiredLicenses += 'Arnold;'

            if is_local:
                self._local_scene_extension = '.ass'
                self._local_render_method = render_info.getBatchRenderMethod().getChildByName('name').getValue()
                self.software = render_service  # 'arnold', that is
                self.version = self.rendererVersion
                self.rendererVersion = KatanaInfo.version
            else:
                self.renderer = render_service
        elif render_service == 'prman':
            self.RequiredLicenses += 'RenderMan;'
            render_info = RenderingAPI.RendererInfo.GetPlugin('PRManRendererInfo')
            self.rendererVersion = render_info.getRegisteredRendererVersion()
            if is_local:
                self._local_scene_extension = '.rib'
                self._local_render_method = render_info.getBatchRenderMethod().getChildByName('name').getValue()
                self.software = 'RenderMan'
                self.renderer = 'ProServer'
                self.version = self.rendererVersion
                self.rendererVersion = KatanaInfo.version
            else:
                self.renderer = 'RenderMan'
        elif render_service == 'dl':
            self.renderer = '3delight'
            self.RequiredLicenses = '3delight;'
            render_info = RenderingAPI.RendererInfo.GetPlugin('dlRendererInfo')
            delight_version = render_info.getRegisteredRendererVersion()

            self.rendererVersion = delight_version.split(" ", 1)[0]
            if is_local:
                self._local_scene_extension = '.rib'
                self._local_render_method = render_info.getBatchRenderMethod().getChildByName('name').getValue()
                self.software = 'RenderMan'
                self.version = self.rendererVersion
        elif render_service == 'vray':
            self.renderer = 'vray'
            self.RequiredLicenses = 'VRay;'
            render_info = RenderingAPI.RendererInfo.GetPlugin('VrayRendererInfo')
            vray_version_full = render_info.getRegisteredRendererVersion()
            ver_start = next(i for i, c in enumerate(vray_version_full) if c.isdigit())
            vray_version = vray_version_full[ver_start:].strip(")")

            if is_local:
                self._local_scene_extension = '.vrscene'
                self._local_render_method = render_info.getBatchRenderMethod().getChildByName('name').getValue()
                self.software = 'VRay_StdA'
                self.version = vray_version
                self.rendererVersion = KatanaInfo.version
                self.renderer = 'multifile'
            else:
                self.rendererVersion = vray_version
        elif render_service == 'Redshift':
            self.renderer = 'redshift'
            self.RequiredLicenses = 'Redshift;'
            render_info = RenderingAPI.RendererInfo.GetPlugin('RedshiftRendererInfo')

            self.rendererVersion = render_info.getRegisteredRendererVersion()

            if is_local:
                UI4.Widgets.MessageBox.Warning("Export aborted", "Redshift export not supported")
                return False
        else:
            UI4.Widgets.MessageBox.Warning("Submission aborted", "Unknown Renderer: '" + render_service + "'")
            return False

        self.rendererVersionName = self.renderer

        if use_yeti:
            self.RequiredLicenses += "Yeti;"

        return True

    def set_local_scene_export(self, file_dir, file_name):
        # check file/dir
        if not os.path.isdir(file_dir):
            if UI4.Widgets.MessageBox.Warning('Warning', 'Directory does not exist.\n' + file_dir + '\n\nCreate it?',
                                              acceptText='Yes', cancelText='No'):
                checkCreateFolder(file_dir)
            else:
                return False

        self.sceneName = os.path.join(file_dir, file_name) + '_<FN4>' + self._local_scene_extension

    def set_framerange(self, framerange):
        """Check given framerange and assign it for the job

        :param framerange: tuple or list containing (start, end)
        :return:
        """
        if framerange is None:
            UI4.Widgets.MessageBox.Warning('Warning', 'Add a valid framerange to the render node settings')
            # TODO: or get scene frame range when no farm range is set/enabled
            return False
        if framerange[1] <= framerange[0]:
            UI4.Widgets.MessageBox.Warning('Warning', 'Invalid framerange: START > END!')
            return False

        self.seqStart, self.seqEnd = (int(f) for f in framerange)
        return True

    def set_output(self, outputs):
        """Set image path from outputs list

        :param outputs: katana render outputs
        :return: success
        """
        image_filepath = None

        for output in outputs:
            if not output['enabled']:
                continue
            location = output['outputLocation']
            if location:
                image_filepath = location
                break  # TODO: multiple outputs

        if image_filepath:
            self.imageFileName, self.imageExtension = os.path.splitext(image_filepath)
            writeDebug("image:{0}\n extension:{1}".format(self.imageFileName, self.imageExtension))

            try:
                last_hash_char = self.imageFileName.rindex('#')
            except ValueError:
                writeInfo("No '#' found in image file name, frame padding left to default value of " + str(self.imageFramePadding))
            else:
                renderPadding = last_hash_char - next(i for i in range(last_hash_char, 0, -1) if self.imageFileName[i] != '#')
                self.imageFramePadding = renderPadding

            return True

        return False

    def set_stereo_settings(self):
        raise NotImplementedError  # TODO
        # self.imageStereoR = ""
        # self.imageStereoL = ""

    def set_image_size_settings(self):
        raise NotImplementedError  # TODO
        # self.imageWidth = 99
        # self.imageHeight = 99
        self._image_size_set = True

    def set_image_channels(self):
        raise NotImplementedError  # TODO
        # self.channel = ""
        # self.maxChannels = 0
        # self.channelFileName = []
        # self.channelExtension = []


class JobFileExport(object):
    def __init__(self, rr_job = None):
        self._rr_jobs = []

        self._additional_parameters = {}
        self._root_element = None
        self._export_file = None

        if rr_job:
            self.addJob(rr_job)

    def addJob(self, rr_job):
        self._rr_jobs.append(rr_job)

    def _init_temp_file(self):
        self._export_file = tempfile.NamedTemporaryFile(mode='w+b', prefix="rrSubmitKatana_", suffix=".xml", delete=False)

    def _indent_xml(self, elem, level=0):
        """from infix.se (Filip Solomonsson)"""
        i = "\n" + level * ' '
        if len(elem) > 0:
            if not elem.text or not elem.text.strip():
                elem.text = i + " "
            for e in elem:
                self._indent_xml(e, level + 1)
                if not e.tail or not e.tail.strip():
                    e.tail = i + " "
            if not e.tail or not e.tail.strip():
                e.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
        return True

    @staticmethod
    def _sub_e(parent, tag, text):
        sub = SubElement(parent, tag)
        if sys.version_info.major == 2:
            if type(text) == unicode:
                sub.text = text
            else:
                sub.text = str(text).decode("utf-8")
        else:
            sub.text = str(text)
        return sub

    def addSubmitterParameter(self, parameter_name, parameter_value):
        """ADD OTHER NOT SCENE-INFORMATION PARAMETERS USING THIS FORMAT:

        :param parameter_name: parameter name
        :param parameter_value: parameter value as string
        :return:
        """
        self._additional_parameters[parameter_name] = parameter_value

    def _writeToXMLstart(self, submit_options):
        rootElement = Element("rrJob_submitFile")
        rootElement.attrib["syntax_version"] = "6.0"
        self._sub_e(rootElement, "DeleteXML", "1")
        self._sub_e(rootElement, "SubmitterParameter", submit_options)

        for parameter_name, parameter_value in self._additional_parameters.items():
            self._sub_e(rootElement, "SubmitterParameter", "{0}={1}".format(parameter_name, parameter_value))

        self._root_element = rootElement

    def _writeToXMLJob(self):

        for rr_job in self._rr_jobs:
            jobElement = self._sub_e(self._root_element, "Job", "")
            self._sub_e(jobElement, "rrSubmitterPluginVersion", "%rrVersion%")
            self._sub_e(jobElement, "Software", rr_job.software)
            self._sub_e(jobElement, "Renderer", rr_job.renderer)
            self._sub_e(jobElement, "RequiredLicenses", rr_job.RequiredLicenses)
            self._sub_e(jobElement, "Version", rr_job.version)
            if len(rr_job.rendererVersionName) > 0:
                self._sub_e(jobElement, "customRenVer_" + rr_job.rendererVersionName, rr_job.rendererVersion)
            self._sub_e(jobElement, "Scenename", rr_job.sceneName)
            self._sub_e(jobElement, "SceneDatabaseDir", rr_job.sceneDatabaseDir)
            self._sub_e(jobElement, "IsActive", rr_job.isActive)
            self._sub_e(jobElement, "SeqStart", rr_job.seqStart)
            self._sub_e(jobElement, "SeqEnd", rr_job.seqEnd)
            self._sub_e(jobElement, "SeqStep", rr_job.seqStep)
            self._sub_e(jobElement, "SeqFileOffset", rr_job.seqFileOffset)
            self._sub_e(jobElement, "SeqFrameSet", rr_job.seqFrameSet)
            if rr_job.export_image_size:
                self._sub_e(jobElement, "ImageWidth", int(rr_job.imageWidth))
                self._sub_e(jobElement, "ImageHeight", int(rr_job.imageHeight))
            self._sub_e(jobElement, "ImageDir", rr_job.imageDir)
            self._sub_e(jobElement, "Imagefilename", rr_job.imageFileName)
            self._sub_e(jobElement, "ImageFramePadding", rr_job.imageFramePadding)
            self._sub_e(jobElement, "ImageExtension", rr_job.imageExtension)
            self._sub_e(jobElement, "ImageSingleOutput", rr_job.imageSingleOutput)
            self._sub_e(jobElement, "ImagePreNumberLetter", rr_job.imagePreNumberLetter)
            self._sub_e(jobElement, "ImageStereoR", rr_job.imageStereoR)
            self._sub_e(jobElement, "ImageStereoL", rr_job.imageStereoL)
            self._sub_e(jobElement, "SceneOS", rr_job.sceneOS)
            self._sub_e(jobElement, "Camera", rr_job.camera)
            self._sub_e(jobElement, "Layer", rr_job.layer)
            self._sub_e(jobElement, "Channel", rr_job.channel)
            self._sub_e(jobElement, "SendAppBit", rr_job.sendAppBit)
            self._sub_e(jobElement, "PreID", rr_job.preID)
            self._sub_e(jobElement, "WaitForPreID", rr_job.waitForPreID)
            self._sub_e(jobElement, "CustomA", rr_job.CustomA)
            self._sub_e(jobElement, "CustomB", rr_job.CustomB)
            self._sub_e(jobElement, "CustomC", rr_job.CustomC)
            self._sub_e(jobElement, "rrSubmitVersion", rr_job.rrSubmitVersion)
            self._sub_e(jobElement, "LocalTexturesFile", rr_job.LocalTexturesFile)
            self._sub_e(jobElement, "Rendernode", rr_job.renderNode)

            for c in range(0, rr_job.maxChannels):
                self._sub_e(jobElement, "ChannelFilename", rr_job.channelFileName[c])
                self._sub_e(jobElement, "ChannelExtension", rr_job.channelExtension[c])
            return True

    def _writeToXMLEnd(self, use_temp_file=True):
        """Write job xml to file and return file path

        :param use_temp_file:
        :return:
        """
        if use_temp_file:
            self._init_temp_file()

        xml = ElementTree(self._root_element)
        self._indent_xml(xml.getroot())

        if not self._export_file:
            writeError("No valid file has been passed to {0}".format(self.__class__.__name__))
            try:
                self._export_file.close()
            except Exception as e:
                writeWarning("Error", "Error while closing invalid file: " + str(e))
            return False
        else:
            xml.write(self._export_file)
            self._export_file.close()

        return self._export_file.name

    def write_xml_file(self, submitter_options=None):
        """Populate xml with job info, export to file and return the file path

        :param submitter_options: submission parameters
        :return: path of exported file
        """
        self._writeToXMLstart(submitter_options)
        self._writeToXMLJob()
        return self._writeToXMLEnd()


################################################################################
# global functions

def checkCreateFolder(filedir):
    if not os.path.exists(filedir):
        writeDebug("creating folder '%s'" % filedir)
        try:
            os.makedirs(filedir)  # throws errno.EEXIST if dir is just being created by others
        except OSError as e:
            writeError("Error: Unable to create folder '%s'" % filedir)
            if e.errno != errno.EEXIST:
                raise


def getOSString():
    platform = sys.platform.lower()
    if platform in ("win32", "win64"):
        return "win"
    if platform == "darwin":
        return "osx"

    return "lx"


def getRR_Root():
    if ('RR_ROOT' in os.environ):
        return os.environ['RR_ROOT'].strip("\r")

    platform = sys.platform.lower()

    # "%RRLocation[PLATFORM]%" is replaced with the actual path by the installer/updater
    if platform in ("win32", "win64"):
        HCPath = "%RRLocationWin%"
    elif platform == "darwin":
        HCPath = "%RRLocationMac%"
    else:
        HCPath = "%RRLocationLx%"

    if not os.path.isdir(HCPath):
        raise Exception("RR path not found: {0}"
                        "\nPerhaps this plugin was not installed via rrWorkstationInstaller!".format(HCPath))

    return HCPath


def getRRSubmitterPath():
    """Return the rrSubmitter filename """
    rrRoot = getRR_Root()

    platform = sys.platform.lower()
    if platform in ("win32", "win64"):
        rrSubmitter = os.path.join(rrRoot, "win__rrSubmitter.bat")
    elif platform == "darwin":
        rrSubmitter = os.path.join(rrRoot, "bin/mac64/rrSubmitter.app/Contents/MacOS/rrSubmitter")
    else:
        rrSubmitter = os.path.join(rrRoot, "lx__rrSubmitter.sh")

    if not os.path.isfile(rrSubmitter):
        raise Exception("rrSubmitter not found: " + rrSubmitter)

    return rrSubmitter


if __name__.startswith("__plugins"):  # example: __plugins3__.rrSubmit_Katana_2+
    Callbacks.addCallback(Callbacks.Type.onStartup, onStartup)
