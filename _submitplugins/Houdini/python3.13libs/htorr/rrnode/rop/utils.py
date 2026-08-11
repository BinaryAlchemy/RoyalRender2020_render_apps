# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy

import logging

logger = logging.getLogger("HtoRR")

try:
    import hou
    tmp = hou.getenv("HIP")
except ImportError:
    logger.info("Module imported outside of hython environment")


def get_camera_res(path):
    cam = hou.node(path)
    return(cam.evalParm("resx"), cam.evalParm("resy"))
