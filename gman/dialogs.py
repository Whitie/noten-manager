# -*- coding: utf-8 -*-

import os

from PyQt5 import QtWidgets, uic


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
