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

def _getRedshiftVersion():
    version = hou.hscript('Redshift_version')[0]
    version = version.replace("\n", "")
    version = version.replace("\r", "")        
    if version.startswith("Unknown"):
        logger.error(" Redshift Plugin not available")
    else:
        return version
            


RS_RESOVERRIDE = [
    0.1,
    0.2,
    0.25,
    1/3,
    0.5,
    2/3,
    0.75
]

class RedshiftRop(RenderNode):
    name = "Redshift_ROP"

    @property
    def outname(self):
        out = super(RedshiftRop, self).outname
        suffix = self._node.parm("RS_outputBeautyAOVSuffix").eval()
        if not suffix:
            out = out.replace(".%AOV%", suffix)
        out = out.replace("%AOV%", suffix)
        return out

    @property
    def camera_parm(self):
        return "RS_renderCamera"

    @property
    def output_parm(self):
        return "RS_outputFileNamePrefix"

    @property
    def renderer(self):
        return "redshift"

    @property
    def renderer_version(self):
        return _getRedshiftVersion()

    @property
    def image_size(self):
        from htorr.rrnode.rop import utils
        x = None
        y = None

        if not hou.node(self.camera):
            return

        try:
            if not self._node.evalParm("RS_overrideCameraRes"):
                x, y = utils.get_camera_res(self.camera)
            else:
                if self._node.evalParm("RS_overrideResScale") == 7:
                    x = self._node.evalParm("RS_overrideRes1")
                    y = self._node.evalParm("RS_overrideRes2")
                else:
                    frac = RS_RESOVERRIDE[self._node.evalParm("RS_overrideResScale")]
                    x, y = utils.get_camera_res(self.camera)
                    x = int(round(x * frac))
                    y = int(round(y * frac))

        except ValueError:
            return

        return(x, y)

    @property
    def aovs(self):
        aovs = []

        multi_layer_exr = self._node.evalParm("RS_outputMultilayerMode") == 1
        multi_parms = self._node.parm("RS_aov").multiParmInstances()
        multi_count= self._node.parm("RS_aov").multiParmInstancesCount()

        if multi_layer_exr:
            logger.debug("RS Multi Layer EXR " + str(len(multi_parms)) + "  " + str(multi_count))
        else:
            logger.debug("RS Single Layer EXR")

        for i in range(1, int(len(multi_parms)/50)+1): #last version tested has 55 parms per AOV.
            enabled = None
            suffix = None
            file_parm = None
            
            enabled_name="RS_aovEnable_{}".format(i)
            suffix_name="RS_aovSuffix_{}".format(i)
            file_parm_name="RS_aovCustomPrefix_{}".format(i)
            for p in range(0, len(multi_parms)):
                if (multi_parms[p].name() == enabled_name):
                    enabled=multi_parms[p].eval()
                elif (multi_parms[p].name()== suffix_name):
                    suffix=multi_parms[p].eval()
                elif (multi_parms[p].name()== file_parm_name):
                    file_parm=multi_parms[p]
                
                if (enabled != None and suffix != None and file_parm != None ):
                    if enabled:
                        logger.debug("AOV enabled :" + suffix)
                        path = None
                        ext = None
                        fileName=file_parm.eval()
                        if (fileName!=None) and (len(fileName)>0):
                            out = Output(file_parm, 1, 2, False)
                            path = os.path.join(out.dir,out.name)
                            ext = out.extension
                    
                        elif not multi_layer_exr:
                            out = Output(self._node.parm(self.output_parm), 1, 2, False)
                            path = os.path.join(out.dir,out.name)
                            ext = out.extension

                        if path:
                            if "%AOV%" in path:
                                path = path.replace("%AOV%",suffix)
                            else:
                                ext = "." + suffix + ext

                            logger.debug(path + ext)
                            aovs.append((path,ext))
                    break
                        
        return aovs 

    
    @property
    def archive(self):
        return self._node.evalParm("RS_archive_enable")

    @property
    def gpu(self):
        return True

    def to_archive(self):
        self.__class__ = RedshiftArchiveROP

    def to_standalone(self):
        self.__class__ = RedshiftStandalone
    

class RedshiftArchiveROP(RedshiftRop):
    name = "Redshift_archive"

    @property
    def renderer(self):
        return "createRS"

    @property
    def output_parm(self):
        return "RS_archive_file"

    @property
    def aovs(self):
        return

    @property
    def gpu(self):
        return False


class RedshiftStandalone(RedshiftRop):
    name = "Redshift_standalone"

    @property
    def software(self):
        return "Redshift"

    @property
    def software_version(self):
        return super(RedshiftStandalone, self).renderer_version

    @property
    def renderer(self):
        return "Houdini"

    @property
    def renderer_version(self):
        return