import logging
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

from .exceptions import *

# Some globals
REDIRURL = 'app://librus'
LOGINURL = 'https://portal.librus.pl/rodzina/login/action'
OAUTHURL = 'https://portal.librus.pl/oauth2/access_token'
SYNERGIAAUTHURL = 'https://portal.librus.pl/api/v2/SynergiaAccounts'
FRESHURL = 'https://portal.librus.pl/api/v2/SynergiaAccounts/fresh/{login}'
CLIENTID = "VaItV6oRutdo8fnjJwysnTjVlvaswf52ZqmXsJGP"
LIBRUSLOGINURL = f'https://portal.librus.pl/oauth2/authorize?client_id={CLIENTID}&redirect_uri={REDIRURL}&response_type=code'
# User agents
XIAOMI_USERAGENT = 'Dalvik/2.1.0 (Linux; U; Android 10; Mi 9T Build/QQ3A.200905.001)LibrusMobileApp'
GOOGLEBOT_USERAGENT = 'Googlebot/2.1 (+http://www.google.com/bot.html)LibrusMobileApp'

class SynergiaUser:
    """
    Obiekt zawierający dane do tworzenia sesji
    """

    def __init__(self, user_dict, root_token, revalidation_token, exp_in):
        self.token = user_dict['accessToken']
        self.refresh_token = revalidation_token
        self.root_token = root_token
        self.name, self.last_name = user_dict['studentName'].split(' ', maxsplit=1)
        self.login = user_dict['login']
        self.uid = user_dict['id']
        self.expires_in = datetime.now() + timedelta(seconds=exp_in)

    def __repr__(self):
        return f'<SynergiaUser for {self.name} {self.last_name} based on ' \
               f'token {self.token[:6] + "..." + self.token[-6:]}>'

    def __str__(self):
        return f'{self.name} {self.last_name}'

    def revalidate_root(self):
        """
        Aktualizuje token do Portalu Librus.
        """
        auth_session = requests.session()
        new_tokens = auth_session.post(
            OAUTHURL,
            data={
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token,
                'client_id': CLIENTID
            }
        )
        logging.debug('%s response %s', new_tokens.status_code, new_tokens.json())
        try:
            self.root_token = new_tokens.json()['access_token']
            self.refresh_token = new_tokens.json()['refresh_token']
        except KeyError:
            raise LibrusTricksAuthException('Invalid payload recived', new_tokens.json())

    def revalidate_user(self):
        """
        Aktualizuje token dostępu do Synergii, który wygasa po 24h.
        """
        def do_revalidation():
            auth_session = requests.session()
            new_token = auth_session.get(
                FRESHURL.format(login=self.login),
                headers={'Authorization': f'Bearer {self.root_token}'}
            )
            logging.debug('%s response %s', new_token.status_code, new_token.json())
            return new_token

        new_token = do_revalidation()
        if new_token.json().get('error') == 'access_denied':
            logging.info('Obtaing new token failed! Refreshing root token')
            self.revalidate_root()
            new_token = do_revalidation() # again...

        try:
            self.token = new_token.json()['accessToken']
        except KeyError:
            raise LibrusTricksAuthException('Invalid response received', new_token.json())

    def check_is_expired(self, use_clock=True, use_query=True):
        """
        :param bool use_clock: Sprawdza na podstawie czasu
        :param bool use_query: Sprawdza poprzez zapytanie http GET na ``/Me``
        :return: krotka z wynikami
        :rtype: tuple[bool]
        """
        clock_resp = None
        query_resp = None

        if use_clock:
            if datetime.now() > self.expires_in:
                clock_resp = False
            else:
                clock_resp = True
        if use_query:
            test = requests.get('https://api.librus.pl/2.0/Me', headers={'Authorization': f'Bearer {self.token}'})
            if test.status_code == 401:
                query_resp = False
            else:
                query_resp = True

        return clock_resp, query_resp

    @property
    def is_valid(self):
        """
        Umożliwia sprawdzenie czy konto ma jeszcze aktualny token.

        :return: ``False`` - trzeba wyrobić nowy token
        :rtype: bool
        """
        return self.check_is_expired(use_clock=False)[1]

    def dump_credentials(self, cred_file=None):
        import json
        if cred_file is None:
            cred_file = open(f'{self.login}.json', 'w')
        json.dump({
            'user_dict': {
                'accessToken': self.token,
                'studentName': f'{self.name} {self.last_name}',
                'id': self.uid,
                'login': self.login,
            },
            'root_token': self.root_token,
            'revalidation_token': self.refresh_token,
            'exp_in': int(self.expires_in.timestamp())
        }, cred_file)

    def dict_credentials(self):
        return {
            'user_dict': {
                'accessToken': self.token,
                'studentName': f'{self.name} {self.last_name}',
                'id': self.uid,
                'login': self.login,
            },
            'root_token': self.root_token,
            'revalidation_token': self.refresh_token,
            'exp_in': int(self.expires_in.timestamp())
        }


def load_json(cred_file):
    import json
    return SynergiaUser(**json.load(cred_file))


def authorizer(email, password, user_agent=None):
    """
    Zwraca listę użytkowników dostępnych dla danego konta Librus Portal

    :param str email: Email do Portalu Librus
    :param str password: Hasło do Portalu Librus
    :return: Listę z użytkownikami połączonymi do konta Librus Synergia
    :rtype: list[librus_tricks.auth.SynergiaUser]
    """
    if user_agent is None:
        user_agent = XIAOMI_USERAGENT
        logging.debug('No user-agent specified, using %s', user_agent)

    auth_session = requests.session()
    auth_session.headers.update({'User-Agent': user_agent, 'X-Requested-With': 'pl.librus.synergiaDru2'})
    site = auth_session.get(LIBRUSLOGINURL)
    soup = BeautifulSoup(site.text, 'html.parser')
    csrf = soup.find('meta', attrs={'name': 'csrf-token'})['content']
    login_response_redirection = auth_session.post(
        LOGINURL, json={'email': email, 'password': password},
        headers={'X-CSRF-TOKEN': csrf, 'Content-Type': 'application/json'}
    )

    if login_response_redirection.status_code != 200:
        if login_response_redirection.status_code == 403:
            if 'g-recaptcha-response' in login_response_redirection.json()['errors']:
                raise CaptchaRequired(login_response_redirection.json())
            raise LibrusPortalInvalidPasswordError(login_response_redirection.json())
        raise LibrusLoginError(login_response_redirection.text)

    redirection_addr = login_response_redirection.json()['redirect']
    redirection_response = auth_session.get(redirection_addr, allow_redirects=False)
    oauth_code = redirection_response.headers['location'].replace('app://librus?code=', '')

    synergia_root_response = auth_session.post(
        OAUTHURL,
        data={
            'client_id': CLIENTID,
            'grant_type': 'authorization_code',
            'code': oauth_code,
            'redirect_uri': REDIRURL
        }
    )
    synergia_root_login_token = synergia_root_response.json()['access_token']
    synergia_root_revalidation_token = synergia_root_response.json()['refresh_token']
    synergia_root_expiration = synergia_root_response.json()['expires_in']

    synergia_users_response = auth_session.get(SYNERGIAAUTHURL,
                                               headers={'Authorization': f'Bearer {synergia_root_login_token}'})
    synergia_users_raw = synergia_users_response.json()['accounts']
    synergia_users = [
        SynergiaUser(user_data, synergia_root_login_token, synergia_root_revalidation_token, synergia_root_expiration)
        for user_data in synergia_users_raw]
    return synergia_users
