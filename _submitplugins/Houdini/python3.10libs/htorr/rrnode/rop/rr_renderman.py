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
output_devices = ["openexr", "deepexr", "tiff", "png", "targa", "texture"]
try:
    import hou
except ImportError:
    logger.info("Module imported outside of hython environment")


def _getRendermanVersion():
    import hou 
    import os 

    try:
        rfh_path  = os.environ['RFHTREE'].replace("\\","/")
    except KeyError:
        logger.warning("Env Variable RFHTREE not set, probably Renderman not correctly setup")
        return

        
    hVers = hou.applicationVersion()
    houVersionString = str(hVers[0]) + "." + str(hVers[1])
    versionFile = os.path.join(rfh_path, houVersionString, 'etc', 'buildid.txt')

    try:
        myFile = open(versionFile, 'r')
        fullVersionString = myFile.readline().rstrip()
        myFile.close()

        versionString = fullVersionString.split()[-1]

        return versionString

    except IOError:
        logger.warning("Unable to read Renderman version from file")

class RendermanRop(RenderNode):

    name = "ris"

    @property
    def camera_parm(self):
        return "camera"

    @property
    def output_parm(self):
        multi_parm = self._node.parm("ri_displays").multiParmInstances()
        for i in range(0, len(multi_parm), 127):
            device_parm = multi_parm[i+2]
            if device_parm.eval() in output_devices:
                return multi_parm[i].name()
                


    @property
    def renderer(self):
        # todo: get correct renderer name
        return "renderman"

    @property
    def renderer_version(self):
       return _getRendermanVersion()

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
        multi_parm = self._node.parm("ri_displays").multiParmInstances()
        main_output_parm_name = self.output_parm
        for i in range(0, len(multi_parm), 127):
            device_parm = multi_parm[i+2]
            output_parm = multi_parm[i]
            if(device_parm.eval() in output_devices and output_parm.name() != main_output_parm_name):
                out = Output(output_parm)
                aovs.append((os.path.join(out.dir,out.name),out.extension))
        if aovs:
            return aovs
        return

    @property
    def archive(self):
        return self._node.evalParm("diskfile")

    @property
    def gpu(self):
        return False

    def check(self):
        has_output = False
        multi_parm = self._node.parm("ri_displays").multiParmInstances()
        for i in range(0, len(multi_parm), 127):
            device_parm = multi_parm[i+2]
            if device_parm.eval() in output_devices:
                has_output = True
                break

        if not has_output:
            logger.warning("{}: No output device selected".format(self.path))

        return has_output  

    def to_archive(self):
        self.__class__ = RendermanArchiveROP

    def to_standalone(self):
        self.__class__ = RendermanStandalone


class RendermanArchiveROP(RendermanRop):

    name = "ris_archive"

    @property
    def renderer(self):
        # todo get correct renderer name
        return "createRib"

    @property
    def output_parm(self):
        return "soho_diskfile"

    @property
    def aovs(self):
        return

    @property
    def gpu(self):
        return False


class RendermanStandalone(RendermanRop):

    name = "ris_standalone"

    @property
    def software(self):
        # todo get correct software 
        return "Renderman"

    @property
    def software_version(self):
        return super(RendermanStandalone, self).renderer_version

    @property
    def renderer(self):
        return "Houdini"

    @property
    def renderer_version(self):
        return
