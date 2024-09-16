# -*- coding: cp1252 -*-
######################################################################
#
# Royal Render Plugin script for Blender 
# Authors, based on:    Felix Bucella, Patrik Gleich, Friedrich Wessel
# Authors:  Paolo Acampora (Binary Alchemy), Holger Schoenberger (Binary Alchemy)
# Last change: %rrVersion%
#
# #win:   rrInstall_Copy:     \*\scripts\startup\
# #linux: rrInstall_Copy:     \*\scripts\startup\
# #mac:   rrInstall_Copy:     \Resources\*\scripts\startup\
# 
######################################################################

bl_info = {
    "name": "Royal Render Submitter",
    "author": "Binary Alchemy",
    "version": "%rrVersion%",
    "blender": (2, 80, 0),
    "description": "Submit scene to Royal Render",
    "category": "Render",
    }

import bpy
import os
import tempfile
import sys
import subprocess

class RoyalRender_Submitter(bpy.types.Panel):
    """Creates an XML and start the RR Submitter"""
    bl_label = "RoyalRender Submitter"
    bl_idname = "OBJECT_PT_RRSubmitter"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'

    bl_context = "output" if bpy.app.version[1] > 79 or bpy.app.version[0] > 2 else "render"

    # switching keyword arguments to keep backward compatibility with 2.79
    _split_kwargs_ = {'factor': 0.05} if bpy.app.version[1] > 79 or bpy.app.version[0] > 2 else {'percentage': 0.05}

    def draw(self, context):
        layout = self.layout

        scn = context.scene
        img_type = scn.render.image_settings.file_format

        renderOut = bpy.path.abspath(scn.render.filepath)
        
        layout.label(text="Submit Scene Recap: ")
        split = layout.split(**self._split_kwargs_)

        split.separator()
        col = split.column()
        row = col.row()
        row.label(text="StartFrame: " + str(scn.frame_start))
        row.label(text="EndFrame: " + str(scn.frame_end))
        col.label(text="ImageType: " + img_type)
        col.label(text="ImageName: " + os.path.basename(renderOut))
        col.label(text="RenderDir: " + os.path.dirname(renderOut))

        if not bpy.data.is_saved:
            row = layout.row()
            row.label(text="No .blend file saved", icon="ERROR")

        row = layout.row()
        row.operator("royalrender.submitscene")


class OBJECT_OT_SubmitScene(bpy.types.Operator):
    """Submit current file to Royal Render"""
    bl_idname = "royalrender.submitscene"
    bl_label = "Submit Scene"

    _renderer_name = ""
    _renderer_version = ""

    @classmethod
    def poll(cls, context):
        return bpy.data.is_saved

    def get_RR_Root(self):
        if 'RR_ROOT' in os.environ: 
            return os.environ['RR_ROOT']

        if sys.platform.lower().startswith('win'):
            HCPath = "%RRLocationWin%"
        elif sys.platform.lower() == "darwin":
            HCPath = "%RRLocationMac%"
        else:
            HCPath = "%RRLocationLx%"
        if not HCPath.startswith("%"):
            return HCPath

        self.report({'ERROR'},
                    "No RR_ROOT environment variable set!"
                    "\n Please execute     rrWorkstationInstaller and restart.")

    @staticmethod
    def get_ocio_config_file():
        try:
            return os.environ['OCIO']
        except KeyError:
            pass
        
        default_cfg_file = os.path.join("<rrBaseAppPath><IsMac /Resources>", "<IsMac <rrJobVersionMajor>.<rrJobVersionMinor>?<rrExeVersion>>", "datafiles", "colormanagement", "config.ocio") #<IsMac must not be a seperate flag on its own (otherwise double // on windows)
        return default_cfg_file
    
    @staticmethod
    def get_out_colorspace_settings(scene):
        try:
            image_settings = scene.render.image_settings
        except AttributeError:
            return ''

        try:
            has_color_space = image_settings.has_linear_colorspace
        except AttributeError:
            return 'sRgb'
        
        if not has_color_space:
            return 'Linear Rec.709'

        if image_settings.color_management == 'FOLLOW_SCENE':
            return 'Linear Rec.709'
        
        return image_settings.linear_colorspace_settings.name

    @staticmethod
    def writeNodeStr(fileID, name, text):
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        text = text.replace("\"", "&quot;")
        text = text.replace("'", "&apos;")
        fileID.write("    <{0}>  {1}   </{0}>\n".format(name, text))

    @staticmethod
    def writeNodeInt(fileID, name, number):
        fileID.write("    <{0}>  {1}   </{0}>\n".format(name, number))

    @staticmethod
    def writeNodeBool(fileID, name, value):
        fileID.write("    <{0}>   {1}   </{0}>\n".format(name, int(value)))

    @staticmethod
    def hasRelativePaths():
        for filepath in bpy.utils.blend_paths(packed=False):
            if filepath.startswith("//"):  # relative path
                return True
        return False

    @staticmethod
    def getSingleOutputExtension(scn, rendertarget, renderOut, hash_position, padding):
        ffmpeg_exts = {'AVI': '.avi', 'FLASH': '.flv', 'MKV': '.mkv',
                       'MPEG1': '.mpg', 'MPEG2': '.dvd', 'MPEG4': '.mp4',
                       'OGG': '.ogv', 'QUICKTIME': '.mov', 'WEBM': '.webm'}

        if rendertarget.startswith("AVI_"):
            extension = '.avi'
        elif rendertarget == 'FFMPEG':
            extension = ffmpeg_exts[scn.render.ffmpeg.format]

        # if the video extension is not part of the output filename,
        # blender will add the frame range
        if renderOut.lower().endswith(extension.lower()):
            renderOut = renderOut[:-len(extension)]
        else:
            if hash_position == -1:
                renderOut = "{0}{1:0{3}d}-{2:0{3}d}".format(renderOut,
                                                            scn.frame_start, scn.frame_end,
                                                            padding)
            else:
                prefix, suffix = renderOut.rsplit("#" * padding, 1)
                renderOut = "{0}{1:0{3}d}-{2:0{3}d}{4}".format(prefix,
                                                               scn.frame_start, scn.frame_end,
                                                               padding,
                                                               suffix)
        return renderOut, extension

    def writeSceneJobs(self, scn, fileID, scene_state="", is_active=True):
        try:
            layers = scn.view_layers
        except AttributeError:
            self.writeLayerJob(scn, fileID, scene_state, is_active=is_active)
        else:
            for layer in layers:
                self.writeLayerJob(scn, fileID, scene_state, layer.name, is_active=is_active and layer == bpy.context.view_layer)

    def writeLayerJob(self, scn, fileID, scene_state="", layer="", is_active=True):
        # file_format and file_codec are used in the render script
        file_format = scn.render.image_settings.file_format
        
        v_major, v_minor, v_release = bpy.app.version
        is_single_output = file_format == 'FFMPEG' or file_format.startswith('AVI_')

        # cmd_frame_format is different in blender 2.79 commandline -F
        if v_major < 3 and v_minor < 80:
            file_format = file_format.replace("OPEN_", "")
            file_format = file_format.replace("TARGA_RAW", "RAWTGA")
            file_format = file_format.replace("TARGA", "TGA")

        if file_format == "JPEG2000":
            file_format = scn.render.image_settings.jpeg2k_codec

        render_out = bpy.path.abspath(scn.render.filepath)

        try:
            hash_position = render_out.rindex('#')
            renderPadding = hash_position - next(i for i in range(hash_position, 0, -1) if render_out[i] != '#')
        except ValueError:
            hash_position = -1
            renderPadding = 4

        if scn.render.use_file_extension:
            if is_single_output:
                render_out, extension = self.getSingleOutputExtension(scn, file_format, render_out, hash_position, renderPadding)
            else:
                extension = scn.render.file_extension
        else:
            extension = ""

        writeNodeStr = self.writeNodeStr
        writeNodeInt = self.writeNodeInt
        writeNodeBool = self.writeNodeBool

        fileID.write("<Job>\n")
        if (self._renderer_name=="Cycles"):
            if scn.cycles.device == 'GPU':
                fileID.write("<SubmitterParameter>")
                fileID.write("COCyclesEnableGPU=1~1 GPUrequired=1~1")
                fileID.write("</SubmitterParameter>")
        if (self._renderer_name=="Luxcore"):
            if scn.luxcore.config.device == 'OCL':
                fileID.write("<SubmitterParameter>")
                fileID.write("COCyclesEnableGPU=1~1 GPUrequired=1~1")
                fileID.write("</SubmitterParameter>")
        writeNodeStr(fileID, "rrSubmitterPluginVersion", "%rrVersion%")
        writeNodeStr(fileID, "Software", "Blender")
        writeNodeStr(fileID, "Renderer", self._renderer_name)
        writeNodeStr(fileID, "rendererVersion", self._renderer_version)
        writeNodeStr(fileID, "Version",  "{0}.{1}.{2}".format(v_major, v_minor, v_release))
        writeNodeStr(fileID, "SceneState", scene_state)
        writeNodeBool(fileID, "IsActive", is_active)
        writeNodeStr(fileID, "Scenename", bpy.data.filepath)
        writeNodeBool(fileID, "ImageSingleOutputFile", is_single_output)
        writeNodeInt(fileID, "SeqStart", scn.frame_start)
        writeNodeInt(fileID, "SeqEnd", scn.frame_end)
        writeNodeInt(fileID, "SeqStep", scn.frame_step)
        writeNodeStr(fileID, "ImageDir", os.path.dirname(render_out))
        writeNodeStr(fileID, "Imagefilename", os.path.basename(render_out))
        writeNodeInt(fileID, "ImageFramePadding", renderPadding)
        writeNodeStr(fileID, "ImageExtension", extension)

        writeNodeStr(fileID, "Layer", layer)
        writeNodeStr(fileID, "CustomFrameFormat", file_format)

        out_colorspace = self.get_out_colorspace_settings(scn)
        if out_colorspace:
            writeNodeStr(fileID, "ColorSpace", out_colorspace)
            writeNodeStr(fileID, "ColorSpace_View", scn.view_settings.view_transform)
            writeNodeStr(fileID, "ColorSpaceConfigFile", self.get_ocio_config_file())

        fileID.write("</Job>\n")


    def rrSubmit(self):
        self.report({'DEBUG'}, "Platform: {0}".format(sys.platform))

        fileID = tempfile.NamedTemporaryFile(mode='w', prefix="rrSubmitBlender_", suffix=".xml", delete=False)
        TempFileName = fileID.name
        self.report({'DEBUG'}, "Create temp Submission File: {0}".format(TempFileName))

        fileID.write("<RR_Job_File syntax_version=\"6.0\">\n")
        if not 'DEBUG' in os.environ: 
            fileID.write("<DeleteXML>1</DeleteXML>\n")

        fileID.write("<SubmitterParameter>")
        if self.hasRelativePaths():  # then we cannot use local scene copy
            fileID.write("AllowLocalSceneCopy=1~0")
        fileID.write("</SubmitterParameter>")

        is_multi_scene = len(bpy.data.scenes) > 1
        
        if is_multi_scene:
            for scn in bpy.data.scenes:
                self.writeSceneJobs(scn, fileID, scn.name, scn == bpy.context.scene)
        else:
            self.writeSceneJobs(bpy.context.scene, fileID)

        fileID.write("</RR_Job_File>\n")
        fileID.close()

        RR_ROOT = self.get_RR_Root()
        if RR_ROOT is None:
            self.report({'ERROR'}, "Cannot find RR install folder, please execute rrWorkstationInstaller")
            return False

        self.report({'DEBUG'}, "Found RR_Root:{0}".format(RR_ROOT))

        is_win_os = False
        if sys.platform.lower().startswith("win"):
            submitCMDs = ('{0}\\win__rrSubmitter.bat'.format(RR_ROOT), TempFileName)
            is_win_os = True
        elif sys.platform.lower() == "darwin":
            submitCMDs = ('{0}/bin/mac64/rrSubmitter.app/Contents/MacOS/rrSubmitter'.format(RR_ROOT), TempFileName)
        else:
            submitCMDs = ('{0}/lx__rrSubmitter.sh'.format(RR_ROOT), TempFileName)

        rr_env= os.environ.copy()
        envCount= len(list(rr_env))
        ie=0
        while (ie<envCount):
            envVar= list(rr_env)[ie]
            if envVar.startswith("QT_"):
                del rr_env[envVar]
                envCount= envCount -1
            else:
                ie= ie+1

        try:
            if not os.path.isfile(submitCMDs[0]):
                raise FileNotFoundError
            subprocess.Popen(submitCMDs, close_fds=True, env=rr_env)
        except FileNotFoundError:
            self.report({'ERROR'}, "rrSubmitter not found\n({0})".format(submitCMDs[0]))
            return False
        except subprocess.CalledProcessError:
            self.report({'ERROR'}, "Error while executing rrSubmitter")
            return False

        return True

    def set_renderer_name(self, context):
        pretty_name = context.scene.render.engine.title()
        prefix = "Blender_"
        if pretty_name.startswith(prefix):
            pretty_name = pretty_name[len(prefix):]

        self._renderer_name = pretty_name
        self.report({'INFO'}, "Renderer Info:")
        self.report({'INFO'}, self._renderer_name)
        if (self._renderer_name=="Redshift"):
            import addon_utils
            mod = sys.modules.get("redshift")
            modInfo= addon_utils.module_bl_info(mod)
            versionStr=""
            for v in modInfo["version"]:
                if (len(versionStr)!=0):
                    versionStr= versionStr + "."
                versionStr= versionStr + str(v)        
            self._renderer_version= versionStr
        if (self._renderer_name=="Luxcore"):
            import addon_utils
            mod = sys.modules.get("BlendLuxCore")
            modInfo= addon_utils.module_bl_info(mod)
            versionStr=""
            for v in modInfo["version"]:
                if (len(versionStr)!=0):
                    versionStr= versionStr + "."
                versionStr= versionStr + str(v)        
            self._renderer_version= versionStr

    def execute(self, context):
        if bpy.data.is_dirty:

            # TODO: ask save
            try:
                self.report({'INFO'}, "Saving mainFile...")
                bpy.ops.wm.save_mainfile()
            except RuntimeError:
                self.report({'WARNING'}, "Cannot save scene file")

        self.set_renderer_name(context)
        if self.rrSubmit():
            self.report({'INFO'}, "Submit Launch Successfull")
        else:
            self.report({'ERROR'}, "Submit Scene Failed")

        return{'FINISHED'}




def register():
    bpy.utils.register_class(RoyalRender_Submitter)
    bpy.utils.register_class(OBJECT_OT_SubmitScene)


def unregister():
    bpy.utils.unregister_class(RoyalRender_Submitter)
    bpy.utils.unregister_class(OBJECT_OT_SubmitScene)


if __name__ == "__main__":
    register()
