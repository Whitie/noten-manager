# -*- coding: utf-8 -*-

import os
import unittest

from datetime import date
from decimal import Decimal as D
from gman import db, utils
from gman.crypto import CryptedDBHandler
from gman.data import IHK, COURSES


PATH = os.path.dirname(os.path.abspath(__file__))
TEST_DB = os.path.join(PATH, 'tests.gmandb')
PASSWORD = 'This#is#the#test#password'
CONNECTION_STRING = 'sqlite:///{}'
TEST_IMAGE = os.path.join(PATH, 'people-icon.jpg')
TEST_LOGO = os.path.join(PATH, 'gman', 'theme', 'bbz_logo.png')


def add_ratings_and_courses(session):
    for p, g, r in IHK:
        session.add(
            db.Ratings(key='IHK', points=p, school_grade=g, text_rating=r)
        )
    for job, courses in COURSES.items():
        for course in courses:
            session.add(
                db.CourseData(job=job, title=course)
            )
    session.commit()


def create_base_data(session):
    data = db.BaseData(group_name='BWCL 125', start=date(2020, 1, 2),
                       internal_code='CL 01/20')
    data.institution = 'Bildungswerk Nordostchemie e. V.'
    with open(TEST_LOGO, 'rb') as fp:
        data.logo = fp.read()
    session.add(data)
    session.commit()
    return data


def create_course(session):
    course = db.Course(title='Grundbildung', trainer='Hr. Dummy',
                       start=date(2020, 1, 2), end=date(2020, 3, 31))
    session.add(course)
    session.commit()
    return course


def create_company(session):
    company = db.Company(name='Meine kleine Firma', short_name='MKF')
    company2 = db.Company(name='Meine zweite Firma', short_name='MZF')
    session.add_all([company, company2])
    session.commit()
    return company


def create_students(session, company):
    mm = db.Student(last_name='Mustermann', first_name='Max',
                    company=company)
    mm.photo = utils.make_image(TEST_IMAGE)
    pm = db.Student(last_name='Musterfrau', first_name='Paula',
                    company=company)
    students = [mm, pm]
    session.add_all(students)
    session.commit()
    return students


def create_experiments(session, course):
    exp1 = db.Experiment(title='Glasbearbeitung', done_on=date(2020, 1, 3),
                         course=course)
    exp2 = db.Experiment(title='Volumenmessungen', done_on=date(2020, 1, 4),
                         course=course)
    exps = [exp1, exp2]
    session.add_all(exps)
    session.commit()
    return exps


def create_tests(session, course):
    test1 = db.Test(subject='Basistest', done_on=date(2020, 1, 2),
                    course=course, weight=0, max_points=45)
    test2 = db.Test(subject='Glas', done_on=date(2020, 1, 10), course=course,
                    max_points=30)
    tests = [test1, test2]
    session.add_all(tests)
    session.commit()
    return tests


def add_practice_grades(session, students, exps):
    mm, pm = students
    exp1, exp2 = exps
    grades = [
        db.PracticeGrade(result=89, experiment=exp1, student=mm),
        db.PracticeGrade(method=82, result=95, docs=95, experiment=exp2,
                         student=mm),
        db.PracticeGrade(result=95, experiment=exp1, student=pm),
        db.PracticeGrade(method=90, result=90, docs=50, experiment=exp2,
                         student=pm),
    ]
    session.add_all(grades)
    session.commit()
    return grades


def add_theory_grades(session, students, tests):
    mm, pm = students
    test1, test2 = tests
    grades = [
        db.TheoryGrade(points=D(17), test=test1, student=mm),
        db.TheoryGrade(points=D('28.5'), test=test2, student=mm),
        db.TheoryGrade(points=D(9), test=test1, student=pm),
        db.TheoryGrade(points=D(14), test=test2, student=pm),
    ]
    session.add_all(grades)
    session.commit()
    return grades


def setup_db():
    handler = CryptedDBHandler(TEST_DB, password=PASSWORD)
    db_path = handler.decrypt()
    connection_string = CONNECTION_STRING.format(db_path)
    Session = db.get_session(connection_string)
    s = Session()
    db.create_tables(s)
    create_base_data(s)
    add_ratings_and_courses(s)
    course = create_course(s)
    company = create_company(s)
    students = create_students(s, company)
    exps = create_experiments(s, course)
    tests = create_tests(s, course)
    add_practice_grades(s, students, exps)
    add_theory_grades(s, students, tests)
    handler.encrypt()


class TestDB(unittest.TestCase):

    def setUp(self):
        self.handler = CryptedDBHandler(TEST_DB, password=PASSWORD)
        db_path = handler.decrypt()
        connection_string = CONNECTION_STRING.format(db_path)
        Session = db.get_session(connection_string)
        self.s = Session()

    def tearDown(self):
        self.s.close()
        self.handler.encrypt()
        self.s = None
        self.handler = None


if __name__ == '__main__':
    setup_db()
    unittest.main()
    #os.remove(TEST_DB)
