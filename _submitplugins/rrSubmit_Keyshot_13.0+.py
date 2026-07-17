# -*- coding: cp1252 -*-
# AUTHOR Royal Render
# VERSION %rrVersion%
# Submit render Queue to Farm

######################################################################
#
# Royal Render submission script for KeyShot
# Author:  Paolo Acampora, Royal Render
# Last change: %rrVersion%
# Copyright (c)  Holger Schoenberger - Binary Alchemy
#
# #win:     rrInstall_Copy: <PUBLIC>\Documents\Keyshot*\Scripts\
#
# #mac:     rrInstall_Copy: /Library/Application Support/KeyShot*/Scripts
#
#########################################################################


import os
import sys
import subprocess
import logging
import mmap
import shutil
import tempfile
import signal
import subprocess
from datetime import datetime

import time


def get_OS_as_String():
    if sys.platform.lower() in ("win32", "win64"):
        return "win"
    elif sys.platform.lower() == "darwin":
        return "osx"
    else:
        return "lx"


def queue_file_to_dicts(queue_file):
    with open(queue_file, "r") as f:
        line = f.readline()
        job_dict = None
        while(line):
            line = line.strip()
            if line == "</queue>":
                break
            
            if line.startswith("<model"):
                entries = line[7:].split('" ')
                job_dict = dict((k, v.strip('"<>')) for k, v in[entry.split("=", 1) for entry in entries])
            elif line.startswith("<texture") and job_dict:
                _, tex = line.rsplit("<", 1)[0].split(">", 1)
                try:
                    job_dict["textures"].append(tex)
                except KeyError:
                    job_dict["textures"] = [tex]

            if line.startswith("</model") and job_dict:
                yield job_dict
                
                job_dict = None

            line = f.readline()


def get_lock_path():
    ks_dir = os.path.join(lux.getKeyShotFolder(lux.FOLDER_RESOURCE_ROOT), "__rrKSwatch__")
    os.makedirs(ks_dir, exist_ok=True)
    return os.path.join(ks_dir, "ks_qwatch.lock")


class rrJob:
    """Contains job properties and xml export methods """
    def __init__(self, version="", scene_os=""):
        self.clear()
        self.version = version
        self.sceneOS = scene_os
    
    def clear(self):
        self.version = ""
        self.software = "KeyShot"
        # self.renderer = ""
        # self.RequiredLicenses = ""
        self.sceneName = ""
        self.sceneDatabaseDir = ""
        self.seqStart = 0
        self.seqEnd = 1
        self.seqStep = 1
        # self.seqFileOffset = 0
        # self.seqFrameSet = ""
        self.imageWidth = 99
        self.imageHeight = 99
        self.imageDir = ""
        self.imageFileName = ""
        # self.imageFramePadding = 4
        self.imageExtension = ""
        self.ImagePreNumberLetter = "."
        self.ImageSingleOutputFile = False
        self.imageStereoR = ""
        self.imageStereoL = ""
        self.sceneOS = ""
        self.camera = ""
        self.layer = ""
        self.channel = ""
        self.maxChannels = 0
        self.channelFileName = []
        self.channelExtension = []
        self.isActive = False
        self.sendAppBit = ""
        # self.preID = ""
        # self.waitForPreID  = ""
        self.CustomProjectName  = ""
        self.CustomSequencePath = ""
        self.CustomPresetPath = ""
        self.LocalTexturesFile  = ""
        self.userName = ""
        self.shotName = ""
        self.seqName = ""
        self.versionName = ""
        self.gpuRequired = False
        # self.splitImageFileInto_DirFileExt = True


def bin_search_render_start(scene_file):
    with open(scene_file, "r+b") as f:
        mm = mmap.mmap(f.fileno(), 0)
        position = mm.find(b'animation_first_frame')
        if position < 1:
            return - 1
        
        f.seek(position - 4, 0)
        data = f.read(4)

    return int.from_bytes(data, 'little') + 1


def search_render_start(scene_file, max_lines=1000):
    res = -1
    with open(scene_file, errors="ignore") as f:
        for i, line in enumerate(f):
            if i > max_lines:
                break
            if line.startswith("binary"):
                continue

            line = line.strip(", ")
            if line.startswith('"animation_first_frame"'):
                 _, frame_num = line.strip(' \t\n,').split(' ', 1)
                 res = int(frame_num) + 1
                 break

    return res


class QueueParser:
    def __init__(self, version_str, project_path, logger: logging.Logger, overwrite=False):
        self.version_str = version_str
        self.version = version_str.split(".")

        self.platform = get_OS_as_String()
        self.project_path = project_path
        self._parse_bip_func = bin_search_render_start if int(self.version[0]) > 11 else search_render_start
        self._logger = logger
        self._overwrite_shared = overwrite
        self.processed_scenes = []

    def copy_queued_to_netpath(self, local_file, type_dir="Scenes", add_timestamp=True, overwrite=False):
        scene_dir = os.path.normpath(self.project_path)
        current_dir = os.path.normpath(os.path.dirname(os.path.dirname(local_file)))

        if current_dir == scene_dir:
            if local_file.endswith(".bip"):
                return local_file

        if not scene_dir.endswith(type_dir):
            scene_dir = os.path.join(scene_dir, type_dir)
            os.makedirs(scene_dir, exist_ok=True)

        scene_name, scene_ext = os.path.splitext(local_file)
        scene_geo = local_file + ".geom"

        if os.path.isfile(scene_geo):
            shutil.copyfile(scene_geo, os.path.join(scene_dir, os.path.split(scene_geo)[-1]))

        scene_ext = ".bip" if scene_ext == ".ext" else scene_ext
        if add_timestamp:
            now_time = datetime.now()
            scene_name = os.path.split(scene_name)[-1]
            cp_name = f"{scene_name}_{now_time.day:02d}{now_time.hour:02d}{now_time.minute:02d}{now_time.second:02d}{scene_ext}"
        else:
            scene_name = os.path.split(scene_name)[-1]
            cp_name = f"{scene_name}{scene_ext}"
        
        sc_copy = os.path.join(scene_dir, cp_name)
        if os.path.isfile(sc_copy) and not overwrite:
            return sc_copy

        shutil.copyfile(local_file, sc_copy)

        return sc_copy

    def copy_to_net_project(self, local_file, fallback_dir):
        local_file = os.path.normpath(local_file)
        res_root = os.path.normpath(lux.getKeyShotFolder(lux.FOLDER_RESOURCE_ROOT))

        if res_root in local_file:
            new_path = os.path.join(self.project_path, local_file[len(res_root):].lstrip('/\\'))
        else:
            new_path = os.path.join(self.project_path, fallback_dir, os.path.split(local_file)[-1].lstrip('/\\'))

        os.makedirs(os.path.dirname(new_path), exist_ok=True)
        if os.path.isfile(new_path) and not self._overwrite_shared:
            return new_path

        return shutil.copyfile(local_file, new_path)

    def replace_resource_root(self, render_dir: str):
        res_root = os.path.normpath(lux.getKeyShotFolder(lux.FOLDER_RESOURCE_ROOT))
        render_dir = os.path.normpath(render_dir)
        return os.path.normpath(render_dir.replace(res_root, os.path.normpath(self.project_path)))

    def parse_for_jobs(self, queue_file, no_submission=False, submit_disabled=False):
        jobs = []
        for ks_job in queue_file_to_dicts(queue_file):
            if ks_job['enabled'] == "false" and not submit_disabled:
                continue

            save_frames = True if ks_job.get('save_frames') == "true" else False
            create_video = True if ks_job.get('create_video') == "true" else False

            if save_frames:
                single_output = False
            elif create_video:
                single_output = True
            elif ks_job['type'] == 'image':
                single_output = True
            else:
                self._logger.warning(f"Skipping {os.path.split(ks_job['file'])[-1]}: please enable Video or Frames output" )
                continue

            ks_queue_scene = ks_job['file']
            if ks_queue_scene in self.processed_scenes:
                self._logger.debug(f"Skipping {ks_queue_scene}")
                continue

            if not os.path.isfile(ks_queue_scene):
                self._logger.warning(f"Scene not found, probably deleted {ks_queue_scene}")
                continue

            self.processed_scenes.append(ks_queue_scene)

            if no_submission:
                continue

            new_job = rrJob(self.version_str, self.platform)
            new_job.ImageSingleOutputFile = single_output

            render_dir, display_name = os.path.split(ks_job['output'])
            new_job.imageDir = self.replace_resource_root(render_dir)
            new_job.sceneDatabaseDir = self.project_path

            new_job.sceneName = self.copy_queued_to_netpath(ks_queue_scene)
            new_job.isActive = True if ks_job['enabled'] == "true" else False

            new_job.imageWidth = ks_job['resolution_x']
            new_job.imageHeight = ks_job['resolution_y']
            
            display_name, new_job.imageExtension = os.path.splitext(display_name)
            new_job.imageFileName = ks_job.get('display_name', display_name)
            
            new_job.seqStart = self._parse_bip_func(new_job.sceneName)
            new_job.seqEnd = new_job.seqStart + int(ks_job['total_frames']) - 1
            new_job.gpuRequired = True if ks_job['uses_gpu'] == 'true' else False

            for texture in ks_job['textures']:
                if not os.path.isfile(texture):
                    self._logger.warning(f"texture mentioned in queue but not found: {texture}")
                else:
                    copied = self.copy_to_net_project(texture, fallback_dir="Textures")
                    self._logger.info(f"Copied '{texture}' to '{copied}'")

            self._logger.info(f"Found new job: {display_name}")
            jobs.append(new_job)

        return jobs


class rrJobsToXml():
    def __init__(self, jobs: list[rrJob]):
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', prefix="rrSubmitKeyshotQue_", suffix=".xml", delete=False)
        
        self.write_head()
        self.write_jobs(jobs)
        self.write_tail()

        self.temp_file.close()
    
    @property
    def file_name(self):
        return self.temp_file.name
    
    def writeNodeStr(self, name, text):
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        text = text.replace("\"", "&quot;")
        text = text.replace("'", "&apos;")
        self.temp_file.write("    <{0}>  {1}   </{0}>\n".format(name, text))

    def writeNodeInt(self, name, number):
        self.temp_file.write("    <{0}>  {1}   </{0}>\n".format(name, number))

    def writeNodeBool(self, name, value):
        self.temp_file.write("    <{0}>   {1}   </{0}>\n".format(name, int(value)))

    def write_head(self):
        self.temp_file.write("<RR_Job_File syntax_version=\"6.0\">\n")
        self.temp_file.write("<DeleteXML>1</DeleteXML>\n")
        
        self.temp_file.write("<SubmitterParameter>")
        self.temp_file.write("AllowLocalSceneCopy=0~0")
        self.temp_file.write("</SubmitterParameter>")
    
    def write_jobs(self, jobs: list[rrJob]):
        for job in jobs:
            self.temp_file.write("<Job>\n")
            if job.gpuRequired:
                self.temp_file.write('<SubmitterParameter> "GPUrequired=0~1" </SubmitterParameter>')

            self.writeNodeStr("rrSubmitterPluginVersion", "%rrVersion%")
            self.writeNodeStr("Software", job.software)
            self.writeNodeStr("Version",  job.version)
            self.writeNodeBool("IsActive", job.isActive)
            self.writeNodeStr("Scenename", job.sceneName)
            self.writeNodeBool("ImageSingleOutputFile", job.ImageSingleOutputFile)
            self.writeNodeInt("SeqStart", job.seqStart)
            self.writeNodeInt("SeqEnd", job.seqEnd)
            self.writeNodeInt("SeqStep", job.seqStep)
            self.writeNodeStr("ImageDir", job.imageDir)
            self.writeNodeStr("SceneDatabaseDir", job.sceneDatabaseDir)
            self.writeNodeStr("Imagefilename", job.imageFileName)
            self.writeNodeStr("ImageExtension", job.imageExtension)
            self.writeNodeStr("ImagePreNumberLetter", job.ImagePreNumberLetter)
            # self.writeNodeInt("ImageFramePadding", renderPadding)

            self.temp_file.write("</Job>\n")


    def write_tail(self):
        self.temp_file.write("</RR_Job_File>\n")


class RR_Submission_Error(Exception):
    def __init__(self, message):
        super().__init__(message)


class RR_WatchLock_Error(Exception):
    def __init__(self, message):
        super().__init__(message)


def get_rr_Root():
    try:
        return os.environ['RR_ROOT']
    except KeyError:
        if sys.platform.lower().startswith('win'):
            HCPath = "%RRLocationWin%"
        elif sys.platform.lower() == "darwin":
            HCPath = "%RRLocationMac%"
        else:
            HCPath = "%RRLocationLx%"
        if not HCPath.startswith("%"):
            return HCPath

    raise RR_Submission_Error("Royal Render Directory not found")


def launch_rr_submitter(tmpfile_name, show_ui=True):
    rr_root = get_rr_Root()

    if not os.path.isdir(rr_root):
        raise RR_Submission_Error(f"RR directory is invalid: {rr_root}")

    if show_ui:
        submitter = "rrSubmitter"
    else:
        submitter = "rrSubmitterconsole"

    if sys.platform.lower().startswith("win"):
        if show_ui:
            submitCMDs = (os.path.join(rr_root, f"win__{submitter}.bat"), tmpfile_name)
        else:
            submitCMDs = (os.path.join(rr_root, 'bin', 'win64', f"{submitter}.exe"), tmpfile_name)
    elif sys.platform.lower() == "darwin":
        submitCMDs = (f'{rr_root}/bin/mac64/{submitter}.app/Contents/MacOS/{submitter}', tmpfile_name)
    else:
        if show_ui:
            submitCMDs = (f'{rr_root}/lx__{submitter}.sh', tmpfile_name)
        else:
            submitCMDs = (f'{rr_root}/bin/lx64/{submitter}', tmpfile_name)

    try:
        if not os.path.isfile(submitCMDs[0]):
            raise FileNotFoundError
        subprocess.Popen(submitCMDs, close_fds=True)
    except FileNotFoundError:
        raise RR_Submission_Error("rrSubmitter not found\n({0})".format(submitCMDs[0]))
    except subprocess.CalledProcessError:
        raise RR_Submission_Error("Error while executing rrSubmitter")
    
    return True


class Watcher:
    def __init__(self, watch_file: str, logger: logging.Logger, parser: QueueParser, show_submitter=False):

        if not os.path.isfile(watch_file):
            raise FileNotFoundError

        self._interval_secs = 3
        self._is_running = False

        self._filename = watch_file
        self._last_stamp = os.stat(self._filename).st_mtime
        self._parser = parser
        self._show_submitter = show_submitter

        self.logger = logger

    def start_watching(self):
        # TODO: check existing jobs and ask what to do: send all, save backup etc...
        self.logger.info(f'Start Watching "{self._filename}"')

        self._parser.parse_for_jobs(self._filename, no_submission=True)
        if self._parser.processed_scenes:
            newtab = "\n\t"
            self.logger.info(f'Jobs queued previously are ignored:\n\t{newtab.join(self._parser.processed_scenes)}')

        self._is_running = True

        self.watch()

    def on_queue_file_changed(self):
        self.logger.debug("Queue file changed")
        
        rr_jobs = self._parser.parse_for_jobs(self._filename)
        if not rr_jobs:
            self.logger.info("No new jobs found in queue")
            return
    
        num_jobs = len(rr_jobs)
        self.logger.info(f"Submitting {num_jobs} job{'s' if num_jobs > 0 else ''}")
        jobs_xml = rrJobsToXml(rr_jobs)
        launch_rr_submitter(jobs_xml.file_name, show_ui=self._show_submitter)

    def look(self):
        """Look for changes in queue file"""
        stamp = os.stat(self._filename).st_mtime
        if stamp == self._last_stamp:
            return
        
        self._last_stamp = stamp
        self.on_queue_file_changed()
     
    def watch(self):
        while self._is_running: 
            try: 
                # Look for changes
                time.sleep(self._interval_secs) 
                self.look() 
            except KeyboardInterrupt: 
                print('Exiting') 
                break
            except Exception as e:
                print(f"Unhandled error: {e}")
                break
        
        clean_up()


def create_logger(level=logging.INFO, name="KS_QueueWatch"):
    logger = logging.Logger(name)
    logger.setLevel(level)
    s_handler = logging.StreamHandler(sys.stdout)


    # TODO: file handler
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    s_handler.setFormatter(formatter)
    logger.addHandler(s_handler)

    return logger


def clean_up():
    print("Removing lock file")
    time.sleep(3)
    try:
        os.remove(get_lock_path())
    except FileNotFoundError:
        print("Lock file not present")
    else:
        time.sleep(1)


def get_resources_default_path():
    if sys.platform.startswith("win"):
        return os.path.join(os.environ['PUBLIC'], 'Documents', 'KeyShot')
    
    if sys.platform == "mac":
        return "/Library/Application Support/KeyShot"
    
    raise Exception(f"platform {sys.platform} not supported")


def kill_watcher(logger, lock_file):
    lock_pid = -1
    with open(lock_file, 'r') as f:
        lock_pid = f.readline()

    logger.info(f"Found lock file: {lock_file}, pid {lock_pid}")

    try:
        os.kill(int(lock_pid), signal.SIGINT)
    except OSError:
        logger.warning(f"Failed to kill process: {lock_pid}")
    except SystemError as e:
        logger.warning(f"Error while killing process {lock_pid}: {e}")


def main():
    try:
        import lux
    except ImportError:
        ks_gui = False
        version = "13.0"  # TODO: use regkey
    else:
        ks_gui = not lux.isHeadless()
        version = lux.getSystemInfo()['process']['version'].split(".", 3)
    
    lock_file = get_lock_path()

    if ks_gui:
        logger = create_logger(name="rrSubmit", level=logging.DEBUG)
        values = [
            ("rr_net_prj_path", lux.DIALOG_FOLDER, "Shared Project Path:", None),
            ("rr_overwrite", lux.DIALOG_CHECK, "Overwrite shared assets", False),
            ]

        if os.path.isfile(lock_file):
            values.append((lux.DIALOG_LABEL, "Queue Watcher was launched and not closed"))
            values.append(("rr_watch_action", lux.DIALOG_ITEM, "Mode", 'Check', ["Check", "Stop"]))
        else:
            values.append(("rr_sub_mode", lux.DIALOG_ITEM, "Mode", 'Submit', ["Submit (UI)", "Submit (No UI)", "Watch"]))
        
        desc = "Submit to Royal Render"
        opts = lux.getInputDialog(title = "RR Submission",
                                  desc = desc,
                                  values = values,
                                  id = "submit_queue.py.rr12")
        
        if not opts:
            logger.info("User cancelled")
            return
        if not opts['rr_net_prj_path']:
            lux.getMessageBox("Please, specify a network path")
            raise RR_Submission_Error("No project path selected")
        if not opts['rr_net_prj_path']:
            lux.getMessageBox(f"Cannot find network path {opts['rr_net_prj_path']}, please make sure it exists")
            raise RR_Submission_Error(f"Can't find network path: {opts['rr_net_prj_path']}")
        
        scenes_folder = lux.getKeyShotFolder(lux.FOLDER_SCENES)
        queue_file = os.path.join(scenes_folder, "q.xml")
    
        if not os.path.isfile(queue_file):
            raise RR_Submission_Error(f"Queue file not found: {queue_file}")
        
        version_str = ".".join(version[:2])  # e.g "13.1"
        
        try:
            action = opts['rr_sub_mode'][1]
        except KeyError:
            try:
                action = opts['rr_watch_action'][1]
            except KeyError:
                raise Exception("No submit Action set")

        if action == "Watch":
            # watch queue file in a separate process
            ks_dir, ks_exe = os.path.split(sys.executable)
            name, ext = os.path.splitext(ks_exe)
            cmd_exe = os.path.join(ks_dir, f"{name}_headless{ext}")

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

            cmds = [cmd_exe, "-script",
                    os.path.realpath(__file__), "-w",
                    "-q", queue_file,
                    "-p", opts['rr_net_prj_path'],
                    "-v", version_str]
            
            if opts['rr_overwrite']:
                cmds.append("-o")

            subprocess.Popen(cmds, close_fds=True, env=rr_env)
        elif action == "Stop":
            kill_watcher(logger, get_lock_path())
            clean_up()
        else:
            qparser = QueueParser(version_str, opts['rr_net_prj_path'], logger, overwrite=opts['rr_overwrite'])
            Watcher(queue_file, logger, qparser, show_submitter=action == "Submit (UI)").on_queue_file_changed()
    else:
        # running from command line
        import argparse
        import atexit

        atexit.register(clean_up)
        parser = argparse.ArgumentParser()

        parser.add_argument("-k", "--kill", help="Kill watcher if found", action=argparse.BooleanOptionalAction, default=False)
        parser.add_argument("-w", "--watch", help="Start watching", action=argparse.BooleanOptionalAction, default=False)
        parser.add_argument("-p", "--project_folder", help="Shared folder for Keyshot's render project")
        parser.add_argument("-o", "--overwrite", help="Overwrite assets on shared folder (e.g. Textures)", default=False)
        
        parser.add_argument("-q", "--queue_file", help="file containing queue jobs", default="auto")
        parser.add_argument("-v", "--version", help="Keyshot version, e.g. 13.1. 'auto' for getting it from the lux module", default="auto")
        parser.add_argument("--loglevel", help="Level for log messages", choices=["debug", "info", "warning", "error", "critical"], default="info")
        
        args = parser.parse_args()

        logger = create_logger(level=getattr(logging, args.loglevel.upper()))

        if args.kill:
            if os.path.isfile(lock_file):
                kill_watcher(logger, lock_file)
            else:
                logger.warning("Lock file not found, nothing to kill")
        else:
            if os.path.isfile(lock_file):
                raise RR_WatchLock_Error(f"Lock File found. If RR Queue Watch is not running, please delete: {lock_file}")

            version = args.version
            if version == "auto":
                try:
                    import lux
                except ModuleNotFoundError:
                    # TODO: registry key
                    raise Exception("Cannot get version from lux, please specify a version string, e.g. 13.1")
                else:
                    version = lux.getSystemInfo()['process']['version'].split(".", 3)
                    version = ".".join(version[:2])  # e.g 13.1

            queue_file = args.queue_file
            if queue_file == 'auto':
                try:
                    import lux
                except ModuleNotFoundError:
                    logger.warning("Cannot get resource path from lux, looking into default paths")
                    queue_file = os.path.join(get_resources_default_path(), 'Scenes', "q.xml")
                    if not os.path.isfile(queue_file):
                        raise Exception(f"queue file not found {queue_file}")
                else:
                    queue_file = os.path.join(lux.getKeyShotFolder(lux.FOLDER_SCENES), "q.xml")
            
            logger.debug(f"Write lock file: {lock_file}")
            with open(lock_file, "w") as f:
                f.write(str(os.getpid()))

            qparser = QueueParser(version, args.project_folder, logger)
            watcher = Watcher(args.queue_file, logger, qparser)

            if args.watch:
                logger.info(f"Jobs added to KeyShot queue will be rendered to {args.project_folder}")
                logger.handlers[0].flush()
                watcher.start_watching()
            else:
                watcher.on_queue_file_changed()


if __name__ == "__main__":
    main()
