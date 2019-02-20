# -*- coding: utf-8 -*-

import os

from datetime import date, timedelta
from collections import OrderedDict
from functools import partial
from PyQt5 import Qt, QtCore, QtGui, QtWidgets, uic

from . import crypto, db, dialogs, items, resources, utils
from .data import IHK, COURSES


STARTDIR = os.path.expanduser('~') or '.'


class CreateDBWizard(QtWidgets.QWizard):

    db_created = QtCore.pyqtSignal(crypto.CryptedDBHandler)

    def __init__(self, ui_path, status, parent=None):
        QtWidgets.QWizard.__init__(self, parent)
        self.status = status
        self.values = OrderedDict()
        self.setWindowTitle('Neue Datenbank erstellen')
        self.setWindowIcon(QtGui.QIcon(':/icons/db-new'))
        self.addPage(CreateDBWizardPage1(ui_path, self))
        self.addPage(CreateDBWizardPage2(ui_path, self))
        self.addPage(CreateDBWizardPage3(ui_path, self))
        self.addPage(CreateDBWizardPage4(ui_path, self))

    def create_new_db(self):
        group = self.values['group']
        save_path = self.values['save_path']
        date = self.values['start_date']
        logo = self.values['logo']
        if self.values['auth'] == 'file':
            keyfile = self.values['file']
            password = None
        else:
            keyfile = None
            password = self.values['password']
        crypted = os.path.join(
            save_path, '{}.gmandb'.format(group.replace(' ', '_'))
        )
        self.status.showMessage(
            'Erstelle verschlüsselte Datei {}'.format(crypted)
        )
        handler = crypto.CryptedDBHandler(crypted, keyfile, password)
        db_path = handler.decrypt()
        Session = db.get_session('sqlite:///{}'.format(db_path), False)
        s = Session()
        self.status.showMessage('Erstelle Datenbanktabellen')
        db.create_tables(s)
        self.status.showMessage('Schreibe Basisdaten')
        base = db.BaseData(
            group_name=group, start=date.toPyDate(),
            internal_code=self.values['internal_name'],
            institution=self.values['own_name']
        )
        if logo:
            with open(logo, 'rb') as fp:
                base.logo = fp.read()
        s.add(base)
        self.status.showMessage('Schreibe Punktschlüssel')
        for points, school, text in IHK:
            s.add(
                db.Ratings(key='IHK', points=points, school_grade=school,
                           text_rating=text)
            )
        self.status.showMessage('Schreibe Kurse')
        for job, courses in COURSES.items():
            for course in courses:
                s.add(db.CourseData(job=job, title=course))
        s.commit()
        self.status.showMessage('Die Datenbank ist jetzt verwendbar')
        QtWidgets.QMessageBox.information(
            self, 'Datenbank wurde erfolgreich erstellt',
            'Bewahren Sie den Schlüssel / das Passwort gut auf!'
        )
        self.db_created.emit(handler)

    def save(self, on_close=False):
        pass


class CreateDBWizardPage1(QtWidgets.QWizardPage):

    def __init__(self, ui_path, parent):
        QtWidgets.QWizardPage.__init__(self, parent)
        uic.loadUi(os.path.join(ui_path, 'create_db_wiz_1.ui'), self)
        self.btn_logo.clicked.connect(self.get_logo)

    def validatePage(self):
        text = self.own_name.text().strip()
        if len(text) >= 3:
            self.wizard().values['own_name'] = text
            self.wizard().values['logo'] = self.logo.text().strip()
            return True
        return False

    def get_logo(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Logo auswählen', STARTDIR, 'Bilddateien (*.png *.jpg)'
        )
        if filename:
            self.logo.setText(filename)


class CreateDBWizardPage2(QtWidgets.QWizardPage):

    def __init__(self, ui_path, parent):
        QtWidgets.QWizardPage.__init__(self, parent)
        uic.loadUi(os.path.join(ui_path, 'create_db_wiz_2.ui'), self)
        self.btn_path.clicked.connect(self.get_path)

    def validatePage(self):
        group = self.group.text().strip()
        start_date = self.start_date.date()
        save_path = self.save_path.text().strip()
        internal_name = self.internal_name.text().strip()
        if group and start_date and save_path:
            self.wizard().values['group'] = group
            self.wizard().values['start_date'] = start_date
            self.wizard().values['save_path'] = save_path
            self.wizard().values['internal_name'] = internal_name
            return True
        return False

    def get_path(self):
        dir_ = QtWidgets.QFileDialog.getExistingDirectory(
            self, 'Verzeichnis auswählen', STARTDIR
        )
        if dir_:
            self.save_path.setText(dir_)


class CreateDBWizardPage3(QtWidgets.QWizardPage):

    def __init__(self, ui_path, parent):
        QtWidgets.QWizardPage.__init__(self, parent)
        uic.loadUi(os.path.join(ui_path, 'create_db_wiz_3.ui'), self)
        self.yes = QtGui.QPixmap(':/icons/yes')
        self.no = QtGui.QPixmap(':/icons/no')
        self.opt_keyfile.toggled.connect(self._enable_fields)
        self.password_1.textChanged.connect(self._validate_passwords)
        self.password_2.textChanged.connect(self._validate_pw_2)
        self.btn_path.clicked.connect(self.get_path)
        self.active = 'keyfile'

    def validatePage(self):
        if self.active == 'keyfile':
            filename = self.keyfile_path.text().strip()
            if filename:
                self.wizard().values['auth'] = 'file'
                self.wizard().values['file'] = filename
                return True
            return False
        else:
            password = self.password_1.text().strip()
            self.wizard().values['auth'] = 'password'
            self.wizard().values['password'] = password
            return self._validate_passwords(password)

    def initializePage(self):
        group = self.wizard().values['group']
        self.startpath = os.path.join(
            STARTDIR, '{group}.key'.format(group=group)
        )
        self.keyfile_path.setText(self.startpath)

    def get_path(self):
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Datei speichern', self.startpath,
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
        self.btn_path.setEnabled(enable)
        self.password_1.setDisabled(enable)
        self.password_2.setDisabled(enable)
        self.pw_match.setDisabled(enable)

    def _validate_pw_2(self, pw_2):
        return self._validate_passwords(self.password_1.text())

    def _validate_passwords(self, pw_1):
        pw_1 = pw_1.strip()
        pw_2 = self.password_2.text().strip()
        if len(pw_1) >= 5 and pw_1 == pw_2:
            self.pw_match.setPixmap(self.yes)
            return True
        else:
            self.pw_match.setPixmap(self.no)
            return False


class CreateDBWizardPage4(QtWidgets.QWizardPage):

    def __init__(self, ui_path, parent):
        QtWidgets.QWizardPage.__init__(self, parent)
        uic.loadUi(os.path.join(ui_path, 'create_db_wiz_4.ui'), self)
        self.btn_password.pressed.connect(self._show_password)
        self.btn_password.released.connect(self._hide_password)
        self.btn_create_db.clicked.connect(self._create_db)

    def initializePage(self):
        store = self.wizard().values
        date = store['start_date'].toPyDate()
        self.name.setText(store['own_name'])
        self.logo.setText(store['logo'] or '-')
        self.group.setText(store['group'])
        self.start_date.setText(date.strftime('%d.%m.%Y'))
        self.internal_name.setText(store['internal_name'] or '-')
        self.save_path.setText(store['save_path'])
        self.keyfile.setText(store.get('file', '-'))
        if store['auth'] == 'password':
            self.password.setText('***')
            self.btn_password.setEnabled(True)
        else:
            self.password.setText('-')

    def _show_password(self):
        self.password.setText(self.wizard().values['password'])

    def _hide_password(self):
        self.password.setText('***')

    def _create_db(self, checked):
        print('Create DB')
        self.btn_create_db.setDisabled(True)
        self.wizard().create_new_db()
        self.btn_create_db.setIcon(QtGui.QIcon(':/icons/yes'))


class CompaniesWidget(QtWidgets.QWidget):

    def __init__(self, ui_path, status, session, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        uic.loadUi(os.path.join(ui_path, 'companies.ui'), self)
        self.status = status
        self.session = session
        self.to_remove = []
        self.status.showMessage('Lade vorhandene Firmen', 5000)
        self.load_tree()
        self.companies.itemChanged.connect(self.item_changed)
        self.companies.itemClicked.connect(self._enable_remove)
        self.btn_new.clicked.connect(self.new_item)
        self.btn_remove.clicked.connect(self.remove_item)
        self.btn_save.clicked.connect(self.save_item)

    def _enable_remove(self, item, col):
        self.btn_remove.setEnabled(True)

    def load_tree(self):
        self.companies.clear()
        q = self.session.query(db.Company).order_by(db.Company.short_name)
        for c in q.all():
            item = items.CompanyItem(self.companies, c)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
            self.companies.addTopLevelItem(item)

    def new_item(self):
        company = db.Company(name='Langer Name', short_name='Kürzel')
        item = items.CompanyItem(self.companies, company)
        item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
        self.companies.addTopLevelItem(item)
        self.companies.setCurrentItem(item)
        self.btn_save.setEnabled(True)

    def remove_item(self):
        item = self.companies.currentItem()
        index = self.companies.indexOfTopLevelItem(item)
        self.companies.takeTopLevelItem(index)
        self.to_remove.append(item.company)
        self.btn_save.setEnabled(True)

    def save(self, on_close=False):
        self.status.showMessage('Speichere Firmen', 5000)
        iterator = QtWidgets.QTreeWidgetItemIterator(self.companies)
        while iterator.value():
            item = iterator.value()
            iterator += 1
            if item.modified:
                self.session.add(item.company)
        for c in self.to_remove:
            self.session.delete(c)
        self.session.commit()

    def save_item(self):
        self.save()
        self.btn_save.setDisabled(True)
        self.load_tree()

    def item_changed(self, item, col):
        item.company.short_name = item.text(0)
        item.company.name = item.text(1)
        item.modified = True
        self.btn_save.setEnabled(True)


class StudentsWidget(QtWidgets.QWidget):

    saved = QtCore.pyqtSignal()

    def __init__(self, ui_path, status, session, new_count=0, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        uic.loadUi(os.path.join(ui_path, 'students.ui'), self)
        self.status = status
        self.session = session
        self.new_count = new_count
        self.students = {}
        self.load_data()
        self.btn_save.clicked.connect(self.save)

    def _get_companies(self, current_text=''):
        q = self.session.query(db.Company).order_by(db.Company.name)
        box = QtWidgets.QComboBox(self.table)
        for c in q.all():
            box.addItem(c.name, c.pk)
        if current_text:
            box.setCurrentText(current_text)
        return box

    def _get_photo_widget(self, row, student):
        btn = QtWidgets.QPushButton(self.table)
        btn.setToolTip('Foto hinzufügen / ändern')
        btn.clicked.connect(partial(self._edit_photo, student, btn))
        if student.photo:
            pic = QtGui.QPixmap()
            pic.loadFromData(student.photo)
            icon = QtGui.QIcon(pic)
            btn.setIcon(icon)
        else:
            btn.setText('...')
        return btn

    def _get_checkbox(self, student):
        wid = QtWidgets.QWidget(self.table)
        wid.setToolTip('Teilnehmer, die vorzeitig ausgeschieden sind, können '
                       'hier ausgeblendet werden.')
        box = QtWidgets.QCheckBox(wid)
        box.stateChanged.connect(partial(self._state_changed, student))
        layout = QtWidgets.QHBoxLayout()
        if not student.show:
            box.setCheckState(QtCore.Qt.Unchecked)
        else:
            box.setCheckState(QtCore.Qt.Checked)
        layout.addWidget(box)
        layout.setAlignment(QtCore.Qt.AlignCenter)
        wid.setLayout(layout)
        return wid

    def load_data(self):
        q = self.session.query(db.Student).order_by(db.Student.last_name)
        count = q.count()
        for i, s in enumerate(q.all()):
            self.students[i] = s
            self.table.insertRow(i)
            self.table.setItem(
                i, 0, QtWidgets.QTableWidgetItem(s.last_name)
            )
            self.table.setItem(
                i, 1, QtWidgets.QTableWidgetItem(s.first_name)
            )
            self.table.setCellWidget(i, 2, self._get_companies(s.company.name))
            self.table.setCellWidget(i, 3, self._get_photo_widget(i, s))
            self.table.setCellWidget(i, 4, self._get_checkbox(s))
        for i in range(count, count + self.new_count):
            s = self.students[i] = db.Student()
            self.table.insertRow(i)
            self.table.setItem(
                i, 0, QtWidgets.QTableWidgetItem('')
            )
            self.table.setItem(
                i, 1, QtWidgets.QTableWidgetItem('')
            )
            self.table.setCellWidget(i, 2, self._get_companies())
            self.table.setCellWidget(i, 3, self._get_photo_widget(i, s))
            self.table.setCellWidget(i, 4, self._get_checkbox(s))

    def _edit_photo(self, student, btn):
        photo = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Foto auswählen', STARTDIR, 'Bilddateien (*.png *.jpg)'
        )
        if not photo[0]:
            return
        student.photo = utils.make_image(photo[0])
        pic = QtGui.QPixmap()
        pic.loadFromData(student.photo)
        icon = QtGui.QIcon(pic)
        btn.setIcon(icon)
        btn.setText('')

    def _state_changed(self, student, new_state):
        student.show = bool(new_state)

    def save(self, on_close=False):
        for row in range(self.table.rowCount()):
            wid = self.table.item(row, 0)
            if not wid:
                continue
            name = wid.text().strip()
            if name:
                student = self.students[row]
                student.last_name = name
                student.first_name = self.table.item(row, 1).text().strip()
                student.company_id = self.table.cellWidget(
                    row, 2
                ).currentData()
                self.session.add(student)
        self.session.commit()
        if not on_close:
            self.saved.emit()


class CourseWidget(QtWidgets.QWidget):

    saved = QtCore.pyqtSignal()

    def __init__(self, ui_path, status, session, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        uic.loadUi(os.path.join(ui_path, 'new_course.ui'), self)
        self.ui_path = ui_path
        self.status = status
        self.session = session
        self.group = self._get_group()
        self.init_boxes()
        self.trainer.lineEdit().setMaxLength(150)
        self.title.textEdited.connect(self._enable_save)
        self.btn_save.clicked.connect(self.save)
        self.btn_courses.clicked.connect(self.find_course)

    def _enable_save(self, text):
        if text.strip():
            self.btn_save.setEnabled(True)
        else:
            self.btn_save.setDisabled(True)

    def _get_group(self):
        data = self.session.query(db.BaseData).first()
        return data.group_name

    def init_boxes(self):
        trainers = set()
        for course in self.session.query(db.Course).all():
            trainers.add(course.trainer)
        keys = set()
        for rating in self.session.query(db.Ratings).all():
            keys.add(rating.key)
        for tr in trainers:
            self.trainer.addItem(tr)
        for key in keys:
            self.rating.addItem(key)
        today = date.today()
        end = today + timedelta(days=14)
        self.start.setDate(today)
        self.end.setDate(end)

    def find_course(self):
        if self.group.upper().startswith('BW'):
            job = self.group[2:4]
        else:
            job = self.group[:2]
        courses = self.session.query(db.CourseData).filter(
            db.CourseData.job.like(job.upper())
        ).all()
        dlg = dialogs.CourseDialog(self, self.ui_path, courses)
        dlg.show()

    def save(self, on_close=False):
        title = self.title.text()
        trainer = self.trainer.currentText()
        start = self.start.date().toPyDate()
        end = self.end.date().toPyDate()
        rating = self.rating.currentText()
        course = db.Course(
            title=title, trainer=trainer, start=start, end=end, rating=rating
        )
        self.session.add(course)
        self.session.commit()
        self.status.showMessage('Neuer Kurs wurde gespeichert.', 5000)
        if not on_close:
            self.saved.emit()
