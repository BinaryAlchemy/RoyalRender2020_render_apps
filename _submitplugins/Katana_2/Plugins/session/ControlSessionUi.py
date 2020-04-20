# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '/home/MEDIANET/aschachner/Documents/work/tools/katana2rr/Resources/Plugins/ui/controlSession.ui'
#
# Created: Wed Jun 15 19:34:00 2016
#      by: pyside-uic 0.2.14 running on PySide 1.2.0
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore, QtGui

class Ui_FileExport(object):
    def setupUi(self, FileExport):
        FileExport.setObjectName("FileExport")
        FileExport.resize(220, 352)
        FileExport.setMinimumSize(QtCore.QSize(220, 0))
        FileExport.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.verticalLayout_2 = QtGui.QVBoxLayout(FileExport)
        self.verticalLayout_2.setSpacing(3)
        self.verticalLayout_2.setContentsMargins(3, 3, 3, 3)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.scrollArea = QtGui.QScrollArea(FileExport)
        self.scrollArea.setFrameShape(QtGui.QFrame.StyledPanel)
        self.scrollArea.setFrameShadow(QtGui.QFrame.Raised)
        self.scrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.scrollArea.setObjectName("scrollArea")
        self.progressLayHolder = QtGui.QWidget()
        self.progressLayHolder.setGeometry(QtCore.QRect(0, 0, 208, 293))
        self.progressLayHolder.setObjectName("progressLayHolder")
        self.verticalLayout = QtGui.QVBoxLayout(self.progressLayHolder)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.progressLay = QtGui.QVBoxLayout()
        self.progressLay.setSpacing(3)
        self.progressLay.setObjectName("progressLay")
        self.verticalLayout.addLayout(self.progressLay)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.scrollArea.setWidget(self.progressLayHolder)
        self.verticalLayout_2.addWidget(self.scrollArea)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.cancelBtn = QtGui.QPushButton(FileExport)
        self.cancelBtn.setObjectName("cancelBtn")
        self.horizontalLayout.addWidget(self.cancelBtn)
        self.verticalLayout_2.addLayout(self.horizontalLayout)
        self.infoLbl = QtGui.QLabel(FileExport)
        self.infoLbl.setObjectName("infoLbl")
        self.verticalLayout_2.addWidget(self.infoLbl)

        self.retranslateUi(FileExport)
        QtCore.QMetaObject.connectSlotsByName(FileExport)

    def retranslateUi(self, FileExport):
        FileExport.setWindowTitle(QtGui.QApplication.translate("FileExport", "Control Monitor", None, QtGui.QApplication.UnicodeUTF8))
        self.cancelBtn.setText(QtGui.QApplication.translate("FileExport", "Cancel", None, QtGui.QApplication.UnicodeUTF8))
        self.infoLbl.setText(QtGui.QApplication.translate("FileExport", "rrConversionSession", None, QtGui.QApplication.UnicodeUTF8))

