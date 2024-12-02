import lux

from enum import Enum
import datetime
import os
import sys

import logging


# LOGGING

def create_logger(level=logging.INFO, name="RR"):
    logger = logging.Logger(name)
    logger.setLevel(level)
    s_handler = logging.StreamHandler(sys.stdout)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    s_handler.setFormatter(formatter)
    logger.addHandler(s_handler)

    return logger


LOGGER = create_logger()


def log_debug(msg):
    LOGGER.debug(msg)

def log_info(msg):
    LOGGER.info(msg)

def log_set(msg):
    LOGGER.info(f"SET{msg}")

def log_warning(msg):
    LOGGER.warning(msg)

def log_error(msg):
    LOGGER.error(f"{msg}\n\nError reported, aborting render script")
    exit(1)

def flush_log():
    sys.stdout.flush()
    sys.stderr.flush()


###


class ImageFormat(Enum):
    jpg = lux.RENDER_OUTPUT_JPEG
    png = lux.RENDER_OUTPUT_PNG
    exr = lux.RENDER_OUTPUT_EXR
    # tif = lux.RENDER_OUTPUT_TIFF8
    tif = lux.RENDER_OUTPUT_TIFF32
    # psd = lux.RENDER_OUTPUT_PSD8
    # psd = lux.RENDER_OUTPUT_PSD16
    psd = lux.RENDER_OUTPUT_PSD32


def load_scene(scene_path):
    time_start = datetime.datetime.now()

    lux.openFile(r'{0}'.format(scene_path))

    load_time = datetime.datetime.now() - time_start
    log_info("Scene load time: {0} h:m:s.ms".format(load_time))
    flush_log()


def search_missing_textures(project_dir):
    tex_dir = os.path.join(project_dir, "Textures")

    for mat_name in lux.getSceneMaterials():
        for node in lux.getMaterialGraph(mat_name).getNodes():
            try:
                tex_param = node.getParameter("texture")
            except Exception:
                continue

            tex_path = tex_param.getValue()
            if not os.path.exists(tex_path):
                tex_file_dir, tex_filename = os.path.split(tex_path)
                net_path = os.path.join(tex_dir, tex_file_dir.split("Textures", 1)[-1], tex_filename)

                if os.path.isfile(net_path):
                    tex_param.setValue(net_path)
                    log_info(f"Replaced missing texture '{tex_path}' with '{net_path}'")
                else:
                    log_warning(f"Missing texture: '{tex_path}'")


class KS_RenderManager(object):

    def __init__(self, output_path, output_ext, frame_start=1, frame_end=1, frame_step=1, frame_padding=4):
        self.output_path = output_path
        self.output_ext = output_ext

        self.frame_start = frame_start
        self.frame_end = frame_end
        self.frame_step = frame_step
        self.frame_padding = frame_padding

        self.render_ops = lux.getRenderOptions()

    def set_max_samples(self, samples):
        self.render_ops.setMaxSamplesRendering(samples)

    def set_max_time(self, seconds):
        self.render_ops.setMaxTimeRendering(seconds)

    def set_cores(self, cores):
        self.render_ops.setThreads(cores)
    
    def set_camera(self, camera):
        lux.setCamera(camera)
    
    def set_modelset(self, modelsets):
        set_list = modelsets.split(":")
        return lux.setModelSets(set_list)

    def set_region(self, start_x, start_y, end_x, end_y):
        self.render_ops.setRegion((start_x, start_y, end_x, end_y))

    def render_scene(self):
        # Background starts rendering and returns immediatly
        self.render_ops.setBackgroundRendering(False)
        
        # renderFrames() is not available in headless mode
        if self.output_ext == "_":  # single file
            writeRenderPlaceholder(self.output_path)
            lux.renderImage(path=self.output_path, opts=self.render_ops)

            log_info("Rendered single file" + self.output_path)
            flush_log()

            return

        for frame_num in range(self.frame_start, self.frame_end + 1, self.frame_step):
            lux.setAnimationFrame(frame_num)
            fr_num = str(frame_num).zfill(self.frame_padding)
            output_full = "".join((self.output_path, fr_num, self.output_ext))

            writeRenderPlaceholder(output_full)
            lux.renderImage(path=output_full, opts=self.render_ops)

            log_info("Rendered frame " + output_full)
            flush_log()


def add_py_path(additional_path):
    if not os.path.isdir(additional_path):
        log_warning("additional python path not found: " + additional_path)
        return
    if additional_path not in sys.path:
        sys.path.append(additional_path)


if __name__ == '__main__':
    log_info("Render Plugin Starting")
    flush_log()

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("scene", help="render scene")
    parser.add_argument("out_path", help="output path")
    parser.add_argument("out_ext", help="output extension")
    parser.add_argument("seq_start", help="first frame", type=int)
    parser.add_argument("seq_end", help="last frame", type=int)
    parser.add_argument("seq_step", help="frame step", type=int)
    parser.add_argument("seq_padding", help="frame padding", type=int)
    parser.add_argument("prj_path", help="Network project path")

    parser.add_argument("--samples", help="max render samples", type=int, default=-1)
    parser.add_argument("--max_time", help="max render time in seconds. Not used if the option --samples is provided", type=int, default=-1)
    parser.add_argument("--cores", help="number of cores to be used", type=int, default=-1)

    parser.add_argument("--RegionLeft", help="left pixel of image region", type=int, default=-1)
    parser.add_argument("--RegionRight", help="right pixel of image region", type=int, default=-1)
    parser.add_argument("--RegionBtm", help="bottom pixel of image region", type=int, default=-1)
    parser.add_argument("--RegionTop", help="top pixel of image region", type=int, default=-1)
    
    parser.add_argument("--ModelSets", help="Sets of visible objects", default='')
    parser.add_argument("--Camera", help="Render Camera", default='')

    parser.add_argument("--python_path", help="helper python scripts", default='')

    args = parser.parse_args()

    if args.python_path:
        add_py_path(args.python_path)

    try:
        from kso_tcp import writeRenderPlaceholder
    except:
        log_warning("RR render help tools not found: render placeholders omitted")

        def writeRenderPlaceholder(filename):
            pass
    else:
        log_debug("RR render placeholders were enabled")
    flush_log()

    load_scene(args.scene)
    search_missing_textures(os.path.dirname(args.prj_path))

    render_manager = KS_RenderManager(
        args.out_path, args.out_ext,
        args.seq_start, args.seq_end, args.seq_step, args.seq_padding,
    )

    if args.samples and args.samples > 0:
        render_manager.set_max_samples(args.samples)
    elif args.max_time and args.max_time > 0:
        render_manager.set_max_time(args.max_time)

    if args.cores:
        render_manager.set_cores(args.cores)
    
    if args.Camera:
        render_manager.set_camera(args.Camera)
    
    if args.ModelSets:
        render_manager.set_modelset(args.ModelSets)

    if any((args.RegionLeft > 0, args.RegionTop > 0, args.RegionRight > 0, args.RegionBtm > 0)):
        render_manager.set_region(args.RegionLeft, args.RegionTop, args.RegionRight + 1, args.RegionBtm + 1)

    render_manager.render_scene()

    log_info("Exit Render Plugin")
    exit(0)
