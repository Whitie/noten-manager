# -*- coding: utf-8 -*-

import os

from datetime import date, timedelta
from functools import partial
from PyQt5 import Qt, QtCore, QtGui, QtWidgets, uic

from . import db, dialogs, items, resources, utils
from .data import IHK, COURSES


PATH = os.path.dirname(os.path.abspath(__file__))
STARTDIR = r'\\DC1SBS2011\Zensuren'
INSTITUTION = 'Bildungswerk Nordostchemie e. V.'
LOGO = os.path.join(PATH, 'theme', 'bbz_logo.png')


class NewDBWidget(QtWidgets.QWidget):

    db_created = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def __init__(self, ui_path, status, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        uic.loadUi(os.path.join(ui_path, 'new_db.ui'), self)
        self.status = status
        self.btn_path.clicked.connect(self.get_path)
        self.btn_save.clicked.connect(self.save_new_db)
        self.btn_logo.clicked.connect(self.get_logo)
        self.btn_save.setEnabled(False)
        self.group.textChanged.connect(self.check_inputs)
        self.path.textChanged.connect(self.check_inputs)
        self.own_name.setText(INSTITUTION)
        self.logo.setText(LOGO)
    
    def get_path(self):
        dir_ = QtWidgets.QFileDialog.getExistingDirectory(
            self, 'Verzeichnis auswählen', STARTDIR
        )
        if dir_:
            self.path.setText(dir_)

    def get_logo(self):
        file_ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Logo auswählen', STARTDIR, 'Bilddateien (*.png *.jpg)'
        )
        if file_[0]:
            self.logo.setText(file_[0])

    def save_new_db(self):
        group = self.group.text().strip()
        save_path = self.path.text().strip()
        date = self.start.date()
        logo = self.logo.text().strip()
        filename = os.path.join(save_path,
                                '{}.gmandb'.format(group.replace(' ', '_')))
        self.status.showMessage('Erstelle Datei {}'.format(filename), 2000)
        Session = db.get_session('sqlite:///{}'.format(filename))
        s = Session()
        self.status.showMessage('Erstelle Datenbanktabellen', 2000)
        db.create_tables(s)
        base = db.BaseData(
            group_name=group, start=date.toPyDate(),
            internal_code=self.internal.text().strip(),
            institution=self.own_name.text()    
        )
        if logo:
            with open(logo, 'rb') as fp:
                base.logo = fp.read()
        s.add(base)
        for points, school, text in IHK:
            s.add(
                db.Ratings(key='IHK', points=points, school_grade=school,
                           text_rating=text)
            )
        for job, courses in COURSES.items():
            for course in courses:
                s.add(db.CourseData(job=job, title=course))
        s.commit()
        self.status.showMessage('Datei ist jetzt verwendbar', 5000)
        self.db_created.emit(filename)
        self.finished.emit()

    def check_inputs(self, text):
        group = self.group.text()
        save_path = self.path.text()
        is_valid = os.path.isdir(save_path)
        date = self.start.date()
        if group and save_path and date and is_valid:
            self.btn_save.setEnabled(True)
        else:
            self.btn_save.setEnabled(False)

    def save(self):
        pass


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
    
    def save(self):
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
        l = QtWidgets.QHBoxLayout()
        if not student.show:
            box.setCheckState(QtCore.Qt.Unchecked)
        else:
            box.setCheckState(QtCore.Qt.Checked)
        l.addWidget(box)
        l.setAlignment(QtCore.Qt.AlignCenter)
        wid.setLayout(l)
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

    def save(self):
        for row in range(self.table.rowCount()):
            wid = self.table.item(row, 0)
            if not wid:
                continue
            name = wid.text().strip()
            if name:
                student = self.students[row]
                student.last_name = name
                student.first_name = self.table.item(row, 1).text().strip()
                student.company_id = self.table.cellWidget(row, 2
                    ).currentData()
                self.session.add(student)
        self.session.commit()


class CourseWidget(QtWidgets.QWidget):

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

    def save(self):
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
        self.close()
