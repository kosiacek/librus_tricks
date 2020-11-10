import os

from prettytable import PrettyTable

from librus_tricks import minified_login, SynergiaTimetable

session = minified_login(os.environ['librus_email'], os.environ['librus_password'])

timetable = session.timetable()


class EmptyWindow:
    subject = ''
    start = None
    end = None

    def __repr__(self):
        return '<Okienko>'

    def __str__(self):
        return ''


def matrix_completion(matrix):
    """

    :param list[list[librus_tricks.classes.SynergiaTimetableEvent]] matrix:
    :return:
    """
    first_lesson_no = 1
    last_lesson_no = 1
    for col in matrix:
        for lesson in col:
            if lesson.lesson_no > last_lesson_no:
                last_lesson_no = lesson.lesson_no
            if lesson.lesson_no < first_lesson_no:
                first_lesson_no = lesson.lesson_no

    col_pointer = 0
    for col in matrix:
        first_lesson = col[0].lesson_no
        last_lesson = col[-1].lesson_no

        lessons_to_add_on_beginning = first_lesson - first_lesson_no
        lessons_to_add_on_end = last_lesson_no - last_lesson

        matrix[col_pointer] = [EmptyWindow() for _ in range(lessons_to_add_on_beginning)] + \
                              [f'{lesson.subject.name} {lesson.classroom.symbol} ({lesson.teacher.name[0]}. {lesson.teacher.last_name})'
                               for lesson in col] + \
                              [EmptyWindow() for _ in range(lessons_to_add_on_end)]
        col_pointer += 1

    return matrix


def convert_timetable_matrix(timetable: SynergiaTimetable):
    days = timetable.days
    weekdays = []

    for weekday in days.keys():
        if days[weekday].lessons.__len__() > 0:
            weekdays.append(weekday.strftime("%A"))

    matrix = [[] for _ in weekdays]

    matrix_pointer = 0
    for day in days.values():
        for lesson in day.lessons:
            matrix[matrix_pointer].append(lesson)
        matrix_pointer += 1

    return matrix_completion(matrix), weekdays


def print_table(matrix, weekdays):
    """

    :param list[list[librus_tricks.classes.SynergiaTimetableEvent]] matrix:
    :return:
    """
    pt = PrettyTable()

    all_hours = set()
    for day in session.timetable().days.values():
        for lesson in day.lessons:
            if not isinstance(lesson, EmptyWindow):
                all_hours.add(f'{lesson.start.strftime("%H:%M")}-{lesson.end.strftime("%H:%M")}')

    pt.add_column('', sorted(all_hours))
    for pointer in range(matrix.__len__()):
        pt.add_column(
            weekdays[pointer],
            matrix[pointer]
        )
    print(pt)


if __name__ == '__main__':
    matrix, weekdays = convert_timetable_matrix(timetable)
    print_table(matrix, weekdays)
