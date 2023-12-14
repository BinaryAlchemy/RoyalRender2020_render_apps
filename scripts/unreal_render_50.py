#python
# -*- coding: cp1252 -*-
######################################################################
#
# Royal Render Render script for Unreal Engine
# Author:  Antonio Ruocco, Paolo Acampora
# Last Change: d9.0.06Unreal
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


# Store the executor globally so that Python can get the callbacks from it.
SUBSYSTEM_EXECUTOR = None
TICK_HANDLE = None


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


def get_shot_tracks(ue_job):
    seq_asset_path = ue_job.sequence.to_tuple()[0]
    package_path_seq = seq_asset_path.rsplit('.', 1)[0]

    asset_data = unreal.EditorAssetLibrary.find_asset_data(package_path_seq)
    asset = asset_data.get_asset()

    return asset.find_master_tracks_by_type(unreal.MovieSceneCinematicShotTrack)


def seq_range_matches(job, start, end):
    asset_path_seq = job.sequence.to_tuple()[0]
    package_name = asset_path_seq.rsplit('.', 1)[0]

    asset_data = unreal.EditorAssetLibrary.find_asset_data(package_name)
    seq_range = asset_data.get_asset().get_playback_range()

    if seq_range.inclusive_start != start:
        return False
    
    return seq_range.exclusive_end - 1 == end


def get_shot_sequences(ue_job):
    shot_tracks = get_shot_tracks(ue_job)

    if not shot_tracks:
        for info in ue_job.shot_info:
            yield info, None
    else:
        shot_sections = shot_tracks[0].get_sections()
        
        for info in ue_job.shot_info:
            yield info, next((sec for sec in shot_sections if sec.get_shot_display_name() == info.outer_name), None)


def disable_out_of_range_shots(job, start, end):
    num_shots = len(job.shot_info)
    if num_shots < 2:
        return

    shot_tracks = get_shot_tracks(job)
    if not shot_tracks:
        unreal.log_warning(f"Render job has {num_shots} shots but no shot track")
        return

    if len(shot_tracks) > 1:
        unreal.log_warning(f"Render job has {len(shot_tracks)} shot tracks, only the first is taken into account")

    shot_sections = shot_tracks[0].get_sections()
    if len(shot_sections) != num_shots:
        unreal.log_warning(f"Render job has {num_shots} shots but {len(shot_sections)} sections. Shots preceding {start} won't be disabled")

    matching_shot = None
    for info, section in get_shot_sequences(job):
        if not section:
            continue

        shot_start = section.get_start_frame()
        shot_end = section.get_end_frame()

        if shot_end <= start:
            info.enabled = False
            unreal.log(f"shot {info.outer_name} ends before first frame {start}, disabled")
        if shot_start >= end:
            unreal.log(f"shot {info.outer_name} starts after last frame {end}, disabled")
            info.enabled = False

        if shot_start == start and shot_end == end:
            unreal.log(f"shot {info.outer_name} matches job's start, end, no custom range required")
            matching_shot = info
    
    return matching_shot
 

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
    
    if img_ext == "mov":
        return unreal.MoviePipelineAppleProResOutput
    
    if img_ext == "mxf":
        return unreal.MoviePipelineAvidDNxOutput
    
    unreal.log_warning(f"Image extension '{img_ext}' not found")
             

@unreal.uclass()
class MoviePipelineRoyalExecutor(unreal.MoviePipelinePythonHostExecutor):
    
    activeMoviePipeline = unreal.uproperty(unreal.MoviePipeline)
    _is_rendering = False

    seq_start = 0
    seq_end = 0
    seq_offset = 0

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

        outputSetting.file_name_format = self.img_name + ("{frame_number_shot}" if self.seq_offset else "{frame_number}")
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
        self.seq_offset = int(cmdParameters['rOffset'])
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


class RenderArgs:
    def __init__(self, cmdParameters):
        self.img_width = int(cmdParameters['rW'])
        self.img_height = int(cmdParameters['rH'])
        self.seq_start = int(cmdParameters['rStart'])
        self.seq_end = int(cmdParameters['rEnd'])
        self.seq_offset = int(cmdParameters['rOffset'])
        self.img_name = cmdParameters['rOutName']

        self.img_folder = cmdParameters['rOutFolder']
        self.img_ext = cmdParameters['rExt']
        self.img_padding = int(cmdParameters['rPad'])
        try:
            self.anti_alias_mult = float(cmdParameters['rAA'])
        except KeyError:
            self.anti_alias_mult = 1.0
    
        self._cmdParameters = cmdParameters

        self.map_game_path = self.get_map_game_path()
        self.sequence_game_path = self.get_sequence_game_path()
        self.preset_path = self.get_preset_path()
        
        self._cmdParameters = None

        if self.img_name.endswith(".mov") or self.img_name.endswith(".mxf"):
            self.img_name, self.img_ext = os.path.splitext(self.img_name)

        unreal.log("Initialized job arguments:")
        unreal.log(f"\tpreset: {self.preset_path}")
        unreal.log(f"\tmap: {self.map_game_path}")
        unreal.log(f"\tsequence: {self.sequence_game_path}")

    def get_map_game_path(self):
        map_full_path = self._cmdParameters['rMap']
        if map_full_path.startswith('/Game/'):
            map_relative_path = all_forward_slashes(map_full_path)
        else:
            map_relative_path = all_forward_slashes(map_full_path).split('/Content/', 1)[-1]
            map_relative_path = '/Game/' + map_relative_path
        
        map_relative_path, map_file_name = os.path.split(map_relative_path)
        map_name, _ = os.path.splitext(map_file_name)

        return f"{map_relative_path}/{map_name}.{map_name}"

    def get_sequence_game_path(self):
        sequence_relative_path = self._cmdParameters['rSeq']
        _, seq_name = os.path.split(sequence_relative_path)
        return all_forward_slashes(f"/Game/{sequence_relative_path}.{seq_name}")

    def get_preset_path(self):
        preset = self._cmdParameters['MoviePipelineConfig']
        _, preset_name = os.path.split(preset)
        return all_forward_slashes(f"{preset}.{preset_name}")


def on_queue_finished_callback(executor, success):
    unreal.log("Render completed. Success status: " + str(success))
    unreal.SystemLibrary.quit_editor()


def on_individual_job_finished_callback(params):
    unreal.log("single job completed")


def on_individual_shot_finished_callback(params):
    unreal.log("job shot completed")


def on_executor_error(is_fatal, error_text):
    unreal.log(f"Got {'non' if not is_fatal else ''} error: {error_text}")


class RenderCommander(RenderArgs):
    def __init__(self):
        cmdTokens, cmdSwitches, cmdParameters = unreal.SystemLibrary.parse_command_line(unreal.SystemLibrary.get_command_line())
        super().__init__(cmdParameters)

        self.preset = unreal.load_asset(self.preset_path)
        if not self.preset:
            raise Exception(f"Preset Not Found: {self.preset_path}")
    
    def override_global_TAA(self):
        aa_samples = unreal.SystemLibrary.get_console_variable_int_value('r.TemporalAASamples')

        if aa_samples == 0:
            unreal.log_warning("'r.TemporalAASamples' variable not found")
            return
        
        new_samples = max(1, int(aa_samples * self.anti_alias_mult))
        unreal.SystemLibrary.execute_console_command(None, f"r.TemporalAASamples {new_samples}")
        unreal.log(f"r.TemporalAASamples changed from {aa_samples} to {unreal.SystemLibrary.get_console_variable_int_value('r.TemporalAASamples')}")

    def overide_AASettings_samples(self):
        aa_setting = self.preset.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
        
        aa_samples = aa_setting.temporal_sample_count
        if (aa_samples == 1 and aa_setting.spatial_sample_count == 1):
            # aa_setting has default value, using r.TemporalAASamples
            aa_samples = unreal.SystemLibrary.get_console_variable_int_value('r.TemporalAASamples')

        new_samples = max(1, int(aa_samples * self.anti_alias_mult))
        if new_samples == aa_samples:
            unreal.log_warning(f"Preset's TemporalAASamples not changed from {aa_samples}")
            return

        aa_setting.temporal_sample_count = new_samples
        unreal.log(f"Preset's TemporalAASamples changed from {aa_samples} to {aa_setting.temporal_sample_count}")

        if not aa_setting.override_anti_aliasing and self.anti_alias_mult > 1.0:
            # if still relying on project's TAA, we make sure that r.TemporalAASamples is increased as well
            self.override_global_TAA()

    def create_out_setting(self):
        try:
            output_setting = next(setting for setting in self.preset.get_all_settings() if isinstance(setting, unreal.MoviePipelineOutputSetting))
        except StopIteration:
            output_setting = self.preset.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)

        output_setting.output_resolution = unreal.IntPoint(self.img_width, self.img_height)

        if self.anti_alias_mult != 1.0:
            self.overide_AASettings_samples()

        if output_setting.file_name_format[-4:] in (".wav", ".mov", ".mxf", ""):
            output_setting.file_name_format = self.img_name[:-4]
        else:
            output_setting.file_name_format = self.img_name + ("{frame_number_shot}" if self.seq_offset else "{frame_number}")
        unreal.log(f"Rendering with filename: {output_setting.file_name_format}")

        output_setting.output_directory.path = self.img_folder
        output_setting.zero_pad_frame_numbers = self.img_padding

        return output_setting
    
    def render_new_queue(self):
        subsystem = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
        pipelineQueue = subsystem.get_queue()

        job = pipelineQueue.allocate_new_job(unreal.MoviePipelineExecutorJob)
        job.job_name = 'RENDER_JOB'
        job.map = unreal.SoftObjectPath(self.map_game_path)
        job.sequence = unreal.SoftObjectPath(self.sequence_game_path)
        
        output_setting =  self.create_out_setting()

        img_class = get_img_ext_class(self.img_ext)
        if img_class:
            self.preset.find_or_add_setting_by_class(img_class)

        seq_matches = seq_range_matches(job, self.seq_start, self.seq_end)
        if seq_matches:
            # TODO: make sure there's only one active shot
            unreal.log("job's sequence matches render start/end, no frame range or shot disabling required")
        else:
            matching_shot = disable_out_of_range_shots(job, self.seq_start, self.seq_end)
        if matching_shot:
            unreal.log(f"About to render shot {matching_shot.outer_name}")
        else:
            unreal.log_warning(f"no shot matching job's start/end ({self.seq_start}/{self.seq_end}), a custom sequence range will be used")
            set_custom_seq_range(self.preset, self.seq_start, self.seq_end)
            unreal.log(f"About to render range {output_setting.custom_start_frame}, {output_setting.custom_end_frame} (last frame excluded)")

        # Make sure all settings are filled
        self.preset.initialize_transient_settings()
        job.set_preset_origin(self.preset)

        global SUBSYSTEM_EXECUTOR
        SUBSYSTEM_EXECUTOR = unreal.MoviePipelinePIEExecutor(subsystem)

        SUBSYSTEM_EXECUTOR.on_executor_finished_delegate.add_callable_unique(on_queue_finished_callback)
        SUBSYSTEM_EXECUTOR.on_individual_job_work_finished_delegate.add_callable_unique(on_individual_job_finished_callback) # Only available on PIE Executor
        SUBSYSTEM_EXECUTOR.on_individual_shot_work_finished_delegate.add_callable_unique(on_individual_shot_finished_callback) # Only available on PIE executor
        
        # Have the Queue Subsystem run the actual render - this 'locks' the UI while a render is in progress and suppresses the
        # Sequencer 'Auto Bind to PIE' feature which would cause duplicate objects.
        subsystem.render_queue_with_executor_instance(SUBSYSTEM_EXECUTOR)


def wait_for_asset_registry(delta_seconds):
    asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()
    if asset_registry.is_loading_assets():
        unreal.log_warning("Asset Registry still loading...")
        pass
    else:
        global TICK_HANDLE
        
        unreal.unregister_slate_pre_tick_callback(TICK_HANDLE)
        TICK_HANDLE = None

        RenderCommander().render_new_queue()
                

if __name__ == "__main__":
    unreal.log("RR render module %rrVersion%")
    TICK_HANDLE = unreal.register_slate_pre_tick_callback(wait_for_asset_registry)
