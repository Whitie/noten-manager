# -*- coding: utf-8 -*-

import sqlalchemy as sa

from datetime import datetime
from getpass import getuser
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker


Base = declarative_base()


def get_session(connection_string='sqlite:///:memory:', echo=False):
    engine = sa.create_engine(connection_string, echo=echo)
    return sessionmaker(bind=engine)


def create_tables(session):
    Base.metadata.create_all(session.connection())


# ORM classes
class BaseData(Base):
    __tablename__ = 'base_data'

    pk = sa.Column(sa.Integer, primary_key=True)
    group_name = sa.Column(sa.Unicode(30))
    start = sa.Column(sa.Date)
    internal_code = sa.Column(sa.Unicode(30))
    institution = sa.Column(sa.UnicodeText)
    logo = sa.Column(sa.LargeBinary)

    def __str__(self):
        return '{} ({})'.format(
            self.group_name, self.start.strftime('%d.%m.%Y')
        )


class Course(Base):
    __tablename__ = 'courses'

    pk = sa.Column(sa.Integer, primary_key=True)
    title = sa.Column(sa.Unicode(100))
    trainer = sa.Column(sa.Unicode(150))
    start = sa.Column(sa.Date)
    end = sa.Column(sa.Date)
    rating = sa.Column(sa.Unicode(20), default='IHK')
    finished = sa.Column(sa.Boolean, default=False)
    printed = sa.Column(sa.Boolean, default=False)
    added = sa.Column(sa.DateTime, default=datetime.now)
    added_by = sa.Column(sa.Unicode(50), default=getuser)

    experiments = relationship('Experiment', order_by='Experiment.done_on',
                               back_populates='course')
    tests = relationship('Test', order_by='Test.done_on',
                         back_populates='course')

    def __str__(self):
        return '{}, {} ({} - {})'.format(
            self.title, self.trainer, self.start.strftime('%d.%m.%Y'),
            self.end.strftime('%d.%m.%Y')
        )

    @property
    def duration_weeks(self):
        duration = self.end - self.start
        return (duration.days + 4) // 7


class Company(Base):
    __tablename__ = 'companies'

    pk = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.Unicode(100))
    short_name = sa.Column(sa.Unicode(15))

    students = relationship('Student', order_by='Student.last_name',
                            back_populates='company')

    def __str__(self):
        return '{} ({})'.format(self.name, self.short_name)


class Student(Base):
    __tablename__ = 'students'

    pk = sa.Column(sa.Integer, primary_key=True)
    last_name = sa.Column(sa.Unicode(75))
    first_name = sa.Column(sa.Unicode(75))
    company_id = sa.Column(sa.Integer, sa.ForeignKey('companies.pk'))
    photo = sa.Column(sa.LargeBinary)
    show = sa.Column(sa.Boolean, default=True)

    company = relationship('Company', back_populates='students')
    practice_grades = relationship('PracticeGrade', back_populates='student')
    theory_grades = relationship('TheoryGrade', back_populates='student')
    conferences = relationship('ConferenceStudent', back_populates='student')

    def __str__(self):
        return '{}, {}'.format(self.last_name, self.first_name)

    @property
    def fullname(self):
        return '{}, {}'.format(self.last_name, self.first_name)


class Experiment(Base):
    __tablename__ = 'experiments'

    pk = sa.Column(sa.Integer, primary_key=True)
    title = sa.Column(sa.Unicode(100))
    done_on = sa.Column(sa.Date)
    weight = sa.Column(sa.Integer, default=100)
    notes = sa.Column(sa.UnicodeText)
    course_id = sa.Column(sa.Integer, sa.ForeignKey('courses.pk'))
    weight_method = sa.Column(sa.Integer, default=40)
    weight_result = sa.Column(sa.Integer, default=40)
    weight_docs = sa.Column(sa.Integer, default=20)
    presented = sa.Column(sa.Boolean, default=False)
    added = sa.Column(sa.DateTime, default=datetime.now)
    added_by = sa.Column(sa.Unicode(50), default=getuser)

    course = relationship('Course', back_populates='experiments')
    grades = relationship('PracticeGrade', back_populates='experiment')

    def __str__(self):
        return self.title


class Test(Base):
    __tablename__ = 'tests'

    pk = sa.Column(sa.Integer, primary_key=True)
    subject = sa.Column(sa.Unicode(100))
    course_id = sa.Column(sa.Integer, sa.ForeignKey('courses.pk'))
    done_on = sa.Column(sa.Date)
    weight = sa.Column(sa.Integer, default=100)
    notes = sa.Column(sa.UnicodeText)
    max_points = sa.Column(sa.Integer)
    presented = sa.Column(sa.Boolean, default=False)
    added = sa.Column(sa.DateTime, default=datetime.now)
    added_by = sa.Column(sa.Unicode(50), default=getuser)

    course = relationship('Course', back_populates='tests')
    grades = relationship('TheoryGrade', back_populates='test')

    def __str__(self):
        return '{}, {}'.format(
            self.subject, self.done_on.strftime('%d.%m.%Y')
        )


class Ratings(Base):
    __tablename__ = 'ratings'

    pk = sa.Column(sa.Integer, primary_key=True)
    key = sa.Column(sa.Unicode(20), nullable=False)
    points = sa.Column(sa.Integer, nullable=False)
    school_grade = sa.Column(sa.Numeric(precision=1), nullable=False)
    text_rating = sa.Column(sa.Unicode(20))

    def __str__(self):
        txt = '{}: {} -> {}'.format(self.key, self.points, self.school_grade)
        if self.text_rating:
            return '{} ({})'.format(txt, self.text_rating)
        return txt


class CourseData(Base):
    __tablename__ = 'coursedata'

    pk = sa.Column(sa.Integer, primary_key=True)
    job = sa.Column(sa.Unicode(5))
    title = sa.Column(sa.Unicode(100))

    def __str__(self):
        return '{} ({})'.format(self.title, self.job)


class PracticeGrade(Base):
    __tablename__ = 'practice_grades'

    pk = sa.Column(sa.Integer, primary_key=True)
    method = sa.Column(sa.Integer, default=None)
    result = sa.Column(sa.Integer, default=None)
    docs = sa.Column(sa.Integer, default=None)
    experiment_id = sa.Column(sa.Integer, sa.ForeignKey('experiments.pk'))
    student_id = sa.Column(sa.Integer, sa.ForeignKey('students.pk'))
    recorded = sa.Column(sa.DateTime, default=datetime.now)
    recorded_by = sa.Column(sa.Unicode(50), default=getuser)

    experiment = relationship('Experiment', back_populates='grades',
                              cascade='save-update, merge, delete')
    student = relationship('Student', back_populates='practice_grades',
                           cascade='save-update, merge, delete')

    @property
    def grade(self):
        weights = 0
        grades = 0
        if self.method is not None:
            grades += self.method * self.experiment.weight_method
            weights += self.experiment.weight_method
        if self.result is not None:
            grades += self.result * self.experiment.weight_result
            weights += self.experiment.weight_result
        if self.docs is not None:
            grades += self.docs * self.experiment.weight_docs
            weights += self.experiment.weight_docs
        if weights:
            return grades / weights


class TheoryGrade(Base):
    __tablename__ = 'theory_grades'

    pk = sa.Column(sa.Integer, primary_key=True)
    points = sa.Column(sa.Numeric(precision=1))
    test_id = sa.Column(sa.Integer, sa.ForeignKey('tests.pk'))
    student_id = sa.Column(sa.Integer, sa.ForeignKey('students.pk'))
    recorded = sa.Column(sa.DateTime, default=datetime.now)
    recorded_by = sa.Column(sa.Unicode(50), default=getuser)

    test = relationship('Test', back_populates='grades',
                        cascade='save-update, merge, delete')
    student = relationship('Student', back_populates='theory_grades',
                           cascade='save-update, merge, delete')

    @property
    def grade(self):
        return self.points / self.test.max_points


class Conference(Base):
    __tablename__ = 'conferences'

    pk = sa.Column(sa.Integer, primary_key=True)
    date = sa.Column(sa.Date)
    grades_til = sa.Column(sa.Date)
    title = sa.Column(sa.Unicode(60))

    students = relationship('ConferenceStudent', back_populates='conference')


class ConferenceStudent(Base):
    __tablename__ = 'conference_student'

    conference_id = sa.Column(sa.Integer, sa.ForeignKey('conferences.pk'),
                              primary_key=True)
    student_id = sa.Column(sa.Integer, sa.ForeignKey('students.pk'),
                           primary_key=True)
    note = sa.Column(sa.UnicodeText)

    conference = relationship('Conference', back_populates='students')
    student = relationship('Student', back_populates='conferences')
