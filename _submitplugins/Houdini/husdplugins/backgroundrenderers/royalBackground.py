# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy

import os, sys
import logging
import shutil

sharedPath=os.path.abspath(os.path.join(os.path.dirname(__file__), "../../shared"))
sys.path.append(sharedPath)
import royalCommands as rrCmds
logger = rrCmds.getLogger()
#logger.setLevel(logging.INFO)
#rrCmds.setVerboseLevel(4)
import royalDefs as rrDefs


import hou
import husd
from husd.backgroundrenderer import BackgroundRenderer

from hutil.Qt import QtWidgets, QtCore

from husdui.widgets import RenderDelegateComboBox

class OptionsDialog(QtWidgets.QDialog):

    def __init__(self, parent=None, old_options=None):
        super(OptionsDialog, self).__init__(parent)
        self.setWindowTitle("Background Rendering Options")

        delegates = hou.lop.availableRendererNames()
        delegate = ''
        if old_options and 'delegate' in old_options:
            delegate = old_options['delegate']
        output_image = ''
        if old_options and 'output_image' in old_options:
            output_image = old_options['output_image']
        usd_directory = ''
        if old_options and 'usd_directory' in old_options:
            usd_directory = old_options['usd_directory']
        hqueue_server = ''
        if old_options and 'hqueue_server' in old_options:
            hqueue_server = old_options['hqueue_server']
        job_name = ''
        if old_options and 'job_name' in old_options:
            job_name = old_options['job_name']

        vbox = QtWidgets.QVBoxLayout()

        frame = QtWidgets.QGroupBox("Rendering")
        grid = QtWidgets.QGridLayout()
        grid.addWidget(QtWidgets.QLabel("Render Delegate"), 0, 0, 1, 1)
        self._renderDelegateWidget = RenderDelegateComboBox(aov_support_only=True)
        self._renderDelegateWidget.setCurrentIndexByName(delegate)
        grid.addWidget(self._renderDelegateWidget, 0, 1, 1, 2)
        
        grid.addWidget(QtWidgets.QLabel("Required: USD Directory"), 1, 0, 1, 1)
        self._usdDirectoryWidget = QtWidgets.QLineEdit()
        self._usdDirectoryWidget.setText(usd_directory)
        grid.addWidget(self._usdDirectoryWidget, 1, 1, 1, 1)
        browseBtn = QtWidgets.QPushButton("Browse...")
        browseBtn.clicked.connect(self.__chooseUsdDirectory)
        grid.addWidget(browseBtn, 1, 2, 1, 1)
        
        grid.addWidget(QtWidgets.QLabel("Optional: Override Gallery Folder"), 2, 0, 1, 1)
        self._outputImageWidget = QtWidgets.QLineEdit()
        self._outputImageWidget.setText(output_image)
        grid.addWidget(self._outputImageWidget, 2, 1, 1, 1)
        browseBtn = QtWidgets.QPushButton("Browse...")
        browseBtn.clicked.connect(self.__chooseOutputImage)
        grid.addWidget(browseBtn, 2, 2, 1, 1)
        

        frame.setLayout(grid)
        vbox.addWidget(frame)

        hbox = QtWidgets.QHBoxLayout()
        hbox.addStretch()
        okBtn = QtWidgets.QPushButton("OK")
        okBtn.setDefault(True)
        okBtn.clicked.connect(self.accept)
        hbox.addWidget(okBtn)
        cancelBtn = QtWidgets.QPushButton("Cancel")
        cancelBtn.clicked.connect(self.reject)
        hbox.addWidget(cancelBtn)
        vbox.addLayout(hbox)

        self.setLayout(vbox)

    def __chooseOutputImage(self):
        res = QtWidgets.QFileDialog.getExistingDirectory(self,
                                                    "Output Image Folder",
                                                    QtCore.QDir.currentPath())
        if res[0]:
            self._outputImageWidget.setText(res[0])

    def __chooseUsdDirectory(self):
        res = QtWidgets.QFileDialog.getExistingDirectory(self,
                                                         "USD Directory",
                                                         QtCore.QDir.currentPath())
        if res:
            self._usdDirectoryWidget.setText(res)


class royalBackground(BackgroundRenderer):
    # The default __init__ implementation sets up some useful instance variables:
    # self._lopnet_path:
    #     (str) The node path of the LOP network, for example "/stage"
    # self._item_id:
    #     (int) A unique ID number for this render. You can use this to construct
    #     names or identifiers, for example a job name for a render farm manager.

    # You can call the following helper functions:
    #
    # self.updateImagePath(image_path)
    #     Update the snapshot to use the image at the given path.
    #
    # self.updateMetadata(metadata)
    #     Update the snapshot's metadata using the given dict. The keys are mostly
    #     arbitrary, but a few are used by Houdini's UI:
    #     "totalClockTime":
    #         (float) current elapsed time in seconds, the render gallery viewer
    #         displays this in the render stats.
    #     "percentDone":
    #         (float) Percent complete (0-100), also displayed in the render stats.
    #     "peakMemory":
    #         (int) Maximum memory usage of the 

    def pollFrequency(self):
        #logger.debug("pollFrequency")
        # How often (every this number of (floating poitn) seconds) the system
        # should ask call the methods on this object to get updates.
        return 30.0

    def getConfigOptions(self, old_options):
        #logger.debug("getConfigOptions")
        dialog = OptionsDialog(hou.qt.mainWindow(), old_options)
        if dialog.exec_():
            return {
                'delegate': dialog._renderDelegateWidget.currentName(),
                'output_image': dialog._outputImageWidget.text(),
                'usd_directory': dialog._usdDirectoryWidget.text()
            }
        else:
            return None

    def startBackgroundRender(self, usd_filepath, options):
        logger.debug("startBackgroundRenderer")
        self._rrJobID =0
        hipFileName = os.path.splitext(hou.hipFile.basename())[0] 
        #QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.BusyCursor)
        logger.info("start| usd_filepath :{}".format(usd_filepath))
        old_usd_directory, usd_file = os.path.split(usd_filepath)
        usd_subdir = os.path.basename(old_usd_directory)
        usd_subdir = hipFileName + "_" + usd_subdir
        new_usd_directory = options['plugin']['usd_directory']
        logger.info("start| new_usd_directory: {}".format(new_usd_directory))
        logger.info("start| new_usd_directory len: {}".format(len(new_usd_directory)))
        if len(new_usd_directory)>0:
            new_usd_directory= os.path.join(new_usd_directory, usd_subdir)
            usd_filepath = os.path.join(new_usd_directory, usd_file)
            shutil.copytree(old_usd_directory, new_usd_directory)
        else:
            #we have not changed usd_filepath, so use the original value
            pass
            
        imageFileName= hipFileName + "_<IDstr>."
        new_image_path = options['plugin']['output_image']
        if len(new_image_path)==0:
            new_image_path = os.path.dirname(hou.hipFile.path()) 
            new_image_path = os.path.join(new_image_path, "galleries")
            new_image_path = os.path.join(new_image_path, hipFileName+".stage")
        imageFileName = os.path.join(new_image_path, imageFileName)
            
        
        newJob= rrCmds.createJob(usd_filepath, rrDefs.plugin_version_str)
        logger.debug("start| usd scene: {}".format(usd_filepath))
        
        newJob.seqStart= hou.frame()
        newJob.seqEnd= hou.frame()
        newJob.camera= options['viewport']['camera_path']
        newJob.imageWidth= options['viewport']['res_x']
        newJob.imageHeight= options['viewport']['res_y']
        newJob.imageFileName= imageFileName + "#.exr"
        logger.debug("start| imageFileName: {}".format(newJob.imageFileName))
        renderSettings=options['viewport']['rendersettings_path']
        if len(renderSettings)>0:
            newJob.customDataAppend_Str("rrSubmitterParameter",' "AdditionalCommandlineParam=0~1~ -s {}"'.format(renderSettings))   
        newJob.customDataAppend_Str("rrSubmitterParameter",' "OverrideImageWidth=0~{}"'.format(options['viewport']['res_x']))   
        newJob.customDataAppend_Str("rrSubmitterParameter",' "OverrideImageHeight=0~{}"'.format(options['viewport']['res_y']))   
        newJob.customDataAppend_Str("rrSubmitterParameter",' "DisableAllScripts=0~1"') 
        newJob.customDataAppend_Str("rrSubmitterParameter",' "RenderPreviewFirst=0~0"')   
        newJob.customDataAppend_Str("rrSubmitterParameter",' "CustomSCeneName=0~{}"'.format(hipFileName))   
        
        
        renderApp= rrCmds.createRenderApp()
        logger.debug("start| renderer :{}".format(options['plugin']['delegate']))
        if (options['plugin']['delegate']=="arnold"):
            renderApp.name="Arnold-singlefile"
            renderApp.rendererName= "HtoA"
            try:
                import arnold
                renderApp.setVersionBoth(arnold.AiGetVersionString())
            except ImportError:
                pass
        elif (options['plugin']['delegate']=="HdVRayRendererPlugin"):
            renderApp.name="USD_StdA_single"
            renderApp.rendererName= "VRay"
            renderApp.setVersionBoth(hou.applicationVersionString())
        elif (options['plugin']['delegate']=="BRAY_HdKarma"):
            renderApp.name="USD_StdA_single"
            renderApp.setVersionBoth(hou.applicationVersionString())
            renderApp.rendererName= "Karma"
        else:
            renderApp.name="USD_StdA_single"
            renderApp.setVersionBoth(hou.applicationVersionString())
            renderApp.rendererName= options['plugin']['delegate']
        
        newJob.renderApp= renderApp
        rrCmds.addJob(newJob)
        if (not rrCmds.submitJobList()):
            logger.error("Unable to submit jobs!")
            return 

        self._rrJobID= rrCmds.jobsSendID(0)
        jobIDStr= rrCmds.jobsID2Str(self._rrJobID)
        jobIDStr= jobIDStr.replace('{','')
        jobIDStr= jobIDStr.replace('}','') 
        jobIDStr= jobIDStr.replace(' ','') 
        imageFileName= imageFileName.replace("<IDstr>", jobIDStr)
        self._imageFile= imageFileName + str(int(hou.frame())) + ".exr"
        logger.info("Job {} submitted! {}".format(rrCmds.jobsID2Str(self._rrJobID), self._imageFile))
        global rrJob
        import rrJob   #required for rrJob._Status.sFinished. Module is available after we have used rrCmds
        pass

    def isRenderFinished(self):
        #logger.debug("isRenderFinished")
        if (self._rrJobID == 0):
            return True
        jobStatus=  rrCmds.sendrequest_jobStatusInfo(self._rrJobID)
        if (jobStatus.ID==0):
            logger.error("Job {} does not exist any more!".format(rrCmds.jobsID2Str(self._rrJobID)))
            return True
        else:
            metadata = {
                'status': str(jobStatus.statusAsString()),
            }
            logger.debug("job status: {}".format(jobStatus.statusAsString()))
            metadata['totalClockTime'] = jobStatus.infoRenderTimeSum_seconds
            metadata['peakMemory'] = jobStatus.infoClients_maxMemoryUsageMB*1024*1024
            self.updateMetadata(metadata)
            if (jobStatus.status >= rrJob._Status.sFinished):
                logger.debug("Image done: {}".format(self._imageFile))
                self.updateImagePath(self._imageFile)
                return True
            else:
                return False
            
                
        pass

    def mouseClick(self, x, y):
        # Called when the user clicks in a render preview window.
        # x and y are normalized coordinates, so for example x=0.0 means
        # the left edge, x=0.5 means the center, and x=1.0 means the
        # right edge.
        # The usual behavior for mouse clicks is to concentrate rendering
        # in the part of the image where the user clicked.
        pass

    def stopBackgroundRender(self):
        logger.debug("stopBackgroundRender")
        if (self._rrJobID == 0):
            return    
        rrCmds.abortNDisableJob(self._rrJobID)
        pass


# You must include the registration function: this is what Houdini looks for
# when it loads your plugin file

def registerBackgroundRenderers(manager):
    # The first argument is a human-readable label for the render type,
    # the second argument is your background render class
    manager.registerBackgroundRenderer('Royal Render', royalBackground)
