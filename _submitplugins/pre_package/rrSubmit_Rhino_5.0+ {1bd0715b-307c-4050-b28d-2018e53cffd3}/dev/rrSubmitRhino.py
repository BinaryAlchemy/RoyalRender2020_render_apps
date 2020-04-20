import copy
import itertools
import logging
import os
import sys
import tempfile
from subprocess import call
from xml.etree.ElementTree import ElementTree, Element, SubElement

import Rhino
import System
import rhinoscript
import rhinoscriptsyntax as rs

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
    return rhinoscript.application.IsRunningOnWindows()


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
    """ returns the rrSubmitter filename """
    if isWin():
        rrSubmitter = "\\win__rrSubmitter.bat"
    else:
        rrSubmitter = "/bin/mac64/rrSubmitter.app/Contents/MacOS/startlocal.sh"
    return rrSubmitter


def getRRSubmitterConsole():
    """ returns the rrSubmitterconsole filename """
    if isWin():
        rrSubmitterConsole = "\\bin\\win64\\rrSubmitterconsole.exe"
    else:
        rrSubmitterConsole = "/bin/mac64/rrSubmitterConsole.app/Contents/MacOS/startlocal.sh"
    return rrSubmitterConsole


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
        self.imageFileName = ""
        self.imageFormat = ""
        self.imageFramePadding = 4
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
        self.software = "Rhino"
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


def questionDialog(msg, title):
    """Present a Choice Dialog with given message and title,
     return True if the Yes button is pressed

     invoked method changes according to Rhino version
    """
    try:
        ret = Rhino.UI.Dialogs.ShowMessage(msg, title,
                                           Rhino.UI.ShowMessageButton.YesNo,
                                           Rhino.UI.ShowMessageIcon.Question)
    except AttributeError:  # Rhino 5 API
        ret = Rhino.UI.Dialogs.ShowMessageBox(msg, title,
                                              System.Windows.Forms.MessageBoxButtons.YesNo,
                                              System.Windows.Forms.MessageBoxIcon.Question,
                                              System.Windows.Forms.MessageBoxDefaultButton.Button1)
        if ret == System.Windows.Forms.DialogResult.Yes:
            return True

        return False

    if ret == Rhino.UI.ShowMessageResult.Yes:
        return True

    return False


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

    tmpFile = open(tmpDir + os.sep + "rrTmpSubmitRhino.xml", "w")

    if rs.DocumentModified():
        if questionDialog("Save Scene?", "Document has changed"):
            rs.Command("_Save")

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


def getTotalFrames():
    """Return the duration in frames of the animation for the current View"""
    # tries to set an outrageously high frame number,
    # parses the "Number must be Smaller than x" reply message

    if Rhino.ApplicationSettings.AppearanceSettings.LanguageIdentifier != 1033:  # U.S. English
        LOGGER.warning("Animation properties only available with U.S. English locales")
        return 0

    rs.Command('_ViewFirstFrame')
    if rs.CommandHistory()[-42:-1] == "Unable to find viewport to play animation":
        # printed out when we are in a different camera or a new file
        return 0

    rs.Command('_-ViewFrameNumber 9999999999999999 !', 1)
    if rs.CommandHistory()[-26:-1] == "There is no frame to view":
        # printed out when there have never been animated views
        return 0

    out_msg = "Number must be"
    out_idx = rs.CommandHistory().rfind(out_msg)
    return rs.CommandHistory()[out_idx + len(out_msg):].split()[2]

    
def addJobChannel(job, filename, fileext, channelName, is_anim):
    channelName = channelName.replace(" ", "_")
    job.channelExtension.append(fileext)
    ch_name = "{0}.{1}".format(filename, channelName)
    
    if is_anim:
        ch_name += "."

    job.channelFileName.append(ch_name)
    job.maxChannels += 1


def addLegacyVraySettings(vray, view_frames, default_ext, job):
    import clr
    clr.AddReference("System.Xml")
    import System.Xml

    width = clr.Reference[System.Object]()
    height = clr.Reference[System.Object]()
    outfile = clr.Reference[System.Object]()
    is_anim = clr.Reference[System.Object]()
    is_alpha = clr.Reference[System.Object]()

    vray.GetRenderOutputSize(width, height)
    vray.GetSettingsParameterString("/SettingsOutput", "img_file", "string", outfile)
    vray.GetSettingsParameterBool("/SettingsOutput", "do_animation", is_anim)
    vray.GetSettingsParameterBool("/SettingsOutput", "img_separateAlpha", is_alpha)

    outpath = outfile.Value
    if view_frames > 0:  # Submit animation anyway if found
        is_anim.Value = True
    if not outpath:
        outpath = os.path.join("<SceneFolder>", "<SceneName>")
    filename, fileext = os.path.splitext(outpath)
    if not fileext:
        fileext = default_ext
    if is_anim.Value:
        filename += "."

    job.imageName = filename
    job.imageFormat = fileext
    job.imageWidth = width.Value
    job.imageHeight = height.Value

    # Save vray options to a temp file and read unexposed settings through xml
    tmpVOps = tempfile.NamedTemporaryFile(delete=False)
    vray.SaveVisopt(tmpVOps.name)
    xmldoc = System.Xml.XmlDocument()
    tmpVOps.close()
    xmldoc.Load(tmpVOps.name)
    os.unlink(tmpVOps.name)

    _vray_ver = xmldoc.SelectSingleNode("//vropt/Asset/plugin/vrayplugin")
    vray_ver = int(_vray_ver.GetAttributeNode("version").Value)

    channels = []
    if vray_ver < 8:
        vop_chans = xmldoc.SelectNodes(
            "//vropt/Asset[@url='/SettingsVFBChannels']//plugin/vrayplugin/parameters/parameter[@name='channel_names']"
        )
        channels = vop_chans.Item(0).GetElementsByTagName("entry")
    else:
        vop_vfbparams = xmldoc.SelectSingleNode(
            "//vropt/Asset[@url='/SettingsVFBChannels']//plugin/vrayplugin/parameters")

        child_enum = vop_vfbparams.GetEnumerator()
        while child_enum.MoveNext():
            child = child_enum.Current
            ch_name = child.GetAttributeNode("name").Value
            if ch_name.startswith("re_"):
                try:
                    enabled = int(child.InnerText)
                    if enabled == 0:
                        continue
                except ValueError:
                    continue

                addJobChannel(job, filename, fileext, ch_name[3:], is_anim.Value)

    vop_chans_other = xmldoc.SelectNodes(
        "//vropt/Asset[@url='/SettingsVFBChannels']//plugin/vrayplugin/parameters/parameter[@name='other_channels']"
    )

    channels_custom = vop_chans_other.Item(0).GetElementsByTagName("entry")

    if not filename.endswith("."):
        filename += "."

    for chan in itertools.chain(channels, channels_custom):
        if chan.InnerText == "RGB color":
            continue
        if chan.InnerText == "Alpha":
            is_alpha.Value = False  # No need to include Alpha again

        addJobChannel(job, chan.InnerText, is_anim)

    if is_alpha.Value:
        job.channelFileName.append("Alpha")
        job.maxChannels += 1

    if is_anim.Value:
        vop_frames = xmldoc.SelectSingleNode(
            "//vropt/Asset[@url='/SettingsOutput']/plugin/vrayplugin/parameters/parameter[@name='frames']")
        if vray_ver > 7 or vop_frames.GetAttribute('listType') == "none":
            seqStart = "0"
            seqEnd = str(view_frames)
        else:
            frames = vop_frames.SelectSingleNode("value/list")
            num_frames = frames.ChildNodes.Count
            if num_frames == 0:
                seqStart = "0"
                seqEnd = "0"
            else:
                seqStart = frames.FirstChild.InnerText
                seqEnd = frames.LastChild.InnerText
                frame_list = frames.ChildNodes
                if num_frames > 1:
                    fr_prev = int(seqStart)
                    fr = int(frame_list[1].InnerText)
                    step = fr - fr_prev

                    for i in xrange(2, num_frames):
                        # make sure we got the step right, render everything if we didn't
                        fr_prev = fr
                        fr = int(frame_list[i].InnerText)

                        if step != fr - fr_prev:
                            step = 1
                            print "Frame step is not costant," \
                                  " rendering all frames in range", "{0}-{1}".format(seqStart, seqEnd)
                            break

                    job.seqStep = step

        job.seqStart = seqStart
        job.seqEnd = seqEnd
    else:
        job.imageSingleOutput = True
        job.imageFramePadding = 0


def submitCurrentScene(multicam=False, console=False, default_ext=".tif"):
    """Harvest settings and invoke submitToRR "

    :param multicam: if True, a job for camera is submitted
    :param console: if True, don't show submission window
    :return: 0 == success, 1 == cancel; If no value is returned, success is assumed
    """
    jobs = [rrJob()]

    jobs[0].versionInfo = Rhino.RhinoApp.Version.Major
    jobs[0].sceneFilename = rhinoscript.document.DocumentPath()

    if jobs[0].versionInfo > 5:
        # DocumentPath is only the folder in Rhino 6
        jobs[0].sceneFilename = os.path.join(jobs[0].sceneFilename, rhinoscript.document.DocumentName())

    view_frames = getTotalFrames()

    vray_ops = "V-Ray for Rhino"
    if rhinoscript.application.DefaultRenderer() == vray_ops:
        jobs[0].renderer = "VRay"
        vray = rs.GetPlugInObject(vray_ops)

        try:
            # VRay Next API
            vray_scene = vray.Scene()
        except AttributeError:
            # older version
            addLegacyVraySettings(vray, view_frames, default_ext, jobs[0])
        else:
            param = vray_scene.Plugin("/SettingsOutput").Param("img_width")
            width = param.Value()

            param = vray_scene.Plugin("/SettingsOutput").Param("img_height")
            height = param.Value()

            param = vray_scene.Plugin("/SettingsOutput").Param("img_file")
            outpath = param.Value()

            param = vray_scene.Plugin("/SettingsOutput").Param("do_animation")
            do_anim = param.Value()

            if not outpath:
                outpath = os.path.join("<SceneFolder>", "<SceneName>")

            filename, fileext = os.path.splitext(outpath)
            if not fileext:
                fileext = default_ext
            if do_anim:
                filename += "."

            jobs[0].imageName = filename
            jobs[0].imageFormat = fileext
            jobs[0].imageWidth = width
            jobs[0].imageHeight = height

            add_alpha = vray_scene.Plugin("/SettingsOutput").Param("img_separateAlpha").Value()
            # channels
            if fileext == "exr" and vray_scene.Plugin("/SettingsOutput").Param("img_rawFile"):
                # multichannel
                pass
            else:
                channels = vray.Scene().PluginsByType("render_channel", True)
                for chan in channels:
                    chan_name = vray_scene.Plugin(chan.Name()).Param("name").Value()
                    addJobChannel(jobs[0], filename, fileext, chan_name, do_anim)

                    if chan_name == "Alpha":
                        add_alpha = False  # avoid double entry

            if add_alpha:
                addJobChannel(jobs[0], filename, fileext, "Alpha", do_anim)

            if do_anim:
                segment = vray_scene.Plugin("/SettingsOutput").Param("animation_time_segment").Value()
                if segment == 0:
                    seqStart = 0
                    seqEnd = view_frames
                elif segment == 1:
                    # frame range
                    seqStart = vray_scene.Plugin("/SettingsOutput").Param("frame_range_start").Value()
                    seqEnd = vray_scene.Plugin("/SettingsOutput").Param("frame_range_end").Value()

                jobs[0].seqStart = seqStart
                jobs[0].seqEnd = seqEnd
            else:
                jobs[0].imageSingleOutput = True
                jobs[0].imageFramePadding = 0

    else:
        # Rhino Render
        if view_frames == 0:
            jobs[0].imageSingleOutput = True
            jobs[0].imageFramePadding = 0
        else:
            jobs[0].seqStart = 0
            jobs[0].seqEnd = view_frames

        jobs[0].imageWidth, jobs[0].imageHeight = rhinoscript.document.RenderResolution()

    # default values
    if not jobs[0].imageName:
        jobs[0].imageDir = "<SceneFolder>"
        jobs[0].imageName = os.path.join("<SceneFolder>", "<SceneName>")
        if view_frames > 0:
            jobs[0].imageName += "."
    if not jobs[0].imageFormat:
        jobs[0].imageFormat = default_ext

    if isWin():
        jobs[0].osString = "win"
    else:
        jobs[0].osString = "mac"

    jobs[0].camera = rs.CurrentView()
    outdir, outname = os.path.split(jobs[0].imageName)

    BonTools = rs.GetPlugInObject("Rhino Bonus Tools")
    if BonTools:  # add layers
        uppercase_states = []
        layer_states = BonTools.LayerStateNames()
        if layer_states:
            for state in layer_states:
                newJob = copy.deepcopy(jobs[0])
                newJob.layerName = state
                if any(x.isupper() for x in state):
                    if any(x.isupper() for x in state):
                        uppercase_states.append(state)
                if "<Layer>" not in newJob.imageName:
                    newJob.imageName = os.path.join(
                        os.path.dirname(newJob.imageName),
                        "<Layer>",
                        os.path.basename(newJob.imageName)
                    )

                jobs.append(newJob)

    if multicam:  # add cameras
        modified = rs.DocumentModified()  # we might have to restore this
        cam_jobs = []

        for camera in rs.NamedViews():
            # different views can have different frame ranges
            if camera == jobs[0].camera:
                continue

            rs.RestoreNamedView(camera)
            cam_frames = getTotalFrames()

            for job in jobs:
                newJob = copy.deepcopy(job)
                newJob.camera = camera
                if "<Camera>" not in newJob.imageName:
                    jobdir, jobimg = os.path.split(newJob.imageName)
                    newJob.imageName = os.path.join(jobdir, "<Camera>_" + jobimg)

                newJob.seqEnd = cam_frames
                if cam_frames == 0:  # camera job is singlefile
                    newJob.imageSingleOutput = True
                    newJob.imageFramePadding = 0
                    newJob.imageName = newJob.imageName.rstrip(".")
                    for i, chan in enumerate(job.channelFileName):
                        newJob.channelFileName[i] = chan.rstrip(".")
                else:
                    newJob.imageSingleOutput = False
                    newJob.imageFramePadding = 4
                    if not newJob.imageName.endswith("."):
                        newJob.imageName += "."
                    for i, chan in enumerate(job.channelFileName):
                        if not chan.endswith("."):
                            newJob.channelFileName[i] = chan + "."

                cam_jobs.append(newJob)

        jobs += cam_jobs

        rs.RestoreNamedView(jobs[0].camera)
        rs.DocumentModified(modified)

    if uppercase_states:
        msg = 'Layerstates have uppercase characters in their names' \
              '\n\nRender jobs cannot access uppercase names' \
              '\n\nChange layer states names to lowercase and save?'

        if questionDialog(msg, "Uppercase characters in name"):
            for state in uppercase_states:
                bonus_tools = rs.GetPlugInObject("Rhino Bonus Tools")
                bonus_tools.RenameLayerState(state, state.lower())
            rs.Command("_Save")

    result = submitToRR(jobs, useConsole=console, PID=None, WID=None)
    return 0 if result else 1
