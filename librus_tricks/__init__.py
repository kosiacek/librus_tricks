from librus_tricks import exceptions
from librus_tricks.auth import authorizer, load_json as __load_json
from librus_tricks.classes import *
from librus_tricks.core import SynergiaClient


__name__ = 'librus_tricks'
__title__ = 'librus_tricks'
__author__ = 'Krystian Postek'
__version__ = '0.8.1'


def create_session(email, password, fetch_first=True, **kwargs):
    """
    Używaj tego tylko kiedy hasło do Portal Librus jest takie samo jako do Synergii.

    :param email: str
    :param password: str
    :param fetch_first: bool or int
    :rtype: librus_tricks.core.SynergiaClient
    :return: obiekt lub listę obiektów z sesjami
    """
    if fetch_first is True:
        user = authorizer(email, password)[0]
        session = SynergiaClient(user, **kwargs)
    elif fetch_first is False:
        users = authorizer(email, password)
        sessions = [SynergiaClient(user, **kwargs) for user in users]
        return sessions
    else:
        user = authorizer(email, password)[fetch_first]
        session = SynergiaClient(user, **kwargs)

    return session


def use_json(file=None, **kwargs):
    if file is None:
        from glob import glob
        jsons = glob('*.json')

        if jsons.__len__() == 0:
            raise FileNotFoundError('Nie znaleziono zapisanych sesji')
        if jsons.__len__() > 1:
            raise FileExistsError('Zaleziono za dużo zapisanych sesji')

        user = __load_json(open(jsons[0], 'r'))
    else:
        user = __load_json(file)
    session = SynergiaClient(user, **kwargs)
    session.get('Me')
    return session


def minified_login(email, password, **kwargs):
    import logging
    import warnings

    warnings.warn(exceptions.SecurityWarning('Using minified_login in production environment is REAL SECURITY ISSUE!'))
    try:
        logging.debug('Trying to use json file to create session')
        session = use_json(**kwargs)
        logging.debug('Created session using json file')
    except Exception:
        logging.debug('Switching to regular http auth')
        session = create_session(email, password, **kwargs)
        logging.debug('Created session using http auth')

    session.user.dump_credentials()
    return session
