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

def _getArnoldVersion(self):
    try:
        import arnold
    except ImportError:
        msg = 'Failed to import "arnold" python module, \
               htoa is not available.'
        logger.error(msg)
    else:
        return arnold.AiGetVersionString()
            

class ArnoldRop(RenderNode):

    name = "arnold"

    @property
    def camera_parm(self):
        return "camera"

    @property
    def output_parm(self):
        return "ar_picture"

    @property
    def renderer(self):
        return "arnold"

    @property
    def renderer_version(self):
        return _getArnoldVersion()

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
        multi_parms = self._node.parm("ar_aovs").multiParmInstances()
        multi_count= self._node.parm("ar_aovs").multiParmInstancesCount()
        aovs = []
        
        #logger.debug("aovs multi_parms "+str(len(multi_parms))+"   "+str(multi_count))
        
        for i in range(1, int(len(multi_parms)/20)+1): #last version tested has 28 parms per AOV.
            enabled = None
            file = None
            file_parm = None
            
            enabled_name="ar_enable_aov{}".format(i)
            file_enabled_name="ar_aov_separate{}".format(i)
            file_parm_name="ar_aov_separate_file{}".format(i)
            #logger.debug("enabled_name "+str(enabled_name))
            #logger.debug("file_enabled_name "+str(file_enabled_name))
            #logger.debug("file_parm_name "+str(file_parm_name))
            
            for p in range(0, len(multi_parms)):
                logger.debug("multi_parms   "+str(multi_parms[p].name()))
                if (multi_parms[p].name() == enabled_name):
                    enabled=multi_parms[p].eval()
                elif (multi_parms[p].name()== file_enabled_name):
                    file_enabled=multi_parms[p].eval()
                elif (multi_parms[p].name()== file_parm_name):
                    file_parm=multi_parms[p]
                
                if (enabled != None and file_parm != None and file_enabled != None ):
                    
                    if enabled and file_enabled:
                        logger.debug("AOV enabled")
                        out = Output(file_parm,1,2,False)
                        aovs.append((os.path.join(out.dir,out.name),out.extension))                
                
                    break

        return aovs 

    @property
    def archive(self):
        return self._node.evalParm("ar_ass_export_enable")

    @property
    def gpu(self):
        #if self._node.evalParm("ar_render_device") == "CPU":
        if self._node.evalParm("ar_denoise") == 1:
            gpu = False
        else:
            gpu = True
        return gpu

    def to_archive(self):
        self.__class__ = ArnoldArchiveROP

    def to_standalone(self):
        self.__class__ = ArnoldStandalone


class ArnoldArchiveROP(ArnoldRop):

    name = "arnold_archive"

    @property
    def renderer(self):
        return "createASS"

    @property
    def output_parm(self):
        return "ar_ass_file"

    @property
    def aovs(self):
        return

    @property
    def gpu(self):
        return False


class ArnoldStandalone(ArnoldRop):

    name = "arnold_standalone"

    @property
    def software(self):
        return "Arnold"

    @property
    def software_version(self):
        return super(ArnoldStandalone, self).renderer_version

    @property
    def renderer(self):
        return "HtoA"

    @property
    def renderer_version(self):
        return
