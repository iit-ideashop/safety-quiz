# imports
import os
import datetime

import flask
from flask import Flask, request, session, redirect, url_for, render_template, flash, send_from_directory, Markup, jsonify, g, Blueprint
from flask_bootstrap import Bootstrap
from flask_fontawesome import FontAwesome
import sqlalchemy as sa
from multidict import MultiDict
from werkzeug.utils import secure_filename
from werkzeug.exceptions import NotFound
from werkzeug.middleware.dispatcher import DispatcherMiddleware
import random
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
import requests
from flask import current_app

from checkIn.model import User, UserLocation, Type, Access, Location, Training, Machine, Quiz, Question, Option, MissedQuestion, init_db, Major, College, HawkCard
#from reservation import ReservationType, ReservationWindow, Reservations, HasRemoveMethod, init_reservation_db
# blueprintname.route not app.route
from video import video
from public import public
from userflow import userflow
from auth import auth
from reservation import init_reservation_db, reservation_bp

# app setup
app = Flask(__name__, static_url_path='/safety/static', static_folder='static')  # create the application instance :)
app.config.from_object(__name__)
app.config.from_pyfile('config.cfg')
app.config.from_envvar('FLASKR_SETTINGS', silent=True)
UPLOAD_FOLDER = 'static/images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# application
Bootstrap(app)
FontAwesome(app)

db_session = init_db(app.config['DB'])
db_reservations = init_reservation_db(app.config['DB_RESERVATION'])

# This variable specifies the name of a file that contains the OAuth 2.0
# information for this application, including its client_id and client_secret.
CLIENT_SECRETS_FILE = "client_secret.json"

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account and requires requests to use an SSL connection.
SCOPES = ["https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile",
          'openid']
API_SERVICE_NAME = 'oauth2'
API_VERSION = 'v2'

@app.before_request
def before_request():
    g.db_session = init_db(app.config['DB'])
    if 'sid' not in session \
            and request.endpoint not in ['auth.login', 'auth.login_google', 'auth.authorize', 'auth.oauth2callback',
                                         'register', 'check_sid', 'logout', 'get_machine_access','welcome',
                                         'public.shop_status', 'static', 'public.custom_css', 'public.animation_js',
                                         'public.index']:
        print(request.endpoint)
        return redirect(url_for('auth.login'))


@app.context_processor
def utility_processor():
    def current_time():

        return datetime.datetime.now().strftime('%x %X')
    return dict(current_time=current_time)

@app.errorhandler(Exception)
def error_handler(e):
    app.logger.error(e, exc_info=True)
    if type(e) == Warning and 'google' in str(e):
        flash('Looks like something went wrong with Google Login. Please try this legacy login instead.', 'danger')
        return redirect(url_for('auth.login', legacy=True))
    flash(Markup('<b>An error occurred.</b> Please contact <a href="mailto:ideashop@iit.edu">ideashop@iit.edu</a> and include the '
          'current time ' + str(datetime.datetime.now().strftime('%x %X')) +
          ' as well as a brief description of what you were doing.'), 'danger')
    return redirect(url_for('public.index'))

@app.route('/admin/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(url_for('public.index'))
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(url_for('public.index'))
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('uploaded_file',
                                    filename=filename))


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'GET' and ({'email', 'name'}.issubset([x for x in request.args.keys()])):
        db = db_session()
        majors = db.query(Major).order_by(Major.name.asc()).all()
        colleges = db.query(College).order_by(College.name.asc()).all()
        statuses = ['undergraduate', 'graduate', 'continuing_education', 'employee']
        return render_template('register.html', email=request.args['email'], name=request.args['name'], majors=majors, colleges=colleges, statuses=statuses)
    elif request.method == 'POST' and {'sid', 'name', 'email', 'major', 'college', 'status'}.issubset([x for x in request.form.keys()]):
        db = db_session()
        major = db.query(Major).filter_by(id=int(request.form['major'])).one_or_none()
        college = db.query(College).filter_by(id=int(request.form['college'])).one_or_none()
        if college and major:
            user = User(sid=int(request.form['sid']), name=request.form['name'], email=request.form['email'], major_id=major.id, college_id=college.id, status=request.form['status'])
        else:
            user = User(sid=int(request.form['sid']), name=request.form['name'], email=request.form['email'], status=request.form['status'])
        db.add(user)
        db.add(UserLocation(sid=user.sid,location_id=2,type_id=2))
        db.add(UserLocation(sid=user.sid,location_id=3,type_id=2))
        db.commit()
        flash("Registered user %s." % user.name, 'success')
        return redirect(url_for('auth.login_google'))
    else:
        flash("Error.",'danger')
        return render_template('layout.html')


@app.route('/register/api/checkSID')
def check_sid():
    db = db_session()
    user = db.query(User).filter_by(sid=request.args['sid']).one_or_none()
    if user:
        return jsonify({'sid': user.sid, 'exists': True})
    else:
        return jsonify({'sid': None, 'exists': False})


@app.route('/quiz/override/<training_id>', methods=['GET','POST'])
def override(training_id):
    db = db_session()
    training = db.query(Training).filter(Training.id == training_id).one_or_none()
    if request.method == 'POST':
        quiz(training_id)
        if int(training.quiz_score) == 100:
            return redirect(url_for('public.index'))
    if not (training and training.machine and training.machine.quiz and training.machine.quiz.questions):
        flash("There was an error with your request. Please try again or see Idea Shop staff if the issue persists.", 'danger')
        return redirect(url_for('public.index'))
    else:
        questions = training.machine.quiz.questions
        random.shuffle(questions)

    quiz_stats = db.query(sa.func.stddev(Training.quiz_attempts).label('stddev'),
                          sa.func.avg(Training.quiz_attempts).label('avg')) \
        .filter(Training.quiz_attempts > 0) \
        .filter(Training.machine_id == training.machine_id) \
        .one()

    if training.quiz_attempts and training.quiz_attempts < max(float(quiz_stats.avg) + (3.5 * quiz_stats.stddev), 12):
        remaining_attempts = max(float(quiz_stats.avg) + (3.5 * quiz_stats.stddev), 12) - training.quiz_attempts
        flash("Override mode: %s attempts remaining." % remaining_attempts, 'danger')
        return render_template('quiz.html', training=training, questions=questions, warning=True)
    else:
        flash("You have reached the maximum number of override attempts on the %s quiz without passing. Please see Idea Shop staff for assistance." % (training.machine.name), 'danger')
        return redirect(url_for('public.index'))


@app.route('/quiz/<training_id>', methods=['GET', 'POST'])
def quiz(training_id):
    db = db_session()
    training = db.query(Training).filter(Training.id == training_id).one_or_none()
    if not (training and training.machine and training.machine.quiz and training.machine.quiz.questions):
        flash("There was an error with your request. Please try again or see Idea Shop staff if the issue persists.", 'danger')
        return redirect(url_for('public.index'))
    else:
        questions = training.machine.quiz.questions
        random.shuffle(questions)

    quiz_stats = db.query(sa.func.stddev(Training.quiz_attempts).label('stddev'), sa.func.avg(Training.quiz_attempts).label('avg')) \
        .filter(Training.quiz_attempts > 0) \
        .filter(Training.machine_id == training.machine_id) \
        .one()

    if request.method == 'GET':
        if training.quiz_attempts and training.quiz_attempts >= max(float(quiz_stats.avg) + (3 * quiz_stats.stddev), 10):
            flash("You have reached the maximum number of attempts on the %s quiz without passing and your training has been invalidated. Please see Idea Shop staff for assistance." % (training.machine.name), 'danger')
            return redirect(url_for('public.index'))
        if training.quiz_attempts and training.quiz_attempts >= max(float(quiz_stats.avg) + (1.5 * quiz_stats.stddev), 6):
            warning = True
        else:
            warning = False
        return render_template('quiz.html', training=training, questions=questions, warning=warning)
    elif request.method == 'POST':
        quiz_max_score = 0.0
        quiz_current_score = 0.0
        wrong_questions = []
        for question in questions:
            quiz_max_score += 1
            question_current_score = 0
            question_max_score = 0
            for option in question.option:
                if (option.correct == 1) and (str(option.id) in request.form.getlist(str(question.id))):
                    # print("Correct: %s" % option.id)
                    question_current_score += 1
                    question_max_score += 1
                elif (str(option.id) in request.form.getlist(str(question.id))):
                    # print("Incorrect: %s" % option.id)
                    question_current_score -= 1
                elif (option.correct == 1):
                    # print("Missed: %s" % option.id)
                    question_max_score += 1
            if question_max_score == question_current_score:
                quiz_current_score += 1.0
            else:
                db.add(MissedQuestion(question_id=question.id,training_id=training.id))
                wrong_questions.append(str(question.prompt))
        quiz_percent = round(((quiz_current_score / quiz_max_score) * 100),2)
        training.quiz_score = quiz_percent
        training.quiz_date = sa.func.now()

        if training.quiz_attempts:
            training.quiz_attempts += 1
            if quiz_percent != 100.00 and training.quiz_attempts >= max(float(quiz_stats.avg) + (3 * quiz_stats.stddev), 10):
                training.invalidation_date = sa.func.now()
                training.invalidation_reason = "Quiz attempt maximum reached."
                flash(
                    "You have reached the maximum number of attempts on the %s quiz without passing and your training has been invalidated. Please see Idea Shop staff for assistance." % (
                        training.machine.name), 'danger')

        else:
            training.quiz_attempts = 1
        db.commit()
        if quiz_percent == 100.00:
            flash(("Score: %s/%s (%s%%)" % (quiz_current_score, quiz_max_score, quiz_percent)), 'info')
        else:
            message = str("Score: %s/%s (%s%%)" % (quiz_current_score, quiz_max_score, quiz_percent)) + str("<br>Incorrect response to:<ul>")
            for each in wrong_questions:
                message += "<li>"
                message += str(each)
                message += "</li>"
            message += "</ul>"
            flash(Markup(message), 'warning')
        return redirect(url_for('public.index'))
    else:
        flash("There was an error with your request. Please try again or see Idea Shop staff if the issue persists.", 'danger')
        return redirect(url_for('public.index'))


@app.route('/edit_quiz/<id>', methods=['GET', 'POST'])
def edit_quiz(id):
    db = db_session()
    if session['admin']:
        if request.method == 'GET':
            questions = db.query(Question).filter_by(quiz_id=id).all()
            quiz = db.query(Quiz).filter_by(id=id).one()
            return render_template('admin/quiz.html', quiz=quiz, questions=questions, id=id)
        elif request.method == 'POST':
            form_data = MultiDict()
            form_data.extend({'question': {}})
            form_data.extend({'option': {}})
            for each in request.form.items():
                if each[0] == 'add_option':
                    form_data['question'][each[1]]['add_option'] = True
                elif each[0] == 'add_question':
                    form_data['add_question'] = True
                elif each[0] == 'delete_question':
                    form_data['question'][each[1]]['delete'] = True
                elif each[0] == 'delete_option':
                    form_data['option'][each[1]]['delete'] = True
                else:
                    line_data = each[0].split("_")
                    if not form_data[line_data[0]].get(line_data[1]):
                        form_data[line_data[0]].update({line_data[1]: {line_data[2]: each[1]}})
                    else:
                        form_data[line_data[0]][line_data[1]].update({line_data[2]: each[1]})

            if 'add_question' in form_data:
                new_question = Question(quiz_id=id, prompt='New Question', description='New Description')
                db.add(new_question)
                for i in range(4):
                    db.add(Option(text='Option ' + str(i + 1), question=new_question))

            for question_id in form_data['question']:
                if db.query(Question).filter_by(id=question_id):
                    if 'add_option' in form_data['question'][question_id]:
                        db.add(Option(question_id=question_id, text='New Option'))

                    db.merge(Question(id=question_id,
                                      prompt=form_data['question'][question_id]['prompt'],
                                      description=form_data['question'][question_id]['description'],
                                      option_type=form_data['question'][question_id]['optiontype']))

            for option_id in form_data['option']:
                option = db.query(Option).get(option_id)
                if option:
                    if 'delete' in form_data['option'][option_id]:
                        db.delete(option)
                    else:
                        try:
                            if 'correct' in form_data['question'][str(option.question_id)]:
                                option.correct = form_data['question'][str(option.question_id)]['correct'] == str(
                                    option_id)
                            else:
                                option.correct = 'correct' in form_data['option'][option_id]
                        except KeyError:
                            pass

                        db.merge(Option(id=option_id,
                                        text=form_data['option'][option_id]['text']))

            for question_id in form_data['question']:
                if 'delete' in form_data['question'][question_id]:
                    if 'delete' in form_data['question'][question_id]:
                        db.query(Option).filter_by(question_id=question_id).delete()
                        db.query(Question).filter_by(id=question_id).delete()
                else:
                    question = db.query(Question).get(question_id)
                    if question.option_type == 'radio':
                        # check that only one option is correct on a radio button question
                        found = False
                        for option in question.option:
                            if option.correct:
                                if not found:
                                    found = True
                                else:
                                    option.correct = False

            for file in request.files:
                if request.files[file] and allowed_file(request.files[file].filename):
                    print("New file %s: %s" % (file,request.files[file]))
                    object_data=file.split("_")
                    filename = secure_filename(request.files[file].filename)
                    request.files[file].save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    path = url_for('uploaded_file', filename=filename)
                    if object_data[0] == 'question':
                        db.merge(Question(id=object_data[1], image=path))
                    elif object_data[0] == 'option':
                        db.merge(Option(id=object_data[1], image=path))

            db.commit()
            return redirect(url_for('edit_quiz', id=id))
    else:
        return redirect(url_for('public.index'))


@app.route('/admin/api/add/<object_type>', methods=['POST'])
def add_object(object_type):
    db = db_session()
    if object_type == 'question':
        new = Question(quiz_id=request.form['quiz_id'])
        db.add(new)
        db.commit()
        return {'id': new.id}
    elif object_type == 'option':
        new = Option(question_id=request.form['question_id'])
        db.add(new)
        db.commit()
        return {'id': new.id}


# app routes end

@app.teardown_appcontext
def close_db(error):
    db_session.remove()


# end teardown

def no_app(environ, start_response):
    return NotFound()(environ, start_response)

# Blueprint registration
app.register_blueprint(video)
app.register_blueprint(reservation_bp)
app.register_blueprint(auth)
app.register_blueprint(public)
app.register_blueprint(userflow)
# main
if __name__ == '__main__':
    #os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' #if insecure dev uncomment
    app.wsgi_app = DispatcherMiddleware(no_app, {'/safety': app.wsgi_app})
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(host='0.0.0.0', debug=bool(app.config['DEBUG']), port=app.config['PORT'])
