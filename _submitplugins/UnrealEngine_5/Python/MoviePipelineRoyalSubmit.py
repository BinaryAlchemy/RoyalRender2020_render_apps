# Copyright Epic Games, Inc. All Rights Reserved.
import unreal

import copy
import os
import sys
import subprocess
import tempfile

from xml.etree.ElementTree import ElementTree, Element, SubElement


UE_to_RR_tokens = {
    '{level_name}': '<SceneName>',
    '{project_dir}': '<DataBase>',
    '{sequence_name}': '<Layer>',
    '{frame_number}': ''
    }


# rr utils

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
        self.CustomSequencePath = ""
        self.CustomPresetPath = ""
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
        self.subE(jobElement, "CustomSequencePath", self.CustomSequencePath)
        self.subE(jobElement, "CustomPresetPath", self.CustomPresetPath)
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


        # submitter_function_utils


def get_seq_range(package_name):
    asset_data = unreal.EditorAssetLibrary.find_asset_data(package_name)
    seq_range = asset_data.get_asset().get_playback_range()

    assert seq_range.has_start_value
    assert seq_range.has_end_value

    return seq_range.inclusive_start, seq_range.exclusive_end


def clean_up_game_path(game_path):
    if game_path.startswith("/Game/"):
        game_path = game_path[6:]
    
    return game_path


def submit_ue_jobs(queue):
    system_lib = unreal.SystemLibrary()

    unreal_ver = system_lib.get_engine_version().split('-', 1)[0]

    project_dir = system_lib.get_project_directory()
    project_fpath = unreal.Paths().get_project_file_path()
    project_fdir, project_fname = os.path.split(project_fpath)

    # attributes for all RR jobs
    base_job_rr = rrJob()
    base_job_rr.software = "Unreal Engine"
    base_job_rr.renderer = "MoviePipeline"
    base_job_rr.version = unreal_ver
    base_job_rr.sceneOS = get_OS_String()
    base_job_rr.CustomProjectName = project_fname
    base_job_rr.sceneDatabaseDir = project_dir
    base_job_rr.imageSingleOutput = ''
    base_job_rr.seqStep = 1

    rr_jobs = []

    # get Unreal Engine jobs
    ue_jobs = queue.get_jobs()

    # copy UE jobs to RR jobs
    for ue_job in ue_jobs:
        new_job_rr = copy.deepcopy(base_job_rr)

        # scene file
        map_asset_path = ue_job.map.to_tuple()[0].rsplit('.', 1)[0]
        map_asset_path = clean_up_game_path(map_asset_path)

        new_job_rr.CustomLevelDir = map_asset_path
        new_job_rr.sceneName = f"<DataBase>/Content/{map_asset_path}.umap"
        
        # sequence path
        seq_asset_path = ue_job.sequence.to_tuple()[0]
        seq_asset_path = clean_up_game_path(seq_asset_path)
        
        new_job_rr.CustomSequencePath, seq_asset_name = os.path.split(seq_asset_path)

        # sequence file
        seq_asset_name = seq_asset_name.rsplit('.', 1)[0]
        new_job_rr.layer = seq_asset_name

        # movie pipeline preset
        
        preset = ue_job.get_preset_origin()
        if not preset:
            # TODO: warn that job is skipped
            continue

        preset_path = preset.get_path_name().rsplit('.', 1)[0]
        if preset_path.startswith('/Game'):
            preset_path = preset_path[6:]

        new_job_rr.CustomPresetPath = preset_path

        out_settings = ue_job.get_configuration().get_all_settings()

        # ALL SETTINGS contain output, format, and other setting classes        
        for setting in out_settings:
            if isinstance(setting, unreal.MoviePipelineOutputSetting):
                # MoviePipelineOutputSetting contains Output path and range
                output_dir = setting.output_directory.path
                output_file = str(setting.file_name_format)
                
                zero_pad = setting.zero_pad_frame_numbers
                new_job_rr.imageFramePadding = zero_pad

                for UE_token, RR_token in UE_to_RR_tokens.items():
                    output_file = output_file.replace(UE_token, RR_token)
                    
                    output_dir = output_dir.replace(UE_token, RR_token)

                # output path
                new_job_rr.imageFileName = output_file
                new_job_rr.imageDir = output_dir 

                # output resolution
                output_res = setting.output_resolution
                new_job_rr.imageWidth = output_res.x
                new_job_rr.imageHeight = output_res.y

                # output range
                if setting.use_custom_playback_range:
                    custom_start_frame = setting.custom_start_frame
                    new_job_rr.seqStart = custom_start_frame

                    custom_end_frame = setting.custom_end_frame
                    new_job_rr.seqEnd = custom_end_frame    
                else: 
                    asset_path_seq = ue_job.sequence.to_tuple()[0]
                    package_path_seq = asset_path_seq.rsplit('.', 1)[0]
                    seq_start_frame, seq_end_frame = get_seq_range(package_path_seq)

                    new_job_rr.seqStart = seq_start_frame
                    new_job_rr.seqEnd = seq_end_frame
                    
            class_name = setting.get_class().get_name()
            if 'ImageSequenceOutput' not in class_name:
                continue

            # ImageSequenceOutput class name contains the output format
            img_protocol = '.' + class_name.rsplit('_', 1)[-1].lower()
            new_job_rr.imageExtension = img_protocol

        rr_jobs.append(new_job_rr)

    # launch_rr_submitter

    tmp_file = tempfile.NamedTemporaryFile(mode='w+b',
                                        prefix="rrSubmitUnreal_",
                                        suffix=".xml",
                                        delete=False)

    xmlObj = base_job_rr.writeToXMLstart("")

    for rr_job in rr_jobs:
        rr_job.writeToXMLJob(xmlObj)

    if base_job_rr.writeToXMLEnd(tmp_file, xmlObj):
        launch_rr_submitter(tmp_file.name)
    else:
        unreal.log_error("Could not write submission file") 


# Royal Render Executor
#
# Submits a job to Royal Render using the Render button from Movie Render Queue,
# Renders a sequence if loaded through  the commandline
#
# REQUIREMENTS:
#    Requires the "Python Editor Script Plugin" to be enabled in your project.
#
# USAGE:
#   Use the following command line argument to launch this:
#   UE4Editor-Cmd.exe <path_to_uproject> <map_name> -game
#                     -MoviePipelineLocalExecutorClass=/Script/MovieRenderPipelineCore.MoviePipelinePythonHostExecutor
#                     -ExecutorPythonClass=/Engine/PythonTypes.MoviePipelineRoyalExecutor
#                     -MyLevelSequence=<path_to_level_sequence>
#                     -MyMoviePreset=<path_to_movie_preset>
#                     -MyLevelDir=<path_to_map_directory>
#                     -windowed -resx=1280 -resy=720 -log
#   ie:
#   UE4Editor-Cmd.exe "E:\SubwaySequencer\SubwaySequencer.uproject" subwaySequencer_P -game -MoviePipelineLocalExecutorClass=/Script/MovieRenderPipelineCore.MoviePipelinePythonHostExecutor -ExecutorPythonClass=/Engine/PythonTypes.MoviePipelineRoyalExecutor -LevelSequence="/Game/Sequencer/SubwaySequencerMASTER.SubwaySequencerMASTER" -windowed -resx=1280 -resy=720 -log
#   "UnrealEditor-Cmd.exe" "D:\User\Documents\Unreal Projects\RoyalBlank\RoyalBlank.uproject" Minimal_Default -game -MoviePipelineLocalExecutorClass="/Script/MovieRenderPipelineCore.MoviePipelinePythonHostExecutor" -ExecutorPythonClass="/Engine/PythonTypes.MoviePipelineRoyalExecutor" -MyLevelSequence="MovieLevelSequence" -windowed -resx=1280 -resy=720 -log -MyMoviePreset="Pending_MoviePipelineMasterConfig" -MyLevelDir="StarterContent/Maps"
#


@unreal.uclass()
class MoviePipelineRoyalSubmit(unreal.MoviePipelinePythonHostExecutor):
    # We can override specific UFunctions declared on the base class with
    # this markup.
    @unreal.ufunction(override=True)
    def execute_delayed(self, inPipelineQueue):
        # This function is called once  the map has finished loading and the 
        # executor is instantiated.
        
        # The user pressed "Remote" in the MoviePipelineQue window: submit the jobs
        submit_ue_jobs(inPipelineQueue)

    @unreal.ufunction(override=True)
    def is_rendering(self):
        return False
