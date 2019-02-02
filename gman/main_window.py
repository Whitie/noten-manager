#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

from getpass import getuser
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from . import db, dialogs, items, resources, widgets


PATH = os.path.dirname(os.path.abspath(__file__))
UI_PATH = os.path.join(PATH, 'ui')


class GradeManagerMain(QtWidgets.QMainWindow):

    def __init__(self, dbfile=''):
        QtWidgets.QMainWindow.__init__(self)
        uic.loadUi(os.path.join(UI_PATH, 'main.ui'), self)
        self.setWindowTitle('bbz Notenmanager - {}'.format(getuser()))
        self.Session = None
        self.dbfile = dbfile
        self.db_connected = False
        self.subwindows = {}
        self.top = None
        if dbfile:
            self.load_db(dbfile)
        self._connect_actions()
        self._check_available_actions()
        self.nav.itemClicked.connect(self.item_clicked)
        self.nav.customContextMenuRequested.connect(self.item_right_clicked)

    def _connect_actions(self):
        self.action_new_db.triggered.connect(self.create_new_db)
        self.action_open_db.triggered.connect(self.open_db)
        self.action_add_students.triggered.connect(self.add_students)
        self.action_companies.triggered.connect(self.edit_companies)
        self.action_new_course.triggered.connect(self.new_course)

    def _check_available_actions(self):
        self.action_add_students.setEnabled(self.db_connected)
        self.action_new_course.setEnabled(self.db_connected)
        self.action_companies.setEnabled(self.db_connected)
        self.action_new_theory.setEnabled(self.has_course)
        self.action_new_practice.setEnabled(self.has_course)

    @property
    def has_course(self):
        if not self.db_connected:
            return False
        s = self.Session()
        q = s.query(db.Course)
        return bool(q.count())

    @property
    def has_students(self):
        if not self.db_connected:
            return False
        s = self.Session()
        q = s.query(db.Student)
        return bool(q.count())

    def item_clicked(self, item, col):
        print('Clicked:', item.type_)

    def item_right_clicked(self, pos):
        item = self.nav.itemAt(pos)
        print('Right Clicked:', item.type_)
        menu = QtWidgets.QMenu(self)
        menu.addAction(self.action_new_db)
        menu.exec_(self.nav.mapToGlobal(pos))

    def add_students(self):
        dlg = dialogs.StudentDialog(self, UI_PATH)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            count = dlg.count.value()
        else:
            print('cancel')
            return
        win = QtWidgets.QMdiSubWindow(self)
        widget = widgets.StudentsWidget(UI_PATH, self.status, self.Session(),
                                        count)
        win.setWidget(widget)
        win.setWindowIcon(QtGui.QIcon(':/icons/group-new'))
        self.main.addSubWindow(win)
        self.subwindows['students'] = win
        win.show()

    def open_db(self):
        dbfile = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Datenbank Datei wählen', widgets.STARTDIR,
            'Noten Dateien (*.gmandb)'
        )
        if dbfile[0]:
            dbfile = dbfile[0]
            if os.path.isfile(dbfile):
                self.load_db(dbfile)

    def load_db(self, dbfile):
        self.nav.clear()
        self.status.showMessage('Lade {}'.format(dbfile), 5000)
        self.dbfile = dbfile
        self.Session = db.get_session('sqlite:///{}'.format(dbfile))
        s = self.Session()
        base = s.query(db.BaseData).first()
        self.top = items.BaseItem(self.nav, [base.group_name],
                                  QtGui.QIcon(':/icons/top'))
        self.nav.addTopLevelItem(self.top)
        group = items.GroupItem(self.top)
        for student in s.query(db.Student).order_by(db.Student.last_name).all():
            stud = items.StudentItem(group, student)
            group.addChild(stud)
        self.top.addChild(group)
        for course in s.query(db.Course).order_by(db.Course.start).all():
            co = items.CourseItem(self.top, course)
            theory = items.BaseItem(co, ['Theorie'])
            co.addChild(theory)
            q = s.query(db.Test).filter(db.Test.course==course).order_by(
                db.Test.done_on
            )
            for t in q.all():
                test = items.TestItem(theory, t)
                theory.addChild(test)
            practice = items.BaseItem(co, ['Praxis'])
            co.addChild(practice)
            q = s.query(db.Experiment).filter(
                db.Experiment.course==course).order_by(db.Experiment.done_on)
            for e in q.all():
                exp = items.ExperimentItem(practice, e)
                practice.addChild(exp)
            self.top.addChild(co)
        self.db_connected = True
        self._check_available_actions()
        self.top.setExpanded(True)

    def create_new_db(self):
        print('new db')
        new_db_window = QtWidgets.QMdiSubWindow(self)
        widget = widgets.NewDBWidget(UI_PATH, self.status)
        widget.db_created.connect(self.load_db)
        widget.finished.connect(new_db_window.close)
        new_db_window.setWidget(widget)
        new_db_window.setObjectName('NewDBWindow')
        new_db_window.setWindowTitle('DB erstellen')
        new_db_window.setWindowIcon(QtGui.QIcon(':/icons/db-new'))
        self.main.addSubWindow(new_db_window)
        new_db_window.show()

    def edit_companies(self):
        win = QtWidgets.QMdiSubWindow(self)
        widget = widgets.CompaniesWidget(UI_PATH, self.status, self.Session())
        win.setWidget(widget)
        win.setWindowIcon(QtGui.QIcon(':/icons/add'))
        self.main.addSubWindow(win)
        self.subwindows['companies'] = win
        win.show()

    def new_course(self):
        print('new course')
        win = QtWidgets.QMdiSubWindow(self)
        widget = widgets.CourseWidget(UI_PATH, self.status, self.Session())
        win.setWidget(widget)
        win.setWindowIcon(QtGui.QIcon(':/icons/course-new'))
        self.main.addSubWindow(win)
        self.subwindows['courses'] = win
        win.show()


def main():
    if len(sys.argv) > 1:
        db = sys.argv.pop(1)
    else:
        db = ''
    app = QtWidgets.QApplication(sys.argv)
    gmm = GradeManagerMain(db)
    gmm.show()
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
