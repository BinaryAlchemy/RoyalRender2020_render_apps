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

try:
    import hou
except ImportError:
    logger.info("Module imported outside of hython environment")


def _getVRayVersion(self):
    try:
        import vray 
    except ImportError:
        return ""

    versionStr = vray.getVRayVersionDetails()
    vray_ver = versionStr.split()[0]   
    return vray_ver
            

class VrayRop(RenderNode):

    name = "vray_renderer"

    @property
    def camera_parm(self):
        return "render_camera"

    @property
    def output_parm(self):
        return "SettingsOutput_img_file_path"
                
    @property
    def renderer(self):
        return "vray"

    @property
    def renderer_version(self):
        return _getVRayVersion()

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
        
        # Check if variable AOV is used, if not, no AOVs will be written
        raw_path = self._node.parm(self.output_parm).rawValue()
        if not "$AOV" in raw_path and not "${AOV}" in raw_path:
            return

        
        network = self._node.parm("render_network_render_channels").evalAsNode()
        if not network:
            return

        aovs = []
        channel_container = None
        channels = []

        # Get Channel Container node
        for node in network.children():
            if node.type().name() == "VRayNodeRenderChannelsContainer":
                channel_container = node
                break
        
        # Get all Render Element Nodes and copy names into channels list
        if channel_container:
            for input in channel_container.inputs():
                if not input.isBypassed() and input.type().name() == "VRayNodeRenderChannelColor":
                    channels.append(input.parm("name").eval())

        for channel in channels:
            try:
                hou.putenv("AOV", channel)
                out = Output(self._node.parm(self.output_parm))
                aovs.append((os.path.join(out.dir,out.name),out.extension))
            finally:
                hou.unsetenv("AOV")

        return aovs

    @property
    def archive(self):
        return self._node.parm("render_export_mode").eval() != '0'

    @property
    def gpu(self):
        if self._node.parm("render_render_mode").eval() == '0':
            return False
        else:
            return True


    def check(self):
        if self._node.parm('SettingsOutput_relements_separate_rgba').eval():
            logger.info("'{}': Feature 'Store Beauty Pass Under a Separate Folder' not yet supported".format(self.path))
        return True

    def to_archive(self):
        self.__class__ = VrayArchiveROP

    def to_standalone(self):
        f1 = self._node.parm("render_export_filepath").evalAtFrame(1)
        f2 = self._node.parm("render_export_filepath").evalAtFrame(2)
        if f1 == f2:
            self.__class__ = VrayStandalone
        else:
            self.__class__ = VrayStandalone_multifile


class VrayArchiveROP(VrayRop):

    name = "vray_renderer_archive"

    @property
    def renderer(self):
        return "createVrScene"

    @property
    def output_parm(self):
        return "render_export_filepath"

    @property
    def aovs(self):
        return

    @property
    def gpu(self):
        return False
    
    @property
    def single_output(self):
        f1 = self._node.parm(self.output_parm).evalAtFrame(1)
        f2 = self._node.parm(self.output_parm).evalAtFrame(2)
        if f1 == f2:
            return True
        else:
            return False

class VrayStandalone(VrayRop):

    name = "vray_renderer_standalone"

    @property
    def software(self):
        return "VRay_StdA"

    @property
    def software_version(self):
        VRay_Version= VrayRop.renderer_version.fget(self)
        logger.debug("{}: VRay_Version {}".format(self._node.path(), VRay_Version ))        
        return VRay_Version

    @property
    def renderer(self):
        return "Houdini"

    @property
    def renderer_version(self):
        return


class VrayStandalone_multifile(VrayRop):

    name = "vray_renderer_standalone_multifile"

    @property
    def software(self):
        return "VRay_StdA"

    @property
    def software_version(self):
        VRay_Version= VrayRop.renderer_version.fget(self)
        logger.debug("{}: VRay_Version {}".format(self._node.path(), VRay_Version ))        
        return VRay_Version

    @property
    def renderer(self):
        return "multifile"

    @property
    def renderer_version(self):
        return
