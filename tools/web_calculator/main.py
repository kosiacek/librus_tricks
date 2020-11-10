import logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(module)s:%(lineno)d - %(funcName)s - %(message)s')

from flask import Flask, render_template, request
from librus_tricks import create_session, exceptions, cache
from librus_tricks.tools import *

app = Flask(__name__)
my_cache = cache.AlchemyCache()


@app.route('/')
def home_view():
    return render_template('home.html')


@app.route('/average', methods=['POST'])
def count_averages():
    logging.info('Recived json %s', request.json)
    try:
        session = create_session(request.json['email'], request.json['password'], cache=my_cache)
        logging.info('Session created %s', session)
    except exceptions.LibrusPortalInvalidPasswordError:
        logging.info('Bad password')
        return render_template('bad_password.html')
    except exceptions.CaptchaRequired:
        logging.info('Captcha')
        return render_template('damn_captcha.html')
    return render_template('averages.html',
                           averages=subjects_averages(session.grades_categorized),
                           percentages=percentage_average(session.grades()))


@app.route('/attendance', methods=['POST'])
def count_user_attendances():
    logging.info('Recived json %s', request.json)
    try:
        session = create_session(request.json['email'], request.json['password'], cache=my_cache)
        logging.info('Session created %s', session)
    except exceptions.LibrusPortalInvalidPasswordError:
        logging.info('Bad password')
        return render_template('bad_password.html')
    except exceptions.CaptchaRequired:
        logging.info('Captcha')
        return render_template('damn_captcha.html')
    return render_template('attenances.html', attendances=count_attendances(session.attendances()),
                           percentages=percentages_of_attendances(session.attendances()),
                           present=present_percentage(session.attendances()),
                           absences=session.all_absences)


if __name__ == '__main__':
    app.run()
