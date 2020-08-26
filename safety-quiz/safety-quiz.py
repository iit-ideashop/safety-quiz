# imports
import os
from datetime import datetime
from flask import Flask, request, session, redirect, url_for, render_template, flash, send_from_directory, Markup
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

from model import User, UserLocation, Type, Training, Machine, Quiz, Question, Option, MissedQuestion, init_db

# app setup
app = Flask(__name__, static_url_path='/static', static_folder='static')  # create the application instance :)
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


# This variable specifies the name of a file that contains the OAuth 2.0
# information for this application, including its client_id and client_secret.
CLIENT_SECRETS_FILE = "client_secret.json"

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account and requires requests to use an SSL connection.
SCOPES = ["https://www.googleapis.com/auth/userinfo.email",'openid']
API_SERVICE_NAME = 'oauth2'
API_VERSION = 'v2'


@app.before_request
def before_request():
	if 'sid' not in session \
			and request.endpoint not in ['login','authorize','oauth2callback']:
		return redirect(url_for('login'))

@app.errorhandler(Exception)
def error_handler(e):
	app.logger.error(e, exc_info=True)
	flash(Markup('<b>An error occurred.</b> Please contact <a href="mailto:ideashop@iit.edu">ideashop@iit.edu</a> and include the '
		  'current time ' + str(datetime.now().strftime('%x %X')) +
		  ' as well as a brief description of what you were doing.'), 'danger')
	return redirect(url_for('index'))


@app.route('/')
def index():
	db = db_session()
	trainings = db.query(Training).outerjoin(Machine).filter(Training.trainee_id == session['sid']).filter(Training.invalidation_date == None).filter(Machine.location_id.in_((2,3))).order_by(Training.date).all()
	if session['admin']:
		quizzes = db.query(Machine).filter(Machine.quiz_id != None).order_by(Machine.quiz_id).all()
		return render_template('admin/index.html', trainings=trainings, quizzes=quizzes)
	else:
		return render_template('index.html', trainings=trainings)

@app.route('/COVID',methods=['GET', 'POST'])
def COVID():
	if request.method == 'GET':
		return render_template('COVID_video.html')
	elif request.method == 'POST':
		db = db_session()
		print(request.form['sid'])
		db.add(Training(trainee_id=int(request.form['sid']),trainer_id=20000000,machine_id=27,date=sa.func.now()))
		db.commit()
		flash("Thank you for participating in the Assembly Area Fall 2020 COVID training. Your verification quiz will be available on this site in one week. \
			You can re-watch the video at any time by visiting https://wiki.ideashop.iit.edu/index.php?title=COVID-19_%26_Remote_File_Submissions",'success')
		return redirect(url_for('index'))

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


@app.route('/oauth2callback')
def oauth2callback():
	# Specify the state when creating the flow in the callback so that it can
	# verified in the authorization server response.
	state = session['state']

	flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
		CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
	flow.redirect_uri = url_for('oauth2callback', _external=True)

	# Use the authorization server's response to fetch the OAuth 2.0 tokens.
	authorization_response = request.url
	flow.fetch_token(authorization_response=authorization_response)

	# Store credentials in the session.
	# ACTION ITEM: In a production app, you likely want to save these
	#              credentials in a persistent database instead.
	credentials = flow.credentials
	session['credentials'] = credentials_to_dict(credentials)
	return redirect(url_for('login'))

def credentials_to_dict(credentials):
	return {'token': credentials.token,
			'refresh_token': credentials.refresh_token,
			'token_uri': credentials.token_uri,
			'client_id': credentials.client_id,
			'client_secret': credentials.client_secret,
			'scopes': credentials.scopes}


@app.route('/login', methods=['GET', 'POST'])
def login():
	if 'credentials' not in session:
		return redirect('authorize')

	# Load credentials from the session.
	credentials = google.oauth2.credentials.Credentials(
		**session['credentials'])

	profile = googleapiclient.discovery.build(API_SERVICE_NAME, API_VERSION, credentials=credentials)

	gSuite = profile.userinfo().get().execute()

	# Save credentials back to session in case access token was refreshed.
	# ACTION ITEM: In a production app, you likely want to save these
	#              credentials in a persistent database instead.
	session['credentials'] = credentials_to_dict(credentials)

	db = db_session()
	user = db.query(User).filter_by(email=gSuite['email']).one_or_none()
	if user:
		session['sid'] = user.sid
		session['email'] = user.email
		user_level_list = db.query(Type.level).outerjoin(UserLocation).filter(UserLocation.sid == session['sid']).all()
		if not user_level_list:
			flash("No User Agreement on file. Please see Idea Shop staff.", 'danger')
			return render_template('login.html')
		user_max_level = max([item for t in user_level_list for item in t])
		if user_max_level == 100:
			session['admin'] = user_max_level
		else:
			session['admin'] = None
		return redirect(url_for('index'))
	else:
		flash("User / Pin combination incorrect.", 'danger')
		return render_template('login.html')

@app.route('/authorize')
def authorize():
	# Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
	flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
		CLIENT_SECRETS_FILE, scopes=SCOPES)

	# The URI created here must exactly match one of the authorized redirect URIs
	# for the OAuth 2.0 client, which you configured in the API Console. If this
	# value doesn't match an authorized URI, you will get a 'redirect_uri_mismatch'
	# error.
	flow.redirect_uri = url_for('oauth2callback', _external=True)

	authorization_url, state = flow.authorization_url(
		# Enable offline access so that you can refresh an access token without
		# re-prompting the user for permission. Recommended for web server apps.
		access_type='offline',
		# Enable incremental authorization. Recommended as a best practice.
		include_granted_scopes='true')

	# Store the state so the callback can verify the auth server response.
	session['state'] = state

	return redirect(authorization_url)


@app.route('/logout')
def logout():
	revoke()
	clear_credentials()
	session.clear()
	return redirect(url_for('login'))

def revoke():
  if 'credentials' not in session:
    return ('You need to <a href="/authorize">authorize</a> before ' +
            'testing the code to revoke credentials.')

  credentials = google.oauth2.credentials.Credentials(
    **session['credentials'])

  revoke = requests.post('https://oauth2.googleapis.com/revoke',
      params={'token': credentials.token},
      headers = {'content-type': 'application/x-www-form-urlencoded'})

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


# app routes end

@app.teardown_appcontext
def close_db(error):
	db_session.remove()


# end teardown

def no_app(environ, start_response):
	return NotFound()(environ, start_response)


# main
if __name__ == '__main__':
	app.wsgi_app = DispatcherMiddleware(no_app, {'/safety': app.wsgi_app})
	app.jinja_env.auto_reload = True
	app.config['TEMPLATES_AUTO_RELOAD'] = True
	app.run(host='0.0.0.0', debug=bool(app.config['DEBUG']), port=app.config['PORT'])
