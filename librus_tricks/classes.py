from datetime import datetime, timedelta


from librus_tricks.exceptions import SessionRequired, APIPathIsEmpty

class _RemoteObjectsUIDManager:
    """
    Menadżer obiektów, które dopiero zostaną utworzone.
    """

    def __init__(self, session, parent):
        """

        :param librus_tricks.core.SynergiaClient session: Obiekt sesji
        """
        self.__storage = dict()
        self._session = session
        self.__parent = parent

    def set_object(self, attr, uid, cls):
        """
        Zapisuje dane przyszłego obiektu.

        :param str attr: Nazwa przyszłego property
        :param int uid: Id obiektu
        :param cls: Klasa obiektu
        """
        self.__storage[attr] = uid, cls
        # self.__parent.__setattr__(attr, cls.create(uid=uid, session=self.__session))
        return self

    def set_value(self, attr, val):
        """
        Ustawia obiekt.

        :param str attr: Nazwa obiektu
        :param val: Obiekt
        """
        self.__storage[attr] = val
        return self

    def assembly(self, attr):
        """
        Pobiera wcześniej zapisany obiekt.

        :param str attr: Nazwa property
        :return: Żądany obiekt
        """
        uid, cls = self.__storage[attr]
        return cls.create(uid=uid, session=self._session)

    def return_id(self, attr):
        """
        Zwraca id obiektu.

        :param str attr: Nazwa property
        :rtype: int
        :return: Id obiektu
        """
        return self.__storage[attr][0]


class SynergiaGenericClass:
    """
    Klasa macierzysta dla obiektów dziennika Synergia.
    """

    def __init__(self, uid, resource, session):
        """

        :param str uid: Id żądanego obiektu
        :param librus_tricks.core.SynergiaClient session: Obiekt sesji
        :param resource: ścieżka do źródła danych
        :type resource: iterable of str
        :param str extraction_key: str zawierający klucz do wyjęcia danych
        :param dict resource: dict zawierający gotowe dane (np. załadowane z cache)
        """

        self._session = session
        self.uid = uid
        self.objects = _RemoteObjectsUIDManager(self._session, self)
        self._json_resource = resource

    # Of course i can comment it out, but for code completion props will be better
    # def __getattr__(self, name):
    #     return self.objects_ids.assembly(name)

    @classmethod
    def assembly(cls, resource, session):
        """
        Umożliwia stworzenie obiektu posiadając dict i obiekt sesji.

        :param dict resource: Gotowe dane do stworzenia obiektu
        :param librus_tricks.core.SynergiaClient session: Obiekt sesji
        :return: Nowy obiekt
        """
        self = cls(resource['Id'], resource, session)
        return self

    @classmethod
    def create(cls, uid=None, path=('',), session=None, extraction_key=None, expire=timedelta(seconds=1)):
        """
        Pobiera i składa nowy obiekt.

        :param int uid: Id obiektu
        :param tuple of str path: Niezłożona ścieżka API
        :param librus_tricks.core.SynergiaClient session: Obiekt sesji
        :param str extraction_key: Klucz do wyciągnięcia danych
        :return: Pobrany obiekt
        """
        import logging

        if uid is None or session is None:
            raise SessionRequired()

        maybe_response = session.cache.get_object(uid, cls)
        if not maybe_response is None:
            logging.debug('Returning %s %s from object cache', maybe_response, uid)
            return maybe_response

        if path == ('',):
            raise APIPathIsEmpty(f'Path for {cls.__name__} class is empty!')

        response = session.get_cached_response(*path, uid, max_lifetime=expire)
        logging.debug('Returning %s %s object from response cache', cls.__name__, uid)

        if extraction_key is None:
            extraction_key = SynergiaGenericClass.auto_extract(response)

        resource = response[extraction_key]
        self = cls(resource['Id'], resource, session)
        return self

    @staticmethod
    def auto_extract(payload):
        """
        Próbuje automatycznie wydobyć klucz.

        :param dict payload:
        :return: Wydobyty klucz
        :rtype: str
        """
        for key in payload.keys():
            if key not in ('Resources', 'Url'):
                return key
        return

    def export_resource(self):
        return self._json_resource.copy()

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.uid} at {hex(id(self))}>'

    def __hash__(self):
        return hash(self.uid)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.uid == other.uid
        raise TypeError(f'Object is not instance of {self.__class__.__name__}')

    def __ne__(self, other):
        return not self.__eq__(other)

    def _is_compatible(self, other):
        if not isinstance(other, self.__class__):
            raise TypeError()
        return True


class SynergiaTeacher(SynergiaGenericClass):
    def __init__(self, uid, resource, session):
        super().__init__(uid, resource, session)
        self.name = self._json_resource['FirstName']
        self.last_name = self._json_resource['LastName']

    @classmethod
    def create(cls, uid=None, path=('Users',), session=None, extraction_key='User', expire=timedelta(days=31)):
        return super().create(uid, path, session, extraction_key, expire)

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.name} {self.last_name}>'

    def __str__(self):
        return f'{self.name} {self.last_name}'


class SynergiaStudent(SynergiaTeacher):
    pass


class SynergiaGlobalClass(SynergiaGenericClass):
    """Klasa reprezentująca klasę (np. 1C)"""

    def __init__(self, uid, resource, session):
        """
        Tworzy obiekt reprezentujący klasę (jako zbiór uczniów)

        :param str uid: id klasy
        :param librus_tricks.core.SynergiaClient session: obiekt sesji z API Synergii
        :param dict resource: dane z json'a
        """
        super().__init__(uid, resource, session)

        self.alias = f'{self._json_resource["Number"]}{self._json_resource["Symbol"]}'
        self.begin_date = datetime.strptime(self._json_resource['BeginSchoolYear'], '%Y-%m-%d').date()
        self.end_date = datetime.strptime(self._json_resource['EndSchoolYear'], '%Y-%m-%d').date()
        self.objects.set_object(
            'tutor', self._json_resource['ClassTutor']['Id'], SynergiaTeacher
        )

    @property
    def tutor(self) -> SynergiaTeacher:
        return self.objects.assembly('tutor')

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.alias}>'


class SynergiaVirtualClass(SynergiaGenericClass):
    def __init__(self, uid, resource, session):
        """
        Tworzy obiekt reprezentujący grupę uczniów

        :param str uid: id klasy
        :param librus_tricks.core.SynergiaClient session: obiekt sesji z API Synergii
        :param dict resource: dane z json'a
        """
        super().__init__(uid, resource, session)

        self.name = self._json_resource['Name']
        self.number = self._json_resource['Number']
        self.symbol = self._json_resource['Symbol']
        self.objects.set_object(
            'teacher', self._json_resource['Teacher']['Id'], SynergiaTeacher
        ).set_object(
            'subject', self._json_resource['Subject']['Id'], SynergiaSubject
        )

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.name}>'

    @property
    def teacher(self) -> SynergiaTeacher:
        return self.objects.assembly('teacher')

    @property
    def subject(self):
        return self.objects.assembly('subject')


class SynergiaSubject(SynergiaGenericClass):
    def __init__(self, uid, resource, session):
        super().__init__(uid, resource, session)
        self.name = self._json_resource['Name']
        self.short_name = self._json_resource['Short']

    @classmethod
    def create(cls, uid=None, path=('Subjects',), session=None, extraction_key='Subject', expire=timedelta(days=31)):
        return super().create(uid, path, session, extraction_key, expire)

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.name}>'

    def __str__(self):
        return self.name


class SynergiaLesson(SynergiaGenericClass):
    def __init__(self, uid, resource, session):
        """
        Klasa reprezentująca jednostkową lekcję

        :type session: librus_tricks.core.SynergiaClient
        """
        super().__init__(uid, resource, session)

        self.objects.set_object(
            'teacher', self._json_resource['Teacher']['Id'], SynergiaTeacher
        ).set_object(
            'subject', self._json_resource['Subject']['Id'], SynergiaSubject
        )

    @classmethod
    def create(cls, uid=None, path=('Lessons',), session=None, extraction_key='Lesson', expire=timedelta(minutes=5)):
        return super().create(uid, path, session, extraction_key, expire)

    @property
    def teacher(self) -> SynergiaTeacher:
        return self.objects.assembly('teacher')

    @property
    def subject(self) -> SynergiaSubject:
        return self.objects.assembly('subject')


class SynergiaGradeCategory(SynergiaGenericClass):
    def __init__(self, uid, resource, session):
        super().__init__(uid, resource, session)

        def __try_to_extract(payload, extraction_key, false_return=None):
            if extraction_key in payload.keys():
                return payload[extraction_key]
            return false_return

        self.count_to_the_average = self._json_resource['CountToTheAverage']
        self.name = self._json_resource['Name']
        self.obligation_to_perform = self._json_resource['ObligationToPerform']
        self.standard = self._json_resource['Standard']
        self.weight = __try_to_extract(self._json_resource, 'Weight', false_return=0)

        if 'Teacher' in self._json_resource.keys():
            self.objects.set_object(
                'teacher', self._json_resource['Id'], SynergiaTeacher
            )

    @classmethod
    def create(cls, uid=None, path=('Grades', 'Categories'), session=None, extraction_key='Category',
               expire=timedelta(days=31)):
        return super().create(uid, path, session, extraction_key, expire)

    @property
    def teacher(self):
        try:
            return self.objects.assembly('teacher')
        except KeyError:
            return

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.name}>'


class SynergiaGradeComment(SynergiaGenericClass):
    def __init__(self, uid, resource, session):
        super().__init__(uid, resource, session)

        self.text = self._json_resource['Text']
        self.objects.set_object(
            'teacher', self._json_resource['AddedBy']['Id'], SynergiaTeacher
        ).set_object(
            'bind', self._json_resource['Grade']['Id'], SynergiaGrade
        )

    def __str__(self):
        return self.text

    @classmethod
    def create(cls, uid=None, path=('Grades', 'Comments'), session=None, extraction_key='Comment',
               expire=timedelta(days=31)):
        return super().create(uid, path, session, extraction_key, expire)

    @property
    def teacher(self) -> SynergiaTeacher:
        return self.objects.assembly('teacher')

    @property
    def grade_bind(self):
        return self.objects.assembly('bind')

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.text}>'


class SynergiaBaseTextGrade(SynergiaGenericClass):
    def __init__(self, uid, resource, session):
        super().__init__(uid, resource, session)

        self.add_date = datetime.strptime(self._json_resource['AddDate'], '%Y-%m-%d %H:%M:%S')
        self.date = datetime.strptime(self._json_resource['Date'], '%Y-%m-%d').date()
        self.grade = self._json_resource['Grade']
        self.semester = self._json_resource['Semester']
        self.visible = self._json_resource['ShowInGradesView']
        self.objects.set_object(
            'teacher', self._json_resource['AddedBy']['Id'], SynergiaTeacher
        ).set_object(
            'subject', self._json_resource['Subject']['Id'], SynergiaSubject
        ).set_object(
            'student', self._json_resource['Student']['Id'], SynergiaStudent
        )

    @classmethod
    def create(cls, uid=None, path=('BaseTextGrades',), session=None, extraction_key='BaseTextGrades',
               expire=timedelta(minutes=5)):
        return super().create(uid, path, session, extraction_key, expire)

    @property
    def teacher(self) -> SynergiaTeacher:
        return self.objects.assembly('teacher')

    @property
    def subject(self) -> SynergiaSubject:
        return self.objects.assembly('subject')

    @property
    def student(self):
        return self.objects.assembly('student')


class SynergiaGrade(SynergiaGenericClass):
    def __init__(self, uid, resource, session):
        super().__init__(uid, resource, session)

        class GradeMetadata:
            def __init__(self, is_c, is_s, is_sp, is_f, is_fp):
                self.is_constituent = is_c
                self.is_semester_grade = is_s
                self.is_semester_grade_proposition = is_sp
                self.is_final_grade = is_f
                self.is_final_grade_proposition = is_fp

        self.add_date = datetime.strptime(self._json_resource['AddDate'], '%Y-%m-%d %H:%M:%S')
        self.date = datetime.strptime(self._json_resource['Date'], '%Y-%m-%d').date()
        self.grade = self._json_resource['Grade']
        self.is_constituent = self._json_resource['IsConstituent']
        self.semester = self._json_resource['Semester']
        self.metadata = GradeMetadata(
            self._json_resource['IsConstituent'],
            self._json_resource['IsSemester'],
            self._json_resource['IsSemesterProposition'],
            self._json_resource['IsFinal'],
            self._json_resource['IsFinalProposition']
        )

        self.objects.set_object(
            'teacher', self._json_resource['AddedBy']['Id'], SynergiaTeacher
        ).set_object(
            'subject', self._json_resource['Subject']['Id'], SynergiaSubject
        ).set_object(
            'category', self._json_resource['Category']['Id'], SynergiaGradeCategory
        )

    @property
    def is_special(self):
        m = self.metadata
        if m.is_final_grade or m.is_final_grade_proposition or m.is_semester_grade or m.is_semester_grade_proposition:
            return True
        return False

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.grade} from SynergiaSubject with id {self.objects.return_id("subject")} ' \
               f'added {self.add_date.strftime("%Y-%m-%d %H:%M:%S")}>'

    def __str__(self):
        return self.grade

    @property
    def teacher(self) -> SynergiaTeacher:
        return self.objects.assembly('teacher')

    @property
    def subject(self) -> SynergiaSubject:
        return self.objects.assembly('subject')

    @property
    def category(self) -> SynergiaGradeCategory:
        return self.objects.assembly('category')

    @property
    def comments(self):
        """

        :rtype: list of SynergiaGradeComment
        """
        if self._json_resource.get('Comments') is not None:
            return [
                SynergiaGradeComment.create(
                    uid=com.get('Id'), session=self._session
                ) for com in self._json_resource.get('Comments')
            ]
        return tuple()

    @property
    def real_value(self):
        return {
            '1': 1,
            '1+': 1.5,
            '2-': 1.75,
            '2': 2,
            '2+': 2.5,
            '3-': 2.75,
            '3': 3,
            '3+': 3.5,
            '4-': 3.75,
            '4': 4,
            '4+': 4.5,
            '5-': 4.75,
            '5': 5,
            '5+': 5.5,
            '6-': 5.75,
            '6': 6
        }.get(self.grade)

    @classmethod
    def create(cls, uid=None, path=('Grades',), session=None, extraction_key='Grade', expire=timedelta(minutes=45)):
        return super().create(uid, path, session, extraction_key, expire)

    def __eq__(self, other):
        self._is_compatible(other)
        return self.real_value == other.real_value and self.category.weight

    def __gt__(self, other):
        self._is_compatible(other)
        return self.real_value > other.real_value and self.category.weight >= other.category.weight

    def __ge__(self, other):
        self._is_compatible(other)
        return self.real_value >= other.real_value and self.category.weight >= other.category.weight

    def __lt__(self, other):
        self._is_compatible(other)
        return self.real_value < other.real_value and self.category.weight <= other.category.weight

    def __le__(self, other):
        self._is_compatible(other)
        return self.real_value <= other.real_value and self.category.weight <= other.category.weight


class SynergiaAttendanceType(SynergiaGenericClass):
    def __init__(self, uid, resource, session):
        super().__init__(uid, resource, session)
        self.color = self._json_resource['ColorRGB']
        self.is_presence_kind = self._json_resource['IsPresenceKind']
        self.name = self._json_resource['Name']
        self.short_name = self._json_resource['Short']

    @classmethod
    def create(cls, uid=None, path=('Attendances', 'Types'), session=None, extraction_key='Type',
               expire=timedelta(days=31)):
        return super().create(uid, path, session, extraction_key, expire)

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.short_name}>'

    def __str__(self):
        return self.name


class SynergiaAttendance(SynergiaGenericClass):
    def __init__(self, uid, resource, session):
        super().__init__(uid, resource, session)
        self.add_date = datetime.strptime(self._json_resource['AddDate'], '%Y-%m-%d %H:%M:%S')
        self.date = datetime.strptime(self._json_resource['Date'], '%Y-%m-%d').date()
        self.lesson_no = int(self._json_resource['LessonNo'])
        self.objects.set_object(
            'teacher', self._json_resource['AddedBy']['Id'], SynergiaTeacher
        ).set_object(
            'student', self._json_resource['Student']['Id'], SynergiaStudent
        ).set_object(
            'type', self._json_resource['Type']['Id'], SynergiaAttendanceType
        ).set_object(
            'lesson', resource['Lesson']['Id'], SynergiaLesson
        )

    @classmethod
    def create(cls, uid=None, path=('Attendances',), session=None, extraction_key='Attendance',
               expire=timedelta(minutes=10)):
        return super().create(uid, path, session, extraction_key, expire)

    @property
    def teacher(self):
        """
        :rtype: SynergiaTeacher
        """
        return self.objects.assembly('teacher')

    @property
    def student(self):
        """
        :rtype: SynergiaStudent
        """
        return self.objects.assembly('student')

    @property
    def type(self):
        """
        :rtype: SynergiaAttendanceType
        """
        return self.objects.assembly('type')

    @property
    def lesson(self):
        """
        :rtype: librus_tricks.classes.SynergiaLesson
        """
        return self.objects.assembly('lesson')

    def __repr__(self):
        return f'<SynergiaAttendance at {self.date.isoformat()} lesson {self.lesson_no}>'

    def __str__(self):
        return self.type.__str__()


class SynergiaExamCategory(SynergiaGenericClass):
    def __init__(self, uid, resource, session):
        super().__init__(uid, resource, session)

        self.name = self._json_resource['Name']
        self.objects.set_object('color', self._json_resource['Color']['Id'], SynergiaColor)

    @classmethod
    def create(cls, uid=None, path=('HomeWorks', 'Categories'), session=None, extraction_key='Category',
               expire=timedelta(days=31)):
        return super().create(uid, path, session, extraction_key, expire)

    @property
    def color(self):
        """

        :rtype: SynergiaColor
        """
        return self.objects.assembly('color')

    def __str__(self):
        return self.name


class SynergiaExam(SynergiaGenericClass):
    def __init__(self, uid, resource, session):

        super().__init__(uid, resource, session)

        self.add_date = datetime.strptime(self._json_resource['AddDate'], '%Y-%m-%d %H:%M:%S')
        self.content = self._json_resource['Content']
        self.date = datetime.strptime(self._json_resource['Date'], '%Y-%m-%d').date()
        self.lesson = self._json_resource['LessonNo']
        if self._json_resource['TimeFrom'] is None:
            self.time_start = None
        else:
            self.time_start = datetime.strptime(self._json_resource['TimeFrom'], '%H:%M:%S').time()
        if self._json_resource['TimeTo'] is None:
            self.time_end = None
        else:
            self.time_end = datetime.strptime(self._json_resource['TimeTo'], '%H:%M:%S').time()

        self.objects.set_object(
            'teacher', self._json_resource['CreatedBy']['Id'], SynergiaTeacher
        ).set_object(
            'category', self._json_resource['Category']['Id'], SynergiaExamCategory
        )
        if 'Subject' in self._json_resource:
            self.objects.set_object('subject', self._json_resource['Subject']['Id'], SynergiaSubject)
            self.__subject_present = True
        else:
            self.__subject_present = False

    @classmethod
    def create(cls, uid=None, path=('HomeWorks',), session=None, extraction_key='HomeWork', expire=timedelta(days=3)):
        return super().create(uid, path, session, extraction_key, expire)

    def __repr__(self):
        return f'<{self.__class__.__name__} ' \
               f'{self.date.strftime("%Y-%m-%d")} for subject {self.subject}>'

    @property
    def teacher(self) -> SynergiaTeacher:
        return self.objects.assembly('teacher')

    # @property
    # def group(self):
    #    """
    #
    #    :rtype: SynergiaGlobalClass
    #    :rtype: SynergiaVirtualClass
    #    """
    #    if self.objects_ids.group_type is SynergiaGlobalClass:
    #        return SynergiaGlobalClass(self.objects_ids.group, self._session)
    #    else:
    #        return SynergiaVirtualClass(self.objects_ids.group, self._session)

    @property
    def subject(self):
        if self.__subject_present:
            return self.objects.assembly('subject')
        return None

    @property
    def category(self):
        return self.objects.assembly('category')


class SynergiaColor(SynergiaGenericClass):
    def __init__(self, uid, resource, session):
        super().__init__(uid, resource, session)
        self.name = self._json_resource['Name']
        self.hex_rgb = self._json_resource['RGB']

    @classmethod
    def create(cls, uid=None, path=('Colors',), session=None, extraction_key='Color', expire=timedelta(days=31)):
        return super().create(uid, path, session, extraction_key, expire)

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.hex_rgb}>'

    def __str__(self):
        return self.hex_rgb


class SynergiaClassroom(SynergiaGenericClass):
    def __init__(self, uid, resource, session):
        super().__init__(uid, resource, session)
        self.name = self._json_resource['Name']
        self.symbol = self._json_resource['Symbol']

    @classmethod
    def create(cls, uid=None, path=('Classrooms',), session=None, extraction_key=None, expire=timedelta(days=31)):
        return super().create(uid, path, session, extraction_key, expire)

    def __repr__(self):
        return f'<SynergiaClassroom {self.symbol}>'

    def __str__(self):
        return self.name


class SynergiaTeacherFreeDaysTypes(SynergiaGenericClass):
    def __init__(self, uid, resource, session):
        super().__init__(uid, resource, session)
        self.name = self._json_resource[0]['Name']


class SynergiaTeacherFreeDays(SynergiaGenericClass):
    def __init__(self, uid, resource, session):
        super().__init__(uid, resource, session)

        self.starts = datetime.strptime(self._json_resource['DateFrom'], '%Y-%m-%d').date()
        self.ends = datetime.strptime(self._json_resource['DateTo'], '%Y-%m-%d').date()
        self.objects.set_object(
            'teacher', self._json_resource['Teacher']['Id'], SynergiaTeacher
        )

        if self._json_resource.get('TimeTo') is not None:
            self.time_begin = datetime.strptime(self._json_resource['TimeFrom'], '%H:%M:%S').time()
            self.time_ends = datetime.strptime(self._json_resource['TimeTo'], '%H:%M:%S').time()
        else:
            self.time_begin = None
            self.time_ends = None

    @property
    def period_length(self):
        return self.ends - self.starts

    @property
    def teacher(self) -> SynergiaTeacher:
        """

        :rtype: SynergiaTeacher
        """
        return self.objects.assembly('teacher')

    def __repr__(self):
        return f'<SynergiaTeacherFreeDays {self.starts.isoformat()} - {self.ends.isoformat()} ({(self.ends - self.starts).days} days) for {self.objects.return_id("teacher")}>'


class SynergiaSchoolFreeDays(SynergiaGenericClass):
    def __init__(self, uid, resource, session):
        super().__init__(uid, resource, session)
        self.starts = datetime.strptime(self._json_resource['DateFrom'], '%Y-%m-%d').date()
        self.ends = datetime.strptime(self._json_resource['DateTo'], '%Y-%m-%d').date()
        self.name = self._json_resource['Name']

    @classmethod
    def create(cls, uid=None, path=('Calendars', 'SchoolFreeDays'), session=None, extraction_key='SchoolFreeDays',
               expire=timedelta(minutes=5)):
        return super().create(uid, path, session, extraction_key, expire)

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.starts.isoformat()} - {self.ends.isoformat()}>'


class SynergiaTimetableEntry(SynergiaGenericClass):
    def __init__(self, uid, resource, session):
        super().__init__(uid, resource, session)
        self.available = datetime.strptime(resource['DateFrom'], '%Y-%m-%d').date(), \
                         datetime.strptime(resource['DateTo'], '%Y-%m-%d').date()

    @classmethod
    def create(cls, uid=None, path=('TimetableEntries',), session=None, extraction_key='TimetableEntry',
               expire=timedelta(seconds=15)):
        return super().create(uid, path, session, extraction_key, expire)


class SynergiaTimetableEvent:
    def __init__(self, resource, session):
        self.lesson_no = int(resource['LessonNo'])  #: int: numer lekcji
        self.start = datetime.strptime(resource['HourFrom'], '%H:%M').time()  #: time: początek lekcji
        self.end = datetime.strptime(resource['HourTo'], '%H:%M').time()  #: time: koniec lekcji
        self.is_cancelled = resource['IsCanceled']  #: bool: czy lekcja jest odwołana
        self.is_sub = resource['IsSubstitutionClass']  #: bool: czy lekcja jest zastępstwem
        self.preloaded = {
            'subject_title': resource['Subject']['Name'],
            'teacher': f'{resource["Teacher"]["FirstName"]} {resource["Teacher"]["LastName"]}'
        }
        self.objects = _RemoteObjectsUIDManager(session, self)
        self.objects.set_object(
            'subject', resource['Subject']['Id'], SynergiaSubject
        ).set_object(
            'teacher', resource['Teacher']['Id'], SynergiaTeacher
        )

        self.__set_classroom(resource)

    def __set_classroom(self, resource):
        """

        :param dict resource:
        :return:
        """
        if 'Classroom' in resource.keys():
            self.objects.set_object(
                'classroom', resource['Classroom']['Id'], SynergiaClassroom
            )
        elif 'OrgClassroom' in resource.keys():
            self.objects.set_object(
                'classroom', resource['OrgClassroom']['Id'], SynergiaClassroom
            )
        else:
            self.objects.set_value('classroom', None)

    @property
    def lesson_status(self):
        if self.is_cancelled:
            return 'Cancelled'
        elif self.is_sub:
            return 'Changed'
        return 'Planned'

    @property
    def subject(self):
        """
        :rtype: librus_tricks.classes.SynergiaSubject
        """
        return self.objects.assembly('subject')

    @property
    def teacher(self):
        """
        :rtype: librus_tricks.classes.SynergiaTeacher
        """
        return self.objects.assembly('teacher')

    @property
    def classroom(self):
        """
        :rtype: librus_tricks.classes.SynergiaClassroom
        """
        return self.objects.assembly('classroom')

    @property
    def human_readable_time_range(self):
        return f'{self.start.strftime("%H:%M")} - {self.end.strftime("%H:%M")}'

    def __repr__(self):
        return f'<SynergiaTimetableEvent {self.preloaded["subject_title"]} {self.start} {self.end} with {self.preloaded["teacher"]}>'

    def __str__(self):
        return self.preloaded["subject_title"]


class SynergiaTimetableDay:
    def __init__(self, lessons):
        self.lessons = tuple(lessons)  #: tuple[SynergiaTimetableEvent]: krotka z lekcjami
        if self.lessons.__len__() != 0:
            self.day_start = self.lessons[0].start
            self.day_end = self.lessons[-1].end
        else:
            self.day_start = None
            self.day_end = None

    def __repr__(self):
        return f'<{self.__class__.__name__} with {self.lessons.__len__()} lessons between {self.day_start} and {self.day_end}>'


class SynergiaTimetable(SynergiaGenericClass):
    """
    Obiekt zawierający cały tydzień w planie lekcji
    """

    def __init__(self, uid, resource, session):
        super().__init__(uid, resource, session)
        self.days = self.convert_parsed_timetable(
            self.parse_timetable(resource)
        )  #: list[SynergiaTimetableDay]: lista z dniami tygodnia

    @property
    def today_timetable(self):
        """

        :rtype: list of SynergiaTimetableEvent
        """
        return self.days[datetime.now().date()]

    @classmethod
    def assembly(cls, resource, session):
        pseudo_id = int(datetime.now().timestamp()).__str__()
        self = cls(pseudo_id, resource, session)
        return self

    @classmethod
    def create(cls, uid=None, path=('Timetables',), session=None, extraction_key='Timetable',
               expire=timedelta(seconds=15)):
        response = session.get_cached_response(*path)

        if extraction_key is None:
            extraction_key = SynergiaGenericClass.auto_extract(response)

        resource = response[extraction_key]
        self = cls.assembly(resource, session)
        return self

    @staticmethod
    def parse_timetable(resource):
        root = {}

        for day in resource.keys():
            day_date = datetime.strptime(day, '%Y-%m-%d').date()
            root[day_date] = []
            for period in resource[day]:
                if period.__len__() != 0:
                    root[day_date].append(period[0])
        return root

    def convert_parsed_timetable(self, timetable):
        for day in timetable:
            for event_index in range(len(timetable[day])):
                if timetable[day][event_index].keys().__len__() != 0:
                    timetable[day][event_index] = SynergiaTimetableEvent(timetable[day][event_index], self._session)

        for day in timetable.keys():
            timetable[day] = SynergiaTimetableDay(timetable[day])

        return timetable

    def __repr__(self):
        return f'<{self.__class__.__name__} for {self.days.keys()}>'

    def __str__(self):
        o_str = ''
        for day_key in self.days.keys():
            o_str += f'{day_key}\n'
            for event in self.days[day_key]:
                if event != {}:
                    o_str += f'  {event.__str__()}\n'
        return o_str


class SynergiaNativeMessageAuthor(SynergiaGenericClass):
    def __init__(self, uid, resource, session):
        super().__init__(uid, resource, session)
        self.name = resource.get('Name')

    @classmethod
    def create(cls, uid=None, path=('Messages', 'User'), session=None, extraction_key='User',
               expire=timedelta(days=60)):
        return super().create(uid, path, session, extraction_key, expire)

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.name}>'

    @property
    def matching_indentity(self):
        teachers = self._session.return_objects('Users', cls=SynergiaTeacher, extraction_key='Users')
        for teacher in teachers:
            if str(teacher.name) in self.name and str(teacher.last_name) in self.name:
                return teacher
        return


class SynergiaNativeMessage(SynergiaGenericClass):
    def __init__(self, uid, resource, session):
        super().__init__(uid, resource, session)
        self.body = self._json_resource['Body']  #: str: wiadomość
        self.topic = self._json_resource['Subject']  #: str: temat
        self.send_date = datetime.fromtimestamp(self._json_resource['SendDate'])  #: datetime: data wysłania
        self.objects.set_object('sender', self._json_resource['Sender']['Id'], SynergiaNativeMessageAuthor)

    @property
    def sender(self) -> SynergiaNativeMessageAuthor:
        return self.objects.assembly('sender')

    @classmethod
    def create(cls, uid=None, path=('Messages',), session=None, extraction_key='Message', expire=timedelta(days=31)):
        return super().create(uid, path, session, extraction_key, expire)


class SynergiaNews(SynergiaGenericClass):
    """
    Obiekt reprezentujący ogłoszenie szkolne
    """

    def __init__(self, uid, resource, session):
        super().__init__(uid, resource, session)
        self.content = self._json_resource['Content']  #: str: wiadomość ogłoszenia
        self.created = datetime.strptime(self._json_resource['CreationDate'],
                                         '%Y-%m-%d %H:%M:%S')  #: datetime: data utworzenia
        self.unique_id = self._json_resource['Id']  #: int: id ogłoszenia
        self.topic = self._json_resource['Subject']  #: str: temat
        self.was_read = self._json_resource['WasRead']  #: bool: status odczytania?
        self.starts = datetime.strptime(self._json_resource['StartDate'], '%Y-%m-%d')  #: date: ??
        self.ends = datetime.strptime(self._json_resource['EndDate'], '%Y-%m-%d')  #: date: ??
        self.objects.set_object(
            'teacher', self._json_resource['AddedBy']['Id'], SynergiaTeacher
        )

    @property
    def teacher(self) -> SynergiaTeacher:
        return self.objects.assembly('teacher')

    @classmethod
    def create(cls, uid=None, path=('SchoolNotices',), session=None, extraction_key='SchoolNotices',
               expire=timedelta(days=31)):
        return super().create(uid, path, session, extraction_key, expire)

    def __repr__(self):
        return f'<SynergiaNews {self.topic} posted {self.created}>'


class SynergiaSchool(SynergiaGenericClass):
    """
    Obiekt zawierający informacje o szkole
    """

    def __init__(self, uid, resource, session):
        super().__init__(uid, resource, session)
        self.name = resource['Name']  #: str: nazwa szkoły
        self.location = f'{resource["Town"]} {resource["Street"]} {resource["BuildingNumber"]}'  #: str: adres szkoły

    @classmethod
    def create(cls, uid=None, path=('Schools',), session=None, extraction_key='School', expire=timedelta(seconds=1)):
        return super().create(uid, path, session, extraction_key, expire)

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.name}>'


class SynergiaSubstitution(SynergiaGenericClass):
    def __init__(self, uid, resource, session):
        super().__init__(uid, resource, session)

    @classmethod
    def create(cls, uid=None, path=('Calendars', 'Substitutions'), session=None, extraction_key='Substitution',
               expire=timedelta(days=7)):
        return super().create(uid, path, session, extraction_key, expire)


class SynergiaRealization(SynergiaGenericClass):
    def __init__(self, uid, resource, session):
        super().__init__(uid, resource, session)
        self.topic = resource['Topic']
        self.date = datetime.strptime(resource['Date'], '%Y-%m-%d')
        self.is_trip = resource['IsTrip']
        self.teaching_program = resource.get('TeachingProgramTopic')
        self.lesson_no = resource['LessonNo']
        self.objects.set_object(
            'teacher', self._json_resource['AddedBy']['Id'], SynergiaTeacher
        ).set_object(
            'lesson', resource['Lesson']['Id'], SynergiaLesson
        )

    @property
    def teacher(self):
        """
        :rtype: librus_tricks.classes.SynergiaTeacher
        """
        return self.objects.assembly('teacher')

    @property
    def lesson(self):
        """
        :rtype: librus_tricks.classes.SynergiaLesson
        """
        return self.objects.assembly('lesson')

    @classmethod
    def create(cls, uid=None, path=('Realizations',), session=None, extraction_key='Realization',
               expire=timedelta(seconds=1)):
        return super().create(uid, path, session, extraction_key, expire)

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.topic}>'
