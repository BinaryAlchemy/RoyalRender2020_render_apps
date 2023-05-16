#python
# -*- coding: cp1252 -*-
######################################################################
#
# Royal Render Render script for Unreal Engine
# Author:  Antonio Ruocco, Paolo Acampora
# Last Change: %rrVersion%
#
# Copyright (c) Holger Schoenberger - Binary Alchemy
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
import os


def all_forward_slashes(filepath):
    return os.path.normpath(filepath).replace('\\', '/')


def set_custom_seq_range(configuration, start, end):
    out_settings = configuration.get_all_settings()
    
    # ALL SETTINGS contain output, format, and other setting classes        
    for setting in out_settings:
        if isinstance(setting, unreal.MoviePipelineOutputSetting):
            setting.use_custom_playback_range = True

            setting.custom_start_frame = start
            setting.custom_end_frame = end
            
            return
    
    raise Exception("Settings Not Found")


def get_img_ext_class(img_ext):
    img_ext = img_ext.lower().strip(".")

    if img_ext == "png":
        return unreal.MoviePipelineImageSequenceOutput_PNG
    
    if img_ext == "jpg":
        unreal.log_warning("Unreal Enging saves JPG outputs with a '.jpeg' extension")
        img_ext = "jpeg"

    if img_ext == "jpeg":
        return unreal.MoviePipelineImageSequenceOutput_JPG
    
    if img_ext == "exr":
        return unreal.MoviePipelineImageSequenceOutput_EXR

    if img_ext == "bmp":
        return unreal.MoviePipelineImageSequenceOutput_BMP
    
    unreal.log_warning(f"Image extension '{img_ext}' not found")
             

@unreal.uclass()
class MoviePipelineRoyalExecutor(unreal.MoviePipelinePythonHostExecutor):
    
    activeMoviePipeline = unreal.uproperty(unreal.MoviePipeline)
    _is_rendering = False

    seq_start = 0
    seq_end = 10

    img_width = 0
    img_height = 0

    img_pad = 4
    img_ext = None

    def execute_render(self, map_path, seq_path, preset_path):
        self.pipelineQueue = unreal.new_object(unreal.MoviePipelineQueue, outer=self)
        job = self.pipelineQueue.allocate_new_job(unreal.MoviePipelineExecutorJob)
        
        job.job_name = 'RENDER_JOB'
        job.map = unreal.SoftObjectPath(map_path)
        job.sequence = unreal.SoftObjectPath(seq_path)
        
        preset = unreal.load_asset(preset_path)
        if not preset:
            raise Exception(f"Preset Not Found: {preset_path}")

        # Now we can configure the job. Calling find_or_add_setting_by_class is how you add new settings.
        try:
            outputSetting = next(setting for setting in preset.get_all_settings() if isinstance(setting, unreal.MoviePipelineOutputSetting))
        except StopIteration:
            outputSetting = preset.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)

        # Takes resolution from command line
        if self.img_width and self.img_height:
            outputSetting.output_resolution = unreal.IntPoint(self.img_width, self.img_height)

        outputSetting.file_name_format = self.img_name + "{frame_number}"
        outputSetting.output_directory.path = self.out_dir
        outputSetting.zero_pad_frame_numbers = self.img_pad
        
        img_class = get_img_ext_class(self.img_ext)
        if img_class:
            preset.find_or_add_setting_by_class(img_class)

        set_custom_seq_range(preset, self.seq_start, self.seq_end)

        # Make sure all settings are filled
        preset.initialize_transient_settings()

        job.set_preset_origin(preset)     
        self.activeMoviePipeline = unreal.new_object(self.target_pipeline_class, outer=self.get_last_loaded_world(), base_type=unreal.MoviePipeline)

        # Register finish callback to exit Unreal
        self.activeMoviePipeline.on_movie_pipeline_finished_delegate.add_function_unique(self, "on_movie_pipeline_finished")

        self._is_rendering = True
        self.activeMoviePipeline.initialize(job)

    # We can override specific UFunctions declared on the base class with
    # this markup.
    @unreal.ufunction(override=True)
    def execute_delayed(self, inPipelineQueue):
        # This function is called once  the map has finished loading and the 
        # executor is instantiated.
        
        (cmdTokens, cmdSwitches, cmdParameters) = unreal.SystemLibrary.parse_command_line(unreal.SystemLibrary.get_command_line())

        map_full_path = cmdTokens[0]
        if map_full_path.startswith('/Game/'):
            map_relative_path = map_full_path
        else:
            map_relative_path = all_forward_slashes(map_full_path).split('/Content/', 1)[-1]
            map_relative_path = '/Game/' + map_relative_path
        
        map_relative_path, map_file_name = os.path.split(map_relative_path)
        map_name, _ = os.path.splitext(map_file_name)

        sequence = cmdParameters['rSeq']
        _, seq_name = os.path.split(sequence)

        # -MoviePipelineConfig is a UE argument and contains /Game/ already
        preset = cmdParameters['MoviePipelineConfig']
        _, preset_name = os.path.split(preset)

        self.img_name = cmdParameters['rOutName']

        self.seq_start = int(cmdParameters['rStart'])
        self.seq_end = int(cmdParameters['rEnd'])
        self.out_dir = cmdParameters['rOutFolder']

        self.img_pad = int(cmdParameters['rPad'])

        try:
            self.img_width = int(cmdParameters['rW'])
            self.img_height = int(cmdParameters['rH'])
        except KeyError:
            pass

        self.img_ext = cmdParameters['rExt']

        self.execute_render(
            map_path=f"{map_relative_path}/{map_name}.{map_name}",
            seq_path=f"/Game/{sequence}.{seq_name}",
            preset_path=f"{preset}.{preset_name}"
            )
      
    # This function is called every frame and can be used to do simple countdowns, checks, etc.
    @unreal.ufunction(override=True)
    def on_begin_frame(self):
        # Call super to process async socket messages.
        super(MoviePipelineRoyalExecutor, self).on_begin_frame()        

        if self.activeMoviePipeline:
            done_percentage = unreal.MoviePipelineLibrary.get_completion_percentage(self.activeMoviePipeline) * 100
            unreal.log(f"Progress: {done_percentage:.2f} %")

    @unreal.ufunction(override=True)
    def is_rendering(self):
        return self._is_rendering

    @unreal.ufunction(ret=None, params=[unreal.MoviePipeline, bool])
    def on_movie_pipeline_finished(self, inMoviePipeline, bSuccess):
        unreal.log("Finished rendering movie! Success: " + str(bSuccess))
        self.activeMoviePipeline = None
        self._is_rendering = False
        self.on_executor_finished_impl()
