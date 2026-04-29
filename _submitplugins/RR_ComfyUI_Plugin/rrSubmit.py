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
import sys
import tempfile
import folder_paths
import subprocess #it is imported now as the CompfyUI security/vulnerability check  
import traceback
from pathlib import Path
import re
from xml.etree.ElementTree import ElementTree, Element, SubElement
from . import rrWorkflow

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
        writeError(f"FULL DEBUG STACK:\n{full_stack}")
        raise Exception(error_msg)    


def argValid(argValue):
    return ((argValue is not None) and (len(str(argValue))>0))

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
        sub.text = text
        return sub

    def writeToXMLstart(self, globalSubmitOptions):
        rootElement = Element("rrJob_submitFile")
        rootElement.attrib["syntax_version"] = "6.0"
        self.subE(rootElement, "DeleteXML", "1")
        if (globalSubmitOptions is not None and len(globalSubmitOptions)>0):
            self.subE(rootElement, "SubmitterParameter", globalSubmitOptions)
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
            writeError("No valid file has been passed to the write function")
            try:
                f.close()
            except Exception:  
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
    
    #writeDebug(f"          PKG | {'Package Name':<30} | {'Version':<15}")
    #writeDebug("          PKG | " +"-" * 50)
    
    found_comfy = False
    for dist in dists:
        name = dist.metadata['Name']
        version = dist.version
        
        # Highlight anything related to Comfy
        if "comfy" in name.lower():
            #writeDebug(f"          PKG | \033[92m{name:<30} | {version:<15} <-- FOUND\033[0m") green color
            writeDebug(f"          PKG | {name:<30} | {version:<15}")
            found_comfy = True
        #else:
            #writeDebug(f"          PKG | {name:<30} | {version:<15}")
            
    if not found_comfy:
        writeDebug("          PKG | \n--- No package with 'comfy' in the name was found. ---")
        writeDebug("          PKG | This confirms that ComfyUI is running as a standalone script folder, not a site-package.")
        

def get_parent_process_file(allow_python):
    
    try:
        import psutil
    except ImportError:
        writeInfo("          get_parent_process_file: psutil not installed")
        return None

    current_exe_path = sys.executable
    current_exe_name = os.path.basename(current_exe_path).lower()
    
    writeDebug(f"          --- Parent Check Start (allow_python={allow_python}) ---")
    writeDebug(f"          Current: {current_exe_name}")

    # Step 1: Check if the current executable is what we want
    is_python = any(py in current_exe_name for py in ["python", "python3", "pythonw"])
    
    if allow_python and is_python:
        writeDebug(f"          Found Python as current EXE: {current_exe_path}")
        return current_exe_path
    
    if not is_python and "comfy" in current_exe_name:
        writeDebug(f"          Found Comfy Launcher as current EXE: {current_exe_path}")
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
                writeDebug(f"          Level {i+1} Parent: {parent_name}")

                # Logic Switch
                is_parent_python = any(py in parent_name for py in ["python", "python3", "pythonw"])
                
                if allow_python and is_parent_python:
                    writeDebug(f"            -> MATCH: Found Python parent: {parent_exe}")
                    return parent_exe

                if not is_parent_python:
                    # Target Comfy Desktop App
                    if "comfy" in parent_name:
                        writeDebug(f"            -> MATCH: Found Comfy launcher: {parent_exe}")
                        return parent_exe
                    
                    # Ignore Shells and keep climbing
                    if any(sh in parent_name for sh in ["cmd.exe", "powershell.exe", "explorer.exe", "conhost.exe"]):
                        #writeDebug(f"            -> Shell detected, climbing higher...")
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
        writeDebug(f"          Error: {e}")
        
    return None

def get_comfyui_DesktopApp_version():
    ret_version=""
    
    DEBUG_TestAll= hasEnvDebugMode()

    env_version = os.environ.get('__COMFYUI_DESKTOP_VERSION__')
    if env_version:
        ret_version=env_version
        writeInfo("comfy_AppVer,env: Version is " +ret_version)
        if not DEBUG_TestAll:
            return ret_version
    else:
        writeInfo("comfy_AppVer,env: No env var __COMFYUI_DESKTOP_VERSION__")
        
    
    exe_path = get_parent_process_file(False) #ComfyUI.exe if we run the Desktop App
    app_root=""
    if exe_path:
        app_root = os.path.dirname(exe_path)
    writeInfo("          (process: "+str(exe_path)+")")
    
    
    if exe_path:
        # Try to find version in the folder path (e.g., "ComfyUI 0.8.3")
        # We search for patterns like 0.8.3 or v0.8.3 in the absolute path
        path_match = re.search(r'[vV]?(\d+\.\d+\.\d+)', app_root)
        if path_match:
            writeInfo("comfy_AppVer,exe_path: "+ path_match.group(1))
            if len(ret_version)<1: #this information can be wrong in case someone updated ComfyUI.
                ret_version= path_match.group(1)
            if not DEBUG_TestAll:
                return ret_version
        else:
            writeInfo("comfy_AppVer,exe_path: version not found in "+str(app_root))
    else:
        writeInfo("comfy_AppVer,exe_path: no process")
    
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
                        writeInfo("comfy_AppVer,asar1: "+ret_version)
                        if not DEBUG_TestAll:
                            return ret_version
                    else:
                        # Fallback to the very first version string found in the chunk
                        all_versions = re.findall(r'"version"\s*:\s*"(\d+\.\d+\.\d+)"', chunk)
                        if all_versions:
                            ret_version = all_versions[0]
                            writeInfo("comfy_AppVer,asar2: "+ret_version)
                            if not DEBUG_TestAll:
                                return ret_version

            except Exception as e:
                writeInfo("comfy_AppVer,asar: "+str(e))
        else:
            writeInfo("comfy_AppVer,asar: file not found "+str(asar_path))
    else:
        writeInfo("comfy_AppVer,asar: no process")
            
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
                    writeInfo( "comfy_AppVer,exe: " + ret_version )
                    if not DEBUG_TestAll:
                        return ret_version
            except Exception as e:
                writeInfo("comfy_AppVer,exe: "+str(e))

        if sys.platform == "darwin":
            # Typical path: ComfyUI.app/Contents/Info.plist
            # You can use 'defaults read' or plistlib
            try:
                import plistlib
                plist_path = os.path.join(os.path.dirname(os.path.dirname(exe_path)), "Info.plist")
                with open(plist_path, 'rb') as f:
                    pl = plistlib.load(f)
                    ret_version=pl.get('CFBundleShortVersionString')
                    writeInfo( "comfy_AppVer,exe: " + ret_version )
                    if not DEBUG_TestAll:
                        return ret_version                    
            except Exception as e:
                writeInfo("comfy_AppVer,exe: "+str(e))    
    else:
        writeInfo("comfy_AppVer,exe: no process")                  
        
    return ret_version     
        
def get_comfyui_core_version():
    ret_version = ""
    DEBUG_TestAll = hasEnvDebugMode()


    try:
        import comfyui_version
        ret_version= comfyui_version.__version__
        writeInfo(f"comfy_coreVer,import: {ret_version}")
        if not DEBUG_TestAll: 
            return ret_version
    except Exception as e:
        writeInfo("comfy_coreVer,import: "+str(e))
        writeInfo("sys.path is "+str(sys.path))
        return ""
        

    for p in sys.path:
        if not p or p == ".": 
            continue
        abs_p = os.path.abspath(p)
        
        # Check current path and parent (for 'comfy' subfolder cases)
        potential_roots = [abs_p, os.path.dirname(abs_p)]
        
        for root in potential_roots:
            # Target 1: comfyui_version.py (Runtime artifact)
            target_vpy = os.path.join(root, "comfyui_version.py")
            if os.path.exists(target_vpy):
                #writeInfo(f"          found file "+target_vpy)
                try:
                    with open(target_vpy, "r", encoding="utf-8") as f:
                        match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', f.read())
                        if match:
                            ret_version = str(match.group(1))
                            writeInfo(f"comfy_coreVer,file: {target_vpy} -> {ret_version}")
                            if not DEBUG_TestAll: 
                                return ret_version
                except Exception as e:
                    writeInfo("comfy_coreVer,vpy_err: open "+str(target_vpy)+" "+str(e))
            #else:
            #    writeInfo("comfy_coreVer,vpy_err: does not exist "+str(target_vpy))

            # Target 2: pyproject.toml (Project source)
            target_toml = os.path.join(root, "pyproject.toml")
            if os.path.exists(target_toml):
                #writeInfo(f"          found file "+target_toml)
                try:
                    with open(target_toml, "r", encoding="utf-8") as f:
                        # Simple regex to avoid needing a TOML library
                        match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', f.read(), re.MULTILINE)
                        if match:
                            ret_version = str(match.group(1))
                            writeInfo(f"comfy_coreVer,toml: {target_toml} -> {ret_version}")
                            if not DEBUG_TestAll: 
                                return ret_version
                except Exception as e:
                    writeInfo(f"comfy_coreVer,toml_err: {e}")
        
        if ret_version and not DEBUG_TestAll:
            break



    exe_path = get_parent_process_file(False) #ComfyUI.exe if we run the Desktop App
    if exe_path:
        writeInfo("          (parentProcess: "+str(exe_path)+")")
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
                        writeInfo("comfy_coreVer,asar1: "+ret_version)
                        if not DEBUG_TestAll:
                            return ret_version
                    else:
                        # Fallback to the very first version string found in the chunk
                        all_versions = re.findall(r'"version"\s*:\s*"(\d+\.\d+\.\d+)"', chunk)
                        if all_versions:
                            ret_version = all_versions[0]
                            writeInfo("comfy_coreVer,asar2: "+ret_version)
                            if not DEBUG_TestAll:
                                return ret_version

            except Exception as e:
                writeInfo("comfy_coreVer,asar_exe: "+str(e))
        else:
            writeInfo("comfy_coreVer,asar_exe: file not found "+str(asar_path))

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
        
##############################################
#                                            #
##############################################        




    

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
        subprocess.Popen(
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



 
    
    

def submit_workflow(workflowHybrid, workflowName, submit_node_id):
    try:
        writeInfo("-------------------- rrSubmit version %rrVersion% --------------------")
        
        outNodeID=-1
        outFixedFilename="none"
        
        workflowUI= workflowHybrid["ui"]
    

        '''
        DEBUG_BREAK= hasEnvDebugMode()
        ourConversionBreaksFile= False
        #we verify that our function convert_ui_to_api_dynamic works with this workflow
        try:
            workflowApiRR = rrWorkflow.convert_ui_to_api_dynamic(workflowUI)
        except Exception as e:
            print_exception(e, "submit_workflow")
                
        try:
            rrWorkflow.compare_workflows(workflowApiRR, workflowHybrid.get("api_export_comfy", {}))
            writeInfo("submit_workflow: Validation SUCESS (1)")
        except Exception as e:
            ourConversionBreaksFile= True
            writeError("WARNING: submit_workflow: Validation failed (1): "+str(e))
        if DEBUG_BREAK:
            return False, None
        '''

        settings = rrWorkflow.get_workflow_settings(workflowUI, getRR_Root()) 
        
        if (not submit_node_id or (submit_node_id==-1) or (submit_node_id=="-1")):
            submit_node_id=""
        if submit_node_id:
            writeDebug(f"Submitting node only: {submit_node_id}")
        
        # Checkpoint Prüfung über die neue Funktion
        if not rrWorkflow.workflow_has_any_loader(workflowUI):
            writeInfo("Warning: No checkpoint loader found in workflow.")

        workflowHybrid["api_export_comfy"] = rrWorkflow.sort_comfy_api_workflow(workflowHybrid.get("api_export_comfy", {}) )

        summaryData= rrWorkflow.analyze_workflow_detailed(workflowUI)
        rrWorkflow.print_workflow_analysis(summaryData) 

        outNodeID, outName, outExt, isVideo = rrWorkflow.getOutput(workflowUI, submit_node_id)
        
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



        ###################### we have collected all settings, time to change stuff ###################### 

        #add some stats. IN some future version we might be able to copy only custom nodes and models that are used
        if "rr_metadata" not in workflowHybrid:
            workflowHybrid["rr_metadata"] = {}
        workflowHybrid["rr_metadata"].update({
            "summary": summaryData,
            })


        workflowUI= rrWorkflow.disable_Outputs(workflowUI, outNodeID)
        workflowUI, outFixedFilename = rrWorkflow.swap_to_rr_nodes(workflowUI, outNodeID, outName, outExt, isVideo, global_output_path, settings)
        
        if (settings.get('add_seed')):
            workflowUI = rrWorkflow.add_rrSeed(workflowUI)


        #We wanted the workflow in UI format to the able to load it in ComfyUI FrontEnd to verify what we have done.
        #But the ComfyUI core/backend does not know this format at all. They use a different API format. 
        #So we need the API format for rendering
        #So we invented: THE HYBRID FORMAT!  UI format with an extra field for the API data that the frontend ignores
                
        workflowApiRR =  rrWorkflow.convert_ui_to_api_dynamic(workflowUI)
        if (workflowApiRR):
            print("workflowApiRR works fine")
        else:
            print(f"workflowApiRR is {workflowApiRR}")
        
        
        filepath= rrWorkflow.save_workflow(settings['farm_workflow_path'], workflowName, workflowHybrid, workflowApiRR, workflowUI, outNodeID, outFixedFilename)

        '''
        try:
            compare_workflows(workflowApiRR, workflowHybrid.get("api_export_comfy", {}))
            writeInfo("submit_workflow: Validation SUCESS (2)")
        except Exception as e:
            print_exception(e, "submit_workflow: Validation failed (2)")
            return False, workflowUI        
        '''

        ########################### create rrJob  ########################### 
        newJob=rrJob()
        newJob.software = "ComfyUI"
        newJob.sceneOS = getOSString()
        
        newJob.version = get_comfyui_core_version()
        #newJob.version = get_comfyui_DesktopApp_version()
        if (len(newJob.version) >0) and not settings['use_portable']:
            newJob.renderer="Desktop"
        else:
            newJob.renderer="Portable"
        
        newJob.layer="__ID" + str(outNodeID)
        if outNodeID:
            node_info = next((n for n in workflowUI.get("nodes", []) if str(n.get("id")) == str(outNodeID)), None)
            if node_info:
                class_name = node_info.get("type", "Unknown")
                user_title = node_info.get("title") or f"[{class_name}]"
                newJob.layer = user_title + newJob.layer
            else:
                writeError(f"Node mit ID {outNodeID} not found.")
    
        newJob.sceneName = filepath
        newJob.seqStart = 1
        newJob.seqEnd = settings['iteration_idxs_count']
        newJob.imageFileName = outName
        newJob.imageExtension = outExt
        newJob.customVars["Comfy_OutDir"]=global_output_path #we need to know the base directory for any relative path in any output node
        newJob.imageSingleOutput = isVideo
        if (not outFixedFilename):
            newJob.submitOptions["DoNotCheckForFrames"]= "0~1"

        if (argValid(settings['model_dir_local']) and argValid(settings['model_dir_farm']) and argValid(settings['model_sync_mode'])  and settings['model_sync_mode']!=rrWorkflow.SETTINGS_FIELDS["model_sync_mode"]["choices"][0][1] ):
            newJob.customVars["OnSubmit_CopySourceDir1"]=settings['model_dir_local']
            newJob.customVars["OnSubmit_CopyDestDir1"]=settings['model_dir_farm']
            newJob.customVars["OnSubmit_CopyMode1"]=settings['model_sync_mode']
            newJob.customVars["OnSubmit_CopyExclude1"]="/__pycache__/;/tests/;/Help/;/torch/include/;/cupy/_core/include/"
        if (argValid(settings['nodes_dir_local']) and argValid(settings['nodes_dir_farm']) and argValid(settings['nodes_sync_mode'])  and settings['nodes_sync_mode']!=rrWorkflow.SETTINGS_FIELDS["model_sync_mode"]["choices"][0][1] ):
            newJob.customVars["OnSubmit_CopySourceDir2"]=settings['nodes_dir_local']
            newJob.customVars["OnSubmit_CopyDestDir2"]=settings['nodes_dir_farm']
            newJob.customVars["OnSubmit_CopyMode2"]=settings['nodes_sync_mode']
            newJob.customVars["OnSubmit_CopyExclude2"]="/__pycache__/;/tests/;/Help/;/torch/include/;/cupy/_core/include/"

        #\\HAM-CLUSTER1\GenAIEval\_pipeline\comfyui\packages\ComfyUI_desktop_nvidia_core-v0.12.3_py-3.12.11_prod\base\.venv\Lib\site-packages\cupy\_core\include\ 2000 files

        #Even if you do not copy the files from local on submission, we need it as source at render time
        if argValid(settings['model_dir_farm']):
            newJob.customVars["ModelDir"]=settings['model_dir_farm']
        if argValid(settings['nodes_dir_farm']):
            newJob.customVars["NodesDir"]=settings['nodes_dir_farm']


        if (argValid(settings['seq_div_min'])):
            newJob.submitOptions["SeqDivMINComp"]= "0~" + str(settings['seq_div_min'])
            newJob.submitOptions["SeqDivMAXComp"]= "0~" + str(settings['seq_div_min'])
        if (argValid(settings['gpu_mem_min'])):
            newJob.submitOptions["RequiredGPUMemory"]= "0~" + str(settings['gpu_mem_min'])
       
        if (argValid(settings['model_config_yaml'])):
            newJob.customVars["ModelConfigYaml"]=settings['model_config_yaml']

        if (argValid(settings['auto_install_modules'])):
            if (settings['auto_install_modules']):
                newJob.submitOptions["COAutoInstallModules"]= "0~1"
            else:
                newJob.submitOptions["COAutoInstallModules"]= "0~0"
        if (argValid(settings['sync_models'])):
            if (settings['sync_models']):
                newJob.submitOptions["COLocalSyncModels"]= "0~1"
            else:
                newJob.submitOptions["COLocalSyncModels"]= "0~0"
        if (argValid(settings['sync_nodes'])):
            if (settings['sync_nodes']):
                newJob.submitOptions["COLocalSyncNodes"]= "0~1"
            else:
                newJob.submitOptions["COLocalSyncNodes"]= "0~0"
        
        
        #we return the path to the new workflow file to ask within UI to open the copy
        if "extra" not in workflowUI:
            workflowUI["extra"] = {}
        if "info" not in workflowUI["extra"]:
            workflowUI["extra"]["info"] = {}
        workflowUI["extra"]["info"]["name"] = f"SUBMITTED_{workflowName}"
        workflowUI["extra"]["info"]["locked"] = True
        workflowUI["extra"]["rr_full_path"] = filepath
       
        #if (hasEnvDebugMode_strict()):
            #return True, workflowUI
        
        # Submit to RoyalRender
        submitSuccess= submit_job_to_royalrender(newJob, (not settings.get("ui_submit")))
        writeInfo("-------------------- Done--------------------")
        return submitSuccess, workflowUI
        
    except Exception as e:
        print_exception(e, "submit_workflow")
    
    
