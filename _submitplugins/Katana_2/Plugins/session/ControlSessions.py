import math
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

from PySide import QtCore, QtGui

import ControlSessionUi as ui

reload(ui)

dialog = None


class ControlSession(QtGui.QWidget, ui.Ui_FileExport):
    _xmlfile = ""
    _katanafile = ""
    _imagename = ""
    _imgDir = ""
    _startframe = int()
    _endframe = int()
    _renderer = ""
    _rendernode = ""

    _threadCount = int()
    _threads = []
    _threadprogress = []
    packageId = 0
    _progress = 0
    activeThreads = 0
    sessionCount = 0

    def __init__(self, jobFile):
        super(ControlSession, self).__init__()

        self._xmlfile = jobFile[1]
        self._katanafile = jobFile[2]

        # self.setGeometry(300, 300, 400, 130)
        self.setupUi(self)

        self.cancelBtn.clicked.connect(self.interrupt)

        self.jobParser()

    def jobParser(self):
        tree = ET.parse(self._xmlfile)
        root = tree.getroot()

        for job in root.findall('Job'):
            self._imagename = job.find('ImageFilename').text
            self._imgDir = job.find('ImageDir').text
            self._startframe = int(job.find('SeqStart').text)
            self._endframe = int(job.find('SeqEnd').text)
            self._renderer = job.find('Renderer').text

            if self._renderer == "RenderMan":
                self._renderer = "prman"

            self._rendernode = job.find('Rendernode').text
            packageSize = int(job.find('PackageSize').text)
            self._threadCount = int(job.find('ThreadCount').text)

            self.initExport(packageSize)

    def initExport(self, packageSize):
        self.infoLbl.setText('Processing...')

        frameCount = int(self._endframe) - int(self._startframe) + 1
        self.sessionCount = int(math.ceil(int(frameCount) / int(packageSize)))

        # self.progressbar.setMaximum(self.sessionCount)

        # create all script jobs
        for i in range(self.sessionCount):
            threadId = i + 1
            inFrame = int(packageSize) * i + int(self._startframe)
            outFrame = int(packageSize) * i + int(self._startframe) + int(packageSize) - 1

            session = ScriptSession(threadId, self._katanafile, self._renderer, self._rendernode, inFrame, outFrame,
                                    self._imagename, self._imgDir, self)
            self._threads.append(session)

            QtCore.QObject.connect(session, QtCore.SIGNAL('progress(QString)'), self.setProgress,
                                   QtCore.Qt.QueuedConnection)
            QtCore.QObject.connect(session, QtCore.SIGNAL('finishProgress(QString)'), self.finishProgress,
                                   QtCore.Qt.QueuedConnection)
            QtCore.QObject.connect(session, QtCore.SIGNAL('interrupt(QString)'), self.interrupt,
                                   QtCore.Qt.QueuedConnection)

            progressBar = QtGui.QProgressBar()
            progressBar.setMaximum(int(packageSize))
            progressBar.setValue(0)
            progressBar.setFormat('Thread ' + str(threadId) + ' done: %v/%m')
            self.progressLay.addWidget(progressBar)
            self._threadprogress.append(progressBar)

        self.export()

    def export(self):
        # loop until all script jobs are done
        while True:
            # chack for max threads
            if self.activeThreads >= int(self._threadCount):
                return False
            # check if all sessions are done
            if self._progress >= self.sessionCount:
                self.checkSequence()
                return False
            # check if jobs already submitted
            if self.packageId >= self.sessionCount:
                return False
            # start waiting threads
            else:
                self._threads[self.packageId].start()
                self.activeThreads += 1
                self.packageId += 1

    def interrupt(self, err=0):
        # TODO - confirm button

        for thread in self._threads:
            thread.kill()
            self.close()

        """
        if err:
            errMsg = QtGui.QMessageBox()
            errMsg.setText(err)
        for thread in self._threads:
            thread.close()
            # TODO
        """

    def setProgress(self, threadId):
        threadIndex = int(threadId) - 1
        progressBar = self._threadprogress[threadIndex]
        progressBar.setValue(progressBar.value() + 1)

    def finishProgress(self, threadId):
        self._progress += 1
        self.activeThreads -= 1
        self.infoLbl.setText('Process ' + str(self._progress) + '/' + str(self.sessionCount) + ' done')
        self.export()

    def checkSequence(self):
        fileExtension = ''
        if self._renderer == 'prman':
            fileExtension = 'rib'
        elif self._renderer == 'arnold':
            fileExtension = 'ass'

        files = os.listdir(self._imgDir)
        missingFrames = []
        for i in range(self._startframe, self._endframe):
            filename = '%s%04d.%s' % (self._imagename, i, fileExtension)
            if filename not in files:
                missingFrames.append(filename)
        if missingFrames:
            warnMsg = QtGui.QMessageBox()
            warnMsg.setText('Could not convert: ' + str(missingFrames) + '\nSubmit anyhow?')
            warnMsg.addButton(QtGui.QMessageBox.Yes)
            warnMsg.addButton(QtGui.QMessageBox.No)

            ret = warnMsg.exec_()
            if ret == QtGui.QMessageBox.Yes:
                self.submit()

        else:
            # successMsg = QtGui.QMessageBox()
            # successMsg.setText('Finished')
            # ret = successMsg.exec_()

            self.submit()

        self.close()

    def submit(self):
        print (getRRSubmitterPath() + "  \"" + self._xmlfile + "\"")
        os.system(getRRSubmitterPath() + "  \"" + self._xmlfile + "\"")


class ScriptSession(QtCore.QThread):
    # _lock = threading.Lock()
    _renderer = ''
    _katanafile = ''

    def __init__(self, threadId, katanafile, renderer, rendernode, startframe, endframe, imagename, imagedir,
                 controlSession):
        QtCore.QThread.__init__(self)
        self._threadId = threadId
        self._katanafile = katanafile
        self._renderer = renderer
        self._rendernode = rendernode
        self._startframe = startframe
        self._endframe = endframe
        self._imagename = imagename
        self._imagedir = imagedir
        self._controlSession = controlSession
        self._scriptDir = os.path.dirname(sys.argv[0])
        self._live = True

    def run(self):
        # print 'Session %s started processing frame %s to %s' %(self._threadId, self._startframe, self._endframe)

        # TODO - add support for batch files
        env = os.path.join(self._scriptDir, 'KatanaEnv.sh')
        if os.path.exists(env):
            sessionScript = os.path.join(self._scriptDir, 'ScriptSession.py')
        env = subprocess.Popen(env)
        env.wait()
        print 'PING'
        katanaSession = subprocess.Popen(
            [
                '/opt/katana2.5v3/katana',
                '--script=' + sessionScript,
                # '--script=//home/MEDIANET/aschachner/Documents/work/tools/katana2rr/Resources/Plugins/session/ScriptSession.py',
                self._katanafile,
                self._renderer,
                self._rendernode,
                str(self._startframe),
                str(self._endframe),
                self._imagename,
                self._imagedir,
                str(self._threadId),
            ],
            # close_fds=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        exitCode = None
        while katanaSession.poll() is None:
            line = katanaSession.stdout.readline()
            if '[k2rrFrameConvProgress]_' in line:
                frame = line.split('_')[1]
                threadId = line.split('_')[3]
                self.emit(QtCore.SIGNAL('progress(QString)'), str(threadId))
            if '[k2rrThreadFinished]_' in line:
                threadId = line.split('_')[1]
                exitCode = threadId
            if '[ERROR python.NodeDebugOutput]' in line:
                print '#########################################################'
                print line
                print '#########################################################'

            if not self._live:
                katanaSession.kill()

            #	 # errMsg.append(line)
            #	 self.emit(QtCore.SIGNAL('interrupt(QString)'), str(line))

        katanaSession.wait()
        if self._live:
            self.emit(QtCore.SIGNAL('finishProgress(QString)'), str(exitCode))

    def getInpoint(self):
        return self._startframe

    def getOutpoint(self):
        return self._endframe

    def kill(self):
        print 'set kill'
        self._live = False


################################################################################
# global functions // from rrSubmit_Nuke_5.py (Copyright (c) Holger Schoenberger - Binary Alchemy)

def getRR_Root():
    if os.environ.has_key('RR_ROOT'):
        return os.environ['RR_ROOT']
    HCPath = "%"
    if ((sys.platform.lower() == "win32") or (sys.platform.lower() == "win64")):
        HCPath = "%RRLocationWin%"
    elif (sys.platform.lower() == "darwin"):
        HCPath = "%RRLocationMac%"
    else:
        HCPath = "%RRLocationLx%"
    if HCPath[0] != "%":
        return HCPath
    writeError("This plugin was not installed via rrWorkstationInstaller!")


def getRRSubmitterPath():
    ''' returns the rrSubmitter filename '''
    rrRoot = getRR_Root()
    if ((sys.platform.lower() == "win32") or (sys.platform.lower() == "win64")):
        rrSubmitter = rrRoot + "\\win__rrSubmitter.bat"
    elif (sys.platform.lower() == "darwin"):
        rrSubmitter = rrRoot + "/bin/mac64/rrSubmitter.app/Contents/MacOS/rrSubmitter"
    else:
        rrSubmitter = rrRoot + "/lx__rrSubmitter.sh"
    return rrSubmitter


################################################################################
# rrJob // from rrSubmit_Nuke_5.py (Copyright (c) Holger Schoenberger - Binary Alchemy)

if __name__ == '__main__':
    if dialog is not None:
        dialog.close()
        dialog = None
    app = QtGui.QApplication(sys.argv)
    dialog = ControlSession(sys.argv)
    dialog.show()
    sys.exit(app.exec_())
