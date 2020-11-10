import logging
import os
import sys

sys.path.extend(['./'])

from librus_tricks import create_session, cache, use_json

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(module)s:%(lineno)d - %(funcName)s - %(message)s',
                    filename='pytest.log')


def ensure_session():
    if 'session' not in globals():
        global EMAIL
        global PASSWORD
        global session
        try:
            session = use_json()
        except Exception:
            EMAIL = os.environ['librus_email']
            PASSWORD = os.environ['librus_password']
            session = create_session(EMAIL, PASSWORD, cache=cache.AlchemyCache(engine_uri='sqlite:///:memory:'))


def test_grades():
    ensure_session()
    grades = session.grades()
    teachers = [x.teacher for x in grades]
    subjects = [x.subject for x in grades]
    cats = [x.category for x in grades]
    return teachers, subjects, cats


def test_grades_gather():
    ensure_session()
    grades = session.grades()
    for grade in grades:
        assert grade.uid == session.grades(grade.uid)[0].uid


def test_attendances():
    ensure_session()
    att = session.attendances()
    types = [x.type for x in att]
    return att, types


def test_attendances_gather():
    ensure_session()
    att = session.attendances()
    for at in att:
        assert at.uid == session.attendances(at.uid)[0].uid


def test_timetable():
    ensure_session()
    timetable = session.today_timetable.lessons
    subjects = []
    for lesson in timetable:
        subjects.append(lesson.subject)


def test_color_gather():
    ensure_session()
    colors = session.colors()
    for color in colors:
        assert color.uid == session.colors(color.uid)[0].uid


def test_messages_scrapper():
    ensure_session()
    authors = []
    bodies = []
    messages = session.message_reader.read_messages()
    for mess in messages:
        authors.append(
            mess.author
        )
        bodies.append(
            mess.text
        )

    return authors, bodies


def test_native_message():
    ensure_session()
    topics = []
    authors = []
    content = []
    messages = session.messages()
    for message in messages:
        topics.append(
            message.topic
        )
        authors.append(
            message.sender
        )
        content.append(
            message.body
        )

    return topics, authors, content


def test_realizations_gather():
    ensure_session()
    realizations = session.realizations()
    for rel in realizations:
        assert rel.uid == session.realizations(rel.uid)[0].uid
