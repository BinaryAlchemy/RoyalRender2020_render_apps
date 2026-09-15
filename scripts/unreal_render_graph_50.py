#python
# -*- coding: cp1252 -*-
######################################################################
#
# Royal Render Render script for Unreal Engine - Movie Render Graph
# Author:  Holger Schoenberger
# Last Change: %rrVersion%
#
# Copyright (c) Holger Schoenberger - Binary Alchemy
#
######################################################################
#
# Standalone render-side script for Movie Render Graph (MRG) jobs, submitted with their own
# Renderer (see MoviePipelineRoyalGraph.GRAPH_RENDERER_NAME) and their own RR command line
# template - NOT a fallback branch inside unreal_render_50.py, which stays legacy-only and
# untouched. Reuses unreal_render_50's generic (config-system-agnostic) helpers - map/sequence
# path parsing, shot-range disabling - rather than duplicating them.
#
# USAGE (set this as the -ExecCmds target in the MRG Renderer's command line template):
#   -ExecCmds="py <rrLocalRenderScripts>unreal_render_graph_50.py"
#   -MoviePipelineConfig="/Game/<CustomPresetPath>"   (points at the MovieGraphConfig asset)
#   -rMap="<SceneFolder><SceneFileName>"
#   -rSeq="<CustomSequencePath>/<SceneState>"          (see MoviePipelineRoyalGraph.py docstring
#                                                        for why <SceneState>, not <Layer>)
#   -rLayer="<Layer>"                                  (render layer name, or empty for "** All **")
#   -rOutFolder="<ImageDir>" -rOutName="<ImageFilename>" -rPad=<ImageFramePadding>
#   -rExt=<ImageExtension> -rStart=<SeqStart> -rEnd=<SeqEnd+1> -rOffset=<SeqFileOffset>
#   -rW=<ImageWidth> -rH=<ImageHeight> -rAA=<AAsamplesMultiply>
#   (same argument set as the legacy template - only -rSeq's source field and the new -rLayer
#   differ)
#
# STATUS / OPEN QUESTIONS - please confirm against a running editor before relying on this:
#
#   - CONFIRMED against a real project graph: pin name == branch name (e.g. pin "DefaultLayer"
#     connected to a "Render Layer" node; pins "out_ENV"/"out_MEERKAT"/etc. each connected to a
#     "Branch" node). CONFIRMED this does NOT mean the node directly wired to the branch pin is
#     the one you're looking for, though - nodes on a branch are chained through their own pins
#     (Globals -> "Sampling Method" -> ... -> "Global Output Settings" further upstream; a
#     branch pin -> a "Branch" node -> the actual Render Layer node further upstream still).
#     _walk_upstream_nodes() below walks the whole chain rather than assuming one hop - that's
#     the fix for what used to be here. Re-check with:
#         graph = unreal.load_asset("/Game/Path/To/YourGraph")
#         for pin in graph.get_output_node().get_input_pins():
#             print(pin.properties.label, [n.get_node_title(False) for n in pin.get_connected_nodes()])
#     if a branch's chain still doesn't yield a MovieGraphRenderLayerNode/MovieGraphGlobalOutputSettingNode
#     anywhere, the traversal direction or pin-following logic needs another look.
#
#   - CONFIRMED: file_name_format does NOT live on the Global Output Settings node - it lives on
#     each branch's own output format node (EXR/PNG/Audio/...) instead, all apparently sharing a
#     common MovieGraphFileOutputNode base class. apply_global_output_overrides() only touches
#     output_directory/output_resolution/zero_pad_frame_numbers on the global node;
#     apply_branch_filename_override() handles file_name_format on the target branch's format
#     node, found via _find_file_output_node() walking that branch's chain.
#
#   - Mutating nodes found via _walk_upstream_nodes() mirrors a pattern confirmed in an Epic
#     forum post for *setting* values this way, but wasn't tested here end-to-end for actually
#     kicking off a render. If a node lives inside a locked subgraph asset rather than directly
#     in the job's graph, this direct-node mutation may not be reachable this way
#     (get_input_pins()/get_connected_nodes() may not cross into a subgraph) and you'd need
#     job-level graph variable overrides instead (which only works if those fields were promoted
#     to graph variables in your graph asset).
#

import unreal

from unreal_render_50 import (
    RenderArgs,
    disable_out_of_range_shots,
    seq_range_matches,
    on_queue_finished_callback,
    on_individual_job_finished_callback,
    on_individual_shot_finished_callback,
)
import unreal_render_50


TICK_HANDLE = None


# Every line this script itself logs is prefixed like this, so it's visually distinguishable in
# the render log from Unreal's own LogXxx: lines - Holger: "Ich erkenne nicht welche Zeile von uns
# ist und welche von Unreal."
LOG_PREFIX = " rrUnreal       : "


def log_info(message):
    unreal.log(f"{LOG_PREFIX}{message}")


def log_warn(message):
    unreal.log_warning(f"{LOG_PREFIX}{message}")


def log_error(message):
    unreal.log_error(f"{LOG_PREFIX}{message}")


def _walk_upstream_nodes(start_nodes):
    """Returns every node reachable by walking upstream (via each node's own input pins) from
    the given starting nodes, each included once. Confirmed necessary against a real project
    graph: nodes on a branch are chained through their own pins (e.g. Globals -> "Sampling
    Method" -> ... -> "Global Output Settings", or a branch pin -> a "Branch" node -> the actual
    Render Layer node further upstream) rather than all being wired directly to the Outputs
    node's branch pin."""
    visited = []
    stack = list(start_nodes)

    while stack:
        node = stack.pop()
        if any(node == v for v in visited):
            continue
        visited.append(node)

        for pin in node.get_input_pins():
            for upstream in pin.get_connected_nodes():
                if not any(upstream == v for v in visited):
                    stack.append(upstream)

    return visited


def _find_output_settings_node(graph):
    """Returns the (mutable, in-memory-only) Global Output Settings node of the given graph, or
    None. See module docstring for the caveat about subgraphs."""
    output_node = graph.get_output_node()
    globals_pin = output_node.get_input_pin("Globals")
    if not globals_pin:
        return None

    for node in _walk_upstream_nodes(globals_pin.get_connected_nodes()):
        if isinstance(node, unreal.MovieGraphGlobalOutputSettingNode):
            return node

    return None


def _find_render_layer_nodes(graph):
    """Returns {branch/pin name: [MovieGraphNode, ...]} - every node in the full upstream chain
    for each branch coming out of the graph's output node. See module docstring: this assumes
    the pin name matches the branch name used on the submit side (flattened.get_branch_names())."""
    output_node = graph.get_output_node()
    branches = {}

    for pin in output_node.get_input_pins():
        pin_name = str(pin.properties.label)
        if pin_name == "Globals":
            continue

        branches[pin_name] = _walk_upstream_nodes(pin.get_connected_nodes())

    return branches


def _find_file_output_node(nodes):
    """First MovieGraphFileOutputNode (any concrete format subclass - EXR/PNG/Audio/...) found
    among the given nodes, or None."""
    for node in nodes:
        if isinstance(node, unreal.MovieGraphFileOutputNode):
            return node
    return None


def disable_other_render_layers(branches, keep_layer_name):
    """Disables every node in every branch's chain except `keep_layer_name`'s, so only that one
    branch actually renders. Nodes that also appear in the kept branch's own chain (e.g. a
    shared Collection/Modifier node feeding multiple render layers) are left alone even if they
    also appear in a disabled branch's chain, so disabling one layer can't silently break
    another. Returns (found, disabled_nodes): found is True if `keep_layer_name` was located and
    left enabled; disabled_nodes is every node this call actually disabled, so the caller can put
    them back afterward - see the "restore" note in render_new_graph_queue() for why that matters."""
    if keep_layer_name not in branches:
        log_warn(
            f"-rLayer '{keep_layer_name}' not found among graph branches ({', '.join(branches.keys())}); "
            "nothing was disabled, ALL layers will render."
        )
        return False, []

    keep_chain = branches[keep_layer_name]
    disabled_nodes = []

    for branch_name, nodes in branches.items():
        if branch_name == keep_layer_name:
            continue

        for node in nodes:
            if any(node == k for k in keep_chain):
                # shared with the branch we're keeping - leave it alone
                continue

            if not node.can_be_disabled():
                log_warn(f"branch '{branch_name}': node {node.get_node_title(False)} can't be disabled, it may still render")
                continue

            node.set_disabled(True)
            disabled_nodes.append(node)
            log_info(f"disabled branch '{branch_name}' (node {node.get_node_title(False)}) so only '{keep_layer_name}' renders")

    return True, disabled_nodes


def apply_global_output_overrides(output_setting, render_args):
    """Graph equivalent of unreal_render_50.RenderCommander.create_out_setting(), for the
    fields CONFIRMED to live on the Global Output Settings node: directory, resolution, frame
    padding. File name format is NOT here - confirmed to live on each branch's own format node
    instead, see apply_branch_filename_override()."""
    output_setting.override_output_resolution = True

    resolution = unreal.IntPoint(render_args.img_width, render_args.img_height)

    # CONFIRMED (live test, render side): output_resolution is a MovieGraphNamedResolution struct
    # (the "Named Resolution" presets feature) on engine versions that have it, not a plain
    # IntPoint - same discovery already made reading it on the submit side, see
    # MoviePipelineRoyalGraph._apply_output_setting. Writing a bare IntPoint there fails with
    # "Cannot nativize 'IntPoint' as 'MovieGraphNamedResolution'". Fall back to a plain IntPoint
    # assignment on older engines that don't have the struct at all.
    named_resolution_class = getattr(unreal, 'MovieGraphNamedResolution', None)
    if named_resolution_class:
        output_setting.output_resolution = named_resolution_class(profile_name="Custom", resolution=resolution, description="")
    else:
        output_setting.output_resolution = resolution

    output_setting.override_output_directory = True
    output_setting.output_directory = unreal.DirectoryPath(render_args.img_folder)

    output_setting.override_zero_pad_frame_numbers = True
    output_setting.zero_pad_frame_numbers = render_args.img_padding


def _remember_output_setting_state(output_setting, restore_actions):
    """Snapshots the Global Output Settings node's fields that apply_global_output_overrides()
    is about to overwrite, and appends a restore action for them. See render_new_graph_queue()
    docstring for why this matters - `output_setting` lives on the shared, live graph asset."""
    prev_override_resolution = output_setting.override_output_resolution
    prev_resolution = output_setting.output_resolution
    prev_override_directory = output_setting.override_output_directory
    prev_directory = output_setting.output_directory
    prev_override_padding = output_setting.override_zero_pad_frame_numbers
    prev_padding = output_setting.zero_pad_frame_numbers

    def _restore():
        output_setting.override_output_resolution = prev_override_resolution
        output_setting.output_resolution = prev_resolution
        output_setting.override_output_directory = prev_override_directory
        output_setting.output_directory = prev_directory
        output_setting.override_zero_pad_frame_numbers = prev_override_padding
        output_setting.zero_pad_frame_numbers = prev_padding

    restore_actions.append(_restore)


def _remember_file_output_node_state(fmt_node, restore_actions):
    """Snapshots the fields apply_branch_filename_override() is about to overwrite on one
    branch's format node, and appends a restore action for them. Same reasoning as
    _remember_output_setting_state() - see render_new_graph_queue() docstring."""
    prev_override_format = fmt_node.override_file_name_format
    prev_format = fmt_node.file_name_format

    def _restore():
        fmt_node.override_file_name_format = prev_override_format
        fmt_node.file_name_format = prev_format

    restore_actions.append(_restore)


def apply_branch_filename_override(fmt_node, render_args):
    """Pushes the command-line-provided output filename onto one branch's format node (EXR/PNG/
    Audio/...). Only called when -rLayer names a single branch to render - see module docstring
    in render_new_graph_queue() for why "render all layers" mode leaves each branch's own
    {layer_name}-differentiated filename alone instead of forcing them all to the same name."""
    fmt_node.override_file_name_format = True
    fmt_node.file_name_format = render_args.img_name + ("{frame_number_shot}" if render_args.seq_offset else "{frame_number}")

    log_info(f"Rendering with filename: {fmt_node.file_name_format}")


class GraphRenderArgs(RenderArgs):
    """Adds the -rLayer argument on top of the existing RenderArgs (map/sequence/preset/output
    parsing is unchanged and reused as-is)."""
    def __init__(self, cmdParameters):
        super().__init__(cmdParameters)
        self.render_layer = cmdParameters.get('rLayer')
        if not self.render_layer:
            # Expected for the combined "** All **" job (and if -rLayer="<Layer>" hasn't been
            # added to the RR command line template yet) - render every layer in that case.
            log_info("-rLayer not set/empty: rendering all render layers in this graph")


def render_new_graph_queue(render_args, graph):
    """Graph equivalent of unreal_render_50.RenderCommander.render_new_queue().

    IMPORTANT: `graph` (from unreal.load_asset() in render_from_command_line()) is the live,
    shared MovieGraphConfig asset - the exact same object the Editor UI shows, not a private
    duplicate. Every node.set_disabled()/override_* call below therefore mutates that shared
    asset directly. CONFIRMED as the root cause of a real farm failure (a -rLayer=out_EAGLE job
    logging "For render jobs to succeed, one or more render layer node(s) must be present." and
    finishing in ~5s with no GPU work): an earlier render for a different layer had disabled
    out_EAGLE's own nodes and never re-enabled them, so by the time this job ran, every branch -
    including its own target - was left disabled. That state persists either because the asset
    stays resident/cached in memory across repeated calls in one long-lived Editor session, or
    because it gets saved to disk. Every temporary mutation made here is therefore tracked in
    `restore_actions` and undone as soon as the queue finishes (see below), regardless of
    success/failure, so the graph asset always ends up back in its originally authored state."""
    subsystem = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
    pipeline_queue = subsystem.get_queue()

    job = pipeline_queue.allocate_new_job(unreal.MoviePipelineExecutorJob)
    job.job_name = 'RENDER_JOB'
    job.map = unreal.SoftObjectPath(render_args.map_game_path)
    job.sequence = unreal.SoftObjectPath(render_args.sequence_game_path)

    # Every entry is a no-arg callable that puts one piece of shared-asset state back the way it
    # was before this job touched it - run once the render finishes, see
    # _restore_graph_then_forward() further down.
    restore_actions = []

    output_setting = _find_output_settings_node(graph)
    if not output_setting:
        raise Exception("Graph has no Global Output Settings node (or it's inside a subgraph this script can't reach - see module docstring)")

    _remember_output_setting_state(output_setting, restore_actions)
    apply_global_output_overrides(output_setting, render_args)

    branches = _find_render_layer_nodes(graph)

    if render_args.render_layer:
        # Single-layer job (the common case: one rrJob per render layer from the submit side).
        # Disable every other branch, then force this branch's own filename to match what RR
        # expects (<ImageFilename> etc.) so verification finds the right file.
        found, disabled_nodes = disable_other_render_layers(branches, render_args.render_layer)
        for disabled_node in disabled_nodes:
            restore_actions.append(lambda n=disabled_node: n.set_disabled(False))
        if found:
            fmt_node = _find_file_output_node(branches[render_args.render_layer])
            if fmt_node:
                _remember_file_output_node_state(fmt_node, restore_actions)
                apply_branch_filename_override(fmt_node, render_args)
            else:
                log_warn(
                    f"no output format node found in branch '{render_args.render_layer}'s chain - "
                    "filename override skipped, rendering with whatever File Name Format is authored "
                    "in the graph for this branch (verification may not find the expected file)."
                )
    else:
        # "** All **" job (now one per shot, see MoviePipelineRoyalGraph._build_all_layers_jobs):
        # every branch renders with its own {layer_name}-differentiated filename as authored in
        # the graph - forcing render_args.img_name onto every branch would make them all write to
        # the same file and overwrite each other. RR verifies this job's output via its per-branch
        # channelFileName/channelExtension instead, not via a single ImageFilename.
        log_info(f"-rLayer empty: rendering all {len(branches)} render layers with their own filenames from the graph")

    # Frame range: job.shot_info-based, not config-system-specific, so the legacy helpers work
    # unchanged for graph jobs too.
    seq_matches = seq_range_matches(job, render_args.seq_start, render_args.seq_end)
    if seq_matches:
        log_info("job's sequence matches render start/end, no shot disabling required")
    else:
        matching_shot = disable_out_of_range_shots(job, render_args.seq_start, render_args.seq_end)
        if matching_shot:
            log_info(f"About to render shot {matching_shot.outer_name}")
        else:
            # Unlike the legacy path, the graph's Output Setting node has no "custom playback
            # range" override to fall back on (see MoviePipelineRoyalGraph._apply_output_setting)
            # - a mismatch here means the job's own start/end frame will be used as-is, which
            # may not match -rStart/-rEnd. Surfaced as a warning rather than silently rendering
            # the wrong range.
            log_warn(
                f"no shot matching job's start/end ({render_args.seq_start}/{render_args.seq_end}) "
                "and the graph has no custom-range override - the job will render whatever range "
                "its own job/shot data implies, which may not match -rStart/-rEnd."
            )

    job.set_graph_preset(graph)

    # Assigned on the module (not a local variable) so it matches the pattern in
    # unreal_render_50.RenderCommander.render_new_queue(): the executor must stay alive for the
    # duration of the render, so a plain local would risk being garbage-collected.
    unreal_render_50.SUBSYSTEM_EXECUTOR = unreal.MoviePipelinePIEExecutor(subsystem)
    executor = unreal_render_50.SUBSYSTEM_EXECUTOR

    def _restore_graph_then_forward(executor, success):
        # Runs once the whole queue is done (success or failure alike) - undoes every temporary
        # node-disable/override this job made to the shared graph asset before handing off to the
        # normal finished callback, so the next job (this run or a completely separate one reusing
        # the same asset) always starts from the graph's originally authored state. See
        # render_new_graph_queue() docstring for why this is necessary.
        #
        # Signature must match OnMoviePipelineExecutorFinished exactly - (executor, success), not
        # *args/**kwargs - CONFIRMED (live test): add_callable_unique() inspects the callable's
        # argument count itself and rejects a *args-based wrapper with "Callable has the incorrect
        # number of arguments (expected 2, got 0)" before the render is even queued, so this isn't
        # just a style preference.
        log_info(f"restoring {len(restore_actions)} temporary change(s) made to the graph asset for this job")
        for restore_action in restore_actions:
            try:
                restore_action()
            except Exception as exc:
                log_warn(f"failed to restore a graph node/setting to its original state: {exc}")
        on_queue_finished_callback(executor, success)

    executor.on_executor_finished_delegate.add_callable_unique(_restore_graph_then_forward)
    executor.on_individual_job_work_finished_delegate.add_callable_unique(on_individual_job_finished_callback)
    executor.on_individual_shot_work_finished_delegate.add_callable_unique(on_individual_shot_finished_callback)

    log_info("______________________________________________________ Scene init done, starting to render... _____________________________________________________________________")
    subsystem.render_queue_with_executor_instance(executor)


def render_from_command_line():
    cmdTokens, cmdSwitches, cmdParameters = unreal.SystemLibrary.parse_command_line(unreal.SystemLibrary.get_command_line())
    render_args = GraphRenderArgs(cmdParameters)

    graph = unreal.load_asset(render_args.preset_path)
    if not graph:
        raise Exception(f"Graph not found: {render_args.preset_path}")

    if not isinstance(graph, unreal.MovieGraphConfig):
        # This script is only ever invoked from the MRG Renderer's command line template, so
        # -MoviePipelineConfig= should always point at a MovieGraphConfig. A legacy preset here
        # means the Renderer/template setup is wrong somewhere, not something to silently
        # recover from by delegating to unreal_render_50.RenderCommander.
        raise Exception(
            f"{render_args.preset_path} is a {graph.get_class().get_name()}, not a MovieGraphConfig - "
            "check that the MRG Renderer's command line template/-MoviePipelineConfig= is pointing "
            "at a Movie Render Graph asset, not a legacy preset."
        )

    render_new_graph_queue(render_args, graph)


def wait_for_asset_registry(delta_seconds):
    """Mirrors unreal_render_50.wait_for_asset_registry() - separate copy (rather than an
    import) so this script has no dependency on unreal_render_50's tick callback / globals
    beyond the plain helper functions imported above."""
    asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()
    if asset_registry.is_loading_assets():
        log_warn("Asset Registry still loading...")
        return

    global TICK_HANDLE
    unreal.unregister_slate_pre_tick_callback(TICK_HANDLE)
    TICK_HANDLE = None

    log_info("______________________________________________________ Streaming-Assets completed _____________________________________________________________________")
    render_from_command_line()


if __name__ == "__main__":
    log_info("_______________________________________________________ Unreal started ____________________________________________________________________")
    log_info("RR Movie Render Graph render module %rrVersion%")
    log_info("______________________________________________________ waiting while loading Streaming-Assets ___________________________________________________________________")
    TICK_HANDLE = unreal.register_slate_pre_tick_callback(wait_for_asset_registry)
