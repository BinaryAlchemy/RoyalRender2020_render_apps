"""
NAME: RR Start Multiple Renders...
ICON: Icons/renderMode16.png

Starts multiple Preview Renders or Live Renders based on iterating over Render
nodes, values of global Graph State Variables, and frame ranges.
"""


from collections import OrderedDict
import itertools
import logging
import os
import re
import textwrap
import sys

mod_dir = os.path.dirname(__file__)
if mod_dir not in sys.path:
    sys.path.append(mod_dir)
import rrSubmitJob


from PyQt5 import (
    QtCore,
    QtGui,
    QtWidgets,
)

from Katana import (
    FarmAPI,
    KatanaPrefs as Prefs,
    NodegraphAPI,
    PrefNames,
    RenderManager,
    KatanaFile,
    UI4,
)

logger = logging.getLogger('RR_SUBMIT')
logger.setLevel(logging.INFO)

def writeInfo(msg):
    logger = logging.getLogger('RR_SUBMIT')
    logger.info(msg)


def writeError(msg):
    logger = logging.getLogger('RR_SUBMIT')
    logger.error(msg)


def writeWarning(msg):
    logger = logging.getLogger('RR_SUBMIT')
    logger.warning(msg)



# Class Definitions -----------------------------------------------------------

class RR_PanelWidget(QtWidgets.QFrame):
    """
    Class implementing a frame with a title and a list widget listing a number
    of entries that can be individually turned on and off using checkboxes.
    """

    # Initializer -------------------------------------------------------------

    def __init__(self, title, entries, parent=None):
        """
        Initializes an instance of the class.

        @type title: C{str}
        @type entries: C{list} of C{str}
        @type parent: C{QtWidgets.QWidget} or C{None}
        @param title: The text to appear in a label at the top of the panel
            widget. Will be combined with the number of the given C{entries} in
            parentheses, e.g. B{myTitle (42)}.
        @param entries: The list of entries to appear in the panel widget.
        @param parent: The parent widget to use for this panel widget.
        """
        QtWidgets.QFrame.__init__(self, parent)

        # Initialize instance variables
        self.__title = title
        self.__checkeStateChangeCallback = None
        self.__removeButtonCallback = None

        # Create a label for the panel widget's title
        self.__titleLabel = QtWidgets.QLabel('<b>%s</b> (%d)' % (self.__title, len(entries)))

        # Store number of items and number of currently selected items.
        # Useful for self.__allCheckBox
        self.__totalNumberOfItems = len(entries)
        self.__numberOfItemsThatAreChecked = len(entries)

        # Set up a parent checkbox for group selection/desection
        # If no children, the box is deactivated
        if entries:
            self.__allCheckBox = QtWidgets.QCheckBox('All')
            self.__allCheckBox.setCheckState(QtCore.Qt.Checked)
        else:
            self.__allCheckBox = QtWidgets.QCheckBox('None')
            self.__allCheckBox.setCheckState(QtCore.Qt.Unchecked)
            self.__allCheckBox.setEnabled(False)

        # Bool to prevent loops between the __allCheckBox and it's
        # children calling each other. Somewhat mutex-like.
        self.__updatingFromAllCheckBox = False

        # Create a list widget for listing the given list of entries
        self.__listWidget = QtWidgets.QListWidget(self)
        self.__listWidget.setObjectName('listWidget')
        self.__listWidget.setAlternatingRowColors(True)

        for entry in entries:
            item = QtWidgets.QListWidgetItem(entry)
            item.setFlags(QtCore.Qt.ItemIsUserCheckable
                          | QtCore.Qt.ItemIsEnabled)
            item.setCheckState(QtCore.Qt.Checked)
            self.__listWidget.addItem(item)

        # Create a layout for the title label and potentially other widgets
        topLayout = QtWidgets.QHBoxLayout()
        topLayout.setObjectName('topLayout')
        topLayout.addWidget(self.__titleLabel)

        # Create and apply the main layout of this panel widget
        layout = QtWidgets.QVBoxLayout()
        layout.setObjectName('layout')
        layout.addLayout(topLayout)
        layout.addWidget(self.__allCheckBox)
        layout.addWidget(self.__listWidget)
        self.setLayout(layout)

        # Set up signal/slot connections based on object names and signal names
        QtCore.QMetaObject.connectSlotsByName(self)
        self.__allCheckBox.clicked.connect(self.on_allCheckBox_clicked)
        self.__allCheckBox.stateChanged.connect(self.on_allCheckBox_stateChanged)

    # QWidget Property Functions ----------------------------------------------

    def sizeHint(self):
        """
        @rtype: C{QtCore.QSize}
        @return: The recommended size for the widget, or an invalid size if no
            size is recommended.
        """
        return QtCore.QSize(120, 120)

    # Slots -------------------------------------------------------------------

    def on_allCheckBox_clicked(self, checked):
        """
        Slot that is called when the parent checkbox is clicked (only
        activated possible from a user's mouse click).

        Updates all child checkboxes to be either all selected, or all
        deselected.

        @type checked: C{bool}
        @param checked: Whether the checkbox is checked (partially or otherwise)
        """
        # Doesn't make sense to change all children to "partial"
        self.__allCheckBox.setTristate(False)

        # Make sure on_listWidget_itemChanged doesn't call us back
        self.__updatingFromAllCheckBox = True

        for item in range(self.__totalNumberOfItems):
            self.__listWidget.item(item).setCheckState(self.__allCheckBox.checkState())

        # Ensure checkbox label and state are synced
        if self.__allCheckBox.checkState() == QtCore.Qt.Unchecked:
            self.__allCheckBox.setText("None")
        elif self.__allCheckBox.checkState() == QtCore.Qt.Checked:
            self.__allCheckBox.setText("All")
        else:
            self.__allCheckBox.setText("Partial")

        # Allow children to affect state of __allCheckBox
        self.__updatingFromAllCheckBox = False

    def on_allCheckBox_stateChanged(self, state):
        """
        Slot that is called when the parent checkbox is clicked changed
        in any situation.

        Updates label to match state.

        @type state: C{int}
        @param state: 0 => QtCore.Qt.Unchecked, 1 => QtCore.Qt.PartiallyChecked
            2 => QtCore.Qt.Checked
        """
        if state == 0:
            self.__allCheckBox.setText("None")
        elif state == 1:
            self.__allCheckBox.setText("Partial")
        else:
            self.__allCheckBox.setText("All")

    @QtCore.pyqtSlot(QtWidgets.QListWidgetItem)
    def on_listWidget_itemChanged(self, item):
        """
        Slot that is called when the state of a list widget item in the list
        widget of this panel widget has been changed.

        Updates the text of the title label to show the number of entries that
        are turned on vs. the total number of entries listed.

        Calls the function that has been set using
        L{setCheckeStateChangeCallback()} (if any) to react to the change in
        state of the given C{item}, passing the title of this panel widget, the
        text of the given C{item}, and a boolean flag that states whether the
        item is turned on or off as arguments.

        @type item: C{QtWidgets.QListWidgetItem}
        @param item: The item that was changed.
        """
        # Update global storage
        self.__totalNumberOfItems = self.__listWidget.count()
        self.__numberOfItemsThatAreChecked = sum(
            self.__listWidget.item(i).checkState() == QtCore.Qt.Checked
            for i in range(self.__totalNumberOfItems))

        # redfine for `locals()` call
        title = self.__title
        totalNumberOfItems = self.__totalNumberOfItems
        numberOfItemsThatAreChecked = self.__numberOfItemsThatAreChecked
        if numberOfItemsThatAreChecked == totalNumberOfItems:
            self.__titleLabel.setText('<b>%(title)s</b> ' '(%(totalNumberOfItems)d)' % locals())
        else:
            self.__titleLabel.setText('<b>%(title)s</b> ' '(%(numberOfItemsThatAreChecked)s' '/%(totalNumberOfItems)d)' % locals())

        if callable(self.__checkeStateChangeCallback):
            self.__checkeStateChangeCallback(
                title, item.text(), item.checkState() == QtCore.Qt.Checked)

        # If the parent checkbox is current controling flow, don't
        # change it's state.
        if self.__updatingFromAllCheckBox:
            return

        # Update parent checkbox to match state of all children.
        if self.__totalNumberOfItems == self.__numberOfItemsThatAreChecked:
            self.__allCheckBox.setCheckState(QtCore.Qt.Checked)
        elif self.__numberOfItemsThatAreChecked == 0:
            self.__allCheckBox.setCheckState(QtCore.Qt.Unchecked)
        else:
            self.__allCheckBox.setCheckState(QtCore.Qt.PartiallyChecked)

    @QtCore.pyqtSlot(QtWidgets.QListWidgetItem)
    def on_listWidget_itemPressed(self, item):
        """
        Slot that is called when a mouse button is pressed on an item in the
        list widget of this panel widget.

        Toggles the check state of the clicked item.

        Is I{not} called when the checkbox of a list item is clicked.

        @type item: C{QtWidgets.QListWidgetItem}
        @param item: The item that was clicked.
        """
        item.setCheckState(QtCore.Qt.Unchecked
                           if item.checkState() == QtCore.Qt.Checked
                           else QtCore.Qt.Checked)

    @QtCore.pyqtSlot()
    def on_removeButton_clicked(self):
        """
        Slot that is called when the button for removing this panel widget from
        its container has been clicked.

        Calls the function that has been set using L{setRemoveButtonCallback()}
        (if any) to remove this panel widget from its container.
        """
        if callable(self.__removeButtonCallback):
            self.__removeButtonCallback(self)

    # Public Instance Functions -----------------------------------------------

    def getTitle(self):
        """
        @rtype: C{str}
        @return: The title of the panel widget as provided to the initializer
            of this class. Note that this does I{not} include the number of
            entries that is shown in the title label at the top of this widget.
        """
        return self.__title

    def getEntries(self, checkedOnly=False):
        """
        @type checkedOnly: C{bool}
        @rtype: C{list} of C{str}
        @param checkedOnly: Flag that controls whether to only return entries
            that are turned on.
        @return: The list of entries that are listed in this panel widget,
            optionally only those that are turned on.
        """
        return [str(self.__listWidget.item(i).text())
                for i in range(self.__listWidget.count())
                if not checkedOnly
                or self.__listWidget.item(i).checkState() == QtCore.Qt.Checked]

    def getListWidget(self):
        """
        @rtype: C{QtWidgets.QListWidget}
        @return: The list widget embedded in this panel widget, provided for
            advanced customization.
        """
        return self.__listWidget

    def setListWidgetBorderColor(self, color):
        """
        Sets or resets the color of the border around the list widget in this
        panel widget.

        @type color: C{QtGui.QColor} or C{None}
        @param color: The color to set as the border color, or C{None} to reset
            the border color to its default.
        """
        if color is not None:
            palette = self.palette()
            palette.setColor(QtGui.QPalette.Dark, color)
            palette.setColor(QtGui.QPalette.Light, color)
            self.__listWidget.setPalette(palette)
        else:
            self.style().polish(self.__listWidget)

    def setCheckeStateChangeCallback(self, checkeStateChangeCallback):
        """
        Sets a function to call when the checked state of one of the entries
        that are listed in this panel widget has been changed.

        @type checkeStateChangeCallback: C{callable}
        @param checkeStateChangeCallback: The function to call.
        """
        self.__checkeStateChangeCallback = checkeStateChangeCallback

    def setRemoveButtonCallback(self, removeButtonCallback):
        """
        Sets a function to call when the button for removing this panel widget
        from its container has been clicked.

        Adds a tool button for removing this panel widget, if no such button
        has been created and added to this panel widget yet.

        @type removeButtonCallback: C{callable}
        @param removeButtonCallback: The function to call.
        """
        if callable(removeButtonCallback):
            self.__removeButtonCallback = removeButtonCallback

            removeButton = self.findChild(UI4.Widgets.ToolbarButton,
                                          'removeButton')
            if removeButton is None:
                # Create a tool button for removing this panel widget
                removeButton = UI4.Widgets.ToolbarButton(
                    'Remove', self,
                    UI4.Util.IconManager.GetPixmap('Icons/Panels/x16.png'),
                    rolloverPixmap=UI4.Util.IconManager.GetPixmap(
                        'Icons/Panels/x16_hilite.png'), buttonType=None)
                removeButton.setObjectName('removeButton')
                removeButton.clicked.connect(self.on_removeButton_clicked)

                # Add the tool button to the layout at the top of this panel
                # widget, which contains the panel widget's title label
                topLayout = self.findChild(QtWidgets.QHBoxLayout, 'topLayout')
                topLayout.addStretch()
                topLayout.addWidget(removeButton)

    def setEntryChecked(self, entry, checked):
        """
        Sets the check state of the list widget item that corresponds to the
        given C{entry} according to the given C{checked} state.

        @type entry: C{str}
        @type checked: C{bool}
        @param entry: The text of the entry whose checked state to set.
        @param checked: Flag that controls whether the list widget item that
            corresponds to the given C{entry} is to be shown as checked or not.
        """
        for i in range(self.__listWidget.count()):
            if str(self.__listWidget.item(i).text()) == entry:
                self.__listWidget.item(i).setCheckState(
                    QtCore.Qt.Checked if checked else QtCore.Qt.Unchecked)
                break


class RR_StartMultipleRendersDialog(QtWidgets.QDialog):
    """
    Class implementing a dialog for launching of multiple renders based on
    iterating over a set of Render nodes, values of global Graph State
    Variables, and iterating over a number of frames.
    """

    # Class Variables ---------------------------------------------------------

    kWarningColor = QtGui.QColor(255, 155, 0)
    kErrorColor = QtGui.QColor(235, 32, 32)
    kFrameRangePattern = re.compile(r'^(?P<start>\-?\d+)\-(?P<end>\-?\d+)$')
    kFrameRangeStepPattern = re.compile(r'^(?P<start>\-?\d+)\-(?P<end>\-?\d+)x(?P<step>\-?\d+)$')
    kSingleFramePattern = re.compile(r'^(\-?\d+)$')
    kDefaultStatusLabelStyleSheet = 'font-size: 12pt;'
    kStatusLabelErrorStyleSheet = ('color: %s; %s'
                                   % (kErrorColor.name(),
                                      kDefaultStatusLabelStyleSheet))
    kStatusLabelWarningStyleSheet = ('color: %s; %s'
                                     % (kWarningColor.name(),
                                        kDefaultStatusLabelStyleSheet))

    # Initializer -------------------------------------------------------------

    def __init__(self):
        """
        Initializes an instance of the class.
        """
        QtWidgets.QDialog.__init__(self, UI4.App.MainWindow.GetMainWindow())

        # Set up the properties of the dialog, and position the dialog near the
        # pointer
        self.setWindowTitle('Royal Render - Start Multiple Renders')
        self.setMinimumWidth(470)
        self.setMinimumHeight(350)
        #self.move(QtGui.QCursor.pos())

        # Create a panel widget listing the names of Render nodes contained in
        # the Katana project, with those that are bypassed being turned off
        renderNodes = NodegraphAPI.GetAllNodesByType('Render')
        renderNodeNames = [renderNode.getName() for renderNode in renderNodes]
        renderNodesPanelWidget = RR_PanelWidget('Render Nodes', renderNodeNames,
                                             self)
        renderNodesPanelWidget.setObjectName('RR_renderNodesPanelWidget')
        for renderNode in renderNodes:
            if renderNode.isBypassed():
                renderNodesPanelWidget.setEntryChecked(renderNode.getName(),False)
        renderNodesPanelWidget.setCheckeStateChangeCallback(self.__renderNodeNameCheckStateChanged)

        # Create a panel widget listing the names of global Graph State
        # Variables, with those that are disabled being turned off
        self.__globalGSVs = RR_GetGlobalGraphStateVariables()
        enabledGlobalGSVs = RR_GetGlobalGraphStateVariables(enabledOnly=True)
        globalGSVsPanelWidget = RR_PanelWidget('Global GSVs', list(self.__globalGSVs.keys()), self)
        globalGSVsPanelWidget.setObjectName('RR_globalGSVsPanelWidget')
        for gsvName in self.__globalGSVs:
            if gsvName not in enabledGlobalGSVs:
                globalGSVsPanelWidget.setEntryChecked(gsvName, False)
        globalGSVsPanelWidget.setCheckeStateChangeCallback( self.__globalGsvCheckStateChanged)

        # Create a horizontal box layout to contain the panel widgets
        self.__panelsLayout = QtWidgets.QHBoxLayout()
        self.__panelsLayout.setObjectName('panelsLayout')
        self.__panelsLayout.setSpacing(14)
        self.__panelsLayout.addWidget(renderNodesPanelWidget)
        self.__panelsLayout.addWidget(globalGSVsPanelWidget)

        # Create panel widgets for each global Graph State Variable that is
        # currently turned on, and add them to the layout of panel widgets
        self.__gsvPanelWidgets = {}
        for gsvName, gsvValues in enabledGlobalGSVs.items():
            gsvPanelWidget = RR_PanelWidget(gsvName, gsvValues, self)
            gsvPanelWidget.setCheckeStateChangeCallback(self.__globalGsvValueCheckStateChanged)
            gsvPanelWidget.setRemoveButtonCallback(self.__removeGsvPanelWidget)
            self.__panelsLayout.addWidget(gsvPanelWidget)
            self.__gsvPanelWidgets[gsvName] = gsvPanelWidget

        # Create a horizontal box layout to contain the layout of panel widgets
        panelsFrameLayout = QtWidgets.QHBoxLayout()
        panelsFrameLayout.addLayout(self.__panelsLayout)
        panelsFrameLayout.addStretch(10)

        # Create a line edit widget for entering frame ranges, and set its text
        # to match the current frame
        self.__frameRangeLineEdit = QtWidgets.QLineEdit()
        self.__frameRangeLineEdit.setObjectName('frameRangeLineEdit')
        self.on_currentFramePresetAction_triggered()

        # Apply the shadow color of the line edit widget to the palette of the
        # list widget in the panel widget listing the names of global GSVs, to
        # visually distinguish it from panel widgets of individual global GSVs
        self.style().polish(self.__frameRangeLineEdit)
        lineEditPaletteShadowColor = self.__frameRangeLineEdit.palette().color(QtGui.QPalette.Shadow)
        globalGSVsPanelWidget.getListWidget().setStyleSheet('background-color: %s' % lineEditPaletteShadowColor.name())

        # Create an action for setting the frame range line edit text to the
        # current frame
        currentFramePresetAction = QtWidgets.QAction('Current Frame', self)
        currentFramePresetAction.setObjectName('currentFramePresetAction')

        # Create an action for setting the frame range line edit text to the
        # frames that correspond to the working frame range of Katana's
        # timeline
        workingInOutFramePresetAction = QtWidgets.QAction('Working In/Out Frame', self)
        workingInOutFramePresetAction.setObjectName('workingInOutFramePresetAction')

        workingInOut_step5_FramePresetAction = QtWidgets.QAction('Working In/Out Frame, step 5', self)
        workingInOut_step5_FramePresetAction.setObjectName('workingInOut_step5_FramePresetAction')


        # Create an action for setting the frame range line edit text to the
        # frames that correspond to the first, middle, and last frames in the
        # working frame range of Katana's timeline
        firstMiddleLastFramePresetAction = QtWidgets.QAction('First/Middle/Last Frame', self)
        firstMiddleLastFramePresetAction.setObjectName('firstMiddleLastFramePresetAction')

        # Create a menu button for presets of frame ranges that can be set as
        # the frame range line edit text
        frameRangeMenuButton = UI4.Widgets.MenuButton(self, 'Presets')
        frameRangeMenu = frameRangeMenuButton.menu()
        frameRangeMenu.addAction(workingInOutFramePresetAction)
        frameRangeMenu.addAction(workingInOut_step5_FramePresetAction)
        frameRangeMenu.addAction(currentFramePresetAction)
        frameRangeMenu.addAction(firstMiddleLastFramePresetAction)
        self.on_workingInOutFramePresetAction_triggered()

        # Create a layout for the frame range controls
        frameRangeLayout = QtWidgets.QHBoxLayout()
        frameRangeLayout.addWidget(self.__frameRangeLineEdit)
        frameRangeLayout.addWidget(frameRangeMenuButton)


        # Create a form layout for the additional frame range widgets and any
        # additional checkbox widgets
        formLayout = QtWidgets.QFormLayout()
        formLayout.setLabelAlignment(QtCore.Qt.AlignRight)
        formLayout.setVerticalSpacing(self.style().pixelMetric(QtWidgets.QStyle.PM_LayoutVerticalSpacing))
        formLayout.addRow('Frame Range:', frameRangeLayout)

        # Create a status label to be displayed at the bottom of the dialog
        self.__statusLabel = QtWidgets.QLabel(self)
        self.__statusLabel.setObjectName('statusLabel')
        self.__statusLabel.setStyleSheet(RR_StartMultipleRendersDialog.kDefaultStatusLabelStyleSheet)
        self.__updateState()

        # Create the buttons for starting the configured renders
        submitButton = QtWidgets.QPushButton('Submit to RR')
        submitButton.setObjectName('submitButton')

        # Create a layout for the widgets at the bottom of the dialog
        bottomLayout = QtWidgets.QHBoxLayout()
        bottomLayout.setObjectName('bottomLayout')
        bottomLayout.setSpacing(self.style().pixelMetric(QtWidgets.QStyle.PM_LayoutHorizontalSpacing))
        bottomLayout.addWidget(self.__statusLabel)
        bottomLayout.addStretch()
        bottomLayout.addWidget(submitButton)

        # Create the main layout of the dialog, bringing the other layouts
        # together
        layout = QtWidgets.QVBoxLayout()
        layout.setObjectName('layout')
        layout.setSpacing(14)
        layout.addLayout(panelsFrameLayout)
        layout.addLayout(formLayout)
        layout.addLayout(bottomLayout)

        self.setLayout(layout)

        # Set up signal/slot connections based on object names and signal names
        QtCore.QMetaObject.connectSlotsByName(self)

    # QWidget Event Handlers --------------------------------------------------

    def showEvent(self, event):
        """
        Event handler for widget show events.

        @type event: C{QtGui.QShowEvent}
        @param event: An object containing details about the widget show event
            to process.
        """
        # pylint: disable=unused-argument

        # Select all text in the Frame Range line edit widget, and focus it
        lineEditWidget = self.__frameRangeLineEdit
        lineEditWidget.setFocus()
        QtCore.QTimer.singleShot(0, lineEditWidget.selectAll)

    # Slots -------------------------------------------------------------------

    @QtCore.pyqtSlot(str)
    def on_frameRangeLineEdit_textChanged(self, text):
        """
        Slot that is called when the text in the line edit widget for entering
        the frame range(s) to render has been changed, either by the user, or
        programmatically.

        Updates the status label to show the number of renders resulting from
        the current configuration of Render nodes, Graph State Variables, and
        frame ranges.

        @type text: C{str}
        @param text: The new text of the line edit widget.
        """
        # pylint: disable=unused-argument
        self.__updateState()

    @QtCore.pyqtSlot(bool)
    def on_currentFramePresetAction_triggered(self, checked=False):
        """
        Slot that is called when the action for setting the frame range to
        render to the current frame has been triggered.

        Sets the text of the frame range line edit widget to the current frame.

        @type checked: C{bool}
        @param checked: Unused.
        """
        # pylint: disable=unused-argument
        now = NodegraphAPI.GetCurrentTime()
        currentFrame = int(now)

        frameRange = str(currentFrame)

        self.__frameRangeLineEdit.setText(frameRange)

    @QtCore.pyqtSlot(bool)
    def on_workingInOutFramePresetAction_triggered(self, checked=False):
        """
        Slot that is called when the action for setting the frame range to
        render to the working in and out frames has been triggered.

        Sets the text of the frame range line edit widget to the in and out
        frames of the working frame range of Katana's timeline.

        @type checked: C{bool}
        @param checked: Unused.
        """
        # pylint: disable=unused-argument, unused-variable
        first = int(NodegraphAPI.GetWorkingInTime())
        last = int(NodegraphAPI.GetWorkingOutTime())

        frameRange = '%(first)s-%(last)s' % locals()

        self.__frameRangeLineEdit.setText(frameRange)

    @QtCore.pyqtSlot(bool)
    def on_workingInOut_step5_FramePresetAction_triggered(self, checked=False):
        """
        Slot that is called when the action for setting the frame range to
        render to the working in and out frames has been triggered.

        Sets the text of the frame range line edit widget to the in and out
        frames of the working frame range of Katana's timeline.

        @type checked: C{bool}
        @param checked: Unused.
        """
        # pylint: disable=unused-argument, unused-variable
        first = int(NodegraphAPI.GetWorkingInTime())
        last = int(NodegraphAPI.GetWorkingOutTime())

        frameRange = '%(first)s-%(last)sx5' % locals()

        self.__frameRangeLineEdit.setText(frameRange)

    @QtCore.pyqtSlot(bool)
    def on_firstMiddleLastFramePresetAction_triggered(self, checked=False):
        """
        Slot that is called when the action for setting the frame range to
        render to the first, middle, and last frame of the working frame range
        of Katana's timeline has been triggered.

        Sets the text of the frame range line edit widget to the first, middle,
        and last frames of the working frame range of Katana's timeline.

        @type checked: C{bool}
        @param checked: Unused.
        """
        # pylint: disable=unused-argument, unused-variable
        first = int(NodegraphAPI.GetWorkingInTime())
        last = int(NodegraphAPI.GetWorkingOutTime())

        middle = int((last - first) / 2) + 1

        frameRange = '%(first)s, %(middle)s, %(last)s' % locals()

        self.__frameRangeLineEdit.setText(frameRange)

    @QtCore.pyqtSlot()
    def on_submitButton_clicked(self):
        """
        Slot that is called when the B{Preview Render} button has been clicked.

        Starts Preview Renders for the chosen Render nodes, Graph State
        Variables, and frame ranges.
        """
        # pylint: disable=invalid-name

        current_filepath = FarmAPI.GetKatanaFileName()
        if KatanaFile.IsFileDirty():
            result = UI4.Widgets.MessageBox.Warning('Unsaved Changes', 'Save your file', acceptText='Save',
                                                    cancelText='Abort')
            if result == 0:  # Save
                KatanaFile.Save(current_filepath)
            else:  # Cancel
                return False


        renderNodes = self.__getChosenRenderNodes(updateAppearance=True)
        graphStateVariables = self.__getChosenGraphStateVariables(updateAppearance=True)
        errorMessage, retStart, retEnd, retStep, retFrameSet = self.__getChosenFrames(updateAppearance=True)
        if (errorMessage or not renderNodes or [] in graphStateVariables.values()):
            return
  
        renders = RR_GetRenders(renderNodes, graphStateVariables)
        
        # Get access to the Graph State Variables parameter in project settings
        rootNode = NodegraphAPI.GetRootNode()
        variablesParameter = rootNode.getParameter('variables')
        now = NodegraphAPI.GetCurrentTime()
        currentFrame = int(now)        
        
        jobList=[]
        
        
        # Iterate over the information of renders to start
        for (renderNode, gsvCombination) in renders:
        
            gsv_commandline=""
            # Configure the global Graph State Variables to be able to retrieve the right settings like output filename
            for name, value in gsvCombination:
                gsvParameter = variablesParameter.getChild('%s.value' % name)
                if gsvParameter is not None:
                    gsvParameter.setValue(value, currentFrame)
                    gsv_commandline= gsv_commandline + ("--var %s=%s" % (name, value)  )
                    
                    
            nodeRenderSettings= FarmAPI.GetSortedDependencies(renderNode)[-1]
            
            newJob= rrSubmitJob.createSubmitJob(nodeRenderSettings, False)
            if len(retFrameSet)>0:
                newJob.seqFrameSet=retFrameSet
            else:
                newJob.seqStart=retStart
                newJob.seqEnd=retEnd
                newJob.seqStep=retStep
                
            if len(gsv_commandline)>0:
                newJob.customGSV=gsv_commandline
                
            
            jobList.append(newJob)
            
        rrSubmitJob.submitJobList(jobList)
        
        self.accept()



    # Private Instance Functions ----------------------------------------------
    # Private Instance Functions ----------------------------------------------
    # Private Instance Functions ----------------------------------------------

    def __renderNodeNameCheckStateChanged(self, title, renderNodeName, checked):
        """
        Callback that is called when the checked state of the Render node with
        the given name has been changed.

        Updates the status label to show the number of renders resulting from
        the current configuration of Render nodes, Graph State Variables, and
        frame ranges.

        @type title: C{str}
        @type renderNodeName: C{str}
        @type checked: C{bool}
        @param title: The title of the panel widget listing Render node names.
        @param renderNodeName: The name of the Render node whose checked state
            has been changed.
        @param checked: Flag that states whether the Render node with the given
            name is to be included when generating the renders to start when
            clicking the B{Preview Render} or B{Live Render} button.
        """
        # pylint: disable=unused-argument
        self.__updateState()

    def __globalGsvCheckStateChanged(self, title, gsvName, checked):
        """
        Callback that is called when the checked state of the global Graph
        State Variable with the given name has been changed.

        Adds or removes a panel widget listing the values of the global GSV
        depending to the given C{checked} state.

        Updates the status label to show the number of renders resulting from
        the current configuration of Render nodes, Graph State Variables, and
        frame ranges.

        @type title: C{str}
        @type gsvName: C{str}
        @type checked: C{bool}
        @param title: The title of the panel widget listing the names of global
            GSVs. (Unused)
        @param gsvName: The name of the global GSV whose checked state has been
            changed.
        @param checked: Flag that states whether a panel widget listing the
            values of the global GSV with the given name is to be shown in the
            dialog.
        """
        # pylint: disable=unused-argument

        # Check if a panel widget for the global GSV with the given name exists
        # already
        if gsvName in self.__gsvPanelWidgets:
            # Add or remove the panel widget for the global GSV
            gsvPanelWidget = self.__gsvPanelWidgets[gsvName]
            if checked:
                self.__panelsLayout.addWidget(gsvPanelWidget)
            else:
                self.__removeGsvPanelWidget(gsvPanelWidget)
        elif checked:
            # Create, register, and add a new panel widget for the global GSV
            gsvValues = self.__globalGSVs[gsvName]
            gsvPanelWidget = RR_PanelWidget(gsvName, gsvValues, self)
            gsvPanelWidget.setRemoveButtonCallback(self.__removeGsvPanelWidget)
            self.__gsvPanelWidgets[gsvName] = gsvPanelWidget
            self.__panelsLayout.addWidget(gsvPanelWidget)

        self.__updateState()

    def __globalGsvValueCheckStateChanged(self, gsvName, gsvValue, checked):
        """
        Callback that is called when the checked state of the value of the
        global Graph State Variable with the given name has been changed.

        Updates the status label to show the number of renders resulting from
        the current configuration of Render nodes, Graph State Variables, and
        frame ranges.

        @type gsvName: C{str}
        @type gsvValue: C{str}
        @type checked: C{bool}
        @param gsvName: The name of the global GSV to which the value belongs.
        @param gsvValue: The value whose checked state has been changed.
        @param checked: Flag that states whether the value of the global GSV
            with the given name is to be included when generating the renders
            to start when clicking the B{Preview Render} or B{Live Render}
            button.
        """
        # pylint: disable=unused-argument
        self.__updateState()

    def __removeGsvPanelWidget(self, gsvPanelWidget):
        """
        Removes the given panel widget listing values of a particular global
        Graph State Variable from the layout of panel widgets.

        Updates the checked state of the entry that corresponds to the global
        GSV in the panel widget listing the names of global GSVs accordingly.

        Updates the status label to show the number of renders resulting from
        the current configuration of Render nodes, Graph State Variables, and
        frame ranges.

        @type gsvPanelWidget: C{PanelWidget}
        @param gsvPanelWidget: The panel widget to remove.
        """
        gsvName = gsvPanelWidget.getTitle()
        self.__panelsLayout.removeWidget(gsvPanelWidget)
        gsvPanelWidget.setParent(None)

        globalGSVsPanelWidget = self.findChild(RR_PanelWidget, 'RR_globalGSVsPanelWidget')
        globalGSVsPanelWidget.setEntryChecked(gsvName, False)

        self.__updateState()

    def __updateState(self):
        """
        Resets the appearance of widgets in the dialog regarding warning and
        error highlights, and updates the status label to show the number of
        renders resulting from the current configuration of Render nodes,
        global Graph State Variables, and frame ranges.
        """
        # pylint: disable=unused-argument

        # Reset the appearance of the Render Nodes panel widget
        renderNodesPanelWidget = self.findChild(RR_PanelWidget,
                                                'RR_renderNodesPanelWidget')
        renderNodesPanelWidget.setListWidgetBorderColor(None)

        # Reset the appearance of all Graph State Variables panel widgets
        for gsvName in self.__gsvPanelWidgets:
            gsvPanelWidget = self.__gsvPanelWidgets[gsvName]
            gsvPanelWidget.setListWidgetBorderColor(None)

        # Reset the appearance of the frame range line edit widget
        self.style().polish(self.__frameRangeLineEdit)

        # Reset the appearance of the status label
        self.__statusLabel.setStyleSheet(
            RR_StartMultipleRendersDialog.kDefaultStatusLabelStyleSheet)

        # Obtain the frames to render based on the current configuration in the dialog
        errorMessage, retStart, retEnd, retStep, retFrameSet = self.__getChosenFrames()
        if errorMessage:
            self.__statusLabel.setText(errorMessage)
            return

        renderNodes = self.__getChosenRenderNodes()
        graphStateVariables = self.__getChosenGraphStateVariables()

        numberOfRenders = len(renderNodes)
        for _gsvName, gsvValues in graphStateVariables.items():
            numberOfRenders *= len(gsvValues)
 
        self.__statusLabel.setText('<b>{:,}</b> jobs'.format(numberOfRenders))

    def __getChosenRenderNodes(self, updateAppearance=False):
        """
        @type updateAppearance: C{bool}
        @rtype: C{list} of C{Nodes2DAPI.Node2D}
        @param updateAppearance: Flag that controls whether to update the
            appearance of the B{Render Nodes} panel widget and the status label
            to indicate warnings or errors.
        @return: A list of Render nodes that have been turned on to be included
            when generating the renders to start when clicking the B{Submit)
            button.
        """
        renderNodesPanelWidget = self.findChild(RR_PanelWidget,
                                                'RR_renderNodesPanelWidget')
        renderNodeNames = renderNodesPanelWidget.getEntries(checkedOnly=True)
        result = [NodegraphAPI.GetNode(renderNodeName)
                  for renderNodeName in renderNodeNames]

        if updateAppearance and not result:
            renderNodesPanelWidget.setListWidgetBorderColor(
                RR_StartMultipleRendersDialog.kWarningColor)
            self.__statusLabel.setStyleSheet(
                RR_StartMultipleRendersDialog.kStatusLabelWarningStyleSheet)

        return result

    def __getChosenGraphStateVariables(self, updateAppearance=False):
        """
        @type updateAppearance: C{bool}
        @rtype: C{collections.OrderedDict}
        @param updateAppearance: Flag that controls whether to update the
            appearance of Graph State Variable panel widgets and the status
            label to indicate warnings or errors.
        @return: A dictionary with sorted names of global Graph State Variables
            that are turned on as keys, and lists of values of these global
            GSVs that are turned on as values.
        """
        result = OrderedDict()

        globalGSVsPanelWidget = self.findChild(RR_PanelWidget,
                                               'RR_globalGSVsPanelWidget')
        for gsvName in globalGSVsPanelWidget.getEntries(checkedOnly=True):
            if gsvName in self.__gsvPanelWidgets:
                gsvPanelWidget = self.__gsvPanelWidgets[gsvName]
                gsvValues = gsvPanelWidget.getEntries(checkedOnly=True)
                result[gsvName] = gsvValues
                if updateAppearance and not gsvValues:
                    gsvPanelWidget.setListWidgetBorderColor(
                        RR_StartMultipleRendersDialog.kWarningColor)

        if updateAppearance and [] in result.values():
            self.__statusLabel.setStyleSheet(
                RR_StartMultipleRendersDialog.kStatusLabelWarningStyleSheet)

        return result

    def __getChosenFrames(self, updateAppearance=False):
        """
        @type updateAppearance: C{bool}
        @rtype: C{list} of C{int}
        @param updateAppearance: Flag that controls whether to update the
            appearance of the frame range line edit widget and the status label
            to indicate warnings or errors.
        @return: returns [errorMessage, start, end, step, framset].
        """
        retStart=1
        retEnd=1
        retStep=1
        retFrameSet=""
        errorMessage = ''

        frameRangeText = str(self.__frameRangeLineEdit.text())

        # Check if the appearance of the frame range line edit and the status
        # label are to be updated in case of warnings, and if no text has been
        # entered, and if so, update the appearance of those widgets
        # accordingly
        if not frameRangeText:
            if updateAppearance:
                palette = self.__frameRangeLineEdit.palette()
                palette.setColor(QtGui.QPalette.Dark, RR_StartMultipleRendersDialog.kWarningColor)
                palette.setColor(QtGui.QPalette.Light, RR_StartMultipleRendersDialog.kWarningColor)
                self.__frameRangeLineEdit.setPalette(palette)
                self.__frameRangeLineEdit.setFocus()
                self.__statusLabel.setStyleSheet( RR_StartMultipleRendersDialog.kStatusLabelWarningStyleSheet)
            return errorMessage, retStart, retEnd, retStep, retFrameSet

        # Parse the frame range text, stopping at the first part of the frame range text that is invalid (if any)
        parts = frameRangeText.split(',')
        for part in parts:
            part = part.strip()
            if not part:
                continue

            match = RR_StartMultipleRendersDialog.kFrameRangeStepPattern.match(part)
            if match:
                retStart = int(match.group('start'))
                retEnd = int(match.group('end')) + 1
                retStep = int(match.group('step'))
                if retStart < retEnd:
                    if retStep<=0:
                        errorMessage = ('Invalid frame step: "%s" ' % part)
                        break
                else:
                    errorMessage = ('Invalid frame range: "%s" (start > end)' % part)
                    break
                writeInfo("Frame Range %(retStart)s-%(retEnd)sx%(retStep)s " % locals())
            else:
                match = RR_StartMultipleRendersDialog.kFrameRangePattern.match(part)
                if match:
                    retStart = int(match.group('start'))
                    retEnd = int(match.group('end')) + 1
                    retStep=1
                    if retStart > retEnd:
                        errorMessage = ('Invalid frame range: "%s" (start > end)' % part)
                        break
                    writeInfo("Frame Range %(retStart)s-%(retEnd)sx%(retStep)s " % locals())
                else:
                    match = RR_StartMultipleRendersDialog.kSingleFramePattern.match(part)
                    if match:
                        retStart = int(match.group())
                        retEnd=retStart
                        retStep=1
                    else:
                        errorMessage = 'Invalid frame range: "%s"' % part
                        break
                    writeInfo("Frame  %s  ".format(retStart))
        if len(parts)>1:
            retFrameSet= frameRangeText
        # Check if the appearance of the frame range line edit and the status
        # label are to be updated in case of errors, and if an error message is
        # set, and if so, update the appearance of those widgets accordingly
        
        if updateAppearance and errorMessage:
            palette = self.__frameRangeLineEdit.palette()
            palette.setColor(QtGui.QPalette.Dark, RR_StartMultipleRendersDialog.kErrorColor)
            palette.setColor(QtGui.QPalette.Light, RR_StartMultipleRendersDialog.kErrorColor)
            self.__frameRangeLineEdit.setPalette(palette)
            self.__frameRangeLineEdit.setFocus()
            self.__statusLabel.setStyleSheet(RR_StartMultipleRendersDialog.kStatusLabelErrorStyleSheet)

        return errorMessage, retStart, retEnd, retStep, retFrameSet




# Module Functions ------------------------------------------------------------

def RR_GetGlobalGraphStateVariables(enabledOnly=False):
    """
    @type enabledOnly: C{bool}
    @rtype: C{collections.OrderedDict} of C{str} S{rarr} C{list}
    @param enabledOnly: Flag that controls whether only those GSVs should be
        returned that are currently turned on.
    @return: A dictionary with sorted names of global Graph State Variables as
        keys, and lists of values of these global GSVs as values.
    """
    result = OrderedDict()

    rootNode = NodegraphAPI.GetRootNode()
    variablesParameter = rootNode.getParameter('variables')
    now = NodegraphAPI.GetCurrentTime()

    for gsvGroupParameter in variablesParameter.getChildren():
        gsvName = gsvGroupParameter.getName()

        if enabledOnly:
            enableChild = gsvGroupParameter.getChild('enable')
            if enableChild and enableChild.getValue(0) != 1:
                continue

        gsvValues = []

        optionsChild = gsvGroupParameter.getChild('options')
        if optionsChild:
            for option in optionsChild.getChildren():
                gsvValues.append(option.getValue(now))

        result[gsvName] = gsvValues

    return result


def RR_GetRenders(renderNodes, graphStateVariables):
    """
    Generates a list of descriptions of individual renders from the given list
    of Render nodes, mapping of names and values of Graph State Variables, and
    list of frames.

    Each entry in the resulting list is a 3-tuple of a render node, a specific
    unique combination of Graph State Variables, e.g. 'shot' = '0020' and
    'timeOfDay' = 'night', and the frame to render.

    @type renderNodes: C{list} of C{NodegraphAPI.Node}
    @type graphStateVariables: C{collections.OrderedDict} of C{str} S{rarr}
        C{list}
    @type frames: C{list} of C{float}
    @rtype: C{list} of 3-C{tuple}
    @param renderNodes: A list of Render nodes from which to start renders.
    @param graphStateVariables: A map of names and values of Graph State
        Variables to iterate over in all possible combinations.
    @return: A list of tuples describing renders to start.
    """
    result = []

    numberOfGSVs = len(graphStateVariables)

    for renderNode in renderNodes:
        nameValueTuples = []

        for name, values in [(name, values)
                             for name, values in graphStateVariables.items()]:
            for value in values:
                nameValueTuples.append((name, value))

        if numberOfGSVs == 1:
            gsvCombinationList = [[entry] for entry in nameValueTuples]
        else:
            # Create a list of combinations of GSV name/value tuples, making sure that each GSV only appears once
            gsvCombinationList = [
                entries
                for entries in itertools.combinations(nameValueTuples, numberOfGSVs)
                if len(dict(entries)) == numberOfGSVs]

        for gsvCombination in gsvCombinationList:
            result.append((renderNode, gsvCombination))
            gsvCombinationText = '\n'.join( '|%s: %s  ' % (name, value)  for name, value in gsvCombination)
            writeInfo("adding '{}' with GSV '{}'".format(renderNode, gsvCombinationText))

    return result

