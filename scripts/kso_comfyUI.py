#python
# -*- coding: latin-1 -*-
######################################################################
#
# Royal Render Render script for Houdini
# Author:  Royal Render, Holger Schoenberger, Binary Alchemy
# Version %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy
# 
######################################################################



import subprocess
import time
import json
import uuid
import urllib.request
import websocket
import os
import sys
import argparse
import datetime
import ctypes
import copy

DEBUG= False
if "DEBUG" in os.environ:
    DEBUG= True
   
   
def logMessageGen(lvl, msg):
    if (len(lvl)==0):
        print(datetime.datetime.now().strftime("' %H:%M.%S") + " rrComfy      : " + str(msg))
    else:
        print(datetime.datetime.now().strftime("' %H:%M.%S") + " rrComfy - " + str(lvl) + ": " + str(msg))

def logMessage(msg):
    logMessageGen("",msg)
    
def logMessageDebug( msg):
    global DEBUG
    if DEBUG:
        logMessageGen("DGB", msg)

def logMessageSET(msg):
    logMessageGen("SET",msg)

def flushLog():
    sys.stdout.flush()        
    sys.stderr.flush()    

def logMessageError(msg, doRaise, printTraceback):
    msg= str(msg).replace("\\n","\n")
    logMessageGen("ERR", str(msg)+"\n")
    if "Traceback" in msg:
        printTraceback=False
    if printTraceback:
        import traceback
        traceBack_str= traceback.format_exc()
        logMessageGen("ERR","-------------------------------- Traceback --------------------------------:\n"+ traceBack_str +"---------------------------------------------------------------------------\n")    
 
    flushLog()
    if doRaise:
        raise NameError("\n\nError reported, aborting render script\n")  from None


def argValid(argValue):
    return ((argValue is not None) and (len(str(argValue))>0))




# Windows-spezifische Peek-Logik
if sys.platform == "win32":
    import msvcrt
    from ctypes import wintypes
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    PeekNamedPipe = kernel32.PeekNamedPipe
    PeekNamedPipe.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                              wintypes.LPDWORD, wintypes.LPDWORD, wintypes.LPDWORD]
    PeekNamedPipe.restype = wintypes.BOOL
else:
    import select


def format_exit_code(code):
    # Ensure it's treated as a 32-bit value (important for negative codes)
    unsigned_code = code & 0xFFFFFFFF
    # Convert to signed int32 (e.g., 4294967295 becomes -1)
    signed_code = code if code < 0x80000000 else code - 0x100000000
    
    # Return a string with both Int32 and Hex representation
    return f"Int32: {signed_code} | Hex: 0x{unsigned_code:08X}"


class ComfyLogManager:
    def __init__(self, process, prefix="Comfy", log_level=2):
        self.process = process
        self.prefix = prefix
        self.log_level = log_level  # 0: Silent, 1: Errors Only, 2: Everything
        self.stdout_buffer = ""
        self.stderr_buffer = ""

    def _get_data(self, pipe):
        """Liest verfügbare Bytes ohne zu blockieren (Cross-Platform)."""
        if sys.platform == "win32":
            handle = msvcrt.get_osfhandle(pipe.fileno())
            avail = wintypes.DWORD()
            if PeekNamedPipe(handle, None, 0, None, ctypes.byref(avail), None) and avail.value > 0:
                return os.read(pipe.fileno(), avail.value)
        else:
            r, _, _ = select.select([pipe], [], [], 0)
            if r:
                return os.read(pipe.fileno(), 4096)
        return b""

    def _handle_stream(self, raw_data, buffer, is_error_stream):
        """Verarbeitet Rohdaten, füllt den Buffer und druckt basierend auf LOG_LEVEL."""
        new_lines = []
        if not raw_data:
            return buffer, new_lines

        # Daten dekodieren und zum Buffer hinzufügen
        combined = buffer + raw_data.decode("utf-8", errors="replace")
        
        if "\n" in combined:
            parts = combined.split("\n")
            # Alle fertigen Zeilen durchgehen
            for line in parts[:-1]:
                clean_line = line.strip()
                new_lines.append(clean_line)
                
                # Log-Level Entscheidung
                # Level 2: Alles | Level 1: Nur Errors | Level 0: Nichts
                should_print = False
                if self.log_level == 2:
                    should_print = True
                elif self.log_level == 1 and is_error_stream:
                    should_print = True
                
                if should_print:
                    label = f"{self.prefix}-ERR" if is_error_stream else self.prefix
                    print(f"[{label}] {clean_line}")
            
            # Den unvollständigen Rest zurückgeben
            return parts[-1], new_lines
        
        return combined, new_lines

    def update(self):
        """Leert die Pipes und gibt alle neuen vollständigen Zeilen zurück."""
        # Standard Output
        self.stdout_buffer, out_lines = self._handle_stream(
            self._get_data(self.process.stdout), self.stdout_buffer, False
        )
        # Error Output
        self.stderr_buffer, err_lines = self._handle_stream(
            self._get_data(self.process.stderr), self.stderr_buffer, True
        )
        
        if out_lines or err_lines:
            sys.stdout.flush()
            
        return out_lines + err_lines

    def wait_for_strings(self, success_strings, error_strings=None, timeout=60):
        """Wartet blockierend (mit Polling) auf bestimmte Strings."""
        if isinstance(success_strings, str): 
            success_strings = [success_strings]
        error_strings = error_strings or []
        if isinstance(error_strings, str): 
            error_strings = [error_strings]

        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check ob der Prozess überhaupt noch läuft
            status = self.process.poll()
            if status is not None:
                # Hier kannst du deine format_exit_code Funktion einbauen
                return "TERMINATED", f"Exit Code: {format_exit_code(status)}"

            # Pipes auslesen
            lines = self.update()
            for line in lines:
                # Zuerst auf Fehler prüfen
                for e in error_strings:
                    if e in line:
                        return "ERROR", line
                # Dann auf Erfolg prüfen
                for s in success_strings:
                    if s in line:
                        return "SUCCESS", line
            
            time.sleep(0.1)
            
        return "TIMEOUT", f"Reached {timeout}s without finding target strings."
        
        
        
    
server_proc = None
log_mgr = None

    
    
    
def launch_comfy(args):

    if not os.path.exists(args.python_exe):
        print(f"CRITICAL: Python not found at {args.python_exe}")
        return False
    if not os.path.exists(args.comfy_main):
        print(f"CRITICAL: main.py not found at {args.comfy_main}")
        return False
    
    
    cmd = [args.python_exe, 
        "-s",  
        args.comfy_main, 
        "--port", str(args.port), 
        #"--dont-print-server",  
        "--log-stdout", 
        "--temp-directory", os.environ["rrLocalTemp"], 
        "--disable-auto-launch", 
        "--disable-manager-ui", 
        "--disable-smart-memory", 
        "--output-directory", args.output_directory, 
        "--base-directory", args.base_directory, 
        ]
    # ::win   --windows-standalone-build #Windows standalone build: Enable convenient things that most people using the standalone windows build will probably enjoy (like auto opening the page on startup).
    #Flag	Nutzen für Batch/C++
    #--disable-smart-memory	Verhindert, dass ComfyUI Modelle aggressiv aus dem VRAM entlädt. Gut, wenn du viele Bilder nacheinander mit demselben Modell renderst.
    #--highvram / --normalvram	Erzwingt ein Speicherprofil, damit dein C++ Programm vorhersagbare Performance hat.
    #--dont-print-server	Reduziert den Spam im log_mgr (keine "Importing module..." Meldungen), falls du nur echte Error/Success Meldungen willst.


    if (args.rrRenderer =="Desktop"):
        comfy_dir = os.path.dirname(args.comfy_main)
        frontend_root = os.path.join(comfy_dir, "web_custom_versions", "desktop_app")
        cmd.append("--front-end-root")
        cmd.append(frontend_root)

    if argValid(args.extra_model_paths_config):
        cmd.append("--extra-model-paths-config")
        cmd.append(args.extra_model_paths_config)
    
    if argValid(args.verbose):
        cmd.append("--verbose")
        cmd.append(args.verbose)
        
    if argValid(args.database):
        database_url=args.database
        database_url= database_url.replace("\\","/")
        database_url="sqlite:///" + database_url
        cmd.append("--database-url")
        cmd.append(database_url)
    
        
    print(f"Executing: {' '.join(cmd)} ")
    flushLog()
    global server_proc, log_mgr

    # Ensure environment is passed and paths are normalized
    current_env = os.environ.copy()    
    server_proc = subprocess.Popen(
        cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,
#        stdin=subprocess.DEVNULL, 
        bufsize=0,                
        env=current_env,           
        cwd=os.path.dirname(args.comfy_main) 
    )
    
    
    log_mgr = ComfyLogManager(server_proc, log_level=2)
    
    # Erster Check: Auf Start warten
    result, msg = log_mgr.wait_for_strings("To see the GUI go to:", timeout=120)
    
    log_mgr.update() 
    if result == "SUCCESS":
        print("ComfyUI is up and running.")
        return True
    else:
        raise Exception(f"Launch failed: {result} - {msg}")
        return False


def stop_comfy():
    global server_proc, log_mgr
    
    if log_mgr:
        log_mgr.update() #print everything from pipe buffer
    
    # Prüfen, ob der Prozess überhaupt existiert
    if server_proc is None:
        print("[INFO] ComfyUI is not running (no process found).")
        return

    # Prüfen, ob er vielleicht schon von selbst beendet wurde
    exit_code = server_proc.poll()
    
    if exit_code is not None:
        # Prozess ist bereits aus, wir geben den Code aus
        # Hier kannst du deine format_exit_code Funktion nutzen
        print(f"[INFO] ComfyUI was already terminated ({format_exit_code(exit_code)}).")
    else:
        # Prozess läuft noch, jetzt beenden wir ihn aktiv
        print("Terminating ComfyUI process...")
        server_proc.terminate()
        try:
            # Kurz warten, ob er brav ausgeht
            server_proc.wait(timeout=5)
            if log_mgr:
                log_mgr.update()            
            print("ComfyUI terminated successfully.")
        except subprocess.TimeoutExpired:
            # Wenn er nicht hört, dann die harte Tour
            print("Process did not respond, killing it...")
            server_proc.kill()
            server_proc.wait()
            if log_mgr:
                log_mgr.update()
    # In jedem Fall die globalen Variablen zurücksetzen
    server_proc = None
    log_mgr = None


def print_comfy_error(error_response):
    try:
        # Parse JSON if it's a string, otherwise use as dict
        data = json.loads(error_response) if isinstance(error_response, str) else error_response
        
        error_info = data.get("error", {})
        node_errors = data.get("node_errors", {})

        print("\n" + "="*70)
        print(f" ERROR: {error_info.get('type', 'Unknown Error')}")
        print(f" MESSAGE: {error_info.get('message', 'No message provided')}")
        print("="*70)

        if node_errors:
            print("\nDETAILED NODE ERRORS:")
            for node_id, info in node_errors.items():
                class_type = info.get("class_type", "Unknown")
                print(f"   [ Node ID: {node_id} | Class: {class_type} ]")
                
                for err in info.get("errors", []):
                    # Clean up details for better readability
                    details = err.get('details', '')
                    print(f"     - Error: {err.get('message')}")
                    print(f"       Detail: {details}")
        
        print("\n" + "="*70 + "\n")

    except Exception as e:
        print(f"Failed to format error output: {e}")
        print(f"Original Response: {error_response}")

def send_prompt(workflow, server_address, client_id):
    # Post the JSON workflow to the ComfyUI API endpoint
    payload = {"prompt": workflow, "client_id": client_id}
    
    try:
        data = json.dumps(payload).encode('utf-8')
        url = f"http://{server_address}/prompt"
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header('Content-Type', 'application/json')

        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            
            # Check if prompt_id is actually in the response
            if 'prompt_id' in result:
                return result['prompt_id']
            else:
                print(f"Error: Server response missing prompt_id. Response: {result}")
                return None

    except urllib.error.HTTPError as e:
        log_mgr.update()
        # Handle specific HTTP errors (e.g., 404, 500)
        error_body = e.read().decode('utf-8') if e.readable() else "No error body"
        print(f"HTTP Error {e.code}: {e.reason}")
        print_comfy_error(error_body)
        return None

    except urllib.error.URLError as e:
        log_mgr.update()
        # Handle connection errors (e.g., server not reachable)
        print(f"Connection Error: Failed to reach the server at {server_address}. Reason: {e.reason}")
        return None

    except json.JSONDecodeError:
        log_mgr.update()
        # Handle cases where the server does not return valid JSON
        print("Error: Failed to decode JSON response from server.")
        return None

    except Exception as e:
        log_mgr.update()
        # Catch-all for any other unexpected errors
        print(f"Unexpected Error in send_prompt: {str(e)}")
        return None



def validate_and_extract_api(workflow_input, args):
    """
    Validates the input and returns ONLY the API-format dictionary.
    Supports: Hybrid-JSON (ui/api)  and   Pure API-JSON.
    """
    api_workflow = None

    # 1. Format-Erkennung
    if isinstance(workflow_input, dict):
        if "api_format_rr" in workflow_input:
            # Es ist ein Hybrid-Format
            api_workflow = workflow_input["api_format_rr"]
            print("Format: Hybrid (UI + API) detected.")
        elif "nodes" in workflow_input and "links" in workflow_input:
            # Es ist ein reines UI-Format (ohne API-Teil)
            print("Error: This is a pure UI-format. No API-data found inside.")
            print("ComfyUI console supports API format only.")
            print("Please use our submitter or save it as API format")
            return None
        else:
            # Wahrscheinlich bereits API-Format oder ein flaches Dict
            api_workflow = workflow_input
            print("Format: Standard API-only detected.")
    else:
        print("Error: Invalid workflow data type.")
        return None

    # 2. Grundcheck: Enthält das Dict nummerierte IDs? (Typisch für API)
    if not any(str(key).isdigit() for key in api_workflow.keys()):
        print("Error: The extracted workflow contains no numeric Node-IDs. Not a valid API prompt.")
        return None

    # 3. Validierung gegen rrLayer (falls angegeben)
    if argValid(args.rrLayer):
        parts = args.rrLayer.split("__")
        target_node_id = str(parts[-1])
        # Entferne nur das "ID" Präfix, falls es existiert
        if target_node_id.startswith("ID"):
            target_node_id = target_node_id[2:] # Schneidet die ersten zwei Zeichen ab
        if (int(target_node_id)>=0):
            title = parts[0] if parts[0] else "Untitled"

            # Existiert die Node im extrahierten API-Format?
            node = api_workflow.get(target_node_id)
            
            if node is None:
                # Falls Node-ID nicht direkt gefunden, schauen wir in den _meta Daten nach dem Titel
                # (Manchmal ändert sich die ID, aber der Titel bleibt)
                found_id = None
                for nid, n_data in api_workflow.items():
                    if n_data.get("_meta", {}).get("title") == title:
                        found_id = nid
                        break
                
                if found_id:
                    print(f"Note: Node ID {target_node_id} not found, but found Node with title '{title}' at ID {found_id}.")
                    args.rrLayer = f"{title}__{found_id}"
                else:
                    print(f"Error: Output Node #{target_node_id} ('{title}') not found in the workflow!")
                    return None

            # Falls wir hier sind, ist die Node valide
            print(f"Validation: Node #{target_node_id} exists.")

    # Wir geben das reine API-Format zurück
    return api_workflow
    

def get_out_path(args, absolute, frame):
    """
    Returns either the full absolute path or the path relative to output-directory.
    rrDirName + rrFileName
    """
    # Create the full path (Absolute)
    # English comment: Construct the full target path from directory and filename
    full_path = os.path.join(args.rrDirName, args.rrFileName)
    full_path=f"{full_path}.{frame:2}"
    
    if absolute:
        return full_path
    
    # Calculate relative path to output-directory
    # Get the relative portion by stripping the base output directory
    try:
        rel_path = os.path.relpath(full_path, args.output_directory)
        return rel_path
    except ValueError:
        # Fallback falls die Pfade auf unterschiedlichen Laufwerken liegen (Windows)
        return full_path


def modify_workflow(api_workflow, args, frame):
    """
    Passt die Iterations-Indizes für rrSeed-Nodes an und setzt den 
    Dateinamen für die Ziel-Layer-Node.
    """
    
    # 1. Alle rrSeed-Nodes finden und iteration_idx ändern
    # Wir iterieren über alle Nodes im API-Workflow
    rrSeed_changed= False
    for node_id, node_data in api_workflow.items():
        if node_data.get("class_type") == "rrSeed":
            if "iteration_idx" in node_data.get("inputs", {}):
                # Wir setzen den Index aus den Args (z.B. für Batch-Rendering)
                old_idx = node_data["inputs"]["iteration_idx"]
                node_data["inputs"]["iteration_idx"] = frame
                print(f"Node {node_id} (rrSeed): iteration_idx {old_idx} -> {frame}")
                rrSeed_changed= True
                
    #if not rrSeed_changed:
    target_node_types = ["KSampler", "KSamplerAdvanced", "Seed (rgthree)", "GlobalSeed", "PrimitiveNode"]
    for node_id, node in api_workflow.items():
        node_type = node.get("class_type")
        inputs = node.get("inputs", {})

        # Check if this node is a KSampler or a known Seed node
        if node_type in target_node_types or "seed" in inputs:
            
            # Logic: Check "control_after_generation" 
            # In the API format, this is often an input value
            control_setting = inputs.get("control_after_generation")
            print(f"Node {node_id} {node_type} control_setting: {control_setting}.")

            
            # We only change if it's NOT "fixed"
            # Note: Sometimes it's lowercase, sometimes uppercase depending on custom nodes
            if not control_setting or str(control_setting).lower() != "fixed":
                
                # Update the seed (e.g., to -1 for random or a specific new seed)
                # Setting it to -1 tells ComfyUI to generate a new one on next run
                # if the node supports it, otherwise we generate a random int here.
                new_seed = frame* 10000
                inputs["seed"] = new_seed
                print(f"Updated Node {node_id} {node_type} to new seed {new_seed}.")

    # 2. Den filename_prefix für die spezifische rrLayer-Node ändern
    if argValid(args.rrLayer):
        parts = args.rrLayer.split("__")
        target_node_id = str(parts[-1])
        # Entferne nur das "ID" Präfix, falls es existiert
        if target_node_id.startswith("ID"):
            target_node_id = target_node_id[2:] # Schneidet die ersten zwei Zeichen ab
        title = parts[0] if parts[0] else "Untitled"
        if (int(target_node_id)>=0):
            target_node = api_workflow.get(target_node_id)
            if target_node:
                class_type = target_node.get("class_type", "")
                
                if "filename_prefix" in target_node.get("inputs", {}):
                    
                    # Check if it is a custom RR node or a standard ComfyUI node
                    is_rr_node = class_type in ["rrSaveImage", "rrSaveVideo"]
                    
                    # Generate path based on node type
                    new_prefix = get_out_path(args, is_rr_node, frame)
                    
                    old_prefix = target_node["inputs"]["filename_prefix"]
                    target_node["inputs"]["filename_prefix"] = new_prefix
                    
                    print(f"Node {target_node_id} {title} ({class_type}): filename_prefix '{old_prefix}' -> '{new_prefix}'")
                else:
                    print(f"Warning: Node {target_node_id} {title} has no 'filename_prefix' input.")
                    return False
            else:
                print(f"Error: Target node {target_node_id} {title} not found in workflow while applying parameters.")
                return False

    return True
        


def rrMakedirs(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


def render_frame(frame):
    global workflow
    global ws
    global server_address
    global client_id
    
    beforeFrame = datetime.datetime.now()
    logMessage(f"\n---------- Rendering Iteration {frame} ---------- Sending Workflow to ComfyUI... ----------")
    
    current_workflow = copy.deepcopy(workflow)
    if not modify_workflow(current_workflow, args, frame):
        raise Exception("render_frame: Unable to update workflow with new settings")    
    
    logMessageDebug("render_frame: before send_prompt")
    prompt_id = send_prompt(current_workflow, server_address, client_id)
    if prompt_id is None:
        raise Exception("ERROR: ComfyUI did not load workflow")
    
    logMessageDebug("render_frame: Progress & Log-Manager Loop")
    # --- Progress & Log-Manager Loop ---
    finished = False
    while not finished:
        # 1. Websocket mit kurzem Timeout abfragen (verhindert Blockieren)
        try:
            if log_mgr:
                log_mgr.update() 
                flushLog()
            
            ws.settimeout(0.1) # Warte maximal 100ms auf Daten
            out = ws.recv()
            
            if isinstance(out, str):
                message = json.loads(out)
                
                # Progress-Meldung verarbeiten
                if message['type'] == 'progress':
                    v = message['data']['value']
                    m = message['data']['max']
                    progress_pct = int((v/m)*100)
                    logMessage(f"Progress: {progress_pct}% ({v}/{m})")

                # Ende der Ausführung prüfen
                if message['type'] == 'executing':
                    if message['data']['node'] is None and message['data']['prompt_id'] == prompt_id:
                        logMessage("Progress: Finished")
                        finished = True
                        break
        
        except websocket.WebSocketTimeoutException:
            # Kein Problem, nur keine neuen Daten vom Server in diesen 100ms
            pass
        except Exception as e:
            logMessage(f"WS Error: {str(e)}")
            break

 
    
    afterFrame = datetime.datetime.now()
    afterFrame -= beforeFrame
    logMessage(f"Iteration #{frame} Rendered.  Time: {afterFrame}  h:m:s.ms.  ")



def render_multiple_frames(frameStart, frameEnd, frameStep):
    for fr in range(frameStart,frameEnd+1,frameStep):
        render_frame(fr)


############################# main function ############################# 


logMessage("Script %rrVersion%" )
logMessage("Python version: "+str(sys.version))

# Setup command line arguments for flexibility
parser = argparse.ArgumentParser()
parser.add_argument("--PyModPath", required=True, type=str, default="")
parser.add_argument("--python_exe", required=True, default="")
parser.add_argument("--comfy_main", required=True)
parser.add_argument("--port", required=True, type=int, default=0)

parser.add_argument("--base-directory", required=True, type=str, default="")
parser.add_argument("--database", required=True, type=str, default="")
parser.add_argument("--extra-model-paths-config", required=False, type=str, default="")

parser.add_argument("--output-directory", required=True, type=str, default="")
parser.add_argument("--rrDirName", required=True, type=str, default="")
parser.add_argument("--rrFileName", required=True, type=str, default="")

#parser.add_argument("--user-directory", type=str, default="")
#parser.add_argument("--input-directory ", type=str, default="")

parser.add_argument("--verbose", default='INFO', const='DEBUG', nargs="?", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help='Set the logging level')
parser.add_argument("--rrWorkflow", required=True, type=str, default="")
parser.add_argument("--rrLayer", type=str, default="")
parser.add_argument("--rrInterationStart", required=True, type=int, default=1)
parser.add_argument("--rrInterationEnd", required=True, type=int, default=1)
parser.add_argument("--rrInterationStep", type=int, default=1)
parser.add_argument("--rrRenderer", type=str, default="Portable")
args = parser.parse_args()


if (argValid(args.PyModPath)):
    import sys
    logMessage("Append python search path with '" +args.PyModPath+"'" )
    sys.path.append(args.PyModPath)
global kso_tcp
import kso_tcp
kso_tcp.USE_LOGGER= False
kso_tcp.USE_DEFAULT_PRINT= True        
kso_tcp.rrKSO_logger_init()

global server_address
global client_id
client_id = str(uuid.uuid4())
server_address = f"127.0.0.1:{args.port}"

#replicate default folders
try:
    if (not argValid(args.base_directory)):
        logMessageError("base-directory commandline flag not set!", True, False)
    rrMakedirs(args.base_directory)
    rrMakedirs(os.path.join(args.base_directory,"custom_nodes"))
    rrMakedirs(os.path.join(args.base_directory,"input"))
    rrMakedirs(os.path.join(args.base_directory,"models"))
    rrMakedirs(os.path.join(args.base_directory,"output"))
    rrMakedirs(os.path.join(args.base_directory,"temp"))
    rrMakedirs(os.path.join(args.base_directory,"user"))
except Exception as e:
    logMessageError(f"Could not create directory: {e}", True, False)

try:
    if argValid(args.database):
        database_folder=os.path.dirname(args.database)
        rrMakedirs(database_folder)
except Exception as e:
    logMessageError(f"Could not create directory: {e}", True, False)
    
if (not argValid(args.rrInterationStep)):
    args.rrInterationStep=1
    
    
try:
    # Establish WebSocket connection for real-time progress feedback
    global workflow
    with open(args.rrWorkflow, "r", encoding="utf-8") as f:
        workflow = json.load(f)
    
    workflow = validate_and_extract_api(workflow, args)
    if workflow is None:
        raise Exception("Invalid Workflow")
    
    #we do a test replacement before we start the ComfyUI webserver and then realize it does not work
    current_workflow = copy.deepcopy(workflow)
    if not modify_workflow(current_workflow, args, args.rrInterationStart):
        raise Exception("Unable to update workflow with new settings")
        
        
    if not launch_comfy(args):
        sys.exit()
    global ws
    ws = websocket.WebSocket()
    ws.connect(f"ws://{server_address}/ws?clientId={client_id}")

        
    render_multiple_frames(args.rrInterationStart, args.rrInterationEnd, args.rrInterationStep)

    ws.close()

except Exception as e:
    logMessageError( str(e)+"\n", False, True)
    
finally:
    # Clean up by terminating the background ComfyUI process
    logMessage("\n--- Shutting down ---")
    stop_comfy()

flushLog()
logMessage("                                      .   ")
logMessage("                                     ...  ")
logMessage("                                    ..... ")
logMessage("                                   ..end..")
flushLog()
time.sleep(2) #some delay as some log messages seem to be cut off

