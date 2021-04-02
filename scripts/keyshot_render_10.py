import lux

from enum import Enum
import datetime
import os
import sys


# LOGGING

def log_message(msg, lvl=""):
    if lvl:
        print(datetime.datetime.now().strftime("' %H:%M.%S") + " KeyShot - " + str(lvl) + ": " + str(msg))
    else:
        print(datetime.datetime.now().strftime("' %H:%M.%S") + " KeyShot      : " + str(msg))

def log_debug(msg):
    log_message("DBG", msg)
    pass

def log_info(msg):
    log_message("", msg)

def log_set(msg):
    log_message("SET", msg)

def log_warning(msg):
    log_message("WRN", msg)

def log_error(msg):
    log_message("ERR", str(msg) + "\n\n")
    log_message("ERR", "Error reported, aborting render script")
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

    def set_region(self, start_x, start_y, end_x, end_y):
        self.render_ops.setRegion((start_x, start_y, end_x, end_y))

    def render_scene(self):
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

    parser.add_argument("--samples", help="max render samples", type=int, default=-1)
    parser.add_argument("--max_time", help="max render time in seconds. Not used if the option --samples is provided", type=int, default=-1)
    parser.add_argument("--cores", help="number of cores to be used", type=int, default=-1)

    parser.add_argument("--RegionLeft", help="left pixel of image region", type=int, default=-1)
    parser.add_argument("--RegionRight", help="right pixel of image region", type=int, default=-1)
    parser.add_argument("--RegionBtm", help="bottom pixel of image region", type=int, default=-1)
    parser.add_argument("--RegionTop", help="top pixel of image region", type=int, default=-1)

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

    if any((args.RegionLeft, args.RegionTop, args.RegionRight, args.RegionBtm)):
        render_manager.set_region(args.RegionLeft, args.RegionTop, args.RegionRight + 1, args.RegionBtm + 1)

    render_manager.render_scene()

    log_info("Exit Render Plugin")
    exit(0)
