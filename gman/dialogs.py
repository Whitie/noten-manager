# -*- coding: utf-8 -*-

import os

from PyQt5 import QtCore, QtWidgets, uic


class StudentDialog(QtWidgets.QDialog):

    def __init__(self, parent, ui_path):
        QtWidgets.QDialog.__init__(self, parent)
        uic.loadUi(os.path.join(ui_path, 'dlg_student_count.ui'), self)


class CourseDialog(QtWidgets.QDialog):

    def __init__(self, parent, ui_path, courses):
        QtWidgets.QDialog.__init__(self, parent)
        uic.loadUi(os.path.join(ui_path, 'dlg_courses.ui'), self)
        for course in courses:
            self.courselist.addItem(QtWidgets.QListWidgetItem(course.title))
        self.courselist.itemDoubleClicked.connect(self.item_selected)

    def item_selected(self, item):
        text = item.text()
        self.parent().title.setText(text)
        self.parent().btn_save.setEnabled(True)
        self.close()


class CredentialsDialog(QtWidgets.QDialog):

    def __init__(self, parent, ui_path, crypted_db_path):
        QtWidgets.QDialog.__init__(self, parent)
        uic.loadUi(os.path.join(ui_path, 'dlg_credentials.ui'), self)
        self.crypted_db.setText(crypted_db_path)
        self.opt_keyfile.toggled.connect(self._enable_fields)
        self.btn_keyfile.clicked.connect(self.get_path)
        self.active = 'keyfile'

    def get_path(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Datei öffnen', os.path.expanduser('~') or '.',
            'Schlüssel-Dateien (*.key)'
        )
        if filename:
            print(filename)
            self.keyfile_path.setText(filename)

    def _enable_fields(self, checked):
        if self.opt_keyfile.isChecked():
            self.active = 'keyfile'
            enable = True
        else:
            self.active = 'password'
            enable = False
        self.keyfile_path.setEnabled(enable)
        self.btn_keyfile.setEnabled(enable)
        self.password.setDisabled(enable)


class HelpDialog(QtWidgets.QDialog):

    def __init__(self, parent, ui_path, doc_path):
        QtWidgets.QDialog.__init__(self, parent)
        uic.loadUi(os.path.join(ui_path, 'help_browser.ui'), self)
        self.browser.setSearchPaths([doc_path])
        self.browser.setSource(QtCore.QUrl('index.html'))
        self.btn_close.clicked.connect(self.close)
        self.btn_home.clicked.connect(self.browser.home)
        self.btn_back.clicked.connect(self.browser.backward)
        self.btn_next.clicked.connect(self.browser.forward)
        self.browser.backwardAvailable.connect(self.btn_back.setEnabled)
        self.browser.forwardAvailable.connect(self.btn_next.setEnabled)
