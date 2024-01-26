# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy

import logging
import os.path
from htorr.rroutput import Output
from htorr.rrnode.base import RenderNode


logger = logging.getLogger("HtoRR")

try:
    import hou
except ImportError:
    logger.info("Module imported outside of hython environment")


logger = logging.getLogger("HtoRR")


def _getOctaneVersion():
    try:
        pass
    except ImportError:
        return ""

    return ""
            

class OctaneRop(RenderNode):

    name = "Octane_ROP"

    @property
    def camera_parm(self):
        return "HO_renderCamera"

    @property
    def output_parm(self):
        return "HO_img_fileName"
                
    @property
    def renderer(self):
        return "Octane"

    @property
    def renderer_version(self):
        return _getOctaneVersion()

    @property
    def image_size(self):
        from htorr.rrnode.rop import utils
        x = None
        y = None
        if not hou.node(self.camera):
            return
        try:
            if not self._node.evalParm("HO_overrideCameraRes"):
                x, y = utils.get_camera_res(self.camera)
            else:
                if self._node.evalParm("HO_overrideResScale") == "user":
                    x = self._node.evalParm("HO_overrideRes1")
                    y = self._node.evalParm("HO_overrideRes2")
                else:
                    frac = float(self._node.evalParm("HO_overrideResScale"))
                    if (frac==1):
                        frac=1/10
                    elif (frac==2):
                        frac=1/5
                    elif (frac==3):
                        frac=1/4
                    elif (frac==4):
                        frac=1/3
                    elif (frac==5):
                        frac=1/2
                    elif (frac==6):
                        frac=2/3
                    elif (frac==7):
                        frac=3/4                    
                    x, y = utils.get_camera_res(self.camera)
                    x = int(round(x * frac))
                    y = int(round(y * frac))

        except ValueError:
            return

        return(x, y)


    @property
    def archive(self):
        return self._node.parm("HO_abc_exportEnabled").eval() == 1

    @property
    def gpu(self):
        return True

    def to_archive(self):
        self.__class__ = OctaneArchiveROP

    def to_standalone(self):
        self.__class__ = OctaneStandalone


class OctaneArchiveROP(OctaneRop):

    name = "Octane_ROP_archive"

    @property
    def renderer(self):
        return "createOctane"

    @property
    def output_parm(self):
        # HO_abc_exportMode   expold expnew
        return "HO_abc_exportFileName"

    @property
    def aovs(self):
        return

    #def check(self):
    #    if self._node.parm('HO_abc_exportMode').eval()=="expold":
    #        logger.info("'{}': ABC export not supported".format(self.path))
    #    return True


    @property
    def gpu(self):
        return False
    
    @property
    def single_output(self):
        return False

class OctaneStandalone_singlefile(OctaneRop):

    name = "Octane_ROP_standalone_singlefile"

    @property
    def software(self):
        return "Octane-singlefile"

    @property
    def software_version(self):
        return OctaneRop.renderer_version.fget(self)

    @property
    def renderer(self):
        return "Houdini"

    @property
    def renderer_version(self):
        return

    @property
    def layerName(self):
        return "Render target"
        #return self._node.parm("HO_renderTarget").eval()


class OctaneStandalone(OctaneRop):

    name = "Octane_ROP_standalone"

    @property
    def software(self):
        return "Octane"

    @property
    def software_version(self):
        return OctaneRop.renderer_version.fget(self)

    @property
    def renderer(self):
        return "Houdini"

    @property
    def renderer_version(self):
        return

    @property
    def layerName(self):
        return "Render target"
        #return self._node.parm("HO_renderTarget").eval()

