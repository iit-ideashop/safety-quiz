# imports
import os
import datetime

import flask
from flask import Flask, request, session, redirect, url_for, render_template, flash, send_from_directory, Markup, jsonify, g
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

from checkIn.model import User, UserLocation, Type, Training, Machine, Quiz, Question, Option, MissedQuestion, init_db, Major, College, HawkCard
from reservation import ReservationType, ReservationWindow, Reservations, HasRemoveMethod, init_reservation_db

# blueprintname.route not app.route
from covid import covid
from auth import auth

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
SCOPES = ["https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile", 'openid']
API_SERVICE_NAME = 'oauth2'
API_VERSION = 'v2'

@app.before_request
def before_request():
    g.db_session = init_db(app.config['DB'])
    if 'sid' not in session \
            and request.endpoint not in ['auth.login', 'auth.login_google', 'auth.authorize', 'auth.oauth2callback', 'register', 'check_sid',
                                         'logout', 'get_machine_access']:
        print(request.endpoint)
        return redirect(url_for('auth.login'))


@app.errorhandler(Exception)
def error_handler(e):
    app.logger.error(e, exc_info=True)
    if type(e) == Warning and 'google' in str(e):
        flash('Looks like something went wrong with Google Login. Please try this legacy login instead.', 'danger')
        return redirect(url_for('auth.login', legacy=True))
    flash(Markup('<b>An error occurred.</b> Please contact <a href="mailto:ideashop@iit.edu">ideashop@iit.edu</a> and include the '
          'current time ' + str(datetime.datetime.now().strftime('%x %X')) +
          ' as well as a brief description of what you were doing.'), 'danger')
    return redirect(url_for('index'))

@app.route('/')
def index():
    db = db_session()
    trainings = db.query(Training).outerjoin(Machine).filter(Training.trainee_id == session['sid']).filter(Training.invalidation_date == None).filter(Machine.location_id.in_((2,3))).order_by(Training.date).all()
    if session['admin'] and session['admin'] >= 85:
        quizzes = db.query(Machine).filter(Machine.quiz_id != None).order_by(Machine.quiz_id).all()
        return render_template('admin/index.html', trainings=trainings, quizzes=quizzes)
    else:
        return render_template('index.html', trainings=trainings)


@app.route('/admin/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(url_for('index'))
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(url_for('index'))
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


@app.route('/logout')
def logout():
    revoke()
    clear_credentials()
    session.clear()
    return redirect(url_for('auth.login'))

def revoke():
  if 'credentials' not in session:
    return ('You need to <a href="/auth.authorize">authorize</a> before ' +
            'testing the code to revoke credentials.')

  credentials = google.oauth2.credentials.Credentials(
    **session['credentials'])

  revoke = requests.post('https://oauth2.googleapis.com/revoke',
      params={'token': credentials.token},
      headers={'content-type': 'application/x-www-form-urlencoded'})

  status_code = getattr(revoke, 'status_code')
  if status_code == 200:
    return('Credentials successfully revoked.')
  else:
    return('An error occurred.')

def clear_credentials():
    if 'credentials' in session:
        del session['credentials']
    return ('Credentials have been cleared.<br><br>')

@app.route('/quiz/override/<training_id>', methods=['GET','POST'])
def override(training_id):
    db = db_session()
    training = db.query(Training).filter(Training.id == training_id).one_or_none()
    if request.method == 'POST':
        quiz(training_id)
        if int(training.quiz_score) == 100:
            return redirect(url_for('index'))
    if not (training and training.machine and training.machine.quiz and training.machine.quiz.questions):
        flash("There was an error with your request. Please try again or see Idea Shop staff if the issue persists.", 'danger')
        return redirect(url_for('index'))
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
        return redirect(url_for('index'))


@app.route('/quiz/<training_id>', methods=['GET', 'POST'])
def quiz(training_id):
    db = db_session()
    training = db.query(Training).filter(Training.id == training_id).one_or_none()
    if not (training and training.machine and training.machine.quiz and training.machine.quiz.questions):
        flash("There was an error with your request. Please try again or see Idea Shop staff if the issue persists.", 'danger')
        return redirect(url_for('index'))
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
            return redirect(url_for('index'))
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
        return redirect(url_for('index'))
    else:
        flash("There was an error with your request. Please try again or see Idea Shop staff if the issue persists.", 'danger')
        return redirect(url_for('index'))


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
        return redirect(url_for('index'))


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

@app.route('/reservations', methods=['GET','POST'])
def reservations():
    if request.method == 'GET':
        ##temp disable reservations since users can still reserve time for current day even if in disbaled range
        if app.config['ALLOW_RESERVATIONS'] != 'True':
            flash("Reservations are currently unavailable and will resume for the Spring 2021 semester.",'warning')
            return render_template('layout.html')
        db = db_session()
        temp = db.query(UserLocation).filter_by(sid=session['sid']).filter_by(location_id=2).one_or_none().get_missing_trainings(db)
        if (9 in [each[0].id for each in temp]):
            flash("You are not cleared to make reservations at this time. Please chcek the status of your safety trainings or contact Idea Shop staff for assistance.",'warning')
            return render_template('layout.html')
        user = db.query(User).filter_by(sid=session['sid']).one_or_none()
        reservation_types = db_reservations().query(ReservationType).order_by(ReservationType.id.asc()).all()
        db.close()
        return render_template('reservations.html', reservation_types=reservation_types, user=user, openDate=datetime.date(2020, 9, 8), dateWindows=get_window())
    if request.method == 'POST':
        user = db_session().query(User).filter_by(sid=session['sid']).one_or_none()
        start_time = datetime.datetime.strptime(request.form['start_time'],"%Y-%m-%d %X")
        end_time = datetime.datetime.strptime(request.form['end_time'],"%Y-%m-%d %X")
        db = db_reservations()
        reservation_type = db.query(ReservationType).filter_by(id=int(request.form['reservation_type'])).one_or_none()
        parent = Reservations(type_id=reservation_type.id, start=start_time, end=end_time, sid=user.sid)
        db.add(parent)
        db.flush()
        flash("Created %s reservation for %s, %s - %s" % (reservation_type.name, user.name, parent.start, parent.end),'success')
        for each in [x for x in list(request.form.keys()) if 'user' in x and request.form[x] != '']:
            response = confirmAllowed(request.form[each])
            if response['valid'] is True:
                db.add(Reservations(type_id=int(request.form['reservation_type']), start=start_time, end=end_time, sid=response['user'].sid, parent_id=parent.id))
                db.flush()
                flash("Created %s reservation for %s, %s - %s" % (reservation_type.name, response['user'].name, parent.start, parent.end),'success')
        db.commit()
        return redirect(url_for('reservations'))

def confirmAllowed(email):
    db = db_session()
    user = db.query(User).filter_by(email=email).one_or_none()
    if user:
        userLocation = db.query(UserLocation).filter_by(sid=user.sid).filter_by(location_id=2).one_or_none()
        if userLocation :
            temp = userLocation.get_missing_trainings(db)
            if (9 in [each[0].id for each in temp]):
                flash("User %s is not cleared for reservations." % email, 'danger')
                return {'valid': False,'user': user}
            else:
                return {'valid': True, 'user': user}
    else:
        flash("User %s does not exist and cannot join reservations." % email, 'danger')
        return {'valid': False, 'user': None}

@app.route('/reservations/api/checkEmail')
def checkEmail():
    db = db_session()
    user = db.query(User).filter_by(email=request.args['email']).one_or_none()
    if user:
        userLocation = db.query(UserLocation).filter_by(sid=user.sid).filter_by(location_id=2).one_or_none()
        if userLocation:
            temp = userLocation.get_missing_trainings(db)
            if (9 in [each[0].id for each in temp]):
                return jsonify({'valid': False, 'reason': "User not cleared for reservations."})
            else:
                return jsonify({'valid': True, 'reason': "User cleared for reservations."})
        else:
            return jsonify({'valid': False, 'reason': "User not cleared for reservations."})
    return jsonify({'valid': False, 'reason': "User does not exist."})

@app.route('/reservations/api/type')
def get_type():
    x = db_reservations().query(ReservationType).filter_by(id=int(request.args['type_id'])).one_or_none()
    if x :
        return jsonify({'id':x.id,'name':x.name,'quantity':x.quantity,'capacity':x.capacity})
    else:
        return ''''''

@app.route('/reservations/api/start_times', methods=['GET'])
def start_times():
    db = db_reservations()
    requested_date = datetime.datetime.strptime(request.args['date'][:15], "%a %b %d %Y").date()
    reservation_type = db.query(ReservationType).filter_by(id=int(request.args['type_id'])).one()
    existing_reservations = db.query(Reservations).filter(Reservations.start >= requested_date).filter(Reservations.end < requested_date+datetime.timedelta(days=1)).filter(Reservations.type_id == reservation_type.id).filter(Reservations.parent_id == None).all()
    open = True
    if open:
        open_time = datetime.datetime.combine(requested_date,datetime.time(9,0))
        close_time = datetime.datetime.combine(requested_date,datetime.time(17,0))
        delta_time = datetime.timedelta(hours=0,minutes=15)
        start_times = []
        for i in range(open_time.hour*60+open_time.minute,close_time.hour*60+close_time.minute,int(delta_time.seconds / 60)):
            i = datetime.datetime.combine(requested_date,datetime.time(int(i/60),int(i%60)))
            availability = reservation_type.quantity
            for each in existing_reservations:
                if i > (each.start - (2*delta_time)) and i < (each.end + (2*delta_time)):
                    availability -= 1
            if availability > 0:
                start_times.append(i)
        return jsonify([{'date': str(x.date()), 'time': str(x.time())} for x in start_times])

@app.route('/reservations/api/end_times', methods=['GET'])
def end_times():
    db = db_reservations()
    reservation_type = db.query(ReservationType).filter_by(id = int(request.args['type_id'])).one()
    start_time = datetime.datetime.strptime(request.args['start_time'],"%Y-%m-%d %X")
    existing_reservations = db.query(Reservations).filter(Reservations.start >= start_time).filter(Reservations.end < start_time.date() + datetime.timedelta(days=1)).filter(Reservations.type_id == reservation_type.id).filter(Reservations.parent_id == None).all()
    close_time = datetime.datetime.combine(start_time.date(), datetime.time(17, 0))
    delta_time = datetime.timedelta(hours=0, minutes=15)
    max_reservation_minutes = 180
    end_times = []
    for i in range(((start_time+delta_time).hour * 60) + (start_time+delta_time).minute, min((close_time.hour * 60) + close_time.minute,((start_time+delta_time).hour * 60) + (start_time+delta_time).minute + max_reservation_minutes), int(delta_time.seconds / 60)):
        i = datetime.datetime.combine(start_time.date(), datetime.time(int(i / 60), int(i % 60)))
        availability = reservation_type.quantity
        for each in existing_reservations:
            if i > (each.start - (2*delta_time)):
                availability -= 1
        if availability > 0:
            end_times.append(i)
        else: break
    return jsonify([{'date': str(x.date()), 'time': str(x.time())} for x in end_times])

@app.route('/reservations/api/windows', methods=['GET'])
def get_window():
    db = db_reservations()
    temp = db.query(ReservationWindow).filter(ReservationWindow.start >= datetime.datetime.today().date()).all()
    return [x.start.strftime('%m %d %Y') for x in temp]

@app.route('/reservations/view')
def view_reservations():
    db = db_reservations()
    start = datetime.datetime.combine(datetime.datetime.now().date(),datetime.time(0,0,0))
    end = datetime.datetime.combine(datetime.datetime.now().date(),datetime.time(23,59,59))
    reservations = db.query(Reservations).filter(Reservations.start > start).filter(Reservations.end < end).order_by(Reservations.start.asc()).all()
    return render_template('view_reservations.html', reservations=reservations)

@app.route('/api/machine_access', methods=['POST'])
def get_machine_access():
    if not request.form or not all(items in request.form.keys() for items in ['machine_name', 'machine_id']):
        return jsonify({'response': 'Invalid request.'})
    machine_id = int(request.form['machine_id'])
    machine_name = request.form['machine_name']
    db = db_session()
    machine = db.query(Machine).filter_by(id=machine_id).one_or_none()
    if machine and machine.name != machine_name:
        return jsonify({'response': 'Invalid request.'})
    sid_list = [item[0] for item in db.query(Training.trainee_id).filter_by(machine_id=machine_id).filter_by(invalidation_date=None)\
        .filter_by(quiz_score=100.0).all()]
    access_list = db.query(HawkCard).filter(HawkCard.sid.in_(sid_list)).all()
    return jsonify({'response': 'Request Successful', 'users':[{'sid': card.sid, 'name': card.user.name, 'facility': card.facility, 'card_number': card.card} for card in access_list]})


# app routes end

@app.teardown_appcontext
def close_db(error):
    db_session.remove()


# end teardown

def no_app(environ, start_response):
    return NotFound()(environ, start_response)

# Blueprint registration

app.register_blueprint(covid)
#app.register_blueprint(nightly)
app.register_blueprint(auth)

# main
if __name__ == '__main__':
    #os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' #if insecure dev uncomment
    app.wsgi_app = DispatcherMiddleware(no_app, {'/safety': app.wsgi_app})
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(host='0.0.0.0', debug=bool(app.config['DEBUG']), port=app.config['PORT'])