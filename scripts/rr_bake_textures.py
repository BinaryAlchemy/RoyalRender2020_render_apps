import pymel.core as pm
from pymel.core import PyNode
from pymel.all import mel

class VrayBakeTexures(object):

    def __init__(self, object_name, output_texture_path):
        self.object_name = object_name
        self.output_texture_path = output_texture_path
        # self.image_width = 50
        # self.cur_version_string = 'v001'

    def configure_global(self):
        """
        Configure V-Ray global baking options
        """

        # Create default VRay bake options node
        # NOTE: Doesn't work in batch mode, assuming already exist
        # pm.mel.vrayShowDefaultBakeOptions()
        bake_options = PyNode('vrayDefaultBakeOptions')

        # Set global bake options
        # bake_options.setAttr('filenamePrefix', self.cur_version_string)
        bake_options.setAttr('outputTexturePath', self.output_texture_path)
        # bake_options.setAttr('resolutionX', self.image_width)

    def bake(self):

        self.configure_global()

        # Select target bake object
        pm.select(self.object_name)

        mel.optionVar(2, intValue="vrayBakeType") # 1 - All, 2 - Selected
        mel.optionVar(0, intValue="vraySkipNodesWithoutBakeOptions")
        mel.optionVar(0, intValue="vrayAssignBakedTextures")
        # mel.optionVar(self.output_texture_path, stringValue="vrayBakeOutputPath")
        mel.optionVar(0, intValue="vrayBakeProjectionBaking")

        mel.vrayStartBake()

def rr_start(obj_name, image_dir, seq_start, seq_end, seq_step):
    print('[D] Baking textures...')
    print('[D] Object Name: ', obj_name)
    print('[D] Image Directory: ', image_dir)
    print('[D] Seq start: ', seq_start)
    print('[D] Seq end: ', seq_end)
    print('[D] Seq step: ', seq_step)

    vb = VrayBakeTexures(object_name=obj_name, output_texture_path=image_dir)
    vb.bake()

    print('[D] Baking is done!')
