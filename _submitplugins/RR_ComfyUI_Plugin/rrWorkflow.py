# Author: Royal Render, Holger Schoenberger, Binary Alchemy
# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy
#
# Installation:
# Please copy the RR_ComfyUI_Plugin folder into your custom_nodes folder of ComfyUI.
# Note: If the RR_ROOT environment variable ist not defined (created when installing something via rrWorkstationInstaller), 
# then you need to edit the function "def getRR_Root()" top update the path to RR.
#


import os
from typing import Dict, Optional, Tuple
import time
from datetime import datetime
import uuid
from server import PromptServer
from aiohttp import web
import json
from pathlib import Path
import folder_paths
import argparse
import sys
import nodes
import inspect
import importlib
import importlib.metadata
from nodes import NODE_CLASS_MAPPINGS

##############################################
# Settings and their default                 #
##############################################


def get_model_config_path():
    
    DEBUG_ALL= True
    ret_yaml_path=""

    try:
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--extra-model-paths-config", action='append', nargs='*')
        args, _ = parser.parse_known_args()

        if args.extra_model_paths_config:
            flat_configs = [item for sublist in args.extra_model_paths_config for item in sublist]
            if flat_configs:
                cmd_path = os.path.realpath(flat_configs[-1])
                print(f"[rrSubmit] Commandline flag location {cmd_path}.")
                if os.path.isfile(cmd_path):
                    ret_yaml_path = cmd_path
                    print(f"[rrSubmit] Commandline flag, found in {ret_yaml_path}.")
                    if not DEBUG_ALL:
                        return ret_yaml_path
    except Exception as e:
        print(f"[rrSubmit] Error parsing arguments: {e}")

    main_mod = sys.modules.get('__main__')
    if main_mod and hasattr(main_mod, '__file__'):
        main_dir = os.path.dirname(os.path.realpath(main_mod.__file__))
        yaml_path= os.path.join(main_dir, "extra_model_paths.yaml")
        print(f"[rrSubmit] main_dir location {yaml_path}.")
        if os.path.isfile(yaml_path):
            ret_yaml_path= yaml_path
            print(f"[rrSubmit] main_dir, found in {ret_yaml_path}.")
            if not DEBUG_ALL:
                return ret_yaml_path

    if sys.argv and sys.argv[0]:
        argv_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
        yaml_path = os.path.join(argv_dir, "extra_model_paths.yaml")
        print(f"[rrSubmit] sys.argv[0] location {yaml_path}.")
        if os.path.isfile(yaml_path):
            ret_yaml_path= yaml_path
            print(f"[rrSubmit] sys.argv[0], found in {ret_yaml_path}.")
            if not DEBUG_ALL:
                return ret_yaml_path

    return ret_yaml_path

def get_workflow_path_RR():
    user_base_path = folder_paths.get_user_directory()
    workflow_path = os.path.join(user_base_path, "default", "workflows", "RR")
    return workflow_path





SETTINGS_KEY = "rrSubmit_CFG"

# Definition: intern_key -> {"default": value, "label": UI-Label, "type": "str/int/bool"}
SETTINGS_FIELDS = {
    "group_general": {"label": "General", "type": "separator", "section": "left"},
    "iteration_idxs_count": {"label": "Number of interations to process", "type": "int", "section": "left"},
    "seq_div_min": {"label": "Sequence Divide (Iteration chunk size)", "type": "int", "section": "left"},
    "gpu_mem_min": {"label": "Required GPU memory in GB", "type": "int", "section": "left"},

    "group_path": {"label": "Paths", "type": "separator", "section": "bottom"},
    "farm_workflow_path": {"label": "directory to save workflow dublicate for render farm", "type": "str", "section": "bottom"},
    "output_path": {"label": f"OPTIONAL: Override directory to save output to<br>DEFAULT:  {folder_paths.get_output_directory()}", "type": "str", "section": "bottom"},
    "model_config_yaml": {"label": f"OPTIONAL: Set extra_model_paths.yaml<br>DEFAULT:  None.  Your file: {get_model_config_path()}", "type": "str", "section": "bottom"},

    "model_group": {"label": "Models", "type": "separator", "section": "bottom"},
    "model_dir_farm": {"label": "Fileserver model directory", "type": "str", "section": "bottom"},
    "model_sync_mode": {
        "label": "!!!N/A yet!!!<br> Copy Mode",
        "type": "choice",
        "choices": [
                ("Do nothing", "none"),
                ("Add local models to existing", "Copy"),
                ("Sync local model (delete non-existing)", "Sync")
                ],
        "section": "bottom"
    },
    "model_dir_local": {"label": f"OPTIONAL: Override local model directory for copy<br>DEFAULT:  {folder_paths.models_dir}", "type": "str", "section": "bottom"},

    "nodes_group": {"label": "Custom Nodes", "type": "separator", "section": "bottom"},
    "nodes_dir_farm": {"label": "Fileserver custom_nodes directory", "type": "str", "section": "bottom"},
    "nodes_sync_mode": {
        "label": "!!!N/A yet!!!<br> Copy Mode",
        "type": "choice",
        "choices": [
                ("Do nothing", "none"),
                ("Add local models to existing", "Copy"),
                ("Sync local model (delete non-existing)", "Sync")
                ],
        "section": "bottom"
    },
    "nodes_dir_local": {"label": f"OPTIONAL: Override local custom_nodes directory for copy<br>DEFAULT:  {folder_paths.get_folder_paths('custom_nodes')[0]}", "type": "str", "section": "bottom"},


    "group_misc": {"label": "Misc", "type": "separator", "section": "middle"},
    "ui_submit": {"label": "UI rrSubmitter (off: Console)", "type": "bool", "section": "middle"},
    "replace_fileout": {"label": "!!!N/A yet!!!<br> (Replace fileout nodes with RR nodes)", "type": "bool", "section": "middle"},
    "add_seed": {"label": "Add rrSeed to all seed inputs", "type": "bool", "section": "middle"},
    "load_farm_workflow": {"label": "DEBUG: view farm workflow after submission", "type": "bool", "section": "middle"},

    "group_farm": {"label": "Farm settings", "type": "separator", "section": "right"},
    "use_portable": {"label": "Don't use ComfyUI Desktop, use ComfyUI Portable", "type": "bool", "section": "right"},
    "sync_models": {"label": "Sync fileserver model directory to local drive", "type": "bool", "section": "right"},
    "sync_nodes": {"label": "Sync fileserver custom_nodes directory to local drive", "type": "bool", "section": "right"},
    "auto_install_modules": {"label": "!!!N/A yet!!!<br> Auto install missing py modules for custom_nodes", "type": "bool", "section": "right"},
}

def settings_compute_default(key, RR_ROOT):
    if key == "iteration_idxs_count":
        return 1

    if key == "seq_div_min":
        return 1
    
    if key == "gpu_mem_min":
        return 8
    
    if key == "farm_workflow_path":
        return get_workflow_path_RR()
        #return os.path.join(RR_ROOT,"inhouse/compfyUI/")

    if key == "output_path":
        return "" 
    if key == "model_config":
        return "" 

    if key == "model_sync_mode":
        return SETTINGS_FIELDS["model_sync_mode"]["choices"][0][1] 
    if key == "nodes_sync_mode":
        return SETTINGS_FIELDS["model_sync_mode"]["choices"][0][1] 

    if key == "model_dir_local":
        return "" 
    if key == "nodes_dir_local":
        return "" 
        #This is an OPTIONAL OVERRIDE. We do not want to hardcode anything as someone might copy the file to some other location/workstation/project
        #return folder_paths.models_dir

    if key == "model_dir_farm":
        return os.path.join(RR_ROOT, "render_apps/renderer_plugins/ComfyUI/models_<rrJobVerMajor>")
    if key == "nodes_dir_farm":
        return os.path.join(RR_ROOT, "render_apps/renderer_plugins/ComfyUI/custom_nodes_<rrJobVerMajor>")

    if key == "ui_submit":
        return True

    if key == "replace_fileout":
        return True

    if key == "add_seed":
        return False

    if key == "load_farm_workflow":
        return False

    if key == "use_portable":
        return False
    if key == "sync_models":
        return False
    if key == "sync_nodes":
        return False
    if key == "auto_install_modules":
        return True

    return None
    



#####################################################################################
# This function has to be changed if an app should show info and error dialog box   #
#####################################################################################

def hasEnvDebugMode():
    debug_val = os.environ.get("DEBUG_MODE", "OFF").upper()
    if (debug_val in ["TRUE", "ON", "1"]) or True:
        return True
    
def hasEnvDebugMode_strict():  #no "or True" during  beta 
    debug_val = os.environ.get("DEBUG_MODE", "OFF").upper()
    if (debug_val in ["TRUE", "ON", "1"]):
        return True    

def writeInfo(msg):
    print("[rrSubmit] "+str(msg))

def writeError(msg):
    print("[rrSubmit-ERROR]: "+str(msg))

def writeDebug(msg):
    if (hasEnvDebugMode()):
        print("[rrSubmit-DGB] "+str(msg))






def get_workflow_settings(workflow, RR_ROOT):
    """
    Extracts the RR settings from the workflow data.
    Supports both dictionary-based input (Web API/JSON) and object-based input.
    """
    # 1. Access the 'extra' section safely based on the data type
    if isinstance(workflow, dict):
        #writeDebug("get_workflow_settings:  Workflow is a dictionary (from JS fetch/JSON)")
        # Case: Workflow is a dictionary (from JS fetch/JSON)
        if "extra" not in workflow:
            workflow["extra"] = {}
        
        # Ensure our specific settings key exists as a dictionary
        if SETTINGS_KEY not in workflow["extra"]:
            workflow["extra"][SETTINGS_KEY] = {}
            
        settings = workflow["extra"][SETTINGS_KEY]
    else:
        #writeDebug("get_workflow_settings:  Workflow is an object (legacy/internal ComfyUI structure)")
        # Case: Workflow is an object (legacy/internal ComfyUI structure)
        if not hasattr(workflow, 'extra'):
            workflow.extra = {}
        
        # setdefault ensures the key exists without overwriting existing data
        settings = workflow.extra.setdefault(SETTINGS_KEY, {})

    #writeDebug("get_workflow_settings: "+str(settings))

    # 2. Fill in missing fields with default values
    # This ensures your logic always finds the expected keys, 
    # even if the user never opened the settings modal in the browser.
    for key, info in SETTINGS_FIELDS.items():
        # Skip UI-only elements like separators
        if info.get("type") == "separator":
            continue
            
        if key not in settings:
            # Calls your computation logic from the logic file
            settings[key] = settings_compute_default(key, RR_ROOT)
    return settings

    



'''
CHECKPOINT_TYPES = {"CheckpointLoaderSimple", "CheckpointLoader", "UNETLoader"}
def workflow_hasCheckpoint(workflow: Dict) -> bool:
    """
    Prüft, ob im Workflow ein Checkpoint-Loader vorhanden ist.
    """
    nodes_data = workflow.get("nodes")
    # UI Format
    if isinstance(nodes_data, list):
        return any(node.get("type") in CHECKPOINT_TYPES for node in nodes_data)
    # API Format
    return any(node.get("class_type") in CHECKPOINT_TYPES for node in workflow.values() if isinstance(node, dict))
    '''

def workflow_has_any_loader(workflow: dict) -> bool:
    """
    Checks if the workflow has any data source:
    - Model Loaders (Checkpoint, Lora, ControlNet, etc.)
    - Image/Video Loaders (Load Image, Load Video, etc.)
    """
    # Define keywords that identify a source node
    # 'loader' covers models, 'load' covers images/media
    source_keywords = ["loader", "loadimage", "load_image", "loadvideo"]

    # Case 1 - UI Format
    if "nodes" in workflow and isinstance(workflow["nodes"], list):
        for node in workflow["nodes"]:
            node_type = str(node.get("type", "")).lower()
            if any(key in node_type for key in source_keywords):
                return True

    # Case 2 - API/Prompt Format
    # We check both top-level keys and values to be safe
    for node_data in workflow.values():
        if isinstance(node_data, dict):
            class_type = str(node_data.get("class_type", "")).lower()
            if any(key in class_type for key in source_keywords):
                return True
                
    return False
    


def _compute_vars(path: str, image_width: int = 0, image_height: int = 0) -> str:
    """
    Replace ComfyUI-style variables in a path string.
    """
    path = path.replace("%width%", str(image_width))
    path = path.replace("%height%", str(image_height))
    now = time.localtime()
    path = path.replace("%year%", str(now.tm_year))
    path = path.replace("%month%", str(now.tm_mon).zfill(2))
    path = path.replace("%day%", str(now.tm_mday).zfill(2))
    path = path.replace("%hour%", str(now.tm_hour).zfill(2))
    path = path.replace("%minute%", str(now.tm_min).zfill(2))
    path = path.replace("%second%", str(now.tm_sec).zfill(2))
    return path
        
        
OUTPUT_FILENAME_KEYS = ["path", "filename", "output_path"]        
def _get_output_info(node: Dict) -> Tuple[Optional[str], Optional[str], bool]:
    """
    Returns (outName, outExt, isVideo)
    Works for both API format (inputs dict) and UI format (widgets_values list).
    """
    if not isinstance(node, dict):
        return None, None, False

    class_type = node.get("class_type", node.get("type", "Unknown"))
    inputs = node.get("inputs", {})
    widgets = node.get("widgets_values", [])
    
    base_name = None
    
    # CASE 1: Standard API Format (inputs is a dict)
    if isinstance(inputs, dict) and inputs:
        keys_to_check = ["filename_prefix", "filename", "file_name", "output_path", "prefix"]
        for key in keys_to_check:
            val = inputs.get(key)
            if val is not None:
                # ComfyUI often wraps values in lists [value, index]
                actual_val = val[0] if isinstance(val, list) and val else val
                if isinstance(actual_val, str) and actual_val.strip():
                    base_name = _compute_vars(actual_val, 0, 0)
                    break

    # CASE 2: UI Format fallback (values are in a flat list)
    if not base_name and isinstance(widgets, list) and len(widgets) > 0:
        # Usually, the first string in widgets_values is the filename/prefix
        for w in widgets:
            if isinstance(w, str) and len(w) > 1:
                base_name = _compute_vars(w, 0, 0)
                break
    
    if not base_name:
        return None, None, False

    # Extension & Video Logic
    ext = ".png"
    is_video = False
    low_class = class_type.lower()
    
    # Check for video nodes
    video_keywords = ["video", "vhs", "savevideo", "animation"]
    if any(kw in low_class for kw in video_keywords):
        fmt = "mp4"
        if isinstance(inputs, dict):
            fmt = inputs.get("format", inputs.get("container", "mp4"))
            if isinstance(fmt, list): 
                fmt = fmt[0]
        elif isinstance(widgets, list):
            # Fallback for UI format: look for format strings in widgets
            for w in widgets:
                if isinstance(w, str) and w.lower() in ["mp4", "mkv", "avi", "mov", "gif"]:
                    fmt = w
                    break
        
        ext = f".{str(fmt).lower().lstrip('.')}"
        if ext not in [".png", ".jpg", ".jpeg", ".tiff", ".webp"]:
            is_video = True

    # Image sequence padding
    if not is_video:
        if "###" not in base_name and "%" not in base_name:
            base_name = f"{base_name}###"

    return base_name, ext, is_video


def getOutput(workflow: Dict, use_node_id: str):
    if not workflow:
        raise Exception("rrSubmit - Empty workflow data.")

    out_name = "noDir/no.frame"
    out_ext = ".check"
    out_node_ID = use_node_id
    is_video = False
    found_output = False

    # OUTPUT_NODE lookup aus NODE_CLASS_MAPPINGS bauen
    from nodes import NODE_CLASS_MAPPINGS
    output_node_types = set()
    for node_type, node_class in NODE_CLASS_MAPPINGS.items():
        if getattr(node_class, "OUTPUT_NODE", False):
            output_node_types.add(node_type)
            if "preview" in node_type:
                continue

    nodes_data = workflow.get("nodes")
    if not isinstance(nodes_data, list):
        raise Exception("rrSubmit - No nodes list found in workflow.")

    def get_node_by_id(target_id):
        target_str = str(target_id)
        return next((n for n in nodes_data if str(n.get("id")) == target_str), None)

    # 1. Gezielte Node-ID Suche
    if use_node_id:
        target_node = get_node_by_id(use_node_id)
        if target_node:
            res_name, res_ext, res_video = _get_output_info(target_node)
            if res_name:
                return use_node_id, res_name, res_ext, res_video
            else:
                writeInfo(f"Requested Node {use_node_id} found, but no filename extracted.")
                return out_node_ID, out_name, out_ext, is_video
        else:
            raise Exception(f"[rrSubmit] Warning: Requested Node ID {use_node_id} not found.")

    # 2. Automatische Suche: nur echte Output-Nodes mit Dateinamen
    writeInfo( "getOutput: Trying to find any output node as main output.")
    writeInfo(f"getOutput: Collected outpoutnode classes '{output_node_types}'.")
    for node in nodes_data:

        node_type = node.get("type", node.get("class_type", ""))
        node_id = node.get("id")

        # Problem 2: IDs wie "123:59" als String belassen
        node_id_str = str(node_id)
        # Bypassed nodes ignorieren (mode 4 = bypassed in ComfyUI)
        if node.get("mode", 0) == 4:
            continue

        # Nur Nodes die OUTPUT_NODE = True haben
        if node_type not in output_node_types:
            continue

        # _get_output_info gibt None zurück wenn kein Dateiname gefunden → Preview-Nodes werden so automatisch ignoriert
        res_name, res_ext, res_video = _get_output_info(node)
        if res_name:
            out_node_ID = node_id_str
            out_name = res_name
            out_ext = res_ext
            is_video = res_video
            found_output = True
            writeDebug(f"Found output node #{out_node_ID} '{res_name}' '{res_ext}'")
            break
        

    if not found_output:
        writeInfo("WARNING: No output nodes found in workflow.")

    return out_node_ID, out_name, out_ext, is_video
    
def disable_Outputs(workflow: Dict, submit_node_id: str):
    """
    Deaktiviert alle Output-Nodes außer submit_node_id.
    Wenn submit_node_id leer, werden alle Output-Nodes mit "preview" im Klassennamen deaktiviert.
    """
    from nodes import NODE_CLASS_MAPPINGS

    if submit_node_id:
        writeInfo(f"disable_Outputs: disabling all beside node #{submit_node_id}.")
    else:
        writeInfo("disable_Outputs: no submit_node_id specified, disabling preview only.")

    # OUTPUT_NODE lookup bauen
    output_node_types = set()
    for node_type, node_class in NODE_CLASS_MAPPINGS.items():
        if getattr(node_class, "OUTPUT_NODE", False):
            output_node_types.add(node_type)

    nodes_data = workflow.get("nodes")
    if not isinstance(nodes_data, list):
        return workflow

    for node in nodes_data:
        node_type = node.get("type", node.get("class_type", ""))

        if node_type not in output_node_types:
            continue

        node_id_str = str(node.get("id", ""))

        if submit_node_id:
            # Alle Output-Nodes außer submit_node_id deaktivieren
            if node_id_str != str(submit_node_id):
                node["mode"] = 4
                writeInfo(f"Disabled output node: {node_id_str} ({node_type})")
            elif (node.get("mode", 4) == 4):
                node["mode"] = 0
                writeInfo(f"Enabled output node: {node_id_str} ({node_type})")
        
        else:
            # Kein submit_node_id: nur Preview-Nodes deaktivieren
            if "preview" in node_type.lower():
                node["mode"] = 4
                writeInfo(f"Disabled output node: {node_id_str} ({node_type})")
    return workflow


 

conversion_results = {}

def send_to_frontend(event, data):
    # Nutzt den ComfyUI PromptServer um eine Nachricht an alle Browser-Clients zu schicken
    PromptServer.instance.send_sync(event, data)

def check_for_conversion_result(request_id):
    # Holt das Ergebnis spezifisch für die request_id ab
    # English comment: pop removes the entry from the dict after reading it
    return conversion_results.pop(request_id, None)
    
    

@PromptServer.instance.routes.post("/rr/conversion_done")
async def conversion_done_callback(request):
    json_data = await request.json()
    req_id = json_data.get("request_id")
    api_prompt = json_data.get("api_prompt")
    
    # Speichere das Ergebnis, damit convert_ui_to_api_dynamic es findet
    conversion_results[req_id] = api_prompt
    return web.json_response({"status": "ok"})
    



def build_seed_control_lookup():
    """
    Liest alle registrierten Nodes aus und findet INT inputs mit control_after_generate.
    Returns: { "NodeType": ["input_name1", "input_name2"] }
    """
    lookup = {}
    
    for node_type, node_class in NODE_CLASS_MAPPINGS.items():
        try:
            input_types = node_class.INPUT_TYPES()
        except Exception:
            continue
        
        all_inputs = {}
        all_inputs.update(input_types.get("required", {}))
        all_inputs.update(input_types.get("optional", {}))
        
        for input_name, input_def in all_inputs.items():
            if not isinstance(input_def, (list, tuple)) or len(input_def) < 2:
                continue
            input_type = input_def[0]
            input_opts = input_def[1] if isinstance(input_def[1], dict) else {}
            
            if input_type == "INT" and input_opts.get("control_after_generate"):
                if node_type not in lookup:
                    lookup[node_type] = []
                lookup[node_type].append(input_name)
    
    return lookup

_seed_control_lookup = None

def get_seed_control_lookup():
    global _seed_control_lookup
    if _seed_control_lookup is None:
        _seed_control_lookup = build_seed_control_lookup()
    return _seed_control_lookup


CONTROL_VALUES = {"randomize", "increment", "decrement", "fixed"}

def extract_seed_control_map(workflow_ui):
    node_controlled_inputs = get_seed_control_lookup()  # { "NodeType": ["input_name", ...] }
    seed_control_map = {}
    CONTROL_VALUES = {"randomize", "increment", "decrement", "fixed"}
    
    for node in workflow_ui.get("nodes", []):
        node_type = node.get("type", "")
        node_id = str(node.get("id"))
        widgets_values = node.get("widgets_values", [])
        
        controlled_inputs = node_controlled_inputs.get(node_type, [])
        if not controlled_inputs:
            continue
        
        widget_index = 0
        for inp in node.get("inputs", []):
            if "widget" not in inp:
                continue
            
            inp_name = inp.get("name")
            if inp_name in controlled_inputs and inp.get("link") is None:
                ctrl_index = widget_index + 1
                if ctrl_index < len(widgets_values):
                    value = widgets_values[ctrl_index]
                    if value in CONTROL_VALUES:
                        if node_id not in seed_control_map:
                            seed_control_map[node_id] = {}
                        seed_control_map[node_id][inp_name] = value
            
            widget_index += 1
    
    return seed_control_map



def convert_ui_to_api_dynamic(workflow_ui):
    """
    Triggert die Konvertierung im JS-Frontend und wartet auf das Ergebnis.
    """
    if ("nodes" not in workflow_ui) or (not isinstance(workflow_ui["nodes"], list)):
        print("convert_ui_to_api_dynamic: Not an UI format")

    seed_control_map = extract_seed_control_map(workflow_ui)

    # 1. Eindeutige ID für diesen spezifischen Request erstellen
    request_id = str(uuid.uuid4())
    
    # 2. Den Request ans Frontend senden (inkl. der ID)
    send_to_frontend("RR_CONVERT_REQUEST", {
        "workflow": workflow_ui,
        "request_id": request_id
    })
    
    # 3. Warten, bis das Ergebnis mit DIESER ID eintrifft
    api_prompt = None
    timeout = 10.0  # Sekunden
    start_time = time.time()
    
    while api_prompt is None:
        # Hier geben wir die request_id mit!
        api_prompt = check_for_conversion_result(request_id)
        
        if (time.time() - start_time) > timeout:
            raise TimeoutError(f"Frontend conversion timed out for request {request_id}")
            
        time.sleep(0.1) # Kurze Pause um die CPU zu schonen
    
    for node_id, controls in seed_control_map.items():
        if node_id in api_prompt:
            api_prompt[node_id]["_meta"]["rr_seed_control"] = controls

    return sort_comfy_api_workflow(api_prompt)
    
    
    
def compare_workflows(generated_api, original_api):
    differences = []

    # Check for missing or extra nodes
    gen_nodes = set(generated_api.keys())
    orig_nodes = set(original_api.keys())
    
    missing_in_gen = orig_nodes - gen_nodes
    extra_in_gen = gen_nodes - orig_nodes
    
    if missing_in_gen:
        differences.append(f"Nodes missing in manual API: {list(missing_in_gen)}")
    if extra_in_gen:
        differences.append(f"Extra nodes in manual API: {list(extra_in_gen)}")

    # Compare common nodes
    common_nodes = gen_nodes & orig_nodes
    for node_id in sorted(common_nodes, key=lambda x: int(x) if x.isdigit() else x):
        gen_node = generated_api[node_id]
        orig_node = original_api[node_id]
        
        # Check class_type
        if gen_node.get("class_type") != orig_node.get("class_type"):
            differences.append(f"Node {node_id:3}: Type mismatch. Gen: {gen_node.get('class_type')} | Orig: {orig_node.get('class_type')}")
            
        # Compare inputs deeply
        gen_inputs = gen_node.get("inputs", {})
        orig_inputs = orig_node.get("inputs", {})
        
        all_input_keys = set(gen_inputs.keys()) | set(orig_inputs.keys())
        for key in sorted(all_input_keys):
            val_gen = gen_inputs.get(key)
            val_orig = orig_inputs.get(key)
            
            # Use strict comparison for values and links
            if val_gen != val_orig:
                # Provide granular detail for each failing input
                key_str = f"'{key}'".ljust(25)
                differences.append(f"Node {node_id:3} Input '{key_str}': Value mismatch. Generated: {val_gen} | Original: {val_orig}")

    if differences:
        # Construct a complete error report for the console/log
        error_summary = "\n".join(differences)
        raise Exception(f"Workflow Validation Failed - Differences found:\n{error_summary}")
    
    return True
    


def sort_comfy_api_workflow(api_workflow):
    """
    Sorts a ComfyUI API workflow:
    1. Top-level Node IDs are sorted numerically.
    2. Internal dictionaries (like 'inputs') are sorted alphabetically by key.
    """
    from collections import OrderedDict
    if not isinstance(api_workflow, dict):
        return api_workflow

    # Sort the top-level node IDs numerically
    # does not work with group IDs "12:34" 
    # sorted_node_ids = sorted(api_workflow.keys(), key=lambda x: int(x) if x.isdigit() else x)

    # Sort keys as plain strings (no int conversion, no error)
    sorted_node_ids = sorted(api_workflow.keys())

    sorted_workflow = OrderedDict()
    
    for node_id in sorted_node_ids:
        node_data = api_workflow[node_id]
        
        sorted_node = {}
        for key, value in node_data.items():
            if isinstance(value, dict):
                # Sort sub-dictionaries like 'inputs' alphabetically by key
                sorted_node[key] = dict(sorted(value.items()))
            else:
                sorted_node[key] = value
                
        sorted_workflow[node_id] = sorted_node
        
    return dict(sorted_workflow)
    




SEED_FIELD_NAMES = {"seed", "noise_seed", "rand_seed", "random_seed", "seed_value"}

def swap_to_rr_nodes(workflow, outNodeID, outName, outExt, isVideo, global_output_path, settings):
    if "nodes" not in workflow:
        return workflow
        
    nodes = workflow["nodes"]
    links = workflow.get("links", [])
    
    outFixedFilename= False
    seed_node_id = None
    #  Use the new rrSeed type
    rrSeed_node = next((n for n in nodes if n["type"] == "rrSeed"), None)
    
    setting_replace_fileout= settings.get('replace_fileout')
    setting_replace_fileout= False #not tested yet
    setting_add_seed= settings.get('add_seed')
    setting_add_seed= False #not tested yet

    if setting_add_seed or setting_replace_fileout:
        if not rrSeed_node:
            seed_node_id = 999999
            rrSeed_node = {
                "id": seed_node_id,
                "type": "rrSeed",
                "pos": [100, 100], 
                "widgets_values": [0, 1], # [base_seed, iteration_idx]
                "inputs": [],
                "flags": {},
                "order": 0 
            }
            nodes.append(rrSeed_node)
        else:
            seed_node_id = rrSeed_node["id"]

    # --- PART 2: Node Replacement ---
    for node in nodes:
        current_id = str(node.get("id"))
        current_type = node.get("type")

        if setting_replace_fileout:
            is_target_node = (current_id == str(outNodeID))
            
            # --- CASE 1: Save Image (rrSaveImage) ---
            if current_type == "SaveImage":
                outFixedFilename=True
                node["type"] = "rrSaveImage"
                if is_target_node:
                    #  Set filename_prefix only. 
                    #  iteration_idx is usually an input from rrSeed
                    node["widgets_values"] = [outName] 
                
                if seed_node_id:
                    #  Connect the iteration_idx output (S2) of rrSeed to the node
                    inject_link(seed_node_id, 2, node["id"], "iteration_idx", links, node)

            # --- CASE 2: Save Video (rrSaveVideo) ---
            elif current_type in ["SaveVideo", "Save Video", "VideoCombine"]:
                node["type"] = "rrSaveVideo"
                outFixedFilename=True
                if is_target_node:
                    #  Mapping outExt to dropdown
                    ext = outExt.lower().replace(".", "")
                    final_format = "mp4" if ext == "mp4" else "auto"
                    
                    #  Widgets: [filename_prefix, format, codec]
                    node["widgets_values"] = [outName, final_format, "h264"]
                
                if seed_node_id:
                    #  Optional: Connect iteration_idx for filename labeling
                    inject_link(seed_node_id, 2, node["id"], "iteration_idx", links, node)

    workflow["nodes"] = nodes
    workflow["links"] = links
    return workflow, outFixedFilename


def inject_link(src_id, src_out_idx, dst_id, dst_input_name, links, dst_node, src_node):
    if "inputs" not in dst_node:
        dst_node["inputs"] = []
    
    # 1. Neue Link-ID generieren
    valid_links = [lk for lk in links if lk]
    new_link_id = max([lk[0] for lk in valid_links] or [0]) + 1
    
    writeDebug(f"[inject_link] Creating link {new_link_id}") # English comment: Generating link ID

    # 2. Ziel-Input setzen
    target_input = next((i for i in dst_node["inputs"] if i.get("name") == dst_input_name), None)
    if not target_input:
        target_input = {"name": dst_input_name, "type": "INT", "link": new_link_id}
        dst_node["inputs"].append(target_input)
    else:
        target_input["link"] = new_link_id

    slot_idx = next(idx for idx, i in enumerate(dst_node["inputs"]) if i["name"] == dst_input_name)
    
    # 3. Source Node (rrSeed) Outputs - Hier liegt der Fix für die Geister-Verschiebung
    if "outputs" not in src_node or not src_node["outputs"]:
        # Initialisierung mit None statt [] für ungenutzte Links
        src_node["outputs"] = [
            {"name": "SEED", "type": "INT", "links": None, "slot_index": 0},
            {"name": "SEED_2", "type": "INT", "links": None, "slot_index": 1},
            {"name": "iteration_idx", "type": "INT", "links": None, "slot_index": 2},
            {"name": "iteration_idx_str", "type": "STRING", "links": None, "slot_index": 3}
        ]
    
    # Link eintragen: Wenn None, dann Liste erstellen, sonst anhängen
    target_out = src_node["outputs"][src_out_idx]
    if target_out.get("links") is None:
        target_out["links"] = [new_link_id]
    else:
        if new_link_id not in target_out["links"]:
            target_out["links"].append(new_link_id)
    
    # 4. Globalen Link-Eintrag hinzufügen
    links.append([new_link_id, src_id, src_out_idx, dst_id, slot_idx, "INT"])
    return new_link_id



def add_rrSeed(workflow):
    writeDebug("--- add_rrSeed Start ---") # English comment: Start seed injection with safety check
    if hasEnvDebugMode_strict(): 
        save_workflow("e:\\2D\\temp", "DEBUG_rrSeed_a_", workflow, None, None, None, None)    

    #import copy
    #clean_workflow = copy.deepcopy(workflow)
    #return clean_workflow
   
    nodes = workflow.get("nodes", [])
    links = workflow.get("links", []) or []
    
    # 1. rrSeed Node finden oder erstellen
    rr_node = next((n for n in nodes if n and n.get("type") == "rrSeed"), None)
    
    if not rr_node:
        seed_node_id = max([n.get("id", 0) for n in nodes] or [0]) + 1
        rr_node = {
            "id": seed_node_id, 
            "type": "rrSeed", 
            "pos": [100, 100],
            "size": [315, 150],
            "widgets_values": [0, None, 1, "increment", 1152921504606847000, 1152921504606847000],
            "outputs": [
                {"name": "SEED", "type": "INT", "links": None, "slot_index": 0, "localized_name": "SEED"},
                {"name": "SEED_2", "type": "INT", "links": None, "slot_index": 1, "localized_name": "SEED_2"},
                {"name": "iteration_idx", "type": "INT", "links": None, "slot_index": 2, "localized_name": "iteration_idx"},
                {"name": "iteration_idx_str", "type": "STRING", "links": None, "slot_index": 3, "localized_name": "iteration_idx_str"}
            ],
            "inputs": [], "flags": {}, "order": 0,
            "properties": {"Node name for S&R": "rrSeed"}
        }
        nodes.append(rr_node)
        workflow["last_node_id"] = max(workflow.get("last_node_id", 0), seed_node_id)
        writeDebug(f"Created rrSeed {seed_node_id}") # English comment: Log node creation
    
    seed_node_id = rr_node["id"]

    # 2. Sampler loopen
    for node in nodes:
        if not node or node["id"] == seed_node_id: 
            continue
        
        target_slot = None
        current_type = node.get("type")
        if current_type in ["KSampler", "Seed (rgthree)"]: 
            target_slot = "seed"
        elif current_type in ["KSamplerAdvanced", "RandomNoise"]: 
            target_slot = "noise_seed"
        
        # Fallback: scan all input slots for seed-like names
        if not target_slot:
            node_inputs = node.get("inputs", [])
            for inp in node_inputs:
                inp_name = (inp.get("name") or inp.get("label") or "").lower()
                if any(seed_name in inp_name for seed_name in SEED_FIELD_NAMES):
                    target_slot = inp.get("name")
                    break

        if target_slot:
            node_inputs = node.get("inputs", [])
            target_input = next((i for i in node_inputs if i.get("name") == target_slot), None)
            
            # Die ID des aktuellen Links (falls vorhanden)
            current_link_id = target_input.get("link") if target_input else None
            
            # WICHTIG: Wenn IRGENDEIN Link existiert, wird dieser Node ignoriert
            if current_link_id is not None:
                writeDebug(f"Skip: Node {node['id']} already has a link ({current_link_id}) in {target_slot}") # English comment: Skip occupied slot
                continue
            
            # Nur wenn der Slot komplett leer (null) ist, wird verlinkt
            inject_link(seed_node_id, 0, node["id"], target_slot, links, node, rr_node)

    # 3. Header Sync
    workflow["links"] = links
    workflow["last_link_id"] = max([li[0] for li in links if li] or [0])
    if hasEnvDebugMode_strict(): 
        save_workflow("e:\\2D\\temp", "DEBUG_rrSeed_b_", workflow, None, None, None, None)    
    return workflow




def safe_make_dirs_for_file(file_path_str):
    """
    Ensures the directory for a given file path exists, but only if the 
    base structure (3 levels up from the file) is already present.
    Example: For '.../share/projekt/comfyUI/temp/file.json', it checks if '.../share/projekt/' exists.
    """
    file_path = Path(file_path_str)
    # .parent is the folder 'tempfiles'
    target_dir = file_path.parent
    # .parent.parent.parent is the base 'projekt'
    base_structure = target_dir.parent.parent
    
    if base_structure.exists() and base_structure.is_dir():
        if not target_dir.exists():
            # Create the folder structure up to 'tempfiles'
            os.makedirs(target_dir, exist_ok=True)
            writeDebug(f"Directory created: {target_dir}")
        return True
    else:
        # Safety trigger: Base structure is missing
        error_msg = f"Safety Error: Base path '{base_structure}' not found. Check your server connection or mapping."
        writeError(error_msg)
        # You might want to raise an exception here to catch it in your handler
        raise Exception(error_msg)
        

def save_workflow(filepath, workflowName, workflowHybrid, workflowApiRR, workflowUI, INFO_outNodeID, INFO_outFixedFilename):
        final_json = workflowHybrid 
        if (workflowApiRR):
            #writeDebug("save_workflow has workflowApiRR")
            final_json["api_format_rr"] = workflowApiRR 
        else:
            #writeDebug("save_workflow NO workflowApiRR")
            try:
                del final_json["api_format_rr"]
            except Exception:
                pass
        if (workflowUI):
            final_json["ui"] = workflowUI 
        else:
            try:
                del final_json["ui"]
            except Exception:
                pass

        if (workflowUI):
            #no metadata for non-final debug exports
            try:
                if "rr_metadata" not in final_json:
                    final_json["rr_metadata"] = {}
                final_json["rr_metadata"].update({
                    "version": "1.0",
                    "layer_node_id": str(INFO_outNodeID),
                    "fixed_filename": str(INFO_outFixedFilename)
                    })
            except Exception:
                pass

        
        #save dublicate of workflow 
        timestamp = datetime.now().strftime("%m%d-%H%M%S") #datetime.now().strftime("%y%m%d-%H%M%S")
        if ("DEBUG_" in workflowName) or (hasEnvDebugMode_strict()):
            filename = f"RR{timestamp}_{workflowName}__.json"
        else:
            filename = f"RR_{workflowName}__{timestamp}.json"
        if len(filepath) <3: 
            raise Exception("farm_workflow_path not set in RRs workflow settings")
        filepath = os.path.join(filepath, filename)
        success = safe_make_dirs_for_file(filepath)
        if not success:
            raise Exception("Unable to create folder "+str(filepath))

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(final_json, f, indent=2)
        writeInfo(f"Workflow saved to {filepath}")

        if hasEnvDebugMode_strict():
            if (workflowApiRR):
                with open(filepath.replace(".json","")+"_apiRR.json", "w", encoding="utf-8") as f:
                    json.dump(workflowApiRR, f, indent=2)
            if workflowHybrid.get("api_export_comfy", {}):
                with open(filepath.replace(".json","")+"_apiComfy.json", "w", encoding="utf-8") as f:
                    json.dump(workflowHybrid.get("api_export_comfy", {}), f, indent=2)
            if ("rr_metadata" in workflowHybrid) and ("summary" in workflowHybrid["rr_metadata"]):
                with open(filepath.replace(".json","")+"_summary.json", "w", encoding="utf-8") as f:
                    json.dump(workflowHybrid["rr_metadata"]["summary"], f, indent=2)
            if (workflowUI):
                with open(filepath.replace(".json","")+"_UI.json", "w", encoding="utf-8") as f:
                    json.dump(workflowUI, f, indent=2)
        return filepath
        





# -----------------------------
# Node Info Extraction
# -----------------------------
def get_node_info(node_type):
    mapping = getattr(nodes, "NODE_CLASS_MAPPINGS", {})
    node_class = mapping.get(node_type)

    if not node_class:
        return {
            "installed": False,
            "path": "",
            "module_name": "",
            "package_name": "",
            "module_version": "",
            "is_custom_node": False,
        }

    try:
        file_path = inspect.getfile(node_class)
        abs_path = os.path.abspath(file_path)

        module_name = node_class.__module__
        is_custom_node = "custom_nodes" in abs_path

        module = importlib.import_module(module_name)
        module_version = getattr(module, "__version__", "")

        package_name = module_name.split(".")[0]
        try:
            package_version = importlib.metadata.version(package_name)
        except Exception:
            package_version = ""

        return {
            "installed": True,
            "path": abs_path,
            "module_name": module_name,
            "package_name": package_name,
            "module_version": module_version or package_version,
            "is_custom_node": is_custom_node,
        }

    except Exception:
        return {
            "installed": True,
            "path": "Core / Built-in",
            "module_name": "",
            "package_name": "",
            "module_version": "",
            "is_custom_node": False,
        }

def print_workflow_format(workflow, location):
    if not isinstance(workflow, dict):
        print(f"{location}: workflow is an Invalid/Unknown format")
        #print("\n" + "="*80)
        #print(f"{workflow}")
        #print("\n" + "="*80)
        return

    # UI-Format Check
    # Das UI-Format hat immer ein Top-Level Feld 'nodes' (als Liste)
    if "nodes" in workflow and isinstance(workflow["nodes"], list):
        print(f"{location}: workflow is UI format")
        if workflow.get("api_export_comfy", {}):
            print(f"{location}: found api_export_comfy")

        return 

    # API-Format Check
    # Im API-Format sind die Top-Level Keys die IDs der Nodes.
    # Wir prüfen, ob die erste "Node" ein 'class_type' Feld besitzt.
    if len(workflow) > 0:
        # Wir nehmen einen beliebigen Key aus dem Dictionary
        first_key = next(iter(workflow))
        first_node = workflow[first_key]
        
        if isinstance(first_node, dict) and "class_type" in first_node:
            print(f"{location}: workflow is API format")
            return

    print(f"{location}: workflow is an Unknown Format")


def analyze_workflow_detailed(workflow):
 
    analysis = {"nodes": [], "models": [], "summary": {}}

    seen_node_types = set()

    #UI format. It contains missing nodes, but is bad to extract data 
    if not isinstance(workflow, dict) or "nodes" in workflow:
        # 1. Schritt: Unbekannte Nodes direkt aus dem UI-Workflow sichern
        # Bevor sie bei der Konvertierung verloren gehen
        if isinstance(workflow, dict) and "nodes" in workflow:
            mapping = getattr(nodes, "NODE_CLASS_MAPPINGS", {})
            for node in workflow.get("nodes", []):
                node_type = node.get("type")
                if node_type and node_type not in mapping:
                    if node_type not in seen_node_types:
                        analysis["nodes"].append({
                            "type": node_type,
                            "installed": False,
                            "path": "",
                            "module_name": "Unknown (Not Installed)",
                            "is_custom_node": True
                        })
                        seen_node_types.add(node_type)

        #if hasEnvDebugMode_strict(): 
        #    save_workflow("e:\\2D\\temp", "DEBUG_Analyze_UI__", workflow, None, None, None, None)

        
        workflow = convert_ui_to_api_dynamic(workflow)

    #if hasEnvDebugMode_strict(): 
    #    save_workflow("e:\\2D\\temp", "DEBUG_Analyze_API_", workflow, None, None, None, None)



    seen_nodes = set()
    seen_models = set()
    node_outputs = {}  # node_id -> list of (filename, category)
    mapping = getattr(nodes, "NODE_CLASS_MAPPINGS", {})

    # -----------------------------
    # Pass 1: detect loader nodes
    # -----------------------------
    for node_id, node_data in workflow.items():
        node_type = node_data.get("class_type")
        if not node_type:
            continue

        node_id = str(node_id)  # normalize

        # Node info
        if node_type not in seen_nodes:
            node_info = get_node_info(node_type)
            analysis["nodes"].append({"type": node_type, **node_info})
            seen_nodes.add(node_type)

        inputs = node_data.get("inputs", {})
        loader_output = []

        # Map known loader nodes to category
        if node_type == "CheckpointLoaderSimple":
            ckpt = inputs.get("ckpt_name")
            if ckpt:
                loader_output.append((ckpt, "checkpoints"))
        elif node_type == "VAEFileLoader":
            vae = inputs.get("vae")
            if vae:
                loader_output.append((vae, "vae"))
        elif node_type == "LoraLoader":
            lora = inputs.get("lora_file")
            if lora:
                loader_output.append((lora, "loras"))
        elif node_type == "ControlNetLoader":
            cn = inputs.get("model")
            if cn:
                loader_output.append((cn, "controlnets"))
        elif node_type == "CLIPTextEncode":
            emb = inputs.get("clip")
            if emb and isinstance(emb, str):
                loader_output.append((emb, "embeddings"))
        elif node_type in ["CheckpointLoaderXL", "CheckpointLoaderSDXL"]:
            ckpt = inputs.get("ckpt_name")
            if ckpt:
                loader_output.append((ckpt, "checkpoints"))

        if loader_output:
            node_outputs[node_id] = loader_output

    # -----------------------------
    # Pass 2: Direkte Modell-Erkennung (API-Format optimiert)
    # -----------------------------
    # Mapping von Input-Keys zu folder_paths Kategorien
    model_key_map = {
        "ckpt_name": "checkpoints",
        "lora_name": "loras",
        "lora_file": "loras",
        "vae_name": "vae",
        "vae": "vae",
        "control_net_name": "controlnets",
        "model_name": "checkpoints", # Manche Custom Nodes nutzen dies
        "clip_name": "clip",
        "upscale_model": "upscale_models"
    }

    for node_id, node_data in workflow.items():
        inputs = node_data.get("inputs", {})
        
        for input_name, input_value in inputs.items():
            # Wir prüfen nur Strings (Dateinamen)
            if isinstance(input_value, str):
                category = model_key_map.get(input_name)
                
                # Falls der Key unbekannt ist, machen wir einen heuristischen Check:
                # Endet die Datei auf eine Modell-Endung?
                if not category:
                    if any(input_value.lower().endswith(ext) for ext in folder_paths.supported_pt_extensions):
                        # Wir raten die Kategorie basierend auf dem Node-Typ oder suchen alle durch
                        for cat in folder_paths.folder_names_and_paths.keys():
                            if folder_paths.get_full_path(cat, input_value):
                                category = cat
                                break
                
                if category:
                    key = (category, input_value)
                    if key not in seen_models:
                        full_path = folder_paths.get_full_path(category, input_value)
                        analysis["models"].append({
                            "category": category,
                            "filename": input_value,
                            "found": bool(full_path),
                            "path": os.path.abspath(full_path) if full_path else ""
                        })
                        seen_models.add(key)

    # -----------------------------
    # Summary
    # -----------------------------
    total_nodes = len(analysis["nodes"])
    custom_nodes = sum(1 for n in analysis["nodes"] if n.get("is_custom_node"))
    missing_nodes = sum(1 for n in analysis["nodes"] if not n.get("installed"))
    total_models = len(analysis["models"])
    models_missing = sum(1 for m in analysis["models"] if not m.get("found"))

    analysis["summary"] = {
        "total_nodes": total_nodes,
        "custom_nodes": custom_nodes,
        "missing_nodes": missing_nodes,
        "total_models": total_models,
        "models_missing": models_missing
    }

    return analysis



def print_workflow_analysis(analysis_dict):
    """Gibt die Analyse in einer sauberen Tabelle aus. Header erscheinen immer."""
    
    # --- NODES SEKTION ---
    print("\n" + "="*120)
    print(f"{'Node Name (Title)':<25} | {'Class Type':<25} | {'Status / Path'}")
    print("-" * 120)

    nodes_data = analysis_dict.get("nodes", [])
    if not nodes_data:
        print(f"{'---':<25} | {'---':<25} | No nodes found")
    else:
        for n in nodes_data:
            n_title = str(n.get("title") or n.get("type") or "Unknown")[:25]
            n_type = str(n.get("type", "Unknown"))[:25]
            
            if n.get("installed"):
                display_path = n.get("path") if n.get("path") else "No Path found"
            else:
                display_path = "!NOT INSTALLED!"
            
            print(f"{n_title:<25} | {n_type:<25} | {display_path}")

    # --- MODELS SEKTION ---
    print("\n" + "="*120)
    print(f"{'Model Filename':<53} | {'Status / Path'}")
    print("-" * 120)

    models_data = analysis_dict.get("models", [])
    if not models_data:
        # Hier war der Fehler: Jetzt wird auch bei leeren Listen eine Zeile ausgegeben
        print(f"{'---':<53} |No models found.")
    else:
        for m in models_data:
            m_name = str(m.get("filename", "Unknown"))[:53]
            display_m_path = m.get("path") if m.get("found") else "!FILE NOT FOUND!"
            print(f"{m_name:<53} | {display_m_path}")

    print(analysis_dict.get("summary", []))

    print("="*120 + "\n")