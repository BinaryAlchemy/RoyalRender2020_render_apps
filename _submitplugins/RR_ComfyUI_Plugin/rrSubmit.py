# Author: Royal Render, Holger Schoenberger, Binary Alchemy
# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy
#
# Installation:
# Please copy the RR_ComfyUI_Plugin folder into your custom_nodes folder of ComfyUI.
# Note: If the RR_ROOT environment variable ist not defined (created when installing something via rrWorkstationInstaller), 
# then you need to edit the function "def getRR_Root()" top update the path to RR.
#
# custom_nodes/
#     └── RR_ComfyUI_Plugin/
#         ├── __init__.py
#         ├── rrSubmit.py
#         ├── rrNodes.py
#         └── js/
#             ├── rrSeed.js
#             └── rr_ui.js


import os
import sys
import json
import tempfile
from typing import Dict, List, Union, Optional, Tuple
from datetime import datetime
import server
import folder_paths
import subprocess #it is imported now as the CompfyUI security/vulnerability check  
import traceback
from pathlib import Path
import time
import uuid
import re
import nodes
from xml.etree.ElementTree import ElementTree, Element, SubElement
import requests
from server import PromptServer
import asyncio
import json
import uuid

##############################################
# Settings and their default                 #
##############################################


DEBUG= False
if "DEBUG" in os.environ:
    DEBUG= True
    
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

def settings_compute_default(key):
    if key == "iteration_idxs_count":
        return 1

    if key == "seq_div_min":
        return 1

    if key == "farm_workflow_path":
        return os.path.join(getRR_Root(),"inhouse/compfyUI/")

    if key == "output_path":
        return "" 
        #This is an OVERRIDE. We do not want to hardcode anything as someone might copy the file to some other location/workstation/project
        '''
        try:
            # Dies ist der sicherste Weg in ComfyUI
            return folder_paths.get_output_directory()
        except Exception as e:
            print(f"[rrSubmit] Error getting output directory: {e}")
        '''

    if key == "model_sync_mode":
        return SETTINGS_FIELDS["model_sync_mode"]["choices"][1][1] 

    if key == "local_model_dir":
        return "" 
        #This is an OVERRIDE. We do not want to hardcode anything as someone might copy the file to some other location/workstation/project
        #return folder_paths.models_dir

    if key == "farm_model_dir":
        return os.path.join(getRR_Root(), "render_apps/renderer_plugins/ComfyUI/models_<rrJobVerMajor>")

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

def writeInfo(msg):
    print("[rrSubmit] "+str(msg))

def writeError(msg):
    print("[rrSubmit] ERROR: "+str(msg))
        


##############################################
# JOB CLASS                                  #
##############################################


class rrJob(object):
         
    def __init__(self):
        self.clear()
    
    def clear(self):
        self.version = ""
        self.rendererVersion= ""
        self.software = ""
        self.renderer = ""
        self.RequiredLicenses = ""
        self.sceneName = ""
        self.sceneDatabaseDir = ""
        self.seqStart = 0
        self.seqEnd = 100
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
        self.isActive = True
        self.preID = ""
        self.waitForPreID  = ""
        self.customVars = {}
        self.submitOptions = {}
        

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

    def writeToXMLstart(self, globalSubmitOptions):
        rootElement = Element("rrJob_submitFile")
        rootElement.attrib["syntax_version"] = "6.0"
        self.subE(rootElement, "DeleteXML", "1")
        if (globalSubmitOptions!=None and len(globalSubmitOptions)>0):
            self.subE(jobElement,"SubmitterParameter", globalSubmitOptions)
        return rootElement

    def writeToXMLJob(self, rootElement):
        jobElement = self.subE(rootElement, "Job", "")
        self.subE(jobElement, "rrSubmitterPluginVersion", "%rrVersion%")
        self.subE(jobElement, "Software", self.software)
        self.subE(jobElement, "Renderer", self.renderer)
        self.subE(jobElement, "RequiredLicenses", self.RequiredLicenses)
        self.subE(jobElement, "Version", self.version)
        self.subE(jobElement, "rendererVersion", self.rendererVersion)
        self.subE(jobElement, "Scenename", self.sceneName)
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
        self.subE(jobElement, "Imagefilename", self.imageFileName)
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
        self.subE(jobElement, "PreID", self.preID)
        self.subE(jobElement, "WaitForPreID", self.waitForPreID)
        for var, value in self.customVars.items():
            if (not var.lower().startswith("custom")):
                var= "Custom"+var
            self.subE(jobElement, var, value)
        for var, value in self.submitOptions.items():
            self.subE(rootElement, "SubmitterParameter", str(var) + "=" + str(value))
        
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



##############################################
# Global RR Functions                        #
##############################################

def getRR_Root():
    if ('RR_ROOT' in os.environ):
        return os.environ['RR_ROOT'].strip("\r")
    HCPath="%"
    if ((sys.platform.lower() == "win32") or (sys.platform.lower() == "win64")):
        HCPath="%RRLocationWin%"
    elif (sys.platform.lower() == "darwin"):
        HCPath="%RRLocationMac%"
    else:
        HCPath="%RRLocationLx%"
    if HCPath[0]!="%":
        return HCPath
    writeError("This plugin was not installed via rrWorkstationInstaller!")

def getRRSubmitterPath():
    ''' returns the rrSubmitter filename '''
    rrRoot = getRR_Root()
    if ((sys.platform.lower() == "win32") or (sys.platform.lower() == "win64")):
        rrSubmitter = [rrRoot+"\\win__rrSubmitter.bat"]
    elif (sys.platform.lower() == "darwin"):
        rrSubmitter = [rrRoot+"/bin/mac64/rrStartLocal", "rrSubmitter"]
    else:
        rrSubmitter = [rrRoot+"/lx__rrSubmitter.sh"]
    return rrSubmitter

def getRRSubmitterConsolePath():
    ''' returns the rrSubmitter filename '''
    rrRoot = getRR_Root()
    if ((sys.platform.lower() == "win32") or (sys.platform.lower() == "win64")):
        rrSubmitter = [rrRoot+"\\bin\\win64\\rrStartLocal", "rrSubmitterconsole"]
    elif (sys.platform.lower() == "darwin"):
        rrSubmitter = [rrRoot+"/bin/mac64/rrStartLocal", "rrSubmitterconsole"]
    else:
        rrSubmitter = [rrRoot+"/bin/lx64/rrStartLocal", "rrSubmitterconsole"]
    return rrSubmitter
    


##############################################
# Other Global Functions                     #
##############################################


def getOSString():
    if ((sys.platform.lower() == "win32") or (sys.platform.lower() == "win64")):
        return "win"
    elif (sys.platform.lower() == "darwin"):
        return "osx"
    else:
        return "lx"
      
def list_all_comfy_packages():
    import importlib.metadata
    # Fetch all installed distributions in the current environment
    dists = sorted(importlib.metadata.distributions(), key=lambda x: x.metadata['Name'].lower())
    
    #print(f"          PKG | {'Package Name':<30} | {'Version':<15}")
    #print("          PKG | " +"-" * 50)
    
    found_comfy = False
    for dist in dists:
        name = dist.metadata['Name']
        version = dist.version
        
        # Highlight anything related to Comfy
        if "comfy" in name.lower():
            #print(f"          PKG | \033[92m{name:<30} | {version:<15} <-- FOUND\033[0m") green color
            print(f"          PKG | {name:<30} | {version:<15}")
            found_comfy = True
        #else:
            #print(f"          PKG | {name:<30} | {version:<15}")
            
    if not found_comfy:
        print("          PKG | \n--- No package with 'comfy' in the name was found. ---")
        print("          PKG | This confirms that ComfyUI is running as a standalone script folder, not a site-package.")
        

def get_parent_process_file(allow_python):
    DEBUG = True 
    
    try:
        import psutil
    except ImportError:
        print("          get_parent_process_file: psutil not installed")
        return None

    current_exe_path = sys.executable
    current_exe_name = os.path.basename(current_exe_path).lower()
    
    if DEBUG: 
        print(f"          --- Parent Check Start (allow_python={allow_python}) ---")
        print(f"          Current: {current_exe_name}")

    # Step 1: Check if the current executable is what we want
    is_python = any(py in current_exe_name for py in ["python", "python3", "pythonw"])
    
    if allow_python and is_python:
        if DEBUG: print(f"          Found Python as current EXE: {current_exe_path}")
        return current_exe_path
    
    if not is_python and "comfy" in current_exe_name:
        if DEBUG: print(f"          Found Comfy Launcher as current EXE: {current_exe_path}")
        return current_exe_path

    # Step 2: Process Tree Climbing
    try:
        process = psutil.Process(os.getpid())
        
        for i in range(5):
            parent = process.parent()
            if not parent:
                break
            
            try:
                parent_exe = parent.exe()
                parent_name = os.path.basename(parent_exe).lower()
                if DEBUG: print(f"          Level {i+1} Parent: {parent_name}")

                # Logic Switch
                is_parent_python = any(py in parent_name for py in ["python", "python3", "pythonw"])
                
                if allow_python and is_parent_python:
                    if DEBUG: print(f"            -> MATCH: Found Python parent: {parent_exe}")
                    return parent_exe

                if not is_parent_python:
                    # Target Comfy Desktop App
                    if "comfy" in parent_name:
                        if DEBUG: print(f"            -> MATCH: Found Comfy launcher: {parent_exe}")
                        return parent_exe
                    
                    # Ignore Shells and keep climbing
                    if any(sh in parent_name for sh in ["cmd.exe", "powershell.exe", "explorer.exe", "conhost.exe"]):
                        #if DEBUG: print(f"            -> Shell detected, climbing higher...")
                        process = parent
                        continue
                    
                    # If it's something else, we stop here
                    break
                else:
                    # It's Python but allow_python is False -> climb higher
                    process = parent
                    continue

            except (psutil.AccessDenied, psutil.NoSuchProcess):
                break
    except Exception as e:
        if DEBUG: print(f"          Error: {e}")
        
    return None

def get_comfyui_DesktopApp_version():
    ret_version=""
    
    DEBUG_TestAll= True

    env_version = os.environ.get('__COMFYUI_DESKTOP_VERSION__')
    if env_version:
        ret_version=env_version
        print("comfy_AppVer,env: Version is " +ret_version)
        if not DEBUG_TestAll:
            return ret_version
    else:
        print("comfy_AppVer,env: No env var __COMFYUI_DESKTOP_VERSION__")
        
    
    exe_path = get_parent_process_file(False) #ComfyUI.exe if we run the Desktop App
    app_root=""
    if exe_path:
        app_root = os.path.dirname(exe_path)
    print("          (process: "+str(exe_path)+")")
    
    
    if exe_path:
        # Try to find version in the folder path (e.g., "ComfyUI 0.8.3")
        # We search for patterns like 0.8.3 or v0.8.3 in the absolute path
        path_match = re.search(r'[vV]?(\d+\.\d+\.\d+)', app_root)
        if path_match:
            print("comfy_AppVer,exe_path: "+ path_match.group(1))
            if len(ret_version)<1: #this information can be wrong in case someone updated ComfyUI.
                ret_version= path_match.group(1)
            if not DEBUG_TestAll:
                return ret_version
        else:
            print("comfy_AppVer,exe_path: version not found in "+str(app_root))
    else:
        print("comfy_AppVer,exe_path: no process")
    
    if exe_path:
        #Fallback: Read the app.asar tail
        asar_path = os.path.join(app_root, "resources", "app.asar")
        if os.path.exists(asar_path):
            try:
                file_size = os.path.getsize(asar_path)
                # We read the last 64KB to be safe, as metadata can shift
                read_size = min(file_size, 65536)
                with open(asar_path, "rb") as f:
                    #Seek to the end of the file and read the chunk
                    f.seek(file_size - read_size)
                    #We use ignore to skip non-text binary data in the asar
                    chunk = f.read(read_size).decode('utf-8', errors='ignore')

                    # This regex looks for ComfyUI as product and then grabs the version
                    # re.DOTALL is important so that '.' matches newlines
                    target_match = re.search(r'"productName"\s*:\s*"ComfyUI".*?"version"\s*:\s*"(\d+\.\d+\.\d+)"', chunk, re.DOTALL)
        
                    if target_match:
                        ret_version = target_match.group(1)
                        print("comfy_AppVer,asar1: "+ret_version)
                        if not DEBUG_TestAll:
                            return ret_version
                    else:
                        # Fallback to the very first version string found in the chunk
                        all_versions = re.findall(r'"version"\s*:\s*"(\d+\.\d+\.\d+)"', chunk)
                        if all_versions:
                            ret_version = all_versions[0]
                            print("comfy_AppVer,asar2: "+ret_version)
                            if not DEBUG_TestAll:
                                return ret_version

            except Exception as e:
                print("comfy_AppVer,asar: "+str(e))
        else:
            print("comfy_AppVer,asar: file not found "+str(asar_path))
    else:
        print("comfy_AppVer,asar: no process")
            
    if exe_path:       
        if (sys.platform == "win32") and exe_path.endswith(".exe") and ("python" not in exe_path.lower()):
            try:
                import ctypes
                # Get the size of the version information block
                size = ctypes.windll.version.GetFileVersionInfoSizeW(exe_path, None)
                if size > 0:
                    # Create a buffer to hold the version info
                    buffer = ctypes.create_string_buffer(size)
                    ctypes.windll.version.GetFileVersionInfoW(exe_path, None, size, buffer)

                    # Retrieve the fixed file info (binary structure)
                    # This gives us the major, minor, build, and private version numbers
                    fixed_info_ptr = ctypes.c_void_p()
                    fixed_info_len = ctypes.c_uint()
                    ctypes.windll.version.VerQueryValueW(buffer, "\\", ctypes.byref(fixed_info_ptr), ctypes.byref(fixed_info_len))
                    
                    # Extract the version numbers from the memory structure
                    # The structure is VS_FIXEDFILEINFO; we need indices for the DWORDs
                    res = ctypes.cast(fixed_info_ptr, ctypes.POINTER(ctypes.c_uint32))
                    
                    # Version is stored as:
                    # dwFileVersionMS (High 16 bits = Major, Low 16 bits = Minor)
                    # dwFileVersionLS (High 16 bits = Build, Low 16 bits = Revision)
                    file_version_ms = res[4]
                    file_version_ls = res[5]
                    
                    major = file_version_ms >> 16
                    minor = file_version_ms & 0xFFFF
                    build = file_version_ls >> 16
                    # revision = file_version_ls & 0xFFFF
                    
                    ret_version= f"{major}.{minor}.{build}"
                    print( "comfy_AppVer,exe: " + ret_version )
                    if not DEBUG_TestAll:
                        return ret_version
            except Exception as e:
                print("comfy_AppVer,exe: "+str(e))

        if sys.platform == "darwin":
            # Typical path: ComfyUI.app/Contents/Info.plist
            # You can use 'defaults read' or plistlib
            try:
                import plistlib
                plist_path = os.path.join(os.path.dirname(os.path.dirname(exe_path)), "Info.plist")
                with open(plist_path, 'rb') as f:
                    pl = plistlib.load(f)
                    ret_version=pl.get('CFBundleShortVersionString')
                    print( "comfy_AppVer,exe: " + ret_version )
                    if not DEBUG_TestAll:
                        return ret_version                    
            except Exception as e:
                print("comfy_AppVer,exe: "+str(e))    
    else:
        print("comfy_AppVer,exe: no process")                  
        
    return ret_version     
        
def get_comfyui_core_version():
    ret_version = ""
    DEBUG_TestAll = True # Keeping it True to see all detection paths in logs


    try:
        import comfyui_version
        ret_version= comfyui_version.__version__
        print(f"comfy_coreVer,import: {ret_version}")
        if not DEBUG_TestAll: return ret_version
    except Exception as e:
        print("comfy_coreVer,import: "+str(e))
        print("sys.path is "+str(sys.path));
        return ""
        

    for p in sys.path:
        if not p or p == ".": continue
        abs_p = os.path.abspath(p)
        
        # Check current path and parent (for 'comfy' subfolder cases)
        potential_roots = [abs_p, os.path.dirname(abs_p)]
        
        for root in potential_roots:
            # Target 1: comfyui_version.py (Runtime artifact)
            target_vpy = os.path.join(root, "comfyui_version.py")
            if os.path.exists(target_vpy):
                #print(f"          found file "+target_vpy)
                try:
                    with open(target_vpy, "r", encoding="utf-8") as f:
                        match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', f.read())
                        if match:
                            ret_version = str(match.group(1))
                            print(f"comfy_coreVer,file: {target_vpy} -> {ret_version}")
                            if not DEBUG_TestAll: return ret_version
                except Exception as e:
                    print(f"comfy_coreVer,vpy_err: does not exist "+str(target_vpy))

            # Target 2: pyproject.toml (Project source)
            target_toml = os.path.join(root, "pyproject.toml")
            if os.path.exists(target_toml):
                #print(f"          found file "+target_toml)
                try:
                    with open(target_toml, "r", encoding="utf-8") as f:
                        # Simple regex to avoid needing a TOML library
                        match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', f.read(), re.MULTILINE)
                        if match:
                            ret_version = str(match.group(1))
                            print(f"comfy_coreVer,toml: {target_toml} -> {ret_version}")
                            if not DEBUG_TestAll: return ret_version
                except Exception as e:
                    print(f"comfy_coreVer,toml_err: {e}")
        
        if ret_version and not DEBUG_TestAll: break



    exe_path = get_parent_process_file(False) #ComfyUI.exe if we run the Desktop App
    if exe_path:
        print("          (parentProcess: "+str(exe_path)+")")
        app_root = os.path.dirname(exe_path)
        
        #Read the app.asar tail
        asar_path = os.path.join(app_root, "resources", "app.asar")
        if os.path.exists(asar_path):
            try:
                file_size = os.path.getsize(asar_path)
                # We read the last 64KB to be safe, as metadata can shift
                read_size = min(file_size, 65536)
                with open(asar_path, "rb") as f:
                    #Seek to the end of the file and read the chunk
                    f.seek(file_size - read_size)
                    #We use ignore to skip non-text binary data in the asar
                    chunk = f.read(read_size).decode('utf-8', errors='ignore')

                    # This regex looks for ComfyUI as product and then grabs the version
                    # re.DOTALL is important so that '.' matches newlines
                    target_match = re.search(r'"comfyUI"\s*:\s*\{.*?"version"\s*:\s*"(\d+\.\d+\.\d+)"', chunk, re.DOTALL)
        
                    if target_match:
                        ret_version = target_match.group(1)
                        print("comfy_coreVer,asar1: "+ret_version)
                        if not DEBUG_TestAll:
                            return ret_version
                    else:
                        # Fallback to the very first version string found in the chunk
                        all_versions = re.findall(r'"version"\s*:\s*"(\d+\.\d+\.\d+)"', chunk)
                        if all_versions:
                            ret_version = all_versions[0]
                            print("comfy_coreVer,asar2: "+ret_version)
                            if not DEBUG_TestAll:
                                return ret_version

            except Exception as e:
                print("comfy_coreVer,asar_exe: "+str(e))
        else:
            print("comfy_coreVer,asar_exe: file not found "+str(asar_path))

    return ret_version    
        
        
def safe_make_dirs(target_path_str):
    """
    Creates the target directory only if the parent's parent already exists.
    This prevents accidental creation of deep, incorrect directory structures.
    """
    target_path = Path(target_path_str)
    
    # Check the "grandparent" directory (2 levels up)
    grandparent = target_path.parent.parent
    
    if grandparent.exists():
        if not target_path.exists():
            # exist_ok=True prevents errors if another process creates it simultaneously
            os.makedirs(target_path, exist_ok=True)
            writeError(f"Directory created: {target_path}")
        else:
            writeError(f"Directory already exists: {target_path}")
        return True
    else:
        # Grandparent does not exist - safety trigger
        writeError(f"Safety Error: Base path '{grandparent}' not found. Directory will not be created.")
        return False
        
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
            print(f"Directory created: {target_dir}")
        return True
    else:
        # Safety trigger: Base structure is missing
        error_msg = f"Safety Error: Base path '{base_structure}' not found. Check your server connection or mapping."
        print(error_msg)
        # You might want to raise an exception here to catch it in your handler
        raise Exception(error_msg)
        
##############################################
#                                            #
##############################################        




def get_workflow_settings(workflow):
    """
    Extracts the RR settings from the workflow data.
    Supports both dictionary-based input (Web API/JSON) and object-based input.
    """
    # 1. Access the 'extra' section safely based on the data type
    if isinstance(workflow, dict):
        #print("get_workflow_settings:  Workflow is a dictionary (from JS fetch/JSON)")
        # Case: Workflow is a dictionary (from JS fetch/JSON)
        if "extra" not in workflow:
            workflow["extra"] = {}
        
        # Ensure our specific settings key exists as a dictionary
        if SETTINGS_KEY not in workflow["extra"]:
            workflow["extra"][SETTINGS_KEY] = {}
            
        settings = workflow["extra"][SETTINGS_KEY]
    else:
        #print("get_workflow_settings:  Workflow is an object (legacy/internal ComfyUI structure)")
        # Case: Workflow is an object (legacy/internal ComfyUI structure)
        if not hasattr(workflow, 'extra'):
            workflow.extra = {}
        
        # setdefault ensures the key exists without overwriting existing data
        settings = workflow.extra.setdefault(SETTINGS_KEY, {})

    #print("get_workflow_settings: "+str(settings))

    # 2. Fill in missing fields with default values
    # This ensures your logic always finds the expected keys, 
    # even if the user never opened the settings modal in the browser.
    for key, info in SETTINGS_FIELDS.items():
        # Skip UI-only elements like separators
        if info.get("type") == "separator":
            continue
            
        if key not in settings:
            # Calls your computation logic from the logic file
            settings[key] = settings_compute_default(key)
    return settings

    

def createJobXML(submission_tmpFile, newJob):
    xmlObj= newJob.writeToXMLstart(None)
    newJob.writeToXMLJob(xmlObj)
    ret = newJob.writeToXMLEnd(submission_tmpFile, xmlObj)
    if ret:
        writeInfo("Job written to " + submission_tmpFile.name)
        pass
    else:
        error_msg="Error - There was a problem writing the job file to " + submission_tmpFile.name
        raise Exception(error_msg)


    return True


def submit_job_to_royalrender(newJob,  consoleMode):
    submission_tmpFile = tempfile.NamedTemporaryFile(mode='w+b',
                                  prefix="rrSubmitComfy_",
                                  suffix=".xml",
                                  delete=False)
                                  
    createJobXML(submission_tmpFile, newJob)
    
    rr_env= os.environ.copy()
    envCount= len(list(rr_env))
    ie=0
    while (ie<envCount):
        envVar= list(rr_env)[ie]
        if envVar.startswith("QT_"):
            del rr_env[envVar]
            envCount= envCount -1
        else:
            ie= ie+1
    
    if consoleMode:
        royalrender_command = getRRSubmitterConsolePath()
    else:
        royalrender_command = getRRSubmitterPath()
    if not royalrender_command:
        raise Exception("RoyalRender path not found!\nPlease provide environment variable RR_ROOT or hardcode path in rrSubmit.py")
        return False #should not be called after raise
    
    royalrender_command.append( submission_tmpFile.name)
    writeInfo("Executing "+str(royalrender_command))

    try:
        proc = subprocess.Popen(
            royalrender_command, 
            close_fds=True,
            env=rr_env,
            encoding='UTF-8'
        )
        return True
        
    except FileNotFoundError:
        exe_name = royalrender_command[0] if isinstance(royalrender_command, list) else royalrender_command
        writeError(f"ERROR: RoyalRender executable not found! {exe_name}")
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        line_number = exc_tb.tb_lineno
        func_name = exc_tb.tb_frame.f_code.co_name
        error_details = f"Error: {e} | Line: {line_number} | Function: {func_name}"
        error_msg=f"submit_job_to_royalrender failed:  {error_details}"

        full_stack = traceback.format_exc()
        
        writeError(error_msg)
        writeError(f"-submit_job_to_royalrender] FULL DEBUG STACK:\n{full_stack}")
        raise Exception(error_msg)




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
        links[:] = [l for l in links if l[0] != old_link]
        existing_input["link"] = new_link_id
    
    # (English comment) Update the global links list
    slot_idx = next(idx for idx, i in enumerate(dst_node["inputs"]) if i["name"] == dst_input_name)
    links.append([new_link_id, src_id, src_out_idx, dst_id, slot_idx, "INT"])
    


def swap_to_rr_nodes(workflow, outNodeID, outName, outExt, isVideo, global_output_path):
    if "nodes" not in workflow:
        return workflow
        
    nodes = workflow["nodes"]
    links = workflow.get("links", [])
    settings = get_workflow_settings(workflow)
    
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




OUTPUT_NODE_TYPES = {"SaveImage", "SaveVideo", "rrSaveImage", "rrSaveVideo"}
CHECKPOINT_TYPES = {"CheckpointLoaderSimple", "CheckpointLoader", "UNETLoader"}
OUTPUT_FILENAME_KEYS = ["path", "filename", "output_path"]

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
            if isinstance(fmt, list): fmt = fmt[0]
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


def workflow_getOutput(workflow: Dict):
    """
    Extracts output information from the workflow.
    Returns: (outName, outExt, isVideo)
    """
    if not workflow:
        raise Exception("rrSubmit - Empty workflow data.")

    found_output = False
    found_input_checkpoint = False
    
    out_name = None
    out_ext = None
    out_node = None
    is_video = False

    # Detect if we are dealing with a UI-style list or API-style dict
    nodes_data = workflow.get("nodes")
    
    if isinstance(nodes_data, list):
        # UI Format: nodes is a list of dictionaries
        for node in nodes_data:
            class_type = node.get("type", "")
            
            if class_type in OUTPUT_NODE_TYPES:
                found_output = True
                if out_name is None:
                    out_name, out_ext, is_video = _get_output_info(node)
                    out_node= node.get("id")

            if class_type in CHECKPOINT_TYPES:
                found_input_checkpoint = True
    else:
        # API Format: workflow itself is a dict of node_id: node_dict
        for node_id, node in workflow.items():
            if not isinstance(node, dict):
                continue
                
            class_type = node.get("class_type", "")
            
            if class_type in OUTPUT_NODE_TYPES:
                found_output = True
                if out_name is None:
                    out_name, out_ext, is_video = _get_output_info(node)
                    out_node= node.get("id")

            if class_type in CHECKPOINT_TYPES:
                found_input_checkpoint = True

    # Error handling
    if not found_output:
        raise Exception("[rrSubmit] No output nodes found in workflow.")
    if not found_input_checkpoint:
        raise Exception("[rrSubmit] No checkpoint loader found in workflow.")
    if out_name is None:
        raise Exception("[rrSubmit] Found output node, but could not extract filename.")

    return out_node, out_name, out_ext, is_video
    
    import json
    
    

# Globaler Speicher für die Antworten vom Frontend

from server import PromptServer
from aiohttp import web

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
    
    
def save_workflow(settings, workflowName, workflowHybrid, workflowApiRR, workflowUI, outNodeID, outFixedFilename):
        final_json = workflowHybrid 
        final_json["api_format_rr"] = workflowApiRR 
        final_json["ui"] = workflowUI 
        final_json["rr_metadata"] = {
            "version": "1.0",
            "layer_node_id": outNodeID,
            "fixed_filename": outFixedFilename
        }
        
        #save dublicate of workflow 
        timestamp = datetime.now().strftime("%m%d-%H%M%S") #datetime.now().strftime("%y%m%d-%H%M%S")
        filename = f"RR_{workflowName}__{timestamp}.json"
        filepath= settings['farm_workflow_path']
        if len(filepath) <3: 
            raise Exception(f"farm_workflow_path not set in submission settings")
        filepath = os.path.join(filepath, filename)
        success = safe_make_dirs_for_file(filepath)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(final_json, f, indent=2)
        writeInfo(f"[rrSubmit] Workflow saved to {filepath}")

        global DEBUG
        if DEBUG:
            with open(filepath.replace(".json","")+"_apiRR.json", "w", encoding="utf-8") as f:
                json.dump(workflowApiRR, f, indent=2)
            with open(filepath.replace(".json","")+"_apiComfy.json", "w", encoding="utf-8") as f:
                json.dump(workflowHybrid.get("api_export_comfy", {}), f, indent=2)
            with open(filepath.replace(".json","")+"_UI.json", "w", encoding="utf-8") as f:
                json.dump(workflowUI, f, indent=2)
        
        return filepath
        
        

def print_exception(e, location):
    error_msg = str(e)
    if "Line:" in error_msg:
        pass #we already printed all info
        return False, None
    else:    
        exc_type, exc_obj, exc_tb = sys.exc_info()
        line_number = exc_tb.tb_lineno
        func_name = exc_tb.tb_frame.f_code.co_name
        error_details = f"Error: {e} | Line: {line_number} | Function: {func_name}"
        error_msg=f"[rrSubmit] {location}:  {error_details}"

        full_stack = traceback.format_exc()
        
        writeError(error_msg)
        writeError(f"[rrSubmit-submit_workflow] FULL DEBUG STACK:\n{full_stack}")
        raise Exception(error_msg)    


def submit_workflow(workflowHybrid, workflowName):
    try:
        writeInfo(f"-------------------- rrSubmit version %rrVersion% --------------------")
        global DEBUG
        DEBUG_BREAK= DEBUG
        
        outNodeID=-1
        outFixedFilename="none"
        
        workflowUI= workflowHybrid["ui"]
        settings = get_workflow_settings(workflowUI) 

        workflowHybrid["api_export_comfy"] =sort_comfy_api_workflow(workflowHybrid.get("api_export_comfy", {}) )
        
        '''
        ourConversionBreaksFile= False
        #we verify that our function convert_ui_to_api_dynamic works with this workflow
        try:
            workflowApiRR = convert_ui_to_api_dynamic(workflowUI)
        except Exception as e:
            print_exception(e, "submit_workflow")
                
        try:
            compare_workflows(workflowApiRR, workflowHybrid.get("api_export_comfy", {}))
            print("submit_workflow: Validation SUCESS (1)")
        except Exception as e:
            ourConversionBreaksFile= True
            try:
                save_workflow(settings, workflowName, workflowHybrid, workflowApiRR, workflowUI, outNodeID, outFixedFilename)
            except:
                pass
            print("WARNING: submit_workflow: Validation failed (1): "+str(e))
            if DEBUG_BREAK:
                return False, None
        '''

            

        outNodeID, outName, outExt, isVideo = workflow_getOutput(workflowUI)
        
      
        global_output_path=""
        global_output_path= settings['output_path']
        
        if len(global_output_path) ==0:            
            global_output_path= folder_paths.get_output_directory()        
        o_path = Path(global_output_path)
        if not o_path.is_absolute():
            raise Exception("No output path!")            
        
        o_path = Path(outName)
        if not o_path.is_absolute():
            outName = os.path.join(global_output_path, outName)    
        
        #workflowApiComfy_Changed=workflowHybrid.get("api_export_comfy", {})
        workflowUI, outFixedFilename = swap_to_rr_nodes(workflowUI, outNodeID, outName, outExt, isVideo, global_output_path)
        
        #We wanted the workflow in UI format to the able to load it in ComfyUI FrontEnd to verify what we have done.
        #But the ComfyUI core/backend does not know this format at all. They use a different API format. 
        #So we need the API format for rendering
        #So we invented: THE HYBRID FORMAT!  UI format with an extra field for the API data that the frontend ignores
                
        workflowApiRR = convert_ui_to_api_dynamic(workflowUI)
        
        
        filepath= save_workflow(settings, workflowName, workflowHybrid, workflowApiRR, workflowUI, outNodeID, outFixedFilename)

        '''
        try:
            compare_workflows(workflowApiRR, workflowHybrid.get("api_export_comfy", {}))
            print("submit_workflow: Validation SUCESS (2)")
        except Exception as e:
            print_exception(e, "submit_workflow: Validation failed (2)")
            return False, workflowUI        
        '''

        #create rrJob
        newJob=rrJob()
        newJob.software = "ComfyUI"
        newJob.sceneOS = getOSString()
        
        newJob.version = get_comfyui_DesktopApp_version()
        if len(newJob.version) >0:
            newJob.rendererVersion= get_comfyui_core_version()
            newJob.renderer="Desktop"
        else:
            newJob.version = get_comfyui_core_version()
            newJob.renderer="Portable"
        
        newJob.layer="__ID" + str(outNodeID)
        node_info = workflowUI.get(str(outNodeID))
        if node_info:
            user_title = node_info.get("_meta", {}).get("title", newJob.layer)
            newJob.layer= user_title + newJob.layer
        else:
            writeError(f"Node mit ID {outNodeID} not found.")
    
        newJob.sceneName = filepath
        newJob.seqStart = 1
        newJob.seqEnd = settings['iteration_idxs_count']
        newJob.imageFileName = outName
        newJob.imageExtension = outExt
        newJob.customVars["Comfy_OutDir"]=global_output_path
        newJob.imageSingleOutput = isVideo
        if len(settings['local_model_dir']) > 1:
            newJob.customVars["OnSubmit_CopyLocalDir"]=settings['local_model_dir']
        else:
            newJob.customVars["OnSubmit_CopyLocalDir"]=folder_paths.models_dir
            
        newJob.customVars["OnSubmit_CopyDestDir"]=settings['farm_model_dir']
        newJob.customVars["OnSubmit_CopyMode"]=settings['model_sync_mode']
        
        newJob.submitOptions["SeqDivMIN"]= "0~" + str(settings['seq_div_min'])
        if (not outFixedFilename):
            newJob.submitOptions["DoNotCheckForFrames"]= "0~1"
       
        
        #we return the path to the new workflow file to ask within UI to open the copy
        if "extra" not in workflowUI:
            workflowUI["extra"] = {}
        if "info" not in workflowUI["extra"]:
            workflowUI["extra"]["info"] = {}
        workflowUI["extra"]["info"]["name"] = f"SUBMITTED_{workflowName}"
        workflowUI["extra"]["info"]["locked"] = True
        workflowUI["extra"]["rr_full_path"] = filepath
       
        #return True, workflowUI
        
        # Submit to RoyalRender
        submitSuccess= submit_job_to_royalrender(newJob, (not settings.get("ui_submit")))
        writeInfo(f"-------------------- Done--------------------")
        return submitSuccess, workflowUI
        
    except Exception as e:
        print_exception(e, "submit_workflow")
    
    
