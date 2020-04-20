# -*- coding: cp1252 -*-
######################################################################
#
# Royal Render FileQuest script for Maya
# Author:  Royal Render, Paolo Acampora
# Last change: %rrVersion%
# Copyright (c)  Holger Schoenberger - Binary Alchemy

######################################################################


import logging
import os
import rrFilePigeon
import sys
import tempfile

import maya.cmds as cmds
import maya.api.OpenMaya as om


# FileQuest class
class rrQuest(object):
    """FileQuest class for Autodesk Maya

    External files used in a maya scene are collected and sent to rrFilePigeon to be transferred
    Changes can be saved into the newly copied maya files

    The following node types are currently looked for:

        file textures (kFileTexture)
        maya scenes (kReference)
    """

    def __init__(self, source, save_changes):
        """
        :param source: Source directory from which to take files
        :param save_changes: if true, saves the new path into the copy of the scene
        """
        self._collecting_ = True  # store maya files referenced in current scene, to edit and save later
        self._to_remap_ = set()  # top level reference nodes to remap after all the other node types
        self._to_open_ = set()  # non top level scenes to open, edit and save after the current

        self.source = source
        self.save_changes = save_changes

    def copy_textures(self):
        """Copy the files referenced in file texture nodes to a path relative to the destination directory.

        If "Save Changes" is active, only non referenced nodes will be handled, and referenced textures
        will be processed later when opening their maya scene.

        :return: None
        """
        iter_nodes = om.MItDependencyNodes(om.MFn.kFileTexture)

        while not iter_nodes.isDone():
            dep_node = om.MFnDependencyNode(iter_nodes.thisNode())
            node_name = dep_node.absoluteName()

            if self.save_changes:
                # referenced nodes will be dealt with in their own scenes
                if cmds.referenceQuery(node_name, isNodeReferenced=True):
                    ref_path = cmds.referenceQuery(node_name, filename=True)
                    logging.debug("Skipping {0}, referenced by {1}".format(node_name, ref_path))
                    if self._collecting_:  # we collect only in the root scene
                        self._to_open_.add(ref_path)
                    iter_nodes.next()
                    continue

            ftn = dep_node.findPlug("fileTextureName", False)  # wantNetworkedPlug=False

            tex_path = ftn.asString()
            dst_path = rrFilePigeon.copy_file(tex_path, self.source)

            assert dst_path

            if self.save_changes:
                logging.info('{0}: "{1}" remapped to \n'
                             '             "{2}"'.format(node_name, tex_path, dst_path))
                ftn.setString(dst_path)

            iter_nodes.next()

    def copy_refs(self):
        """Copy the referenced maya scenes to a path relative to the destination directory.

        If "Save Changes" is active, only top-level references will be handled,
        multi-level references will be opened separately

        :return: None
        """
        iter_nodes = om.MItDependencyNodes(om.MFn.kReference)

        while not iter_nodes.isDone():
            dep_node = om.MFnDependencyNode(iter_nodes.thisNode())
            node_name = dep_node.absoluteName()

            try:
                ref_path = cmds.referenceQuery(node_name, filename=True)
            except RuntimeError:
                logging.debug("No file attribute for {0}".format(node_name))  # usually :sharedreference node
                iter_nodes.next()
                continue

            if self.save_changes:
                if cmds.referenceQuery(node_name, isNodeReferenced=True):  # non-top reference
                    parent_ref_path = cmds.referenceQuery(node_name, filename=True, parent=True)
                    logging.debug("Skipping {0}, referenced by {1}".format(node_name, parent_ref_path))
                    if self._collecting_:  # we collect only in the root scene
                        self._to_open_.add(ref_path)

                    # skip non top references, they'll be dealt in their parent scene
                    iter_nodes.next()
                    continue

                self._to_remap_.add(node_name)  # remap later
            else:  # if we don't save the new paths, we'll just copy any referenced scene
                rrFilePigeon.copy_file(ref_path, self.source)

            iter_nodes.next()

    def do_reference_remap(self):
        """Remap collected references to the destination path and clear the set.
        IMPORTANT: this function must be called after all other node types have been taken care of,
                   or the original file paths will be scrambled to begin with

        :return: None
        """
        for node_name in self._to_remap_:
            # build the same directory structure in destination path
            ref_path = cmds.referenceQuery(node_name, filename=True)
            dst_path = rrFilePigeon.get_remote_path(ref_path, self.source)

            logging.debug('    {0}: "{1}" remapped to \n'
                          '                 "{2}"'.format(node_name, ref_path, dst_path))

            cmds.file(dst_path, loadReference=node_name, loadReferenceDepth="none")

            if ref_path not in self._to_open_:
                rrFilePigeon.copy_file(ref_path, self.source)

        self._to_remap_.clear()

    def open_scene(self, scene_path):
        """Open Maya scene at given path, find and copy the external files.

        If self.save_changes is True, the scene will be saved to self.destination with its new paths.
        If self._collecting_ is True, store paths and nodes to process in a second step

        :param scene_path: path to a maya scene file
        :return: None
        """
        if not os.path.isfile(scene_path):
            raise(Exception("Path {0}\nnot found".format(scene_path)))

        logging.info("opening {0}".format(scene_path))
        cmds.file(scene_path, force=True, open=True)

        # Collect and copy files used by scene nodes
        self.copy_textures()
        self.copy_refs()

        # build the same directory structure in destination path
        #dst_path = os.path.join(self.destination, os.path.relpath(scene_path, self.source))

        if self.save_changes:
            self.do_reference_remap()  # This MUST be called after all nodes have been taken care of

            _, ext = os.path.splitext(scene_path)
            tmp_scene = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            tmp_scene.close()

            cmds.file(rename=tmp_scene.name)
            logging.debug('saving "{0}" to "{1}"'.format(scene_path, tmp_scene.name))
            cmds.file(save=True, type=str(cmds.file(query=True, type=True)[0]))
            rrFilePigeon.copy_file(tmp_scene.name, self.source, orig_path=scene_path)
            os.unlink(tmp_scene.name)
        else:
            rrFilePigeon.copy_file(scene_path, self.source)

    def open_references(self):
        """Stops collecting Maya scenes and open the ones stored so far to edit and save their filepaths

        :return:
        """
        self._collecting_ = False
        logging.debug("Now process referenced scenes if any")
        for file_name in self._to_open_:
            self.open_scene(file_name)


if __name__ == '__main__':
    # Parse args, set logger and execute
    import argparse
    import maya.standalone as std

    parser = argparse.ArgumentParser(description="==== Maya Files Sync ====")
    parser.add_argument('SceneFileName', help='maya scene file')
    parser.add_argument('Database', help='maya project')
    parser.add_argument("-jid", help='job ID')

    parser.add_argument('--save-changes', help='save path changes in copy', default=False, action='store_true')
    parser.add_argument('--log', help='log level: critical, error, warning, info, debug', default='info')

    args = parser.parse_args()
    std.initialize(name='python')

    # Setup logger
    log_level = getattr(logging, args.log.upper())

    logger = logging.getLogger()
    logger.setLevel(log_level)

    if log_level < 20:
        log_format = logging.Formatter("%(asctime)s: %(levelname)s - %(message)s")
    else:
        log_format = logging.Formatter("%(levelname)s - %(message)s")

    if logger.handlers:
        handler = logger.handlers[0]
    else:
        handler = logging.StreamHandler()

    handler.setFormatter(log_format)
    handler.setLevel(log_level)
    handler.stream = sys.stdout  # we log the stdout in RR apps
    logger.addHandler(handler)

    if log_level < 20:
        for k, v in vars(args).items():
            logging.debug("{0}: {1}".format(k, v))

    #
    # create a FileQuest helper to copy the scene and used assets
    #
    filequest = rrQuest(args.Database, args.save_changes)

    # copy workspace file
    wrkspace_path = os.path.join(args.Database, "workspace.mel")
    if os.path.isfile(wrkspace_path):
        rrFilePigeon.copy_file(wrkspace_path, args.Database)

    # open and copy the scene
    filequest.open_scene(args.SceneFileName)
    logging.debug("Process referenced scenes")
    if args.save_changes:  # we will have to save changes in referenced scenes as well
        filequest.open_references()
