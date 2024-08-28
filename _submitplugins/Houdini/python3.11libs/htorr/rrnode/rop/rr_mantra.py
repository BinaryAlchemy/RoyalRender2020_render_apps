# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy

from htorr.rrnode.base import RenderNode
from htorr.rroutput import Output
import logging
import hou
import os.path
logger = logging.getLogger("HtoRR")


class MantraRop(RenderNode):

    name = "ifd"

    @property
    def outname(self):
        out = super(MantraRop, self).outname
        if self.stereo:
            out = add_stereo_token(out)
        return out

    @property
    def output_parm(self):
        return "vm_picture"

    @property
    def camera_parm(self):
        return "camera"

    @property
    def renderer(self):
        return "mantra"

    @property
    def renderer_version(self):
        return self.software_version

    @property
    def image_size(self):
        from htorr.rrnode.rop import utils
        x = None
        y = None

        if not hou.node(self.camera):
            return

        try:
            if not self._node.evalParm("override_camerares"):
                x, y = utils.get_camera_res(self.camera)
            else:
                if self._node.evalParm("res_fraction") == "specific":
                    x = self._node.evalParm("res_overridex")
                    y = self._node.evalParm("res_overridey")
                else:
                    frac = float(self._node.evalParm("res_fraction"))
                    x, y = utils.get_camera_res(self.camera)
                    x = int(round(x * frac))
                    y = int(round(y * frac))

        except ValueError:
            return

        return(x, y)

    @property
    def aovs(self):
        aovs = []
        multi_parms = self._node.parm("vm_numaux").multiParmInstances()
        aovs = []
        for i in range(0, len(multi_parms), 18):
            parms = multi_parms[i:i+18]
            aov_enabled = not parms[0].eval()
            seperate_enabled = parms[5].eval()
            if seperate_enabled and aov_enabled:
                out = Output(parms[6])
                path = os.path.join(out.dir,out.name)
                if self.stereo:
                    path = add_stereo_token(path)
                aovs.append((path,out.extension))
        return aovs

    @property
    def archive(self):
        if self._node.evalParm("soho_outputmode"):
            return True

    def to_archive(self):
        self.__class__ = MantraArchiveROP

    def to_standalone(self):
        self.__class__ = MantraStandalone


class MantraArchiveROP(MantraRop):

    name = "mantra_archive"

    @property
    def renderer(self):
        return "createIFD"

    @property
    def output_parm(self):
        return "soho_diskfile"

    @property
    def aovs(self):
        return

    @property
    def gpu(self):
        return False


class MantraStandalone(MantraRop):

    name = "mantra_standalone"

    @property
    def software(self):
        return "Mantra_StdA"

    @property
    def renderer(self):
        return

    @property
    def renderer_version(self):
        return


def add_stereo_token(path):
    if path.endswith("."):
        return path[:len(path)-1] + "<Stereo>."
    else:
        return path+"<Stereo>"
