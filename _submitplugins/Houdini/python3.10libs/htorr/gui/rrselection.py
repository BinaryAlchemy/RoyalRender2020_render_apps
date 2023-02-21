# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy

from hutil.Qt import QtCore
from PySide2 import QtWidgets
from PySide2 import QtGui
import hou

clients = ["fo","bla","blub","this","that","pc","client"]
client_selected  = ["fo","bla","this","pc"]


class ListSelection(QtWidgets.QDialog):
    def __init__(self, list_src, parm, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.setParent(hou.qt.mainWindow(), QtCore.Qt.Window)

        self.list_src = list_src
        self.parm = parm
        self.list_old_sel = self.parm.eval().split()

        hbox = QtWidgets.QVBoxLayout()
        
        self.setGeometry(500, 300, 250, 600)
        self.setWindowTitle('Select')
        
        self.list_widget = QtWidgets.QListWidget(self)
        self.list_widget.setSelectionMode(QtWidgets.QListWidget.ExtendedSelection)
        
        index = 0
        for c in self.list_src:
            item = QtWidgets.QListWidgetItem()
            item.setText(c)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)

            if c in self.list_old_sel:
                item.setCheckState(QtCore.Qt.Checked)
            else:
                item.setCheckState(QtCore.Qt.Unchecked)
            
            
            self.list_widget.addItem(item)
            index += 1

        hbox.addWidget(self.list_widget)


        self.pb_clear = QtWidgets.QPushButton("Clear")
        self.pb_clear.clicked.connect(self.clear)

        self.list_widget.itemChanged.connect(self.item_checked)

        hbox.addWidget(self.pb_clear)

        self.setLayout(hbox)

    def item_checked(self, item):
        for i in self.list_widget.selectedItems():
            i.setCheckState(item.checkState())
        self.save_checked()


    def save_checked(self):
        selection = []
        for i in range(self.list_widget.count()):
            if self.list_widget.item(i).checkState() == QtCore.Qt.Checked:
                selection.append(self.list_widget.item(i).text())
        self.parm.set(" ".join(selection))

    def clear(self):
        self.parm.set("")
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(QtCore.Qt.Unchecked)


def select_from_list(list, parm):
    dialog = ListSelection(list, parm)
    dialog.show()