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


def test_percentages():
    ensure_session()
    from librus_tricks.tools import extracted_percentages
    return extracted_percentages(session.grades())
