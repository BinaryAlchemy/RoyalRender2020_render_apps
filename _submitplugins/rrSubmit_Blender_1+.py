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
# #mac:   rrInstall_Copy:     \Contents\Resources\*\scripts\startup\
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


class OutputEntry:

    def __init__(self, filepath, file_format, socket_type, name):
        self.filepath = filepath
        self.file_format = file_format
        self.socket_type = socket_type
        self.name = str(name).lower()


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
        if scn.render.save_output:
            col.label(text="ImageType: " + img_type)
            col.label(text="ImageName: " + os.path.basename(renderOut))
            col.label(text="RenderDir: " + os.path.dirname(renderOut))
        else:
            col.label(text="ImageType: Compositor Output")

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
        
        default_cfg_file = os.path.join("<rrBaseAppPath><IsMac /Resources>", "<IsMac <rrJobVerMajorMinor>?<rrExeVer>>", "datafiles", "colormanagement", "config.ocio") #<IsMac must not be a seperate flag on its own (otherwise double // on windows)
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

    def getCompOutputNodes(self, scn):
        if scn.render.use_compositing and scn.use_nodes:
            try:
                node_container = scn.compositing_node_group
            except AttributeError:
                node_container = scn.node_tree

            if node_container:
                for node in node_container.nodes:
                    if node.type != 'OUTPUT_FILE':
                        continue
                    if node.mute:
                        continue

                    yield node

    def getCompFileOut(self, scn):
        for node in self.getCompOutputNodes(scn):
            try:
                base_path = node.directory  # blender 5.0
            except AttributeError:
                base_path = node.base_path

            try:
                base_filename = node.file_name  # blender 5.0
                file_items = node.file_output_items
            except AttributeError:
                base_filename = ""
                file_items = node.file_slots

            if node.format.file_format == 'OPEN_EXR_MULTILAYER':
                if node.label.startswith('File Output'):
                    out_name = next(
                        (s.name for s in file_items if 'beauty' in s.name.lower()),
                        ((s.name for s in file_items if 'diffuse' in s.name.lower()),
                         ((s.name for s in file_items if s.socket_type == 'RGBA'), node.label)
                        ))
                else:
                    out_name = node.label

                full_path = os.path.join(base_path, base_filename).replace("{node_name}", node.name)
                yield OutputEntry(full_path, node.format.file_format, 'RGBA', out_name)
                continue

            for i, out_slot in enumerate(file_items):
                if not node.inputs[i].links:
                    continue

                try:
                    override_format = out_slot.override_node_format
                except AttributeError:
                    override_format = not out_slot.use_node_format

                out_format = out_slot.format.file_format if override_format else node.format.file_format

                out_filename = base_filename
                try:
                    out_filename += out_slot.name
                except AttributeError:
                    out_filename += out_slot.path

                full_path = os.path.join(base_path, out_filename).replace("{node_name}", node.name)
                yield OutputEntry(full_path, out_format, out_slot.socket_type, out_slot.name)

    def writeCompOutputAsChannels(self, fileID, comp_outputs):
        if not comp_outputs:
            return

        # create tmp scene to take advantage of Scene.render.file_extension
        tmp_resolve = bpy.data.scenes.new(f'_rr_tmp_resolve_DELETE_THIS_')

        for comp_output in comp_outputs:
            tmp_resolve.render.image_settings.file_format = comp_output.file_format.replace('_MULTILAYER', "")
            self.writeNodeStr(fileID, "ChannelFilename", comp_output.filepath)
            self.writeNodeStr(fileID, "ChannelExtension", tmp_resolve.render.file_extension)

        bpy.data.scenes.remove(tmp_resolve)

    def writeSceneJobs(self, scn, fileID, scene_state="", is_active=True):
        try:
            layers = scn.view_layers
        except AttributeError:
            self.writeLayerJob(scn, fileID, scene_state, is_active=is_active)
        else:
            per_layer_active=True and is_active
            file_format = scn.render.image_settings.file_format
            if (file_format=='OPEN_EXR_MULTILAYER' and (len(layers)>1) ):
                per_layer_active= False
                self.writeLayerJob(scn, fileID, scene_state, "** All **", is_active=is_active)
            for layer in layers:
                self.writeLayerJob(scn, fileID, scene_state, layer.name, is_active=per_layer_active and layer == bpy.context.view_layer)
                
    def writeFileOutNodes(self, fileID, scn):
        # Not used anymore: we switched to writeCompOutputAsChannels() which handles list of OutputEntry
        if not scn.render.use_compositing:
            return
        if not scn.use_nodes:
            return

        out_nodes = []
        try:
            node_container = scn.compositing_node_group
        except AttributeError:
            node_container = scn.node_tree

        if not node_container:
            return

        for node in node_container.nodes:
            if node.type != 'OUTPUT_FILE':
                continue
            if node.mute:
                continue
            if node.format.file_format == 'OPEN_EXR_MULTILAYER':
                # MULTILAYER EXR is not saved for some reason in 4.3
                # TODO: check 4.4
                self.report({'WARNING'}, f"Node {node.name} saves OPEN_EXR_MULTILAYER and will be skipped")
                continue
            out_nodes.append(node)

        if not out_nodes:
            return

        # create tmp scene to take advantage of Scene.render.file_extension
        tmp_resolve = bpy.data.scenes.new(f'_rr_tmp_resolve_')

        for node in out_nodes:
            try:
                base_path = node.directory  # blender 5.0
            except AttributeError:
                base_path = node.base_path

            tmp_resolve.render.image_settings.file_format = node.format.file_format
            node_extension = tmp_resolve.render.file_extension

            try:
                base_filename = node.file_name  # blender 5.0
                file_items = node.file_output_items
            except AttributeError:
                base_filename = ""
                file_items = node.file_slots
            for i, out_slot in enumerate(file_items):
                if not node.inputs[i].links:
                    continue

                try:
                    override_format = out_slot.override_node_format
                except AttributeError:
                    override_format = not out_slot.use_node_format

                if override_format:
                    tmp_resolve.render.image_settings.file_format = out_slot.format.file_format
                    slot_extension = tmp_resolve.render.file_extension
                else:
                    slot_extension = node_extension

                try:
                    out_tail = out_slot.name
                except AttributeError:
                    out_tail = out_slot.path
                out_name = base_filename + out_tail
                self.writeNodeStr(fileID, "ChannelFilename", os.path.join(base_path, out_name))
                self.writeNodeStr(fileID, "ChannelExtension", slot_extension)

        bpy.data.scenes.remove(tmp_resolve)

    @staticmethod
    def get_path_templates(scn):
        """Replace render tokens in output path"""
        blender_dir, blender_file = os.path.split(bpy.data.filepath)
        res_scale = scn.render.resolution_percentage / 100

        # FIXME: Could have used <Scene> and <SceneFolder>, but that doesn't seem to work for channels
        return dict(
            blend_name=os.path.splitext(blender_file)[0],
            blend_dir=bpy.path.abspath(blender_dir),
            scene_name=scn.name,
            camera_name="<Camera>",
            fps=scn.render.fps * scn.render.fps_base,
            resolution_x=int(scn.render.resolution_x * res_scale),
            resolution_y=int(scn.render.resolution_y * res_scale),
            )
    @staticmethod
    def replace_padding_specifier(in_str, max_tries=10):
        """Replaces # padding with python string formatter, e.g ':###.#' becomes ':05.1f'"""
        count = 0
        while "#}" in in_str:
            count += 1
            if count > max_tries:
                break
            spec_end = in_str.rindex("#}") + 1
            spec_start = in_str.rindex(":", 0, spec_end) + 1
            spec = in_str[spec_start : spec_end]
            try:
                fnum, ffloat = spec.split(".", 1)
                int_digits = len(fnum)
                float_digits = len(ffloat)
                in_str = f"{in_str[:spec_start]}0{int_digits + float_digits + 1}.{float_digits}f{in_str[spec_end:]}"
            except ValueError:
                in_str = f"{in_str[:spec_start]}0{len(spec)}f{in_str[spec_end:]}"

        return in_str

    def writeLayerJob(self, scn, fileID, scene_state="", layer="", is_active=True):
        v_major, v_minor, v_release = bpy.app.version
        blender_version= "{0}.{1}.{2}".format(v_major, v_minor, v_release)
        blender_appName="Blender"
        
        blender_path = bpy.app.binary_path
        if (blender_path.find("Octane")>0 or blender_path.find("octane")>0):
            blender_version=self._renderer_version
            blender_appName="OctaneBlender"

        comp_outputs = list(self.getCompFileOut(scn))

        try:
            use_scene_output = scn.render.save_output
        except AttributeError:  # always using scene output before Blender 5.0
            use_scene_output = True

        job_out = OutputEntry(bpy.path.abspath(scn.render.filepath), scn.render.image_settings.file_format, None, "")
        extension = ""
        if use_scene_output:
            # file_format and file_codec are used in the render script
            is_single_output = job_out.file_format == 'FFMPEG' or job_out.file_format.startswith('AVI_')

            if scn.render.use_file_extension:
                extension = scn.render.file_extension
            # TODO: else check for extension in render_out, e.g. imagename_####.exr
        else:
            if not comp_outputs:
                self.report({'ERROR'}, "'Output' checkbox is disabled, but no 'File Output' nodes found, please check the Compositor")
                fileID.close()
                raise Exception("Unable to find compositor output")

            is_single_output = False  #  no video output from compositor
            # Render plugin doesn't change compositor output at present
            fileID.write("<SubmitterParameter>")
            fileID.write("AllowImageNameChange=0")
            fileID.write("</SubmitterParameter>")
            fileID.write("<SubmitterParameter>")
            fileID.write("AllowImageDirChange=0")
            fileID.write("</SubmitterParameter>")

            # Look for best main output in the compositor
            for i, comp_output in enumerate(comp_outputs):
                self.report({'DEBUG'}, f"--------- {comp_output.name}: {comp_output.filepath}")
                if 'beauty' in comp_output.name:
                    self.report({'DEBUG'}, f"Using {comp_output.name} as job output")
                    break
            else:
                for i, comp_output in enumerate(comp_outputs):
                    if 'diffuse' in comp_output.name:
                        self.report({'DEBUG'}, f"Using {comp_output.name} as job output")
                        break
                    if 'image' in comp_output.name:
                        self.report({'DEBUG'}, f"Using {comp_output.name} as job output")
                        break
                else:
                    for i, comp_output in enumerate(comp_outputs):
                        if 'albedo' in comp_output.name:
                            self.report({'DEBUG'}, f"Using {comp_output.name} as job output")
                            break
                        if 'direct' in comp_output.name:
                            self.report({'DEBUG'}, f"Using {comp_output.name} as job output")
                            break
                    else:
                        for i, comp_output in enumerate(comp_outputs):
                            if comp_output.socket_type == 'MULTI':
                                self.report({'WARNING'}, f"No 'beauty' or 'diffuse' Compositor Output found, using {comp_output.name} as job output")
                                break
                        else:
                            for i, comp_output in enumerate(comp_outputs):
                                if comp_output.socket_type == 'RGBA':
                                    self.report({'WARNING'}, f"No 'beauty' or 'diffuse' Compositor Output found, using {comp_output.name} as job output")
                                    break
                            else:
                                self.report({'WARNING'}, f"No RGBA Compositor Output sockets found, using {comp_outputs[i].name} as job output")

            job_out = comp_outputs.pop(i)

            tmp_resolve = bpy.data.scenes.new('_rr_tmp_resolve_DELETE_THIS_')
            tmp_resolve.render.image_settings.file_format = job_out.file_format.replace('_MULTILAYER', "")
            extension = tmp_resolve.render.file_extension

            bpy.data.scenes.remove(tmp_resolve)

        try:
            hash_position = job_out.filepath.rindex('#')
            renderPadding = hash_position - next(i for i in range(hash_position, 0, -1) if job_out.filepath[i] != '#')
        except ValueError:
            hash_position = -1
            renderPadding = 4
            
        if is_single_output:
            job_out.filepath, extension = self.getSingleOutputExtension(scn, job_out.file_format, job_out.filepath, hash_position, renderPadding)

        # cmd_frame_format is different in blender 2.79 commandline -F
        if v_major < 3 and v_minor < 80:
            job_out.file_format = job_out.file_format.replace("OPEN_", "")
            job_out.file_format = job_out.file_format.replace("TARGA_RAW", "RAWTGA")
            job_out.file_format = job_out.file_format.replace("TARGA", "TGA")

        if job_out.file_format == "JPEG2000":
            job_out.file_format = scn.render.image_settings.jpeg2k_codec

        writeNodeStr = self.writeNodeStr
        writeNodeInt = self.writeNodeInt
        writeNodeBool = self.writeNodeBool

        path_templates = self.get_path_templates(scn)
        job_out.filepath = self.replace_padding_specifier(job_out.filepath, max_tries=len(path_templates)).format(**path_templates)
        for comp_output in comp_outputs:
            self.replace_padding_specifier(comp_output.filepath, max_tries=len(path_templates)).format(**path_templates)

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
        writeNodeStr(fileID, "Software", blender_appName)
        writeNodeStr(fileID, "Renderer", self._renderer_name)
        writeNodeStr(fileID, "rendererVersion", self._renderer_version)
        writeNodeStr(fileID, "Version",  blender_version)
        writeNodeStr(fileID, "SceneState", scene_state)
        writeNodeStr(fileID, "Camera", scn.camera.name)
        writeNodeBool(fileID, "IsActive", is_active)
        writeNodeStr(fileID, "Scenename", bpy.data.filepath)
        writeNodeBool(fileID, "ImageSingleOutputFile", is_single_output)
        writeNodeInt(fileID, "SeqStart", scn.frame_start)
        writeNodeInt(fileID, "SeqEnd", scn.frame_end)
        writeNodeInt(fileID, "SeqStep", scn.frame_step)
        writeNodeStr(fileID, "ImageDir", os.path.dirname(job_out.filepath))
        writeNodeStr(fileID, "Imagefilename", os.path.basename(job_out.filepath))
        writeNodeInt(fileID, "ImageFramePadding", renderPadding)
        writeNodeStr(fileID, "ImageExtension", extension)

        self.writeCompOutputAsChannels(fileID, comp_outputs)

        writeNodeStr(fileID, "Layer", layer)
        writeNodeStr(fileID, "CustomFrameFormat", job_out.file_format)

        out_colorspace = self.get_out_colorspace_settings(scn)
        if out_colorspace:
            writeNodeStr(fileID, "ColorSpace", out_colorspace)
            writeNodeStr(fileID, "ColorSpace_View", scn.view_settings.view_transform)
            writeNodeStr(fileID, "ColorSpaceConfigFile", self.get_ocio_config_file())

        fileID.write("</Job>\n")

    def cleanup_tmp_scenes(self):
        for scene in reversed(bpy.data.scenes):
            if scene.name.startswith('_rr_tmp_resolve'):
                if not scene.objects:
                    self.report({'INFO'}, f"Deleting utility scene {scene.name} from previous submission")
                    bpy.data.scenes.remove(scene)
                else:
                    self.report({'WARNING'}, f"Not deleted utility scene {scene.name} seems to contain objects. Please check and delete the scene")

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

        self.cleanup_tmp_scenes()

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

        if sys.platform.lower().startswith("win"):
            submitCMDs = ('{0}\\win__rrSubmitter.bat'.format(RR_ROOT), TempFileName)

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
        if (self._renderer_name=="Octane"):
            import addon_utils
            mod = sys.modules.get("octane")
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
