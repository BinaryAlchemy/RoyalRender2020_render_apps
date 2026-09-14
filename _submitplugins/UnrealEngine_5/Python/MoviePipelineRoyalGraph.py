# -*- coding: cp1252 -*-
######################################################################
#
# Royal Render Plugin script for Unreal Engine
# Copyright (c)  Holger Schoenberger
#
# Last change: %rrVersion%
#
######################################################################
#
# Movie Render Graph (MRG) job extraction.
#
# Split out from MoviePipelineRoyalSubmit.py so the legacy MoviePipelinePrimaryConfig path
# stays untouched. A job's render *settings* live in a completely different place under MRG
# (a MovieGraphConfig asset instead of a settings array on the job), so this module has its
# own extraction logic; the sequencer/shot/frame-range handling is genuinely shared and lives
# in MoviePipelineRoyalSubmit.finalize_shot_jobs() / resolve_full_sequence_filenames().
#
# STATUS / OPEN QUESTIONS - the items below are CONFIRMED against a real project graph (not
# just API docs) unless marked otherwise:
#
#   - CONFIRMED: flattened.get_branch_names() includes "Globals" itself alongside the actual
#     render layer branches - filtered out below.
#   - CONFIRMED: the global settings node class is MovieGraphGlobalOutputSettingNode, not
#     MovieGraphOutputSettingNode as the API docs implied. It holds output_directory /
#     output_resolution / zero_pad_frame_numbers / frame_number_offset - but NOT a filename.
#   - CONFIRMED: file name format lives on each branch's own output FORMAT node instead (e.g.
#     MovieGraphImageSequenceOutputNode_EXR's `file_name_format` / `override_file_name_format`),
#     and all such format nodes appear to share a common base class MovieGraphFileOutputNode -
#     used below to find "the" format node per branch without enumerating every concrete
#     subclass by hand.
#   - CONFIRMED: the per-layer token is {layer_name}, not {render_layer_name}.
#   - CONFIRMED concrete format node classes (image sequence): _BMP, _EXR, _MultiLayerEXR (both
#     map to .exr on disk - the "Suffix == extension" trick from the legacy code would have
#     produced ".multilayerexr", which is wrong, hence the explicit _FILE_FORMAT_EXTENSIONS map
#     below instead of deriving it from the class name). Audio is a single class,
#     MovieGraphAudioOutputNode (no per-codec subclass the way legacy had). Video (H.264 MP4,
#     ProRes, DNx, ...) - NOT YET CONFIRMED: no node class matching those names showed up in a
#     `dir(unreal)` scan restricted to 'Output'/'Mp4'/'H264' - there may be a single
#     MovieGraphVideoOutputNode with a codec/container property that determines the extension,
#     analogous to Audio. If you use a video output type, tell me which one so I can get its
#     exact node class + extension-relevant property name confirmed rather than guessed.
#
#   - The Global Output Settings node DOES have a custom playback range override (unlike what
#     was assumed before testing) - override_custom_playback_range_start/end (bool) plus both a
#     MovieGraphSequencePlaybackRangeBound struct (custom_playback_range_start/end) and a plain
#     int (*_frame). Your test graph had the override OFF, so the *_frame path below is
#     UNVERIFIED - if you ever turn this override on, please re-run the frame-range test and
#     confirm the numbers _apply_output_setting() computes actually match.
#
#   - Multicam ("render all cameras" per job) has no confirmed 1:1 equivalent node in MRG yet.
#     Left unimplemented (see _apply_multicam below) - single-camera sequences work as-is.
#
#   - RR_NO_SPLIT / RR_NO_UI are read from the job-level `console_variable_overrides` property
#     (the "Console Variables" column in the MRQ job list), which is shared by legacy and graph
#     jobs. If your team instead sets these via a "Set CVar Value" node *inside* the graph, tell
#     me and I'll add a lookup on the flattened graph for that too.
#
#   - If a branch has more than one MovieGraphFileOutputNode (e.g. an image sequence AND an
#     audio node together), only the first one found is used for that branch's rrJob - the rest
#     are logged but ignored. Tell me if you actually use combined image+audio branches and this
#     needs full multi-format-per-branch support.
#
# RENDERER / COMMAND LINE TEMPLATE:
#
#   Graph jobs are submitted with renderer=GRAPH_RENDERER_NAME (see below), NOT "MoviePipeline"
#   - on purpose, so this is its own Renderer in RR with its OWN command line template and its
#     own render-side script (unreal_render_graph_50.py), instead of trying to make graph jobs
#     fit the legacy template's field conventions. Set up that template/renderer entry in RR
#     pointing at unreal_render_graph_50.py before submitting a graph job for real.
#
#   Field choices for that template, using real rrJob/database fields rather than the
#   hand-rolled "Custom..." ones (which are informational and not guaranteed stable for the
#   farm to build a command line from):
#     - <Layer>      -> the render layer name (or "** All **", stripped by the farm) - matches
#                        Unreal's own "Render Layer" terminology 1:1.
#     - <SceneState> -> the Level Sequence name ("Unreal Sequence"), e.g.:
#                          -rSeq="<CustomSequencePath>/<SceneState>"
#     - <SceneTake>  -> not used yet, available if you want it for something (variant/version?).
#     - -rLayer="<Layer>" next to the existing -rExt=<ImageExtension> etc. entries. Empty/absent
#       -rLayer (the "** All **" job, once stripped) means "render every layer".
#
#   For a graph with N render layers, collect_rr_job_from_graph() submits N+1 rrJobs: one per
#   render layer (active), plus one combined "** All **" job (isActive=False, opt-in). The
#   combined job's main Image*/imageDir fields mirror the first render layer; the *other*
#   layers' resolved filenames go into channelFileName/channelExtension so their outputs can
#   still be checked for completeness even though only one job ran.
#
#   If a format node's file name format doesn't contain a {layer_name} token, multiple layers
#   resolve to the *same* output path and would overwrite each other on disk -
#   collect_rr_job_from_graph() logs a warning if the token isn't present (it does NOT inject
#   one, unlike the earlier {render_layer_name} assumption - since the filename is per-branch
#   now, not shared, there's no single global string to safely substitute into).
#

import unreal

import copy
import os

from MoviePipelineRoyalSubmit import (
    UE_to_RR_tokens,
    clean_up_game_path,
    get_seq_range,
    get_job_sequence,
    get_seq_camera,
    get_file_params,
    finalize_shot_jobs,
    resolve_full_sequence_filenames,
)


ALL_LAYERS_VALUE = "** All **"

# Submitted as rrJob.renderer instead of the legacy "MoviePipeline" so graph jobs get their own
# Renderer entry (own command line template, own render-side script) in RR - see module
# docstring. Rename freely, just keep it in sync with what you configure in RR.
GRAPH_RENDERER_NAME = "MovieRenderGraph"


# Explicit map instead of deriving the extension from the class name suffix (that trick broke
# on MovieGraphImageSequenceOutputNode_MultiLayerEXR - see module docstring). Each entry is
# (extension, is_single_file_output). Add to this if you use a class not listed here - a
# missing entry logs a clear warning at submit time rather than silently guessing.
_FILE_FORMAT_EXTENSIONS = {
    'MovieGraphImageSequenceOutputNode_BMP': ('.bmp', False),
    'MovieGraphImageSequenceOutputNode_JPG': ('.jpeg', False),
    'MovieGraphImageSequenceOutputNode_PNG': ('.png', False),
    'MovieGraphImageSequenceOutputNode_EXR': ('.exr', False),
    'MovieGraphImageSequenceOutputNode_MultiLayerEXR': ('.exr', False),
    'MovieGraphAudioOutputNode': ('.wav', True),
    # TODO: MovieGraphVideoOutputNode (H.264 MP4 / ProRes / DNx / ...) - not yet confirmed, see
    # module docstring. Add the real class name + extension here once confirmed.
}


def _flatten_graph_for_job(graph, ue_job):
    """Evaluates the graph for this job, including its job-level variable overrides
    (get_or_create_variable_overrides), and returns a MovieGraphEvaluatedConfig or None."""
    try:
        shot_count = max(len(ue_job.shot_info), 1)
    except TypeError:
        shot_count = 1

    try:
        context = unreal.MovieGraphTraversalContext(
            job=ue_job,
            shot=None,
            shot_index=0,
            shot_count=shot_count,
            root_graph=graph,
        )
    except Exception as e:
        unreal.log_error(f"Could not build MovieGraphTraversalContext for job {ue_job.job_name}: {e}")
        return None

    try:
        result = graph.create_flattened_graph(context)
    except Exception as e:
        unreal.log_error(f"Could not flatten Movie Render Graph for job {ue_job.job_name}: {e}")
        return None

    # create_flattened_graph is documented as returning the evaluated config, plus an error
    # description on failure - Python may expose that as (config, error) or just config
    # depending on engine version, so handle both.
    if isinstance(result, tuple):
        flattened, error = result
    else:
        flattened, error = result, None

    if error:
        unreal.log_warning(f"Graph evaluation warning for job {ue_job.job_name}: {error}")

    return flattened


def _apply_output_setting(output_setting, ue_job, new_job_rr):
    """Directory / resolution / frame padding / (optionally) custom playback range - the fields
    confirmed to really be global. File name format is NOT here - it lives on each branch's own
    output format node instead, see _apply_branch_output()."""
    output_dir = output_setting.output_directory.path
    for UE_token, RR_token in UE_to_RR_tokens.items():
        output_dir = output_dir.replace(UE_token, RR_token)
    new_job_rr.imageDir = output_dir

    new_job_rr.imageFramePadding = output_setting.zero_pad_frame_numbers

    # CONFIRMED (live test): output_resolution is a MovieGraphNamedResolution struct (the "Named
    # Resolution" presets feature), not a plain IntPoint - {profile_name, resolution, description},
    # where .resolution is the actual IntPoint with .x/.y. Not present on older engine versions
    # that still used a plain IntPoint here, so fall back to treating output_res itself as the
    # IntPoint if .resolution isn't there.
    output_res = output_setting.output_resolution
    resolution = getattr(output_res, 'resolution', output_res)
    new_job_rr.imageWidth = resolution.x
    new_job_rr.imageHeight = resolution.y

    range_overridden = bool(getattr(output_setting, 'override_custom_playback_range_start', False)) or \
        bool(getattr(output_setting, 'override_custom_playback_range_end', False))

    if range_overridden:
        # UNVERIFIED against a real graph with this override enabled - see module docstring.
        new_job_rr.seqStart = output_setting.custom_playback_range_start_frame
        new_job_rr.seqEnd = output_setting.custom_playback_range_end_frame - 1
        unreal.log_warning(
            f"job {ue_job.job_name}: custom playback range override is enabled on the Global "
            f"Output Settings node - using custom_playback_range_start_frame/end_frame "
            f"({new_job_rr.seqStart}/{new_job_rr.seqEnd}). This path is unverified against a "
            "real graph - double check these numbers match the actual intended render range."
        )
    else:
        seq_asset_path = ue_job.sequence.to_tuple()[0]
        package_path_seq = seq_asset_path.rsplit('.', 1)[0]
        seq_start_frame, seq_end_frame = get_seq_range(package_path_seq)

        new_job_rr.seqStart = seq_start_frame
        new_job_rr.seqEnd = seq_end_frame


def _find_branch_file_output_nodes(flattened, branch_name):
    base_class = getattr(unreal, 'MovieGraphFileOutputNode', None)
    if base_class is None:
        return []

    # exact_match=False: match MovieGraphFileOutputNode *subclasses* too (the concrete format
    # nodes) - the returned objects keep their real runtime class, get_class().get_name() below
    # still gives you e.g. "MovieGraphImageSequenceOutputNode_EXR".
    return list(flattened.get_settings_for_branch(base_class, branch_name, include_cd_os=False, exact_match=False))


def _flag_no_frame_check(job, ue_job, branch_name, reason):
    """Whenever we can't reliably resolve a branch's output filename/extension - an unhandled
    output type, or some other case this script doesn't cover - RR must not try to verify
    rendered frames against a guessed filename, since that guess may well be wrong. Holger:
    'Dann für diesen Job in das xml das hinzufügen: <SubmitterParameter> DoNotCheckForFrames=0~1
    </SubmitterParameter>' - so instead of writing a possibly-wrong imageFileName/imageExtension
    and letting RR fail verification on it, tell RR to skip frame-count verification for this
    job entirely. Literal value is "0~1" (as given, not "1") - appends rather than overwrites, in
    case something else on the job already set submitter_parameter."""
    unreal.log_warning(f"job {ue_job.job_name}, branch '{branch_name}': {reason} - disabling RR frame check for this job (DoNotCheckForFrames=0~1)")
    flag = "DoNotCheckForFrames=0~1"
    if flag not in job.submitter_parameter:
        job.submitter_parameter = f"{job.submitter_parameter};{flag}" if job.submitter_parameter else flag


def _apply_branch_output(job, flattened, branch_name, ue_job, all_branch_names):
    """Finds the branch's output format node, resolves its file_name_format into job.imageFileName,
    and sets job.imageExtension/imageSingleOutput from its concrete class. Whenever the resolution
    isn't trustworthy (missing/unrecognized node, missing property, ...), falls back to flagging
    the job with DoNotCheckForFrames=0~1 (see _flag_no_frame_check()) instead of submitting a job
    RR will fail to verify against a wrong guess."""
    nodes = _find_branch_file_output_nodes(flattened, branch_name)
    if not nodes:
        _flag_no_frame_check(job, ue_job, branch_name, "no output format node found")
        return

    if len(nodes) > 1:
        unreal.log_warning(
            f"job {ue_job.job_name}: branch '{branch_name}' has {len(nodes)} output format nodes "
            "(e.g. image + audio together) - only the first is used for this rrJob, the rest are "
            "ignored. Tell Holger if you need every one of them represented."
        )

    fmt_node = nodes[0]
    class_name = fmt_node.get_class().get_name()

    ext, is_single_output = _FILE_FORMAT_EXTENSIONS.get(class_name, (None, False))
    if ext is None:
        _flag_no_frame_check(
            job, ue_job, branch_name,
            f"unrecognized output format node class '{class_name}' - add it to "
            "_FILE_FORMAT_EXTENSIONS in MoviePipelineRoyalGraph.py to fix this properly"
        )
    else:
        job.imageExtension = ext
        job.imageSingleOutput = is_single_output

    try:
        output_file = str(fmt_node.file_name_format)
    except AttributeError:
        _flag_no_frame_check(job, ue_job, branch_name, f"output format node '{class_name}' has no file_name_format property")
        return

    # CONFIRMED bug (live test): {layer_name} was being left as the literal string '{layer_name}'
    # in every branch's imageFileName instead of being resolved - so every branch ended up with
    # the exact same (unresolved) filename, and the "does the layer name actually appear in the
    # filename" self-check below always failed. This is the one token that must become a concrete
    # value now (the branch's real name), not an RR command-line token - RR's own <Layer> job
    # field already means something else here (the render layer selector, see module docstring).
    output_file = output_file.replace('{layer_name}', branch_name)

    # The shared UE_to_RR_tokens dict (MoviePipelineRoyalSubmit.py) maps {sequence_name} -> <Layer>,
    # a legacy-only convention (legacy jobs had no real render layers, so RR's Layer field was
    # reused for sequence identity). That collides with <Layer> now meaning the actual render
    # layer for graph jobs, so graph jobs skip that one legacy entry and resolve {sequence_name}
    # to RR's <SceneState> token instead, matching new_job_rr.sceneState (see _build_template_job).
    for UE_token, RR_token in UE_to_RR_tokens.items():
        if UE_token == '{sequence_name}':
            continue
        output_file = output_file.replace(UE_token, RR_token)
    output_file = output_file.replace('{sequence_name}', '<SceneState>')

    output_file = output_file.replace('{frame_number}', '#' * job.imageFramePadding)

    job.imageFileName = output_file

    if len(all_branch_names) > 1 and branch_name not in job.imageFileName:
        _flag_no_frame_check(
            job, ue_job, branch_name,
            f"{len(all_branch_names)} render layers but this branch's output filename "
            f"('{job.imageFileName}') doesn't reference the layer name (no {{layer_name}} token) - "
            "it may overwrite another layer's output on disk, so any frame count check here would "
            "be unreliable too"
        )


def _apply_multicam(ue_job, new_job_rr):
    # TODO: no confirmed MRG equivalent yet for MoviePipelineCameraSetting.render_all_cameras.
    # Left as False (single camera) until we've confirmed the right node/property.
    new_job_rr.multicam = False


def _read_rr_console_var_flags(ue_job):
    split_shot_jobs = True
    submission_ui = True

    try:
        cvar_overrides = ue_job.console_variable_overrides
    except AttributeError:
        # Property not present on this engine version - fall back to defaults.
        return split_shot_jobs, submission_ui

    for entry in cvar_overrides:
        if not entry.is_enabled:
            continue
        if entry.name == 'RR_NO_SPLIT':
            split_shot_jobs = not bool(entry.value)
        elif entry.name == 'RR_NO_UI':
            submission_ui = not bool(entry.value)

    return split_shot_jobs, submission_ui


def _build_template_job(base_job_rr, ue_job, preset_path, output_setting):
    """Everything about the rrJob that's identical regardless of which render layer it's for:
    scene/sequence identity plus the global (directory/resolution/padding/range) output
    settings. imageFileName/imageExtension are NOT set here - those are per-branch, see
    _apply_branch_output()."""
    template_job = copy.deepcopy(base_job_rr)
    template_job.renderer = GRAPH_RENDERER_NAME
    template_job.CustomPresetPath = preset_path
    template_job.userName = ue_job.get_editor_property('author')

    map_asset_path = clean_up_game_path(ue_job.map.to_tuple()[0].rsplit('.', 1)[0])
    template_job.CustomLevelDir = map_asset_path
    template_job.sceneName = f"<DataBase>/Content/{map_asset_path}.umap"

    seq_asset_path = clean_up_game_path(ue_job.sequence.to_tuple()[0])
    template_job.CustomSequencePath, seq_asset_name = os.path.split(seq_asset_path)
    seq_asset_name = seq_asset_name.rsplit('.', 1)[0]
    template_job.seqName = seq_asset_name
    # real rrJob/database field, used in the graph command line template instead of the
    # informational <CustomSeQName> - see module docstring
    template_job.sceneState = seq_asset_name

    _apply_output_setting(output_setting, ue_job, template_job)
    _apply_multicam(ue_job, template_job)

    return template_job


def _build_all_layers_jobs(template_job, ue_job, flattened, branch_names, split_shot_jobs_base):
    """The combined '** All **' jobs: one per shot (not one job for the whole sequence), plus a
    whole-sequence master entry when the per-layer jobs would also get one. Holger's point: shots
    can never run together (different frame ranges/cameras), but layers plausibly CAN be rendered
    together in one graph evaluation if the graph's set up for it - so the '** All **' convenience
    job has to be split per shot just like the individual per-layer jobs are, rather than covering
    the whole sequence in a single job. Each entry is an inactive job (opt-in) with one channel
    per render layer, so each layer's output can still be verified individually.

    Implementation: runs finalize_shot_jobs() once per branch/layer (so per-branch filenames,
    which is what actually differs between layers, all get resolved the normal way), then zips
    the resulting per-shot entry lists together by index - relying on every branch producing the
    same shot structure (same sequence/shot track, independent of which layer it is)."""
    per_branch_entries = []

    for branch_name in branch_names:
        branch_job = copy.deepcopy(template_job)
        branch_job.layer = ALL_LAYERS_VALUE
        _apply_branch_output(branch_job, flattened, branch_name, ue_job, branch_names)

        split_shot_jobs = split_shot_jobs_base
        if branch_job.imageSingleOutput:
            split_shot_jobs = "{shot_name}" in branch_job.imageFileName

        per_branch_entries.append(finalize_shot_jobs(branch_job, ue_job, split_shot_jobs))

    entry_counts = {len(entries) for entries in per_branch_entries}
    if len(entry_counts) > 1:
        unreal.log_warning(
            f"job {ue_job.job_name}: layers produced different numbers of shot entries "
            f"({[len(entries) for entries in per_branch_entries]}) - probably because some layers "
            "are image sequences and others are a single monolithic file (video/audio). Can't zip "
            "them into a combined '** All **' job per shot reliably, so skipping it - submit the "
            "per-layer jobs individually instead."
        )
        return []

    all_jobs = []
    entry_count = entry_counts.pop() if entry_counts else 0

    for shot_index in range(entry_count):
        combined = copy.deepcopy(per_branch_entries[0][shot_index])
        combined.layer = ALL_LAYERS_VALUE
        combined.isActive = False

        channel_filenames = []
        channel_extensions = []

        for branch_entries in per_branch_entries:
            entry = branch_entries[shot_index]
            channel_filenames.append(entry.imageFileName)
            channel_extensions.append(entry.imageExtension)

            if entry.submitter_parameter and "DoNotCheckForFrames=0~1" not in combined.submitter_parameter:
                # a channel's filename/extension couldn't be trusted - the combined job's own
                # frame check (which relies on every channel being correct) can't be trusted
                # either, so the flag propagates from the channel entry to the combined job.
                combined.submitter_parameter = (
                    f"{combined.submitter_parameter};DoNotCheckForFrames=0~1" if combined.submitter_parameter else "DoNotCheckForFrames=0~1"
                )

        combined.maxChannels = len(channel_filenames)
        combined.channelFileName = channel_filenames
        combined.channelExtension = channel_extensions

        all_jobs.append(combined)

    return all_jobs


def collect_rr_job_from_graph(base_job_rr, ue_job):
    """Builds rrJob entries for a job configured with Movie Render Graph (job.get_graph_preset()
    is set). Mirrors collect_rr_job_from_legacy() in MoviePipelineRoyalSubmit.py, but reads
    render settings out of the flattened graph instead of a MoviePipelinePrimaryConfig, and -
    unlike legacy - submits one farm job per render layer/branch PLUS one inactive combined
    '** All **' job. See the module docstring for the required command line template change."""
    entries = []

    graph = ue_job.get_graph_preset()
    if not graph:
        unreal.log_warning(f"job skipped because of missing graph preset: {ue_job.job_name}")
        return entries

    flattened = _flatten_graph_for_job(graph, ue_job)
    if not flattened:
        unreal.log_warning(f"job skipped, graph could not be evaluated: {ue_job.job_name}")
        return entries

    # get_branch_names() includes "Globals" itself alongside the actual render layer branches
    # (confirmed against a real project graph) - filter it out here so it's not treated as a
    # render layer. CONFIRMED (live test): the returned names are unreal.Name, not plain str -
    # str() them here once so every branch_name used below (dict keys, "in" checks against
    # job.imageFileName, get_settings_for_branch's branch_name arg, job.layer, ...) is a real
    # Python string throughout the rest of this module.
    branch_names = [str(b) for b in flattened.get_branch_names() if str(b) != "Globals"]
    if not branch_names:
        unreal.log_warning(f"job skipped, graph has no render layers/branches: {ue_job.job_name}")
        return entries

    preset_path = clean_up_game_path(graph.get_path_name().rsplit('.', 1)[0])

    # --- Global Output Settings node (directory, resolution, frame padding, playback range) ---
    output_setting = flattened.get_setting_for_branch(unreal.MovieGraphGlobalOutputSettingNode, "Globals", include_cd_os=False, exact_match=True)
    if not output_setting:
        unreal.log_warning(f"job skipped, no Global Output Settings node found: {ue_job.job_name}")
        return entries

    split_shot_jobs_base, submission_ui = _read_rr_console_var_flags(ue_job)

    template_job = _build_template_job(base_job_rr, ue_job, preset_path, output_setting)

    # --- one job per render layer/branch ---
    for branch_name in branch_names:
        new_job_rr = copy.deepcopy(template_job)
        new_job_rr.layer = branch_name

        _apply_branch_output(new_job_rr, flattened, branch_name, ue_job, branch_names)

        # mirrors collect_rr_job_from_legacy(): a single monolithic (video/audio) output
        # overrides RR_NO_SPLIT - it's only split by shot if the filename actually varies per
        # shot ({shot_name} token present), regardless of the cvar.
        split_shot_jobs = split_shot_jobs_base
        if new_job_rr.imageSingleOutput:
            split_shot_jobs = "{shot_name}" in new_job_rr.imageFileName

        entries.extend(finalize_shot_jobs(new_job_rr, ue_job, split_shot_jobs))

    # --- combined "** All **" jobs, one per shot (see _build_all_layers_jobs docstring for why),
    # inactive by default so they can be enabled manually ---
    if len(branch_names) > 1:
        entries.extend(_build_all_layers_jobs(template_job, ue_job, flattened, branch_names, split_shot_jobs_base))

    return entries
