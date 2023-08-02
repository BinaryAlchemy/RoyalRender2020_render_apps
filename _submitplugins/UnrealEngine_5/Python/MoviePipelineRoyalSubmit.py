# -*- coding: cp1252 -*-
######################################################################
#
# Royal Render Plugin script for Unreal Engine
# Authors:     Antonio Ruocco, Paolo Acampora
# Copyright (c)  Holger Schoenberger
#
# Last change: %rrVersion%
# 
######################################################################
#
#
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
    '{camera_name}': '<Camera>',
    '{sequence_name}': '<Layer>',
    '{date}': '<date yyyy.MM.dd>',
    '{year}': '<date yyyy>',
    '{month}': '<date MM>',
    '{day}': '<date MM>',
    '{output_width}': '<ImageWidth>',
    '{output_width}': '<ImageHeight>',
    '{output_resolution}': '<ImageHeight>',
    '{job_author}': '<UserName>',
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


def launch_rr_submitter(tmpfile_name, show_ui=True):
    rr_root = get_rr_Root()

    if not rr_root:
        unreal.log_error("Royal Render Directory not found")
        return

    if show_ui:
        submitter = "rrSubmitter"
    else:
        submitter = "rrSubmitterconsole"

    if sys.platform.lower().startswith("win"):
        if show_ui:
            submitCMDs = (f'{rr_root}\\win__{submitter}.bat', tmpfile_name)
        else:
            submitCMDs = (f'{rr_root}\\bin\\win64\{submitter}.exe', tmpfile_name)
    elif sys.platform.lower() == "darwin":
        submitCMDs = (f'{rr_root}/bin/mac64/{submitter}.app/Contents/MacOS/{submitter}', tmpfile_name)
    else:
        if show_ui:
            submitCMDs = (f'{rr_root}/lx__{submitter}.sh', tmpfile_name)
        else:
            submitCMDs = (f'{rr_root}/bin/lx64/{submitter}', tmpfile_name)

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
        self.seqStart = 0
        self.seqEnd = 1
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
        self.userName = ""
        self.shotName = ""
        self.seqName = ""
        self.versionName = ""

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
        self.subE(jobElement, "UserName", self.userName)
        self.subE(jobElement, "CustomSeQName", self.seqName)
        self.subE(jobElement, "CustomSHotName", self.shotName)
        self.subE(jobElement, "CustomVersionName", self.versionName)
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

    return seq_range.inclusive_start, seq_range.exclusive_end - 1


def get_section_start_frame_offset(section):
    sequence = section.get_sequence()
    if not sequence:
        return 0

    tick_res = sequence.get_tick_resolution()
    disp_rate = sequence.get_display_rate()

    disp_rate.numerator *= tick_res.denominator
    disp_rate.denominator *= tick_res.numerator

    params = section.get_editor_property("parameters")
    frame_offset = params.start_frame_offset.value

    return int(frame_offset * disp_rate.numerator / disp_rate.denominator)



def clean_up_game_path(game_path):
    if game_path.startswith("/Game/"):
        game_path = game_path[6:]
    
    return game_path


def get_job_sequence(ue_job):
    seq_asset_path = ue_job.sequence.to_tuple()[0]
    package_path_seq = seq_asset_path.rsplit('.', 1)[0]

    asset_data = unreal.EditorAssetLibrary.find_asset_data(package_path_seq)
    asset = asset_data.get_asset()

    return asset


def get_shot_tracks(ue_job):
    sequence = get_job_sequence(ue_job)
    return sequence.find_master_tracks_by_type(unreal.MovieSceneCinematicShotTrack)


def get_shot_sequences(ue_job):
    shot_tracks = get_shot_tracks(ue_job)

    if not shot_tracks:
        for info in ue_job.shot_info:
            yield info, None
    else:
        shot_sections = shot_tracks[0].get_sections()
        
        for info in ue_job.shot_info:
            yield info, next((sec for sec in shot_sections if sec.get_shot_display_name() == info.outer_name), None)


def get_track_range(track):
    sections = track.get_sections()
    if not sections:
        return 0, 0

    section = sections.pop()
    start = section.get_start_frame()
    end = section.get_end_frame()

    for section in sections:
        start = min(start, section.get_start_frame())
        end = min(end, section.get_end_frame())
    
    return start, end


def copy_output_settings(setting, ue_job, new_job_rr):
    # MoviePipelineOutputSetting contains Output path and range
    output_dir = setting.output_directory.path
    output_file = str(setting.file_name_format)
    
    zero_pad = setting.zero_pad_frame_numbers
    new_job_rr.imageFramePadding = zero_pad

    for UE_token, RR_token in UE_to_RR_tokens.items():
        output_file = output_file.replace(UE_token, RR_token)
        output_dir = output_dir.replace(UE_token, RR_token)

    output_file = output_file.replace('{frame_number}', '#'*new_job_rr.imageFramePadding)

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

        new_job_rr.seqEnd = setting.custom_end_frame - 1
    else: 
        asset_path_seq = ue_job.sequence.to_tuple()[0]
        package_path_seq = asset_path_seq.rsplit('.', 1)[0]
        seq_start_frame, seq_end_frame = get_seq_range(package_path_seq)

        new_job_rr.seqStart = seq_start_frame
        new_job_rr.seqEnd = seq_end_frame


def get_file_params(ue_job):
    file_params = unreal.MoviePipelineFilenameResolveParams()
    file_params.job = ue_job

    try:
        first_shot = ue_job.shot_info[1]
    except IndexError:
        pass
    else:
        file_params.shot_override = first_shot
    
    file_params.initialization_version = unreal.MoviePipelineLibrary().resolve_version_number(file_params)
    file_params.shot_override = None
    
    return file_params


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
        
        # the settings column is the job's movie pipeline preset
        preset = ue_job.get_preset_origin()
        if not preset:
            unreal.log_warning(f"job skipped because of missing settings: {ue_job.job_name}")
            continue

        preset_path = preset.get_path_name().rsplit('.', 1)[0]
        if preset_path.startswith('/Game'):
            preset_path = preset_path[6:]

        new_job_rr = copy.deepcopy(base_job_rr)
        new_job_rr.CustomPresetPath = preset_path
        new_job_rr.userName = ue_job.get_editor_property('author')

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

        split_shot_jobs = True
        submission_ui = True

        out_settings = ue_job.get_configuration().get_all_settings(include_disabled_settings=False)

        # ALL SETTINGS contain output, format, and other setting classes
        for setting in out_settings:
            if isinstance(setting, unreal.MoviePipelineConsoleVariableSetting):
                cvars = setting.console_variables
                try:
                    split_shot_jobs = not bool(cvars['RR_NO_SPLIT'])
                except KeyError:
                    pass
                try:
                    submission_ui = not bool(cvars['RR_NO_UI'])
                except KeyError:
                    pass

                continue

            if isinstance(setting, unreal.MoviePipelineOutputSetting):
                copy_output_settings(setting, ue_job, new_job_rr)
                continue

            class_name = setting.get_class().get_name()

            if class_name == 'MoviePipelineWaveOutput':
                new_job_rr.imageSingleOutput = True
                new_job_rr.imageExtension = ".wav"
                split_shot_jobs = False
                continue

            if 'ImageSequenceOutput' not in class_name:
                continue

            # ImageSequenceOutput class name contains the output format
            img_protocol = '.' + class_name.rsplit('_', 1)[-1].lower()
            new_job_rr.imageExtension = img_protocol.replace(".jpg", ".jpeg")
        
        job_sequence = get_job_sequence(ue_job)
        shot_tracks = job_sequence.find_master_tracks_by_type(unreal.MovieSceneCinematicShotTrack)
        if len(shot_tracks) > 1:
            unreal.log_warning(f"job {ue_job.job_name}'s sequence contains multiple shot tracks, that should not happen and only the first track will be checked")

        if split_shot_jobs:
            shot_sections = shot_tracks[0].get_sections() if shot_tracks else [] * len(ue_job.shot_info)
        else:
            shot_sections = []

        file_params = get_file_params(ue_job)

        new_job_rr.seqName = seq_asset_name
        movie_lib = unreal.MoviePipelineLibrary()

        if shot_sections:
            master_job = copy.deepcopy(new_job_rr)
            master_job.isActive = False
            master_job.shotName = "NoShot"

            master_job.imageFileName, file_args = movie_lib.resolve_filename_format_arguments(master_job.imageFileName, file_params)
            master_job.imageDir, file_args = movie_lib.resolve_filename_format_arguments(master_job.imageDir, file_params)

            master_job.imageFileName = master_job.imageFileName.replace(".{ext}", "")
            master_job.imageDir = master_job.imageDir.replace(".{ext}", "")

            rr_jobs.append(master_job)
        
        movie_utils = unreal.MovieSceneSectionExtensions()
        for info, section in get_shot_sequences(ue_job):
            if section:
                shot_start = section.get_start_frame()
                shot_end = section.get_end_frame() - 1

                if shot_start > new_job_rr.seqEnd:
                    continue

                if shot_end < new_job_rr.seqStart:
                    continue

                sequence = section.get_sequence()
                camera_track = next((t for t in sequence.get_master_tracks() if isinstance(t, unreal.MovieSceneCameraCutTrack)), None)
                if camera_track:
                    cam_start, cam_end = get_track_range(camera_track)
                    cam_start = movie_utils.get_parent_sequence_frame(section, cam_start, job_sequence)
                    cam_end = movie_utils.get_parent_sequence_frame(section, cam_end, job_sequence) - 1

                    shot_start = max(new_job_rr.seqStart, shot_start, cam_start)
                    shot_end = min(new_job_rr.seqEnd, shot_end, cam_end)
                else:
                    shot_start = max(new_job_rr.seqStart, shot_start)
                    shot_end = min(new_job_rr.seqEnd, shot_end)
            else:
                shot_start = new_job_rr.seqStart
                shot_end = new_job_rr.seqEnd

            # TODO: per shot preset override

            shot_job = copy.deepcopy(new_job_rr)
            shot_job.seqStart = shot_start
            shot_job.seqEnd = shot_end

            if split_shot_jobs:
                file_params.shot_override = info
            else:
                file_params.shot_override = None

            if '{frame_number_shot}' in shot_job.imageFileName:
                if section:
                    shot_job.seqFileOffset = -movie_utils.get_parent_sequence_frame(section, 0, job_sequence)
                else:
                    unreal.log_warning(f"no section found for shot {info.outer_name}, frame range might be incorrect")
                shot_job.imageFileName = shot_job.imageFileName.replace('{frame_number_shot}', '#'*shot_job.imageFramePadding)

            shot_job.imageFileName, file_args = movie_lib.resolve_filename_format_arguments(shot_job.imageFileName, file_params)
            shot_job.imageDir, file_args = movie_lib.resolve_filename_format_arguments(shot_job.imageDir, file_params)

            shot_job.imageFileName = shot_job.imageFileName.replace(".{ext}", "")
            shot_job.imageDir = shot_job.imageDir.replace(".{ext}", "")

            if file_params.shot_override:
                shot_job.camera = file_args.filename_arguments['camera_name']
                shot_job.shotName = file_args.filename_arguments['shot_name']

            shot_job.versionName = file_args.filename_arguments['version'].lstrip('v')

            shot_job.isActive = info.enabled
            rr_jobs.append(shot_job)

    if not rr_jobs:
        dialog = unreal.EditorDialog()
        dialog.show_message("No jobs found",
                            "No job found for submission. Please, make sure all job settings were saved: unreal ignores unsaved settings",
                            unreal.AppMsgType.OK)
        return
        
    # launch_rr_submitter

    tmp_file = tempfile.NamedTemporaryFile(mode='w+b',
                                        prefix="rrSubmitUnreal_",
                                        suffix=".xml",
                                        delete=False)

    xmlObj = base_job_rr.writeToXMLstart("")

    for rr_job in rr_jobs:
        rr_job.writeToXMLJob(xmlObj)

    if base_job_rr.writeToXMLEnd(tmp_file, xmlObj):
        launch_rr_submitter(tmp_file.name, show_ui=submission_ui)
    else:
        unreal.log_error("Could not write submission file") 


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
