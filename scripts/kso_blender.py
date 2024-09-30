#  Render script for Blender
#  Last Change: %rrVersion%
#  Copyright (c)  Holger Schoenberger - Binary Alchemy
#  Author: Paolo Acampora, Binary Alchemy
from collections import OrderedDict
import datetime
import os
import sys
import time
from pathlib import Path
import bpy
import addon_utils



# Global values used in kso functions
GPU_RENDERERS = ("redshift", "Octane", "Eevee", "Eevee_Next")
CURRENT_RENDERER = ""

AV_FRAME_TIME = 0
global NO_FRAME_LOOP
NO_FRAME_LOOP = False

RENDER_SCENE = ""
RENDER_LAYER = ""
RENDER_PADDING = 4
RENDER_PATH = ""

global wasError_Close
wasError_Close=False

# Logging

def flush_log():
    sys.stdout.flush()
    sys.stderr.flush()

def log_message_base(lvl, msg):
    msg_start = datetime.datetime.now().strftime("' %H:%M.%S") + " rrBlend"

    if (lvl):
        print(f"{msg_start} - {str(lvl)}: {str(msg)}")
    else:
        print(f"{msg_start}      : {str(msg)}")

def log_msg(msg):
    log_message_base("", msg)

def log_msg_dbg(msg):
    #log_message_base("DBG", msg)
    pass

def log_msg_wrn(msg):
    log_message_base("WRN", msg)

def log_msg_err(msg):
    log_message_base("ERR", str(msg)+"\n\n")
    log_message_base("ERR", "Error reported, aborting render script")
    global wasError_Close
    wasError_Close=True
    bpy.ops.wm.quit_blender()


# Startup Utilities

def set_luxcore_CUDA():
    v_major, v_minor, _ = bpy.app.version

    if v_major > 2 or v_minor > 79:
        prefs = bpy.context.preferences
    else:
        prefs = bpy.context.user_preferences

    addon_prefs = prefs.addons["BlendLuxCore"].preferences
    addon_prefs.gpu_backend="CUDA"


def enable_gpu_devices(addon_name='cycles', use_CPU=False, use_optix=False):
    v_major, v_minor, _ = bpy.app.version

    if v_major > 2 or v_minor > 79:
        prefs = bpy.context.preferences
    else:
        prefs = bpy.context.user_preferences

    addon_prefs = prefs.addons[addon_name].preferences
    addon_prefs.refresh_devices()
    available_devices= {}
    
    
    log_msg(f"[GPU] Device mode was set to: {addon_prefs.compute_device_type}")
    
    log_msg(f"[GPU] List of all modes and devices:")
    # Get a list of all device types that are available (in fact all are available, but some do not offer GPU devices to select. E.g. CUDA on AMD computer)
    for compute_device_type in ('CUDA', 'OPENCL', 'OPTIX', 'HIP', 'ONEAPI', 'METAL', 'NONE'):
        try:
            #testing if it is available in this Blender version:
            addon_prefs.compute_device_type = compute_device_type
            available_devices[compute_device_type]=0
            
            if v_major > 2:
                devices = addon_prefs.get_devices_for_type(compute_device_type)
                if len(devices)>0:
                    log_msg(f"[GPU]    {compute_device_type}")
                for device in devices:
                    log_msg(f"[GPU]      device available: {device.type} - {device.name}")
                    available_devices[compute_device_type]= available_devices[compute_device_type] + 1
            else:
                #TODO: Code missing for Blender 2. For now we add all. Which results to CUDA
                available_devices[compute_device_type]=1
        except TypeError:
            #log_msg(f"[GPU]    {compute_device_type} is not available in this Blender version ")
            pass
            
    #set device mode
    if (use_optix):
        addon_prefs.compute_device_type = 'OPTIX'
    elif (available_devices.keys()==0):
        addon_prefs.compute_device_type = 'NONE'
    else:
        for compute_device_type in available_devices.keys():
            if available_devices[compute_device_type]==0:
                continue
            try:
                addon_prefs.compute_device_type = compute_device_type
                break
            except TypeError:
                log_msg_wrn("[GPU] Failed to enable gpu "+str(compute_device_type))
                return False
    log_msg(f"[GPU] Device mode is now: {addon_prefs.compute_device_type}")

    if v_major > 2:
        gpu_count=0
        addon_prefs.refresh_devices()
        devices = addon_prefs.get_devices_for_type(addon_prefs.compute_device_type)
        for device in devices:
            if (device.type == 'CPU'):
                if not use_CPU:
                    continue
            else:
                log_msg(f"[GPU]     Enabling device {gpu_count} {device.name}")
                gpu_count= gpu_count+1
            device.use = True
        log_msg(f"[GPU]     GPU Count: {gpu_count}")
        if (gpu_count==0):
            log_msg_err(f"[GPU]     No GPU, Aborting render")
            return False        
    else:
        devices = addon_prefs.get_devices(bpy.context)
        for device in devices:
            for dev_entry in device:
                log_msg(f"[GPU]     Enabling device {device.type} - {device.name}")
                dev_entry.use = True
    
    return True


def useAllCores():
    if not sys.platform.lower().startswith("win"):
        return
    log_msg("Enabling Performance cores for Intel 12th+...")
    import ctypes
    
    try:
        dllFileName=""
        if "rrBin" in os.environ:
            dllFileName=os.environ["rrBin"]
        elif "RR_ROOT" in os.environ:
            dllFileName=os.environ["RR_ROOT"]
            dllFileName= dllFileName + "\\bin\\win64\\"
        else:
            log_msg("ERROR: Unable to find rrBin or RR_ROOT")
            return
        dllFileName= dllFileName+ "rrExternal.dll"
        
        lib = ctypes.CDLL(dllFileName)

        # Your function signature: int example_func(int, float)
        lib.winApi_useAllCores.restype = ctypes.c_bool
        result= lib.winApi_useAllCores()
        if result:
            log_msg("Success!")
        else:
            log_msg_wrn("Failed!")

    except Exception as e:
        log_msg_wrn(e)
        import traceback
        log_msg_wrn(traceback.format_exc())  # log and quit




def enable_addon(addon_name):
    log_msg(f"*** Loading {addon_name.title()} addon... ***")
    flush_log()
    
    try:
        addon_utils.enable(addon_name)
    except ModuleNotFoundError:
        log_msg_wrn(f"Failed to enable addon: {addon_name}")
        flush_log()


# Parsing

class RRArgParser(object):
    """ArgParse replacement, parse the command line arguments and store them internally or as global vars for
    kso command. DON'T SET BLENDER VALUE INSIDE THIS CLASS: the scene might not be there yet."""

    def __init__(self, *args):
        self._debug = False

        self.PyModPath=""

        self.blend_file = ""

        self.seq_start = None
        self.seq_end = None
        self.seq_step = 1
        self.padding = 4

        self.kso_mode = False
        self.kso_port = 7774

        self.render_scene = ""
        self.render_layer = ""

        self.renderer = ""
        self.render_filepath = ""
        self.render_fileext = ""
        self.render_format = ""
        self.overwrite_existing = None
        self.bl_placeholder = None

        self.anti_alias_mult = 1.0

        self.res_percent = 100
        self.res_x = None
        self.res_y = None
        self.camera = None

        self.borderMinX = None
        self.borderMaxX = None
        self.borderMinY = None
        self.borderMaxY = None

        self.enable_gpu = False
        self.load_redshift = False
        self.enable_gpu_cpu = False
        self.enable_gpu_optix = False
        
        self.NoFramebyFrameLoop= False

        self.error = ""
        self.parse(args)

        self.success = self._is_valid()
    
    def is_tiled(self):
        if self.borderMinX == None:
            return False
        if self.borderMinY == None:
            return False
        if self.borderMaxX == None:
            return False
        if self.borderMaxY == None:
            return False
        
        return True

    def _is_valid(self):
        if self._debug:
            print("seq_start", self.seq_start)
            print("seq_end", self.seq_step)

        if not self.seq_start:
            self.error = "Missing argument: -rStart (Sequence Start)"
            return False
        if not self.seq_end:
            self.error = "Missing argument: -rEnd (Sequence End)"
            return False
        # TODO: frame start, end

        return True

    def parse(self, args):
        args = list(args)

        if not args:
            raise Exception("no arguments given: -rStart START_FRAME -rEnd END_FRAME -avMemUsage AV_MEM_USAGE -avRenderTime AV_RENDER_TIME")

        while args:
            arg = args.pop(0)

            # Trigger Flags: only one argument

            if arg == "-rDebug":
                self._debug = True
                continue

            if arg == "--":
                continue

            if arg == "-rKso":
                self.kso_mode = True
                continue

            if arg == "-rGPU":
                self.enable_gpu = True
                continue

            if arg == "-rGPU_CPU":
                self.enable_gpu_cpu = True
                continue

            if arg == "-rGPU_Optix":
                self.enable_gpu_optix = True
                continue

            if arg == "-rLoadRS":
                self.load_redshift = True
                continue

            if arg == "-NoFramebyFrameLoop":
                self.NoFramebyFrameLoop = True
                

            # Keyword/Value Flags

            try:
                value = args.pop(0)
            except IndexError:
                if self._debug:
                    print(f" ArgParser: Stopped parsing, last arg was {value}")
                break

            if value.startswith("-"):
                if self._debug:
                    log_msg_wrn(f"Ignored argument {arg}")

                arg = value

            if self._debug:
                print(f" ArgParser: arg: {arg}, value: {value}")

            if arg == "-S":
                self.render_scene = value
                global RENDER_SCENE
                RENDER_SCENE = self.render_scene

            if arg == "-rOverwrite":
                self.overwrite_existing = bool(value)
            
            if arg == "-rPlaceHolder":
                self.bl_placeholder = bool(value)

            if arg == "-rKSOport":
                self.kso_port = int(value)
            
            if arg == "-rAvFrTime":
                global AV_FRAME_TIME
                AV_FRAME_TIME = int(value)

            if arg == "-rOut":
                self.render_filepath = value
                global RENDER_PATH
                RENDER_PATH = self.render_filepath
                continue

            if arg == "-rStart":
                self.seq_start = int(value)
                continue

            if arg == "-rEnd":
                self.seq_end = int(value)
                continue

            if arg == "-rStep":
                self.seq_step = int(value)
                continue

            if arg == "-rPercent":
                self.res_percent = float(value)
                continue

            if arg == "-rX":
                self.res_x = int(value)
                continue

            if arg == "-rY":
                self.res_y = int(value)
                continue

            if arg == "-rMinX":
                self.borderMinX = float(value)
            
            if arg == "-rMaxX":
                self.borderMaxX = float(value)

            if arg == "-rMinY":
                self.borderMinY = float(value)
            
            if arg == "-rMaxY":
                self.borderMaxY = float(value)

            if arg == "-rRenderer":
                self.renderer = value
                global CURRENT_RENDERER
                CURRENT_RENDERER = value
                continue

            if arg == "-rCam":
                self.camera = value
                continue

            if arg == "-rAA":
                try:
                    factor = float(value)
                except ValueError:
                    factor = 1.0
                else:
                    self.anti_alias_mult = factor
                continue

            if arg == "-rBlend":
                self.blend_file = value
            
            if arg == "-rExt":
                self.render_fileext = value
            
            if arg == "-rFormat":
                self.render_format = value
            
            if arg == "-rPad":
                self.padding = int(value)
                global RENDER_PADDING
                RENDER_PADDING = self.padding
            
            if arg == "-rLayer":
                self.render_layer = value
                global RENDER_LAYER
                RENDER_LAYER = self.render_layer
            
            if arg == "-rFormat":
                self.format = value

            if arg == "-rPyModPath":
                self.PyModPath = value

# Errors

class RRArgParseException(Exception):
    pass

class RRFilepathMismatchException(Exception):
    pass


# Setup

FFMPEG_CODECS = {'.avi': 'AVI', '.flv': 'FLASH', '.mkv': 'MKV',
                 '.mpg': 'MPEG1','.dvd': 'MPEG2', '.mp4': 'MPEG4',
                 '.ogv': 'OGG', '.mov': 'QUICKTIME', '.webm': 'WEBM'}


OUT_FORMATS = OrderedDict(
    {'BMP': ['.bmp'], 'IRIS': ['.rgb'], 'PNG': ['.png'], 'JPEG': ['.jpg'], 'JPEG2000': ['.jp2', 'j2c'],
     'TARGA': ['.tga'], 'TARGA_RAW': ['.tga'], 'CINEON': ['.cin'], 'DPX': ['.dpx'],
     'OPEN_EXR': ['.exr'], 'OPEN_EXR_MULTILAYER': ['.exr'], 'HDR': ['.hdr'], 'TIFF': ['.tif'], 'WEBP': ['.webp'],
     'FFMPEG': list(FFMPEG_CODECS.keys()),
     'AVI_JPEG': ['.avi'], 'AVI_RAW': ['.avi']}
)


def open_blend_file(blend_file):
    bpy.ops.wm.open_mainfile(filepath=blend_file)

    if bpy.data.filepath != blend_file:
        raise RRFilepathMismatchException


def set_frame_range(start, end, step):
    scene = bpy.data.scenes[RENDER_SCENE]

    scene.frame_start = start
    scene.frame_end = end
    scene.frame_step = step


def render_frame_range(start, end, step, movie=False):

    scene = bpy.data.scenes[RENDER_SCENE]
    Path(os.path.dirname(scene.render.filepath)).mkdir(parents=True, exist_ok=True)
    
    global NO_FRAME_LOOP
    if not (movie or NO_FRAME_LOOP):
        log_msg(f"Rendering Frames: {start} - {end}")
        for fr in range(start, end + 1, step):
            if scene.render.use_overwrite:
                # if blender does not overwrite, creating placeholder files will prevent from rendering
                # not considering the case when blender creates its own placeholders via scene.render.use_placeholder.
                # They would overwrite RR placeholders before the render starts.

                kso_tcp.writeRenderPlaceholder_nr(RENDER_PATH, fr, RENDER_PADDING, scene.render.file_extension)

            log_msg(f"Rendering Frame #{fr} ...")
            flush_log()

            scene.frame_start = fr
            scene.frame_end = fr
            bpy.ops.render.render(animation=True, use_viewport=False, scene=RENDER_SCENE, layer=RENDER_LAYER)
    else:
        log_msg(f"Rendering Frames: {start} - {end}   (no 'frame by frame' loop)")
        set_frame_range(start, end, step)
        flush_log()
        bpy.ops.render.render(animation=True, use_viewport=False, scene=RENDER_SCENE, layer=RENDER_LAYER)


def set_output_path():
    scene = bpy.data.scenes[RENDER_SCENE]
    out_path = RENDER_PATH

    if RENDER_PADDING != 4:
        out_path += '#' * RENDER_PADDING

    scene.render.filepath = out_path


def set_output_format(file_ext, file_format='', scene=None):
    """Set blender output and pick correct format for given extension.
    Return chosen format, or given file_format if none is found"""
    scene = bpy.data.scenes[RENDER_SCENE]

    log_msg(f"Scene file format is set to {scene.render.image_settings.file_format}")

    if file_ext=="":
        return file_format

    viable_formats = []
    for k, v in OUT_FORMATS.items():
        if file_ext in v:
            viable_formats.append(k)
    
    out_format = ''
    
    if not viable_formats:
        log_msg_wrn(f"No format found for extention '{file_ext}', using parameter '{file_format}'" )
    elif len(viable_formats) == 1:
        out_format = viable_formats[0]

        if file_format:
            log_msg(f"Only one format for rendering {file_ext} files, ignoring format parameter {file_format}")
            if file_format != out_format:
                log_msg_wrn(f"format parameter {file_format} doesn't match {file_ext} format parameter")
        
        if out_format == scene.render.image_settings.file_format:
            log_msg(f"Output format was already set to: {out_format}")
        else:
            log_msg(f"Changing output format to match argument: {file_ext}")
            scene.render.image_settings.file_format = out_format
    elif file_format:
        try:
            extensions = OUT_FORMATS[file_format]
            if file_ext in extensions:
                out_format = file_format
            else:
                log_msg_wrn(f"File format and extension parameters do not match: {file_format}, {file_ext}")
        except:
            log_msg_wrn(f"File format parameter was not found: {file_format}")
    try:
        if out_format:
            scene.render.image_settings.file_format = out_format
        else:
            if scene.render.image_settings.file_format in viable_formats:
                log_msg(f"More formats for extension {file_ext}, using current format {scene.render.image_settings.file_format}")
            else:
                log_msg(f"Changing output format based on extension's default {viable_formats[0]}. Check '-rFormat' parameter (CustomFrameFormat variable in rrControl/rrSubmitter) to do otherwise.")
                
                log_msg(f"Available formats for {file_ext}:")
                for viable_format in viable_formats:
                    log_msg(f"\t{viable_format}")
                log_msg("")

                scene.render.image_settings.file_format = viable_formats[0]
    except:
        log_msg_wrn(f"File format parameter does not exist, unable to override file format: {out_format}")
            
    if out_format == 'FFMPEG':
        # Set container based on extension
        try:
            out_container = FFMPEG_CODECS[file_ext]
        except:
            log_msg_wrn(f"No {out_format} container found for extension {file_ext}, current container is '{scene.render.ffmpeg.format}'")
        else:
            if scene.render.ffmpeg.format != out_container:
                log_msg(f"Setting ffmpeg format to {out_container}")
                scene.render.ffmpeg.format = out_container
    elif out_format == 'JPEG2000':
        scene.render.image_settings.jpeg2k_codec = 'JP2' if file_ext.lower() == '.jp2' else 'J2K'
        log_msg(f"jpeg2k codec set to", scene.render.image_settings.jpeg2k_codec)

    out_extension = scene.render.file_extension
    if out_extension != file_ext:
        log_msg_wrn(f"Render file extension '{out_extension}' doesn't match job settings '{file_ext}'")
    
    return out_format if out_format else file_format


def set_single_file_frame_loop(out_format):
    if out_format == 'FFMPEG' or out_format.startswith('AVI'):
        # Video: single output
        global NO_FRAME_LOOP
        NO_FRAME_LOOP = True

# KSO connection

def rr_kso_start_server(host='localhost', port=7774):
    log_msg("rrKSO startup...")
    server = kso_tcp.rrKSOServer((host, port), kso_tcp.rrKSOTCPHandler)
    flush_log()

    log_msg("rrKSO server started")
    server.print_port()
    flush_log()

    kso_tcp.rrKSONextCommand = ""

    while server.continueLoop:
        try:
            log_msg_dbg("rrKSO waiting for new command...")
            server.handle_request()
            time.sleep(1) # handle_request() seems to return before handle() completed execution
        except Exception as e:
            log_msg_err(e)
            server.continueLoop= False
            import traceback
            log_msg_err(traceback.format_exc())  # log and quit

        log_msg("rrKSO NextCommand ".ljust(112, "_"))
        log_msg(f"rrKSO NextCommand '{kso_tcp.rrKSONextCommand}'")
        log_msg("rrKSO NextCommand ".ljust(112, "_"))
        flush_log()

        if kso_tcp.rrKSONextCommand:
            if kso_tcp.rrKSONextCommand == "ksoQuit()" or kso_tcp.rrKSONextCommand == "ksoQuit()\n":
                server.continueLoop = False
                kso_tcp.rrKSONextCommand = ""
            else:
                exec(kso_tcp.rrKSONextCommand)
                kso_tcp.rrKSONextCommand = ""
    log_msg("Closing TCP")    
    server.closeTCP()
    log_msg("rrKSO closed")
    

def kso_render_frames(start, end, step):
    render_frame_range(start, end, step)
    
    log_msg(f"rrKSO Frame(s) done #{end} ")
    log_msg(" " * 60)
    log_msg(" " * 60)
    log_msg(" " * 60)
    flush_log()


def set_average_frame_time(frame_time):
    global AV_FRAME_TIME
    AV_FRAME_TIME = frame_time

    global NO_FRAME_LOOP
    if not NO_FRAME_LOOP:
        if AV_FRAME_TIME == 0:
            NO_FRAME_LOOP = CURRENT_RENDERER in GPU_RENDERERS
            return

        if AV_FRAME_TIME < 60:
            NO_FRAME_LOOP = True
            return

        if AV_FRAME_TIME < 140:
            NO_FRAME_LOOP = CURRENT_RENDERER in GPU_RENDERERS


def multiply_render_samples(renderer, factor):
    if factor == 1.0:
        return

    scene = bpy.data.scenes[RENDER_SCENE]

    if renderer in ("Eevee", "Eevee_Next"):
        previous = scene.eevee.taa_render_samples
        scene.eevee.taa_render_samples = round(factor * scene.eevee.taa_render_samples)
        log_msg(f"{renderer} samples changed from {previous} to {scene.eevee.taa_render_samples}")
    elif renderer == "Cycles":
        previous = scene.cycles.samples
        scene.cycles.samples = round(factor * scene.cycles.samples)
        log_msg(f"{renderer} samples changed from {previous} to {scene.cycles.samples}")
    else:
        log_msg_wrn(f"Samples override not supported for {renderer}")


def ensure_scene_and_layer():
    """Use current scene in case no scene was passed"""
    global RENDER_SCENE

    if RENDER_SCENE and RENDER_SCENE not in bpy.data.scenes:
        log_msg_wrn(f"The scene {RENDER_SCENE} was not found in this file, will default to loaded scene")
        RENDER_SCENE = ""

    if not RENDER_SCENE:
        RENDER_SCENE = bpy.context.scene.name
        log_msg_wrn(f"No SceneState argument given, using '{RENDER_SCENE}'")
    
    global RENDER_LAYER

    if RENDER_LAYER and (RENDER_LAYER not in bpy.data.scenes[RENDER_SCENE].view_layers):
        log_msg_wrn(f"The layer {RENDER_LAYER} was not found in '{RENDER_SCENE}', will default to loaded layer")
        RENDER_LAYER = ""

    if not RENDER_LAYER:
        RENDER_LAYER = bpy.context.view_layer.name
        log_msg_wrn(f"No Layer argument given, using scene settings")
    else:
        for layer in bpy.data.scenes[RENDER_SCENE].view_layers:
            if (layer.name != RENDER_LAYER):
                log_msg(f"Disabling layer {layer.name}")
                layer.use= False
            else:
                log_msg(f"Enabling layer {layer.name}")
                layer.use= True
    


def adjust_resolution(new_res_x, new_res_y):
    render_settings = bpy.data.scenes[RENDER_SCENE].render
    if new_res_x:
        res_x = render_settings.resolution_x
        if res_x == new_res_x:
            log_msg(f"Render width already set to {res_x}, no change necessary")
        else:
            render_settings.resolution_x = new_res_x
    if new_res_y:
        res_y = render_settings.resolution_y
        if res_y == new_res_y:
            log_msg(f"Render height already set to {res_y}, no change necessary")
        else:
            render_settings.resolution_y = new_res_y


def set_render_region(min_x, max_x, min_y, max_y):
    render_settings = bpy.data.scenes[RENDER_SCENE].render

    render_settings.border_min_x = min_x
    render_settings.border_max_x = max_x
    render_settings.border_min_y = min_y
    render_settings.border_max_y = max_y

    render_settings.use_border = True

####

if __name__ == "__main__":
    log_msg(" Royal Render %rrVersion% blender render plugin ".center(100, "_"))
    log_msg(" Blender started ".center(100, "_"))
    log_msg(" Python version: "+str(sys.version))

    args = RRArgParser(*sys.argv)
    
    if (len(args.PyModPath)>0):
        import sys
        log_msg("Append python search path with '" +args.PyModPath+"'" )
        sys.path.append(args.PyModPath)    
    import kso_tcp
    useAllCores()
    
    log_msg(" Renderer set: "+ args.renderer)
    
    if args.load_redshift:
        enable_addon("redshift")
    if args.renderer.lower() == "luxcore":
        enable_addon("BlendLuxCore")

    log_msg(" About to open blend file ".center(100, "_"))
    log_msg(f"Open scene file: {args.blend_file}")
    flush_log()

    open_blend_file(args.blend_file)
    log_msg(" blend file opened ".center(100, "_"))
    flush_log()

    ensure_scene_and_layer()

    if args.enable_gpu:
        enable_gpu_devices(use_CPU=args.enable_gpu_cpu, use_optix= args.enable_gpu_optix )

        if args.renderer == "Cycles":
            settings = bpy.data.scenes[RENDER_SCENE].cycles
            if settings.device != 'GPU':
                log_msg(f"Switching Cycles render device from '{settings.device}' to 'GPU'")
            settings.device = 'GPU'
            
        if args.renderer.lower() == "luxcore":          
            set_luxcore_CUDA()
            
    if args.NoFramebyFrameLoop != None:
        NO_FRAME_LOOP= True

    adjust_resolution(args.res_x, args.res_y)
    if args.is_tiled():
        set_render_region(args.borderMinX, args.borderMaxX, args.borderMinY, args.borderMaxY)

    multiply_render_samples(args.renderer, args.anti_alias_mult)
    
    set_frame_range(args.seq_start, args.seq_end, args.seq_step)
    set_output_path()
    
    out_format = set_output_format(args.render_fileext, args.render_format)
    set_single_file_frame_loop(out_format)

    if args.overwrite_existing != None:
        bpy.data.scenes[RENDER_SCENE].render.use_overwrite = args.overwrite_existing
    
    if args.bl_placeholder != None:
        bpy.data.scenes[RENDER_SCENE].render.use_placeholder = args.bl_placeholder

    # ensure output dir
    Path(os.path.dirname(RENDER_PATH)).mkdir(parents=True, exist_ok=True)
    flush_log()
    if not wasError_Close:
        if args.kso_mode:
            try:
                rr_kso_start_server(port=args.kso_port)
            except Exception as e:
                log_msg_err(str(e))
            
            log_msg("KSO Session Ended, Exiting")
        else:
            try:
                render_frame_range(args.seq_start, args.seq_end, args.seq_step)
            except Exception as e:
                log_msg_err(str(e))
            
            log_msg("Task Frames Rendered, Exiting")
