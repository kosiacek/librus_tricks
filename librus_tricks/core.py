import logging
from datetime import timedelta
import datetime
import requests

from librus_tricks import cache as cache_lib
from librus_tricks import exceptions, tools
from librus_tricks.classes import *
from librus_tricks.messages import MessageReader


class SynergiaClient:
    """Sesja z API Synergii"""

    def __init__(self, user, api_url='https://api.librus.pl/2.0', user_agent='LibrusMobileApp',
                 cache=cache_lib.AlchemyCache()):
        """
        Tworzy sesję z API Synergii.

        :param librus_tricks.auth.SynergiaUser user: Użytkownik sesji
        :param str api_url: Bazowy url api, zmieniaj jeżeli chcesz używać proxy typu beeceptor
        :param str user_agent: User-agent klienta http, domyślnie się podszywa pod aplikację
        :param librus_tricks.cache.CacheBase cache: Obiekt, który zarządza cache
        """
        self.user = user
        self.session = requests.session()

        self.session.headers.update({'User-Agent': user_agent})
        self.__auth_headers = {'Authorization': f'Bearer {user.token}'}
        self.__api_url = api_url

        if cache_lib.CacheBase in cache.__class__.__bases__:
            self.cache = cache
            self.li_session = self
        else:
            raise exceptions.InvalidCacheManager(f'{cache} can not be a cache object!')

        self.__message_reader = None

    @property
    def message_reader(self):
        if self.__message_reader is None:
            self.__message_reader = MessageReader(self)
        return self.__message_reader
    
    def convert_download_url(self,url):
        _web_session = requests.session()
        logging.debug('Obtain AutoLoginToken from server')
        token = self.post('AutoLoginToken')['Token']
        _web_session.get(f'https://synergia.librus.pl/loguj/token/{token}/przenies/wiadomosci')
        if "synergia.librus.pl" in url:
            return _web_session.get(url).url+'/get'
        else:
            return _web_session.get('https://synergia.librus.pl/'+url).url+'/get'
    
    def __repr__(self):
        return f'<Synergia session for {self.user}>'

    def __update_auth_header(self):
        self.__auth_headers = {'Authorization': f'Bearer {self.user.token}'}
        logging.debug('Updating headers to %s', self.__auth_headers)

    @staticmethod
    def assembly_path(*elements, prefix='', suffix='', sep='/'):
        """
        Składa str w jednego str, przydatne przy tworzeniu url.

        :param str elements: Elementy do stworzenia str
        :param str prefix: Początek str
        :param str suffix: Koniec str
        :param str sep: str wstawiany pomiędzy elementy
        :return: Złożony str
        :rtype: str
        """
        for element in elements:
            prefix += sep + str(element)
        return prefix + suffix

    # HTTP part

    def dispatch_http_code(self, response: requests.Response, callback=None, callback_args=tuple(),
                           callback_kwargs=None):
        """
        Sprawdza czy serwer zgłasza błąd poprzez podanie kodu http, w przypadku błędu, rzuca wyjątkiem.

        :param requests.Response response:
        :raises librus_tricks.exceptions.SynergiaNotFound: 404
        :raises librus_tricks.exceptions.SynergiaForbidden: 403
        :raises librus_tricks.exceptions.SynergiaAccessDenied: 401
        :raises librus_tricks.exceptions.SynergiaInvalidRequest: 401
        :rtype: requests.Response
        :return: sprawdzona odpowiedź http
        """
        if callback_kwargs is None:
            callback_kwargs = dict()

        logging.debug('Dispatching response status')
        if response.json().get('Code') == 'TokenIsExpired':
            logging.info('Server returned error code "TokenIsExpired", trying to obtain new token')
            self.user.revalidate_user()
            self.__update_auth_header()
            logging.debug('Repeating failed response')
            return callback(*callback_args, **callback_kwargs)

        logging.debug('Dispatching http status code')
        if response.status_code >= 400:
            try:
                raise {
                    503: exceptions.SynergiaMaintenanceError(response.url, response.json()),
                    500: exceptions.SynergiaServerError(response.url, response.json()),
                    404: exceptions.SynergiaAPIEndpointNotFound(response.url),
                    403: exceptions.SynergiaForbidden(response.url, response.json()),
                    401: exceptions.SynergiaAccessDenied(response.url, response.json()),
                    400: exceptions.SynergiaAPIInvalidRequest(response.url, response.json()),
                }[response.status_code]
            except KeyError:
                raise exceptions.OtherHTTPResponse('Not excepted HTTP error code!', response.status_code)

        return response.json()

    def get(self, *path, request_params=None):
        """
        Wykonuje odpowiednio spreparowane zapytanie http GET.

        :param path: Ścieżka zawierająca węzeł API
        :type path: str
        :param request_params: dict zawierający kwargs dla zapytania http
        :type request_params: dict
        :return: json przekonwertowany na dict'a
        :rtype: dict
        """
        if request_params is None:
            request_params = dict()
        path_str = self.assembly_path(*path, prefix=self.__api_url)
        response = self.session.get(
            path_str, headers=self.__auth_headers, params=request_params
        )

        response = self.dispatch_http_code(response, callback=self.get, callback_args=path,
                                           callback_kwargs=request_params)

        return response

    def post(self, *path, request_params=None):
        """
        Pozwala na dokonanie zapytania http POST.

        :param path: Ścieżka zawierająca węzeł API
        :type path: str
        :param request_params: dict zawierający kwargs dla zapytania http
        :type request_params: dict
        :return: json przekonwertowany na dict'a
        :rtype: dict
        """
        if request_params is None:
            request_params = dict()
        path_str = self.assembly_path(*path, prefix=self.__api_url)
        response = self.session.post(
            path_str, headers=self.__auth_headers, params=request_params
        )

        response = self.dispatch_http_code(response, callback=self.post, callback_args=path,
                                           callback_kwargs=request_params)

        return response

    # Cache

    def get_cached_response(self, *path, http_params=None, max_lifetime=timedelta(hours=1)):
        """
        Wykonuje zapytanie http GET z poprzednim sprawdzeniem cache.

        :param path: Niezłożona ścieżka do węzła API
        :param http_params: dict zawierający kwargs dla zapytania http
        :type http_params: dict
        :param timedelta max_lifetime: Maksymalny czas ważności cache dla tego zapytania http
        :return: dict zawierający odpowiedź zapytania
        :rtype: dict
        """
        uri = self.assembly_path(*path, prefix=self.__api_url)
        response_cached = self.cache.get_query(uri, self.user.uid)

        if response_cached is None:
            logging.debug('Response is not present in cache!')
            http_response = self.get(*path, request_params=http_params)
            self.cache.add_query(uri, http_response, self.user.uid)
            return http_response

        try:
            age = datetime.now() - response_cached.last_load
        except TypeError:
            age = datetime.now() - response_cached.last_load.replace(tzinfo=None)

        if age > max_lifetime:
            logging.debug('Response is too old! Trying to get latest response from api')
            http_response = self.get(*path, request_params=http_params)
            self.cache.del_query(uri, self.user.uid)
            self.cache.add_query(uri, http_response, self.user.uid)
            return http_response
        return response_cached.response

    def get_cached_object(self, uid, cls, max_lifetime=timedelta(hours=1)):
        """
        Pobiera dany obiekt z poprzednim sprawdzeniem cache. Nie używane domyślnie w bibliotece.

        :param str uid: Id żądanego obiektu
        :param cls: Klasa żądanego obiektu
        :param timedelta max_lifetime: Maksymalny czas ważności cache dla tego obiektu
        :return: Żądany obiekt
        """
        requested_object = self.cache.get_object(uid, cls)

        if requested_object is None:
            logging.debug('Obejct is not present in cache!')
            requested_object = cls.create(uid=uid, session=self)
            self.cache.add_object(uid, cls, requested_object.export_resource())
            return requested_object

        try:
            age = datetime.now() - requested_object.last_load
        except TypeError:
            age = datetime.now() - requested_object.last_load.replace(tzinfo=None)

        if age > max_lifetime:
            logging.debug('Object is too old! Trying to get latest object from api')
            requested_object = cls.create(uid=uid, session=self)
            self.cache.del_object(uid)
            self.cache.add_object(uid, cls, requested_object.export_resource())

        return requested_object

    # API query part

    def return_objects(self, *path, cls, extraction_key=None, lifetime=timedelta(seconds=10), bypass_cache=False):
        """
        Zwraca listę obiektów lub obiekt, wygenerowaną z danych danej ścieżki API.

        :param str path: Niezłożona ścieżka do węzła API
        :param cls: Klasa żądanych obiektów
        :param str extraction_key: Klucz do wyjęcia danych, pozostawienie tego parametru na None powoduje
            automatyczną próbę zczytania danych
        :param timedelta lifetime: Maksymalny czas ważności cache dla tego zapytania http
        :param bool bypass_cache: Ustawienie tego parametru na True powoduje ignorowanie mechanizmu cache
        :return: Lista żądanych obiektów
        :rtype: list[SynergiaGenericClass]
        """
        if bypass_cache:
            raw = self.get(*path)
        else:
            raw = self.get_cached_response(*path, max_lifetime=lifetime)

        if extraction_key is None:
            extraction_key = SynergiaGenericClass.auto_extract(raw)

        raw = raw[extraction_key]

        if isinstance(raw, list):
            stack = []
            for stored_payload in raw:
                stack.append(cls.assembly(stored_payload, self))
            return tuple(stack)
        if isinstance(raw, dict):
            return cls.assembly(raw, self)

        return None

    def grades(self, *grades):
        """
        :param int grades: Id ocen
        :rtype: tuple[librus_tricks.classes.SynergiaGrade]
        :return: krotka z wszystkimi/wybranymi ocenami
        """
        if grades.__len__() == 0:
            return self.return_objects('Grades', cls=SynergiaGrade, extraction_key='Grades')
        ids_computed = self.assembly_path(*grades, sep=',', suffix=',')[1:]
        return self.return_objects('Grades', ids_computed, cls=SynergiaGrade, extraction_key='Grades')

    @property
    def grades_categorized(self):
        grades_categorized = {}
        for subject in self.subjects():
            grades_categorized[subject.name] = []

        for grade in self.grades():
            grades_categorized[grade.subject.name].append(
                grade
            )

        for subjects in grades_categorized.copy().keys():
            if grades_categorized[subjects].__len__() == 0:
                del (grades_categorized[subjects])

        return grades_categorized

    def attendances(self, *attendances):
        """
        :param int attendances: Id obecności
        :rtype: tuple[librus_tricks.classes.SynergiaAttendance]
        :return: krotka z wszystkimi/wybranymi obecnościami
        """
        if attendances.__len__() == 0:
            return self.return_objects('Attendances', cls=SynergiaAttendance, extraction_key='Attendances')
        ids_computed = self.assembly_path(*attendances, sep=',', suffix=',')[1:]
        return self.return_objects('Attendances', ids_computed, cls=SynergiaAttendance, extraction_key='Attendances')

    @property
    def illegal_absences(self):
        """
        :rtype: tuple[librus_tricks.classes.SynergiaAttendance]
        :return: krotka z nieusprawiedliwionymi nieobecnościami
        """

        def is_absence(k):
            if k.type.uid == '1':
                return True
            return False

        return tuple(filter(is_absence, self.attendances()))

    @property
    def all_absences(self):
        """
        :rtype: tuple[librus_tricks.classes.SynergiaAttendance]
        :return: krotka z wszystkimi nieobecnościami
        """
        return tuple(filter(lambda k: not k.type.is_presence_kind, self.attendances()))

    def exams(self, *exams):
        """
        :param int exams: Id egzaminów
        :rtype: tuple[librus_tricks.classes.SynergiaExam]
        :return: krotka z wszystkimi egzaminami
        """
        if exams.__len__() == 0:
            return self.return_objects('HomeWorks', cls=SynergiaExam, extraction_key='HomeWorks')
        ids_computed = self.assembly_path(*exams, sep=',', suffix=',')[1:]
        return self.return_objects('HomeWorks', ids_computed, cls=SynergiaExam, extraction_key='HomeWorks')

    def colors(self, *colors):
        """
        :param int colors: Id kolorów
        :rtype: tuple[librus_tricks.classes.SynergiaColors]
        """
        if colors.__len__() == 0:
            return self.return_objects('Colors', cls=SynergiaColor, extraction_key='Colors')
        ids_computed = self.assembly_path(*colors, sep=',', suffix=',')[1:]
        return self.return_objects('Colors', ids_computed, cls=SynergiaColor, extraction_key='Colors')

    def timetable(self, for_date=datetime.now()):
        """
        Plan lekcji na cały tydzień.

        :param datetime.datetime for_date: Data dnia, który ma być w planie lekcji
        :rtype: librus_tricks.classes.SynergiaTimetable
        :return: obiekt tygodniowego planu lekcji
        """
        monday = tools.get_actual_monday(for_date).isoformat()
        matrix = self.get('Timetables', request_params={'weekStart': monday})
        return SynergiaTimetable.assembly(matrix['Timetable'], self)

    def timetable_day(self, for_date: datetime):
        return self.timetable(for_date).days[for_date.date()]

    @property
    def today_timetable(self):
        """
        Plan lekcji na dzisiejszy dzień.

        :rtype: librus_tricks.classes.SynergiaTimetableDay
        :return: Plan lekcji na dziś
        """
        try:
            return self.timetable().days[datetime.now().date()]
        except KeyError:
            return None

    @property
    def tomorrow_timetable(self):
        """
        Plan lekcji na kolejny dzień.

        :rtype: librus_tricks.classes.SynergiaTimetableDay
        :return: Plan lekcji na jutro
        """
        try:
            return self.timetable(datetime.now() + timedelta(days=1)).days[(datetime.now() + timedelta(days=1)).date()]
        except KeyError:
            return None

    def messages(self, *messages):
        """
        Wymaga mobilnych dodatków.

        :param int messages: Id wiadomości
        :rtype: tuple[librus_tricks.classes.SynergiaNativeMessage]
        """
        if messages.__len__() == 0:
            return self.return_objects('Messages', cls=SynergiaNativeMessage, extraction_key='Messages')
        ids_computed = self.assembly_path(*messages, sep=',', suffix=',')[1:]
        return self.return_objects('Messages', ids_computed, cls=SynergiaNativeMessage, extraction_key='Messages')

    def news_feed(self):
        """
        :return: Wszystkie ogłoszenia szkolne
        :rtype: tuple[librus_tricks.classes.SynergiaNews]
        """
        return self.return_objects('SchoolNotices', cls=SynergiaNews, extraction_key='SchoolNotices')

    def subjects(self, *subject):
        """
        :return: Wszystkie/wybrane przedmioty lekcyjne
        :param int subject: Id przedmiotów
        :rtype: tuple[librus_tricks.classes.SynergiaSubject]
        """
        if subject.__len__() == 0:
            return self.return_objects('Subjects', cls=SynergiaSubject, extraction_key='Subjects')
        ids_computed = self.assembly_path(*subject, sep=',', suffix=',')[1:]
        return self.return_objects('Subjects', ids_computed, cls=SynergiaSubject, extraction_key='Subjects')

    @property
    def school(self):
        """
        :return: Obiekt z informacjami o twojej szkole
        :rtype: librus_tricks.classes.SynergiaSchool
        """
        return self.return_objects('Schools', cls=SynergiaSchool, extraction_key='School')

    @property
    def lucky_number(self):
        """
        :return: Szczęśliwy numerek
        :rtype: int
        """
        return self.get('LuckyNumbers')['LuckyNumber']['LuckyNumber']

    @staticmethod
    def __is_future(day):
        """

        :type day: librus_tricks.classes.SynergiaTeacherFreeDays
        :return:
        """
        if day.ends >= datetime.now().date():
            return True
        return False

    def teacher_free_days(self, *days_ids, only_future=True):
        """
        Zwraca dane przedmioty.

        :param int days_ids: Id zwolnień
        :rtype: tuple[librus_tricks.classes.SynergiaTeacherFreeDays]
        """
        if days_ids.__len__() == 0:
            days = self.return_objects('Calendars', 'TeacherFreeDays', cls=SynergiaTeacherFreeDays)
        else:
            ids_computed = self.assembly_path(*days_ids, sep=',', suffix=',')[1:]
            days = self.return_objects('Calendars', 'TeacherFreeDays', ids_computed, cls=SynergiaTeacherFreeDays)

        days = tuple(sorted(days, key=lambda x: x.starts))
        if only_future:
            return tuple(filter(self.__is_future, days))
        return days

    def school_free_days(self, *days_ids, only_future=True):
        if days_ids.__len__() == 0:
            days = self.return_objects('Calendars', 'SchoolFreeDays', cls=SynergiaSchoolFreeDays)
        else:
            ids_computed = self.assembly_path(*days_ids, sep=',', suffix=',')[1:]
            days = self.return_objects('Calendars', 'SchoolFreeDays', ids_computed, cls=SynergiaSchoolFreeDays)

        days = tuple(sorted(days, key=lambda x: x.starts))
        if only_future:
            return tuple(filter(self.__is_future, days))
        return days

    def realizations(self, *realizations_ids):
        if realizations_ids.__len__() == 0:
            return self.return_objects('Realizations', cls=SynergiaRealization, extraction_key='Realizations')
        ids_computed = self.assembly_path(*realizations_ids, sep=',', suffix=',')[1:]
        return self.return_objects('Realizations', ids_computed, cls=SynergiaRealization, extraction_key='Realizations')

    def substitutions(self):
        pass

    def preload_cache(self):
        self.cache.clear_objects()

        for thing in (*self.attendances(), *self.grades(), *self.subjects(), *self.school_free_days(only_future=False),
                      *self.teacher_free_days(only_future=False)):
            self.cache.add_object(thing.uid, thing.__class__, thing.export_resource())

        logging.info('Loaded %s objects into cache', self.cache.count_object())
