# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy

from htorr.rrnode.base import RenderNode
import logging
import hou

logger = logging.getLogger("HtoRR")


class OpenGLRop(RenderNode):
    """ OpenGL Render ROP to render OpenGL Previews"""

    name = "opengl"

    @property
    def camera_parm(self):
        return "camera"

    @property
    def output_parm(self):
        return "picture"

    @property
    def renderer_version(self):
        return self.software_version

    @property
    def renderer(self):
        return "opengl"

    @property
    def image_size(self):
        from htorr.rrnode.rop import utils
        if not hou.node(self.camera):
            return
        x = None
        y = None
        try:
            if not self._node.evalParm("tres"):
                x, y = utils.get_camera_res(self.camera)
            else:
                x = self._node.evalParm("res1")
                y = self._node.evalParm("res2")
        except ValueError:
            return
        return(x, y)
