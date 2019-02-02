# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QTreeWidgetItem
from PyQt5.QtGui import QIcon


def date_to_str(dt):
    try:
        return dt.strftime('%d.%m.%Y')
    except Exception as error:
        print(error)
        return '-'


class BaseItem(QTreeWidgetItem):
    type_ = 'base'

    def __init__(self, parent, text, icon=None):
        QTreeWidgetItem.__init__(self, parent, text)
        if icon is not None:
            self.setIcon(0, icon)


class GroupItem(QTreeWidgetItem):
    type_ = 'group'

    def __init__(self, parent):
        QTreeWidgetItem.__init__(self, parent, ['Teilnehmer'])
        self.setIcon(0, QIcon(':/icons/group'))


class StudentItem(QTreeWidgetItem):
    type_ = 'student'

    def __init__(self, parent, student):
        QTreeWidgetItem.__init__(self, parent, [student.fullname])
        self.student = student
        self.setIcon(0, QIcon(':/icons/student'))


class CourseItem(QTreeWidgetItem):
    type_ = 'course'

    def __init__(self, parent, course):
        QTreeWidgetItem.__init__(self, parent, [course.title])
        self.course = course
        self.setIcon(0, QIcon(':/icons/course'))


class ExperimentItem(QTreeWidgetItem):
    type_ = 'experiment'

    def __init__(self, parent, exp):
        QTreeWidgetItem.__init__(
            self, parent,
            ['{} ({})'.format(exp.title, date_to_str(exp.done_on))]
        )
        self.exp = exp
        self.setIcon(0, QIcon(':/icons/practice'))


class TestItem(QTreeWidgetItem):
    type_ = 'test'

    def __init__(self, parent, test):
        QTreeWidgetItem.__init__(
            self, parent,
            ['{} ({})'.format(test.subject, date_to_str(test.done_on))]
        )
        self.test = test
        self.setIcon(0, QIcon(':/icons/theory'))


class CompanyItem(QTreeWidgetItem):

    def __init__(self, parent, company):
        if company:
            text = [company.short_name, company.name]
        else:
            text = ['Kürzel', 'Voller Name']
        QTreeWidgetItem.__init__(self, parent, text)
        self.company = company
        self.modified = False
