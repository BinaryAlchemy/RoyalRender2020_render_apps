######################################################################
#
# Royal Render Plugin script for Katana
# Author:  Holger Schoenberger, Paolo Acampora
# Last change: %rrVersion%
#
######################################################################

import os
import sys
import errno
import logging
import tempfile
import datetime
import time
from functools import partial
from xml.etree.ElementTree import ElementTree, Element, SubElement

from Katana import FarmAPI, Callbacks, UI4, RenderingAPI, KatanaFile, LayeredMenuAPI
from Katana import NodegraphAPI, NodeDebugOutput
import KatanaInfo

mod_dir = os.path.dirname(__file__)
if mod_dir not in sys.path:
    sys.path.append(mod_dir)
import rrSubmitJob




################ LOGGING ################

logger = logging.getLogger('RR_SUBMIT')
logger.setLevel(logging.DEBUG)

def writeInfo(msg):
    logger = logging.getLogger('RR_SUBMIT')
    logger.info(msg)


def writeError(msg):
    logger = logging.getLogger('RR_SUBMIT')
    logger.error(msg)


def writeWarning(msg):
    logger = logging.getLogger('RR_SUBMIT')
    logger.warning(msg)



def writeDebug(msg):
    logger = logging.getLogger('RR_SUBMIT')
    logger.debug(msg)




#########################################
#Katana

def RR_PopulateCallback(layeredMenu, tab):
    """
    Callback for the layered menu, which adds entries to the given
    C{layeredMenu} based on the available PRMan shaders.

    @type layeredMenu: L{LayeredMenuAPI.LayeredMenu}
    @type tab: C{NodeGraphTab.NodegraphPanel.NodegraphPanel}
    @param layeredMenu: The layered menu to add entries to.
    @param tab: The B{Node Graph} tab where the entry was chosen.
    """
    _ = tab
    layeredMenu.addEntry("rrSubmit", text="rrSubmit", color=(0.35, 0.57, 1.0))

def RR_ActionCallback(value, tab):
    """
    Callback for the layered menu, which creates a PrmanShadingNode node and
    sets its B{nodeType} parameter to the given C{value}, which is the name of
    a PRMan shader as set for the menu entry in L{PopulateCallback()}.

    @type value: C{str}
    @type tab: C{NodeGraphTab.NodegraphPanel.NodegraphPanel}
    @rtype: C{object}
    @param value: An arbitrary object that the menu entry that was chosen
        represents. In our case here, this is the name of a PRMan shader as
        passed to the L{LayeredMenuAPI.LayeredMenu.addEntry()} function in
        L{PopulateCallback()}.
    @param tab: The B{Node Graph} tab where the entry was chosen.
    @return: An arbitrary object. In our case here, we return the created
        PrmanShadingNode node, which is then placed in the B{Node Graph} tab
        because it is a L{NodegraphAPI.Node} instance.
    """
    _ = tab
    if value=="rrSubmit":
        RR_startMultiUI()


def RR_onStartup(**kwargs):
    """Add Menu Options"""
    FarmAPI.AddFarmPopupMenuOption('RR - Submit Render Node', initExport)
    FarmAPI.AddFarmPopupMenuOption('RR - Export archives (e.g. .rib) on this machine and submit their render', partial(initExport, local_export=True))
    FarmAPI.AddFarmPopupMenuOption('RR - Multiple Render', RR_startMultiUI)
    FarmAPI.AddFarmMenuOption('RoyalRender - Multiple Render', RR_startMultiUI)

    layeredMenu = LayeredMenuAPI.LayeredMenu(RR_PopulateCallback, RR_ActionCallback,
                                             'Alt+R', alwaysPopulate=False,
                                             onlyMatchWordStart=False)
    LayeredMenuAPI.RegisterLayeredMenu(layeredMenu, 'RoyalRender')


    FarmAPI.AddFarmSettingString('rr_fileName')
    FarmAPI.AddFarmSettingString('rr_outputFolder', hints={'widget': 'assetIdInput',
                                                        'dirsOnly': 'true',
                                                        'acceptDir': 'true'})

    FarmAPI.AddFarmSettingNumber('rr_useYetiLic', hints={'widget': 'checkBox'})


def get_local_path(farm_settings):
    """

    :param farm_settings: RR custom farm settings
    :return: (fileDir, fileName)
    """
    fileDir = farm_settings['rr_outputFolder']

    if not fileDir:
        UI4.Widgets.MessageBox.Warning('Missing output folder for frames',
                                       'Please set <b>rr_outputFolder</b> path on RenderNode')

        writeDebug("exiting because of unset dir")
        return

    fileName = farm_settings['rr_fileName']
    if fileName == '':
        UI4.Widgets.MessageBox.Warning('Missing output name for frames',
                                       'Please set <b>rr_fileName</b> output on RenderNode')

        writeDebug("exiting because of unset filename")
        return

    return fileDir, fileName


def export_scene_frames(rr_job, render_service):
    """Export scene for standalone renderer (.rib, .ass, etc.). Exports one file per frame"""
    for current_frame in range(rr_job.seqStart, rr_job.seqEnd + 1):
        NodegraphAPI.SetCurrentTime(current_frame)

        out_file = rr_job.sceneName.replace("<FN4>", "{0:04d}".format(current_frame))
        NodeDebugOutput.WriteRenderOutputForRenderMethod(rr_job.render_method,
                                                         NodegraphAPI.GetNode(rr_job.layer),
                                                         render_service, filename=out_file)


def timerInit():
    return datetime.datetime.now()

def timerBreak(timerBefore, where):
    timerAfter= datetime.datetime.now()
    timerAfter= timerAfter-timerBefore
    writeInfo("   "+where+": "+str(timerAfter)+"  h:m:s.ms")
    return datetime.datetime.now()
 


def initExport(local_export=False):
    """Initialize export. local_export means that you export the .ass files on your machine,
    farm sends the .katana scene to the render farm.

    :param local_export: bool
    :return:
    """
    timerBefore= timerInit()
    writeInfo("RR Katana Submission plugin, %rrVersion%  - {0}".format("local export" if local_export else "farm"))
    nodeRenderSettings= FarmAPI.GetSortedDependencies()[-1]
    current_filepath = FarmAPI.GetKatanaFileName()
    timerBefore=timerBreak(timerBefore, "GetKatanaFileName")
    
    if KatanaFile.IsFileDirty():
        result = UI4.Widgets.MessageBox.Warning('Unsaved Changes', 'Save your file', acceptText='Save',
                                                cancelText='Abort')
        if result == 0:  # Save
            KatanaFile.Save(current_filepath)
        else:  # Cancel
            return False
    timerBefore=timerBreak(timerBefore, "IsFileDirty")
    
    if not FarmAPI.IsSceneValid(FarmAPI.NODES_SELECTED):
        warning_msg = FarmAPI.GetWarningMessages()
        error_msg = FarmAPI.GetErrorMessages()

        detailed_text = "\n".join(error_msg)
        detailed_text += "\n"
        detailed_text = "\n".join(warning_msg)

        result = UI4.Widgets.MessageBox.Warning('Scene might be compromised',
                                                'Some validity checks have failed, do you want to submit anyway?',
                                                acceptText='Submit anyway',
                                                cancelText='Abort',
                                                detailedText=detailed_text)
        if result > 0:
            writeError("Abort due to failed Validity Check")
            return False
    timerBefore=timerBreak(timerBefore, "ValidScene")
    
    jobList=[]
    jobList.append( rrSubmitJob.createSubmitJob(nodeRenderSettings, local_export))
    rrSubmitJob.submitJobList(jobList)
    

def RR_startMultiUI():

    import RR_MultiRender as multi
    RR_startMultipleRendersDialog = multi.RR_StartMultipleRendersDialog()
    RR_startMultipleRendersDialog.show()



if __name__.startswith("__plugins"):  # example: __plugins3__.rrSubmit_Katana_2+
    Callbacks.addCallback(Callbacks.Type.onStartup, RR_onStartup)
