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
            session.user.dump_credentials()


def test_auth():
    ensure_session()
    if not session.user.is_valid:
        session.user.revalidate_user()
    assert session.user.is_valid is True


def test_attendance():
    ensure_session()
    return session.attendances()


def test_exams():
    ensure_session()
    return session.exams()


def test_grades():
    ensure_session()
    return session.grades()


def test_timetable():
    ensure_session()
    return session.tomorrow_timetable, session.today_timetable, session.timetable()


def test_newsfeed():
    ensure_session()
    return session.news_feed()


def test_messages():
    ensure_session()
    return session.messages(), session.message_reader.read_messages()


def test_colors():
    ensure_session()
    return session.colors()


def test_subjects():
    ensure_session()
    return session.subjects()


def test_school():
    ensure_session()
    return session.school


def test_lucky():
    ensure_session()
    return session.lucky_number


def test_free_days():
    ensure_session()
    return session.school_free_days()
