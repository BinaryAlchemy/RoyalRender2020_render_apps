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
import uuid
from server import PromptServer
from aiohttp import web

##############################################
# Settings and their default                 #
##############################################
    
SETTINGS_KEY = "rrSubmit_CFG"

# Definition: intern_key -> {"default": value, "label": UI-Label, "type": "str/int/bool"}
SETTINGS_FIELDS = {
    "group_general": {"label": "General", "type": "separator", "section": "left"},
    "iteration_idxs_count": {"label": "Number of interations to process", "type": "int", "section": "left"},
    "seq_div_min": {"label": "Sequence Divide Min", "type": "int", "section": "left"},

    "group_path": {"label": "Paths", "type": "separator", "section": "bottom"},
    "farm_workflow_path": {"label": "Optional: Path to save workflow dublicate for RR", "type": "str", "section": "bottom"},
    "output_path": {"label": "OPTIONAL: Override path to save output to", "type": "str", "section": "bottom"},

    "group_model": {"label": "Copy model files", "type": "separator", "section": "bottom"},
    "model_sync_mode": {
        "label": "N/A - Copy Mode",
        "type": "choice",
        "choices": [
                ("Do nothing", "none"),
                ("Add local models to existing", "Copy"),
                ("Sync local model (delete non-existing)", "Sync")
                ],
        "section": "bottom"
    },
    "local_model_dir": {"label": "OPTIONAL: Override local model path", "type": "str", "section": "bottom"},
    "farm_model_dir": {"label": "Fileserver model path", "type": "str", "section": "bottom"},

    "group_misc": {"label": "Misc", "type": "separator", "section": "right"},
    "ui_submit": {"label": "Use UI rrSubmitter", "type": "bool", "section": "right"},
    "replace_fileout": {"label": "N/A - Replace fileout nodes with RR nodes", "type": "bool", "section": "right"},
    "add_seed": {"label": "N/A - Add rrSeed to all KSampler seed inputs", "type": "bool", "section": "right"},
    "load_farm_workflow": {"label": "DEBUG: ask to load farm workflow after submission", "type": "bool", "section": "right"},
}

def settings_compute_default(key, RR_ROOT):
    if key == "iteration_idxs_count":
        return 1

    if key == "seq_div_min":
        return 1

    if key == "farm_workflow_path":
        return os.path.join(RR_ROOT,"inhouse/compfyUI/")

    if key == "output_path":
        return "" 
        #This is an OPTIONAL OVERRIDE. We do not want to hardcode anything as someone might copy the file to some other location/workstation/project

    if key == "model_sync_mode":
        return SETTINGS_FIELDS["model_sync_mode"]["choices"][1][1] 

    if key == "local_model_dir":
        return "" 
        #This is an OPTIONAL OVERRIDE. We do not want to hardcode anything as someone might copy the file to some other location/workstation/project
        #return folder_paths.models_dir

    if key == "farm_model_dir":
        return os.path.join(RR_ROOT, "render_apps/renderer_plugins/ComfyUI/models_<rrJobVerMajor>")

    if key == "ui_submit":
        return True

    if key == "replace_fileout":
        return True

    if key == "add_seed":
        return True

    if key == "load_farm_workflow":
        return False


    return None
    



#####################################################################################
# This function has to be changed if an app should show info and error dialog box   #
#####################################################################################

def hasEnvDebugMode():
    debug_val = os.environ.get("DEBUG_MODE", "OFF").upper()
    if (debug_val in ["TRUE", "ON", "1"]) or True:
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
    
def workflow_hasCheckpoint(workflow: Dict) -> bool:
    """
    Prüft dynamisch, ob ein Checkpoint-Loader vorhanden ist, 
    indem die Ausgangs-Typen analysiert werden.
    """
    nodes_data = workflow.get("nodes")
    
    # Hilfsfunktion zur Prüfung der Ausgangs-Struktur
    def is_checkpoint_node(outputs):
        if not outputs or not isinstance(outputs, list):
            return False
        # Ein Checkpoint-Loader hat typischerweise MODEL, CLIP und VAE
        types = {str(o.get("type")).upper() for o in outputs if isinstance(o, dict)}
        return {"MODEL", "CLIP", "VAE"}.issubset(types)

    # UI Format (nodes ist eine Liste)
    if isinstance(nodes_data, list):
        for node in nodes_data:
            if is_checkpoint_node(node.get("outputs")):
                return True
                
    # API Format (workflow ist ein dict von node_id: node_dict)
    # Hinweis: Im API-Format fehlen oft die Metadaten der Outputs. 
    # Daher ist hier ein kleiner Fallback auf die Struktur sinnvoll.
    else:
        for node in workflow.values():
            if not isinstance(node, dict): 
                continue
            
            # Da das API-Format keine Output-Typen mitsendet, 
            # prüfen wir hier auf die typischen Input-Kombinationen 
            # der Nodes, die diesen Loader verwenden (optional).
            # Falls das zu unsicher ist, bleibt für das API-Format 
            # nur die Suche nach Loader-Keywords im Klassennamen:
            class_type = node.get("class_type", "").lower()
            if "checkpoint" in class_type and "loader" in class_type:
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


def workflow_getOutput(workflow: Dict, use_node_id: int):
    """
    Extrahiert Output-Informationen aus dem Workflow.
    """
    if not workflow:
        raise Exception("rrSubmit - Empty workflow data.")

    # Default-Rückgabewerte
    out_name = "noDir/no.frame"
    out_ext = ".check"
    out_node_ID = -1
    is_video = False
    
    found_output = False
    nodes_data = workflow.get("nodes")

    # 1. Gezielte Node-ID Suche (use_node_id != -1)
    if use_node_id != -1:
        target_node = None
        if isinstance(nodes_data, list):
            target_node = next((n for n in nodes_data if str(n.get("id")) == str(use_node_id)), None)
        else:
            target_node = workflow.get(str(use_node_id))

        if target_node:
            res_name, res_ext, res_video = _get_output_info(target_node)
            if res_name:
                return use_node_id, res_name, res_ext, res_video
            else:
                writeInfo(f"[rrSubmit] Requested Node {use_node_id} found, but no filename extracted.")
        else:
            writeInfo(f"[rrSubmit] Warning: Requested Node ID {use_node_id} not found.")

    # 2. Dynamischer Loop (wenn use_node_id == -1 oder oben nichts gefunden wurde)
    if isinstance(nodes_data, list):
        # UI Format
        for node in nodes_data:
            # Dynamische Prüfung auf Output-Node (isOutputNode oder keine Ausgänge)
            if node.get("isOutputNode", False) or not node.get("outputs"):
                res_name, res_ext, res_video = _get_output_info(node)
                if res_name:
                    out_node_ID, out_name, out_ext, is_video = node.get("id"), res_name, res_ext, res_video
                    found_output = True
                    break
    else:
        # API Format
        for node_id, node in workflow.items():
            if not isinstance(node, dict): 
                continue
            res_name, res_ext, res_video = _get_output_info(node)
            if res_name:
                out_node_ID, out_name, out_ext, is_video = node_id, res_name, res_ext, res_video
                found_output = True
                break


    if not found_output:
        writeError("No valid output nodes found in workflow.")

    return out_node_ID, out_name, out_ext, is_video
    
 
def disable_Outputs(workflow: Dict, submit_node_id: int):
    """
    Deaktiviert alle Output-Nodes im Workflow, außer derjenigen, 
    die explizit für den Submit ausgewählt wurde.
    """
    # Validierung: Wenn keine spezifische Node gewählt wurde, brechen wir ab
    if submit_node_id < 0:
        return

    nodes_data = workflow.get("nodes")
    submit_node_str = str(submit_node_id)

    # UI Format (Liste von Nodes)
    if isinstance(nodes_data, list):
        for node in nodes_data:
            node_id = str(node.get("id"))
            
            # Dynamische Prüfung: Ist es eine Output-Node?
            # Wir nutzen dieselbe Logik wie in workflow_getOutput
            is_output = node.get("isOutputNode", False) or not node.get("outputs")
            
            if is_output:
                # Wenn es NICHT unsere Submit-Node ist -> Deaktivieren
                if node_id != submit_node_str:
                    # 'mode' 2 bedeutet 'Disabled' in ComfyUI
                    node["mode"] = 2
                    writeInfo(f"Disabled output node: {node_id} ({node.get('type')})")

    # API Format (Dict von node_id: node_dict)
    # Hinweis: Das API-Format von ComfyUI hat kein 'mode' Feld für das Backend.
    # Wenn du den Workflow für das Backend/Cloud-Rendering manipulierst, 
    # müssten die Nodes hier ggf. komplett aus dem Dict gelöscht werden.
    else:
        # Erstelle eine Liste der Keys zum Löschen, um das Dict während des Loops nicht zu ändern
        to_delete = []
        for node_id, node in workflow.items():
            if not isinstance(node, dict): 
                continue
            
            # Da im API-Format 'isOutputNode' fehlt, nutzen wir _get_output_info als Check
            res_name, _, _ = _get_output_info(node)
            if res_name and str(node_id) != submit_node_str:
                to_delete.append(node_id)
        
        for node_id in to_delete:
            del workflow[node_id]
            writeInfo(f"Removed output node from API-Workflow: {node_id}")



 

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
    

    

def convert_ui_to_api_dynamic(workflow_ui):
    """
    Triggert die Konvertierung im JS-Frontend und wartet auf das Ergebnis.
    """
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

    # English comment: Sort the top-level node IDs numerically
    sorted_node_ids = sorted(api_workflow.keys(), key=lambda x: int(x) if x.isdigit() else x)
    
    sorted_workflow = OrderedDict()
    
    for node_id in sorted_node_ids:
        node_data = api_workflow[node_id]
        
        # English comment: Sort all sub-dictionaries (inputs, _meta, etc.) alphabetically
        sorted_node = {}
        for key, value in node_data.items():
            if isinstance(value, dict):
                # English comment: Recursive call or simple sort for the inputs level
                sorted_node[key] = dict(sorted(value.items()))
            else:
                sorted_node[key] = value
                
        sorted_workflow[node_id] = sorted_node
        
    return dict(sorted_workflow)
    


def inject_link(src_id, src_out_idx, dst_id, dst_input_name, links, dst_node):
    # (English comment) Utility to ensure an input is a link and not a widget
    if "inputs" not in dst_node:
        dst_node["inputs"] = []
    
    # (English comment) Find or create the input slot
    existing_input = next((i for i in dst_node["inputs"] if i["name"] == dst_input_name), None)
    new_link_id = int(str(uuid.uuid4().int)[:8])
    
    if not existing_input:
        dst_node["inputs"].append({"name": dst_input_name, "type": "INT", "link": new_link_id})
    else:
        # (English comment) Cleanup old links
        old_link = existing_input["link"]
        links[:] = [lk for lk in links if lk[0] != old_link]
        existing_input["link"] = new_link_id
    
    # (English comment) Update the global links list
    slot_idx = next(idx for idx, i in enumerate(dst_node["inputs"]) if i["name"] == dst_input_name)
    links.append([new_link_id, src_id, src_out_idx, dst_id, slot_idx, "INT"])
    


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

        # --- PART 3: KSampler (The Heart of the Seed) ---
        if setting_add_seed and seed_node_id:
            target_slot = None
            # Identify the correct seed input name based on the node type
            if current_type == "KSampler":
                target_slot = "seed"
            elif current_type in ["KSamplerAdvanced", "RandomNoise"]:
                target_slot = "noise_seed"
            elif "KSampler" in (current_type or ""):
                # Fallback for other custom KSampler variants
                target_slot = "seed"

            if target_slot:
                # Connect Output 0 of rrSeed (calculated final seed) to the target node
                inject_link(seed_node_id, 0, node["id"], target_slot, links, node)                

    workflow["nodes"] = nodes
    workflow["links"] = links
    return workflow, outFixedFilename


def add_rrSeed(workflow):
    if "nodes" not in workflow:
        return workflow
        
    nodes = workflow["nodes"]
    links = workflow.get("links", [])
    
    seed_node_id = None
    #We do not add a new one if there is already one
    rrSeed_node = next((n for n in nodes if n["type"] == "rrSeed"), None)
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

    # --- PART 2: Connection to Random Nodes  ---
    if seed_node_id:
        for node in nodes:
            current_id = str(node.get("id"))
            current_type = node.get("type") # In manchen Formaten auch 'class_type'
            inputs = node.get("inputs", {})

            target_slot = None
            
            # 1. Identifiziere den korrekten Slot-Namen
            if current_type == "KSampler":
                target_slot = "seed"
            elif current_type in ["KSamplerAdvanced", "RandomNoise"]:
                target_slot = "noise_seed"
            elif current_type in ["Seed (rgthree)", "GlobalSeed", "PrimitiveNode"]:
                target_slot = "seed"
            elif inputs and "seed" in inputs:
                # Dynamischer Check: Falls die Node ein Input-Feld namens "seed" hat
                target_slot = "seed"
            elif current_type and "KSampler" in current_type:
                target_slot = "seed"

            # 2. Wenn ein Slot gefunden wurde, prüfe die "Fixed"-Bedingung
            if target_slot:
                control_setting = inputs.get("control_after_generation")
                
                # Nur injecten, wenn es NICHT auf 'fixed' steht
                # Wir prüfen auf 'fixed' als String (case-insensitive)
                is_fixed = control_setting and str(control_setting).lower() == "fixed"
                
                if not is_fixed:
                    # Verbindung von Output 0 der rrSeed Node zum Ziel-Slot der aktuellen Node
                    # Das ersetzt den statischen Wert durch die rrSeed-Logik
                    inject_link(seed_node_id, 0, node["id"], target_slot, links, node)
                    writeInfo(f"Connected rrSeed to Node {current_id} ({current_type}) on slot '{target_slot}'.")
                else:
                    writeDebug(f"Skipped Node {current_id} because seed is set to 'fixed'.")

    workflow["nodes"] = nodes
    workflow["links"] = links
    return workflow
