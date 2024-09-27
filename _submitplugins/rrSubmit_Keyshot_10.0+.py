# -*- coding: utf-8 -*-
# AUTHOR Royal Render
# VERSION %rrVersion%
# Submit Keyshot Jobs to Royal Render


import sys
import os

import tempfile
import subprocess
import mmap

from datetime import datetime
import shutil


class RR_Submission_Error(Exception):
    def __init__(self, message):
        # Call the base class constructor with the parameters it needs
        super().__init__(message)


def get_rr_Root():
    if 'RR_ROOT' in os.environ: 
        return os.environ['RR_ROOT']

    if sys.platform.lower().startswith('win'):
        HCPath = "%RRLocationWin%"
    elif sys.platform.lower() == "darwin":
        HCPath = "%RRLocationMac%"
    else:
        HCPath = "%RRLocationLx%"
    if not HCPath.startswith("%"):
        return HCPath

    raise RR_Submission_Error("Royal Render Directory not found")


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
        # self.sceneDatabaseDir = ""
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
        # self.splitImageFileInto_DirFileExt = True


class rrJobsToXml():
    def __init__(self, jobs):
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
        self.temp_file.write("AllowLocalSceneCopy=1~0")
        self.temp_file.write("</SubmitterParameter>")
    
    def write_jobs(self, jobs: list[rrJob]):
        for job in jobs:
            self.temp_file.write("<Job>\n")

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
            self.writeNodeStr("Imagefilename", job.imageFileName)
            self.writeNodeStr("ImageExtension", job.imageExtension)
            self.writeNodeStr("ImagePreNumberLetter", job.ImagePreNumberLetter)
            # self.writeNodeInt("ImageFramePadding", renderPadding)

            self.temp_file.write("</Job>\n")


    def write_tail(self):
        self.temp_file.write("</RR_Job_File>\n")


def get_OS_as_String():
    if sys.platform.lower() in ("win32", "win64"):
        return "win"
    elif sys.platform.lower() == "darwin":
        return "osx"
    else:
        return "lx"


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


def queue_file_to_dicts(queue_file):
    with open(queue_file, "r") as f:
        line = f.readline()
        while(line):
            line = line.strip()
            if line == "</queue>":
                break

            if line.startswith("<model"):
                entries = line[7:].split('" ')
                yield dict((k, v.strip('"<>')) for k, v in[entry.split("=", 1) for entry in entries])

            line = f.readline()


def copy_to_net_path(scene_file, output_dir):
    scene_dir, _ = os.path.split(output_dir)
    scene_dir = os.path.join(scene_dir, "Scenes")
    os.makedirs(scene_dir, exist_ok=True)

    scene_name, scene_ext = os.path.splitext(scene_file)
    scene_geo = scene_file + ".geom"

    if os.path.isfile(scene_geo):
        shutil.copyfile(scene_geo, os.path.join(scene_dir, os.path.split(scene_geo)[-1]))

    now_time = datetime.now()
    _, scene_name = os.path.split(scene_name)
    cp_name = f"{scene_name}_{now_time.day:02d}{now_time.hour:02d}{now_time.minute:02d}{now_time.second:02d}.bip"
    
    sc_copy = os.path.join(scene_dir, cp_name)
    shutil.copyfile(scene_file, sc_copy)

    return sc_copy


def parse_queue_file(queue_file):        
    version = lux.getSystemInfo()['process']['version'].split(".", 3)
    version_str = ".".join(version[:2])  # e.g 13.1
    parse_func = bin_search_render_start if int(version[0]) > 11 else search_render_start
    
    sceneOS = get_OS_as_String()
    jobs = []
    for ks_job in queue_file_to_dicts(queue_file):
        save_frames = True if ks_job.get('save_frames') == "true" else False
        create_video = True if ks_job.get('create_video') == "true" else False

        if save_frames:
            single_output = False
        elif create_video:
            single_output = True
        else:
            continue

        new_job = rrJob(version_str, sceneOS)
        new_job.ImageSingleOutputFile = single_output

        new_job.imageDir, display_name = os.path.split(ks_job['output'])
        new_job.sceneName = copy_to_net_path(ks_job['file'], new_job.imageDir)
        new_job.isActive = True if ks_job['enabled'] == "true" else False

        new_job.imageWidth = ks_job['resolution_x']
        new_job.imageHeight = ks_job['resolution_y']
        
        display_name, new_job.imageExtension = os.path.splitext(display_name)
        new_job.imageFileName = ks_job.get('display_name', display_name)
        
        new_job.seqStart = parse_func(new_job.sceneName)
        new_job.seqEnd = new_job.seqStart + int(ks_job['total_frames']) - 1

        jobs.append(new_job)
    
    return jobs


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
            submitCMDs = (f'{rr_root}\\win__{submitter}.bat', tmpfile_name)
        else:
            submitCMDs = (f'{rr_root}\\bin\\win64\{submitter}.exe', tmpfile_name)
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


def main():
    scenes_folder = lux.getKeyShotFolder(lux.FOLDER_SCENES)
    queue_file = os.path.join(scenes_folder, "q.xml")
    
    if not os.path.isfile(queue_file):
        raise RR_Submission_Error(f"Queue file not found: {queue_file}")

    rr_jobs = parse_queue_file(queue_file)

    if not rr_jobs:
        raise RR_Submission_Error("No jobs found")
    
    jobs_xml = rrJobsToXml(rr_jobs)
    launch_rr_submitter(jobs_xml.file_name, show_ui=True)


if __name__ == "__main__":
    main()
