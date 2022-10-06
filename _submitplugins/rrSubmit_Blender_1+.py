# -*- coding: cp1252 -*-
######################################################################
#
# Royal Render Plugin script for Blender 
# Authors, based on:    Felix Bucella, Patrik Gleich
# Authors:              Friedrich Wessel (Callisto FX GmbH)
# Authors, updated by:  Paolo Acampora, Holger Schoenberger (Binary Alchemy)
# Last change: %rrVersion%
#
# rrInstall_Copy:     \*\scripts\startup\
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

        # We submit the current scene. In the future we can implement multi scene submission as RR layers
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
        extension = "." + rendertarget.lower()

        if extension.startswith(".avi"):
            extension = ".avi"
            rendertarget = rendertarget.replace("_", "")

        extension = extension.replace(".tiff", ".tif")
        extension = extension.replace(".jpeg", ".jpg")

        extension = extension.replace(".quicktime", ".mov")
        extension = extension.replace(".flash", ".flv")
        extension = extension.replace(".mpeg1", ".mpg")
        extension = extension.replace(".mpeg2", ".dvd")
        extension = extension.replace(".mpeg4", ".mp4")

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

    def writeSceneInfo(self, scn, fileID, scene_state="", is_active=True):
        img_type = scn.render.image_settings.file_format
        rendertarget = img_type.replace("OPEN_", "")
        if rendertarget == "FFMPEG":
            ImageSingleOutputFile = True
            rendertarget = scn.render.ffmpeg.format
        elif rendertarget == "JPEG2000":
            ImageSingleOutputFile = False
            rendertarget = scn.render.image_settings.jpeg2k_codec
        else:
            ImageSingleOutputFile = False
            rendertarget = rendertarget.replace("TARGA_RAW", "RAWTGA")
            rendertarget = rendertarget.replace("TARGA", "TGA")

        renderOut = bpy.path.abspath(scn.render.filepath)

        try:
            hash_position = renderOut.rindex('#')
            renderPadding = hash_position - next(i for i in range(hash_position, 0, -1) if renderOut[i] != '#')
        except ValueError:
            hash_position = -1
            renderPadding = 4

        extension = ""

        if scn.render.use_file_extension:
            if ImageSingleOutputFile:
                renderOut, extension = self.getSingleOutputExtension(scn, rendertarget, renderOut, hash_position, renderPadding)
            else:
                extension = scn.render.file_extension

        v_major, v_minor, _ = bpy.app.version
        writeNodeStr = self.writeNodeStr
        writeNodeInt = self.writeNodeInt
        writeNodeBool = self.writeNodeBool

        fileID.write("<Job>\n")

        if scn.cycles.device == 'GPU':
            fileID.write("<SubmitterParameter>")
            fileID.write("COCyclesEnableGPU=1~1 GPUrequired=1~1")
            fileID.write("</SubmitterParameter>")
        writeNodeStr(fileID, "rrSubmitterPluginVersion", "%rrVersion%")
        writeNodeStr(fileID, "Software", "Blender")
        writeNodeStr(fileID, "Renderer", self._renderer_name)
        writeNodeStr(fileID, "rendererVersion", self._renderer_version)
        writeNodeStr(fileID, "Version",  "{0}.{1}".format(v_major, v_minor))
        writeNodeStr(fileID, "SceneState", scene_state)
        writeNodeBool(fileID, "IsActive", is_active)
        writeNodeStr(fileID, "SceneName", bpy.data.filepath)
        writeNodeBool(fileID, "ImageSingleOutputFile", ImageSingleOutputFile)
        writeNodeInt(fileID, "SeqStart", scn.frame_start)
        writeNodeInt(fileID, "SeqEnd", scn.frame_end)
        writeNodeInt(fileID, "SeqStep", scn.frame_step)
        writeNodeStr(fileID, "ImageDir", os.path.dirname(renderOut))
        writeNodeStr(fileID, "ImageFilename", os.path.basename(renderOut))
        writeNodeInt(fileID, "ImageFramePadding", renderPadding)
        writeNodeStr(fileID, "ImageExtension", extension)
        if 'MULTILAYER' in rendertarget:
            rendertarget = "MULTILAYER"
        elif v_major == 2 and v_minor < 80:
            writeNodeStr(fileID, "Layer", scn.render.layers[0].name)
        if rendertarget in ("TGA", "RAWTGA", "JPEG", "IRIS", "IRIZ", "AVIRAW",
                            "AVIJPEG", "PNG", "BMP", "HDR", "TIFF", "EXR", "MULTILAYER",
                            "MPEG", "FRAMESERVER", "CINEON", "DPX", "DDS", "JP2"):
            writeNodeStr(fileID, "CustomFrameFormat", rendertarget)

        fileID.write("</Job>\n")


    def rrSubmit(self):
        self.report({'DEBUG'}, "Platform: {0}".format(sys.platform))

        fileID = tempfile.NamedTemporaryFile(mode='w', prefix="rrSubmitBlender_", suffix=".xml", delete=False)
        TempFileName = fileID.name
        self.report({'DEBUG'}, "Create temp Submission File: {0}".format(TempFileName))

        fileID.write("<RR_Job_File syntax_version=\"6.0\">\n")
        fileID.write("<DeleteXML>1</DeleteXML>\n")

        fileID.write("<SubmitterParameter>")
        if self.hasRelativePaths():  # then we cannot use local scene copy
            fileID.write("AllowLocalSceneCopy=1~0")
        fileID.write("</SubmitterParameter>")

        is_multi_scene = len(bpy.data.scenes) > 1
        self.writeSceneInfo(bpy.context.scene, fileID, is_active=not is_multi_scene)
        if is_multi_scene:
            for scn in bpy.data.scenes:
                self.writeSceneInfo(scn, fileID, scn.name, scn == bpy.context.scene)

        fileID.write("</RR_Job_File>\n")
        fileID.close()

        RR_ROOT = self.get_RR_Root()
        if RR_ROOT is None:
            self.report({'ERROR'}, "Cannot find RR install folder, please execute rrWorkstationInstaller")
            return False

        self.report({'DEBUG'}, "Found RR_Root:{0}".format(RR_ROOT))

        is_win_os = False
        if sys.platform.lower().startswith("win"):
            submitCMDs = ('{0}\\win__rrSubmitter.bat'.format(RR_ROOT),
                          TempFileName)
            is_win_os = True
        elif sys.platform.lower() == "darwin":
            submitCMDs = ('{0}/bin/mac64/rrSubmitter.app/Contents/MacOS/rrSubmitter'.format(RR_ROOT), TempFileName)
        else:
            submitCMDs = ('{0}/lx__rrSubmitter.sh'.format(RR_ROOT), TempFileName)

        try:
            if not os.path.isfile(submitCMDs[0]):
                raise FileNotFoundError
            subprocess.Popen(submitCMDs, close_fds=True)
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

    def execute(self, context):
        if bpy.data.is_dirty:
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
