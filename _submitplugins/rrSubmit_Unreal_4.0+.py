# Royal Render Plugin script for Unreal Engine 4
# Author: Royal Render, Antonio Ruocco, Paolo Acampora, Binary Alchemy
# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy


import copy
import os
import sys
import subprocess
import tempfile

from xml.etree.ElementTree import ElementTree, Element, SubElement

import unreal

# OS utils

def get_OS_String():
    if sys.platform.lower() in ("win32", "win64"):
        return "win"
    elif sys.platform.lower() == "darwin":
        return "osx"
    else:
        return "lx"


def get_rr_Root():
    if 'RR_ROOT' in os.environ: 
        return os.environ['RR_ROOT']

    if sys.platform.lower().startswith('win'):
        HCPath = "%RRLocationWin%"
    elif sys.platform.lower() == "darwin":
        HCPath = "%RRLocationMac%"
    else:
        HCPath = "%RRLocationLx%"
    if not HCPath.startswith("%"):
        return HCPath

    unreal.log_error("Royal Render Directory not found")


def launch_rr_submitter(tmpfile_name):
    rr_root = get_rr_Root()

    if not rr_root:
        unreal.log_error("Royal Render Directory not found")
        return

    if sys.platform.lower().startswith("win"):
        submitCMDs = ('{0}\\win__rrSubmitter.bat'.format(rr_root), tmpfile_name)
        submitCMDs = (r'E:\programmierung\RoyalRender2020\project\_debug\bin\win64\rrSubmitter.exe', tmpfile_name)
    elif sys.platform.lower() == "darwin":
        submitCMDs = ('{0}/bin/mac64/rrSubmitter.app/Contents/MacOS/rrSubmitter'.format(rr_root), tmpfile_name)
    else:
        submitCMDs = ('{0}/lx__rrSubmitter.sh'.format(rr_root), tmpfile_name)

    try:
        if not os.path.isfile(submitCMDs[0]):
            raise FileNotFoundError
        subprocess.Popen(submitCMDs, close_fds=True)
    except FileNotFoundError:
        unreal.log_error("rrSubmitter not found\n({0})".format(submitCMDs[0]))
        return False
    except subprocess.CalledProcessError:
        unreal.log_error("Error while executing rrSubmitter")
        return False
    
    return True


# job class

class rrJob:
    """Contains job properties and xml export methods """
    def __init__(self):
        self.clear()
    
    def clear(self):
        self.version = ""
        self.software = ""
        self.renderer = ""
        self.RequiredLicenses = ""
        self.sceneName = ""
        self.sceneDatabaseDir = ""
        self.seqStart = 17
        self.seqEnd = 45
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
        self.CustomProjectName  = ""
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
        self.subE(jobElement, "CustomProjectName", self.CustomProjectName)
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
    
def get_maps_sequence(registry):
    """Returns a dictionary of Maps and their Sequence"""
    
    world_class_name = unreal.Name('World')
    seq_class_name = unreal.Name('LevelSequence')
    filter = unreal.AssetRegistryDependencyOptions(True, True, True, True, True)

    maps_and_seqs = {}

    for asset in registry.get_all_assets():
        if not asset.object_path.__str__().startswith('/Game/'):
            continue

        if asset.asset_class != world_class_name:
            continue

        refs = registry.get_referencers(asset.package_name, filter)
        if len(refs) < 1:
            continue

        # list comprehension
        maps_and_seqs[str(asset.package_name)] = [str(r) for r in refs if unreal.EditorAssetLibrary.find_asset_data(r).asset_class == seq_class_name]
    
    return maps_and_seqs    

def get_seq_range(package_name):
    asset_data = unreal.EditorAssetLibrary.find_asset_data(package_name)
    seq_range = asset_data.get_asset().get_playback_range()

    # sostituisci con skip
    assert seq_range.has_start_value
    assert seq_range.has_end_value

    return seq_range.inclusive_start, seq_range.exclusive_end

def get_seq_imgext(img_protocol):
    img_type = img_protocol.to_tuple()[0]

    if img_type.endswith('.CompositionGraphCaptureProtocol'):
        composition_graph_capture = unreal.CompositionGraphCaptureProtocol().get_default_object()
        img_type = composition_graph_capture.get_editor_property('bCaptureFramesInHDR')
        
        if img_type is True:
            return ".exr"
        else:
            return ".png"
        
        pass
    elif img_type.endswith('.VideoCaptureProtocol'):
        return ".avi"
        pass
    else:
        img_type = img_type.split("_", -1)[-1]
        return "." + img_type.lower()
        pass
    # TODO

def is_video(img_protocol):
    img_type = img_protocol.to_tuple()[0]

    if img_type.endswith('.VideoCaptureProtocol'):
        return True
    else:
        return False

def replace_render_token(token):
    img_file_name = token.output_format

    img_file_name = img_file_name.replace("{world}", "<Scene>")
    img_file_name = img_file_name.replace("{frame}", "")
    return img_file_name


def submit_ue_jobs():
    sys_lib = unreal.SystemLibrary()

    ver = sys_lib.get_engine_version()
    ver = ver.split('-', 1)[0]
    registry = unreal.AssetRegistryHelpers.get_asset_registry()

    capture_default = unreal.AutomatedLevelSequenceCapture().get_default_object()
    
    img_protocol = capture_default.get_editor_property('ImageCaptureProtocolType')
    scene_settings = capture_default.settings
    image_dir_path = scene_settings.output_directory.path
    image_dir_path = sys_lib.convert_to_absolute_path(image_dir_path)

    prj_dir = sys_lib.get_project_directory()

    project_fpath = unreal.Paths().get_project_file_path()
    project_dir, project_fname = os.path.split(project_fpath)

    maps_seqs = get_maps_sequence(registry)

    base_job = rrJob()
    base_job.software = "Unreal Engine"
    base_job.version = ver
    base_job.sceneOS = get_OS_String()
    base_job.CustomProjectName = project_fname
    base_job.sceneDatabaseDir = prj_dir
    base_job.imageDir = image_dir_path    
    base_job.imageExtension = get_seq_imgext(img_protocol)
    base_job.imageFramePadding = scene_settings.get_editor_property('ZeroPadFrameNumbers')
    base_job.imageSingleOutput = is_video(img_protocol)
    base_job.imageFileName = replace_render_token(scene_settings)
    
    # TODO: if we are rendering passes we should add channels to the job and <channelname> to imagefilename

    jobs_list = []
    for map, sequenze in maps_seqs.items():
            for seq in sequenze:
                new_job = copy.deepcopy(base_job)
                new_job.sceneName = map
                new_job.layer = seq

                # TODO: if "Custom Start *" is enabled use those values
                start, end = get_seq_range(seq)
                new_job.seqStart = start
                new_job.seqEnd = end
                new_job.seqStep = 1  # Not sure?

                jobs_list.append(new_job)

    tmp_file = tempfile.NamedTemporaryFile(mode='w+b',
                                          prefix="rrSubmitUnreal_",
                                          suffix=".xml",
                                          delete=False)

    xmlObj= base_job.writeToXMLstart("")
    for rr_job in jobs_list:
        rr_job.writeToXMLJob(xmlObj)
    
    if base_job.writeToXMLEnd(tmp_file, xmlObj):
        launch_rr_submitter(tmp_file.name)
    else:
        unreal.log_error("Could not write submission file")


if __name__ == '__main__':
    submit_ue_jobs()


