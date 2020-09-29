#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

from functools import partial
from getpass import getuser
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from . import crypto, db, dialogs, items, resources, widgets


PATH = os.path.dirname(os.path.abspath(__file__))
UI_PATH = os.path.join(PATH, 'ui')
DOC_PATH = os.path.join(PATH, 'docs')


class GradeManagerMain(QtWidgets.QMainWindow):

    def __init__(self, crypted_db=''):
        QtWidgets.QMainWindow.__init__(self)
        uic.loadUi(os.path.join(UI_PATH, 'main.ui'), self)
        self.setWindowTitle('bbz Notenmanager - {}'.format(getuser()))
        self._Session = None
        self.session = None
        self.db_connected = False
        self.subwindows = {}
        self.top = None
        self.crypted_db = crypted_db
        self.db_path = None
        self.handler = None
        if crypted_db:
            self.handler = self.get_crypto_handler()
            if self.handler:
                self.load_db(self.handler)
        self._connect_actions()
        self.nav.customContextMenuRequested.connect(self.item_right_clicked)
        self.nav.itemClicked.connect(self.item_clicked)
        self.nav.itemDoubleClicked.connect(self.item_doubleclicked)
        self._check_available_actions()

    def _connect_actions(self):
        self.action_new_db.triggered.connect(self.create_new_db)
        self.action_open_db.triggered.connect(self.open_db)
        self.action_add_students.triggered.connect(self.add_students)
        self.action_companies.triggered.connect(self.edit_companies)
        self.action_new_course.triggered.connect(self.new_course)
        self.action_edit_course.triggered.connect(self.edit_course)
        self.action_new_practice.triggered.connect(self.edit_practice)
        self.action_save_all.triggered.connect(self.save_all)
        self.action_help.triggered.connect(self.show_help)

    def _check_available_actions(self, *args, **kw):
        self.action_add_students.setEnabled(self.db_connected)
        self.action_new_course.setEnabled(self.db_connected)
        self.action_companies.setEnabled(self.db_connected)
        self.action_new_theory.setEnabled(self.has_course)
        self.action_new_practice.setEnabled(self.has_course)
        self.action_save_all.setEnabled(bool(self.subwindows))
        self.action_edit_course.setEnabled(self.item_selected('course'))

    def get_crypto_handler(self):
        dlg = dialogs.CredentialsDialog(self, UI_PATH, self.crypted_db)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            result = dict(auth=dlg.active, keyfile=dlg.keyfile_path.text(),
                          password=dlg.password.text())
        else:
            print('cancel')
            return
        if result['auth'] == 'keyfile':
            kw = dict(keyfile=result['keyfile'])
        else:
            kw = dict(password=result['password'])
        try:
            return crypto.CryptedDBHandler(self.crypted_db, **kw)
        except crypto.SetupError as err:
            QtWidgets.QMessageBox.critical(
                self, 'Datenbankfehler', str(err)
            )

    @property
    def has_course(self):
        if not self.db_connected:
            return False
        q = self.session.query(db.Course)
        return bool(q.count())

    @property
    def has_students(self):
        if not self.db_connected:
            return False
        q = self.session.query(db.Student)
        return bool(q.count())

    def item_selected(self, type_):
        item = self.nav.currentItem()
        if item is None or item.type_ != type_:
            return False
        return True

    def item_clicked(self, item, col):
        if item is None:
            return
        self._check_available_actions()
        print('Item clicked:', item.type_)

    def item_doubleclicked(self, item, col):
        if item is None:
            return
        print('Item doubleclicked:', item.type_)
        if item.type_ == 'experiment':
            self.edit_practice(practice=item.exp)
        elif item.type_ == 'course':
            self.new_course(course=item.course)

    def item_right_clicked(self, pos):
        item = self.nav.itemAt(pos)
        if item is None or item.type_ not in ('group', 'course'):
            return
        print('Right Clicked:', item.type_)
        menu = QtWidgets.QMenu(self)
        if item.type_ == 'group':
            menu.addAction(self.action_add_students)
        elif item.type_ == 'course':
            menu.addAction(self.action_edit_course)
            menu.addAction(self.action_new_theory)
            menu.addAction(self.action_new_practice)
        menu.exec_(self.nav.mapToGlobal(pos))

    def add_students(self):
        dlg = dialogs.StudentDialog(self, UI_PATH)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            count = dlg.count.value()
        else:
            print('cancel')
            return
        win = QtWidgets.QMdiSubWindow(self)
        widget = widgets.StudentsWidget(UI_PATH, self.status, self.session,
                                        count)
        widget.saved.connect(partial(self.load_db, handler=self.handler))
        widget.saved.connect(
            partial(self._subwindow_closed, window=win, name='students')
        )
        win.setWidget(widget)
        win.setWindowIcon(QtGui.QIcon(':/icons/group-new'))
        self.main.addSubWindow(win)
        self.subwindows['students'] = win
        win.show()
        self._check_available_actions()

    def open_db(self):
        crypted_db, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Datenbank Datei wählen', '.',
            'Noten Dateien (*.gmandb)'
        )
        if crypted_db and os.path.isfile(crypted_db):
            self.crypted_db = crypted_db
            self.handler = self.get_crypto_handler()
            if self.handler:
                self.load_db(self.handler)

    def load_db(self, handler):
        self.handler = handler
        if handler.useable:
            self.db_path = handler.db_path
        else:
            try:
                self.db_path = handler.decrypt()
            except crypto.CryptoKeyError as error:
                QtWidgets.QMessageBox.critical(
                    self, 'Fehler beim Entschlüsseln', str(error)
                )
                return
        self.nav.clear()
        self.status.showMessage('Lade {}'.format(self.db_path), 5000)
        self._Session = db.get_session('sqlite:///{}'.format(self.db_path))
        self.session = s = self._Session()
        base = s.query(db.BaseData).first()
        self.top = items.BaseItem(self.nav, [base.group_name],
                                  QtGui.QIcon(':/icons/top'))
        self.nav.addTopLevelItem(self.top)
        group = items.GroupItem(self.top)
        for student in s.query(db.Student).order_by(
                db.Student.last_name).all():
            stud = items.StudentItem(group, student)
            group.addChild(stud)
        group.setText(0, 'Teilnehmer ({})'.format(group.childCount()))
        self.top.addChild(group)
        for course in s.query(db.Course).order_by(db.Course.start).all():
            co = items.CourseItem(self.top, course)
            ov = items.OverviewItem(co)
            co.addChild(ov)
            theory = items.TheoryItem(
                co, ['Theorie'], QtGui.QIcon(':/icons/theory')
            )
            co.addChild(theory)
            for t in course.tests:
                test = items.TestItem(theory, t)
                theory.addChild(test)
            practice = items.PracticeItem(
                co, ['Praxis'], QtGui.QIcon(':/icons/practice')
            )
            co.addChild(practice)
            print('EXPs:', list(course.experiments))
            for e in course.experiments:
                print('EXP:', e)
                exp = items.ExperimentItem(practice, e)
                practice.addChild(exp)
            self.top.addChild(co)
        self.db_connected = True
        self.top.setExpanded(True)
        self._check_available_actions()

    def create_new_db(self):
        print('new db')
        new_db_window = QtWidgets.QMdiSubWindow(self)
        new_db_window.resize(580, 450)
        widget = widgets.CreateDBWizard(UI_PATH, self.status)
        widget.db_created.connect(self.load_db)
        widget.finished.connect(new_db_window.close)
        new_db_window.setWidget(widget)
        new_db_window.setObjectName('CreateDBWizard')
        self.main.addSubWindow(new_db_window)
        new_db_window.show()

    def edit_companies(self):
        win = QtWidgets.QMdiSubWindow(self)
        widget = widgets.CompaniesWidget(UI_PATH, self.status, self.session)
        win.setWidget(widget)
        win.setWindowIcon(QtGui.QIcon(':/icons/add'))
        self.main.addSubWindow(win)
        self.subwindows['companies'] = win
        win.show()
        self._check_available_actions()

    def edit_course(self):
        if not self.item_selected('course'):
            return
        item = self.nav.currentItem()
        self.new_course(course=item.course)

    def new_course(self, checked=False, course=None):
        print('new/edit course')
        win = QtWidgets.QMdiSubWindow(self)
        widget = widgets.CourseWidget(UI_PATH, self.status, self.session)
        win.setWidget(widget)
        win.setWindowIcon(QtGui.QIcon(':/icons/course-new'))
        widget.saved.connect(partial(self.load_db, handler=self.handler))
        widget.saved.connect(
            partial(self._subwindow_closed, window=win, name='courses')
        )
        self.main.addSubWindow(win)
        self.subwindows['courses'] = win
        if course is not None:
            widget.update(course)
        win.show()
        self._check_available_actions()

    def edit_practice(self, checked=False, practice=None):
        print('Add/edit practice')
        if self.item_selected('course'):
            item = self.nav.currentItem()
            course = item.course
        else:
            course = None
        win = QtWidgets.QMdiSubWindow(self)
        widget = widgets.ExperimentWidget(UI_PATH, self.session, course)
        win.setWidget(widget)
        widget.saved.connect(partial(self.load_db, handler=self.handler))
        widget.saved.connect(
            partial(self._subwindow_closed, window=win, name='experiment')
        )
        self.main.addSubWindow(win)
        self.subwindows['experiment'] = win
        if practice is not None:
            widget.update(practice)
        win.show()
        self._check_available_actions()

    def show_help(self):
        print('Help requested')
        dlg = dialogs.HelpDialog(self, UI_PATH, DOC_PATH)
        dlg.show()

    def _subwindow_closed(self, window, name):
        window.close()
        try:
            del self.subwindows[name]
        except KeyError:
            pass

    def save_all(self, on_close=False):
        for name, subwindow in self.subwindows.items():
            if isinstance(subwindow, list):
                for sub in subwindow:
                    self._save(name, sub, on_close)
            else:
                self._save(name, subwindow, on_close)
        self.subwindows = {}
        self._check_available_actions()

    def _save(self, name, window, on_close):
        print('Saving:', name, window)
        self.status.showMessage('Speichere: {}'.format(name))
        widget = window.widget()
        try:
            widget.save(on_close=on_close)
        except Exception as error:
            print('Fehler beim Speichern:', error)

    def closeEvent(self, event):
        if self.handler and self.handler.useable:
            self.save_all(True)
            print('Encrypting DB')
            self.handler.encrypt()
        event.accept()


def main():
    if len(sys.argv) > 1:
        crypted_db = sys.argv.pop(1)
    else:
        crypted_db = ''
    app = QtWidgets.QApplication(sys.argv)
    gmm = GradeManagerMain(crypted_db)
    gmm.show()
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
