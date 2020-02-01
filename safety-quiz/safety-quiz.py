# imports
import os
from flask import Flask, request, session, redirect, url_for, render_template, flash, send_from_directory, Markup
from flask_bootstrap import Bootstrap
from flask_fontawesome import FontAwesome
import sqlalchemy as sa
from multidict import MultiDict
from werkzeug.utils import secure_filename
from werkzeug.exceptions import NotFound
from werkzeug.middleware.dispatcher import DispatcherMiddleware
import random

from model import User, UserLocation, Type, Training, Machine, Quiz, Question, Option, init_db

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

@app.before_request
def before_request():
	if 'sid' not in session \
			and request.endpoint != 'login':
		return redirect(url_for('login'))


@app.route('/')
def index():
	db = db_session()
	trainings = db.query(Training).outerjoin(Machine).filter(Training.trainee_id == session['sid']).filter(Training.invalidation_date == None).filter(Machine.location_id.in_((2,3))).order_by(Training.date).all()
	if session['admin']:
		quizzes = db.query(Machine).filter(Machine.quiz_id != None).order_by(Machine.quiz_id).all()
		return render_template('admin/index.html', trainings=trainings, quizzes=quizzes)
	else:
		return render_template('index.html', trainings=trainings)


@app.route('/admin/upload', methods=['GET', 'POST'])
def upload_file():
	if request.method == 'POST':
		# check if the post request has the file part
		if 'file' not in request.files:
			flash('No file part')
			return redirect(url_for('index'))
		file = request.files['file']
		# if user does not select file, browser also
		# submit an empty part without filename
		if file.filename == '':
			flash('No selected file')
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


@app.route('/login', methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		db = db_session()
		user = db.query(User).filter_by(email=request.form['email']).one_or_none()
		if user and (user.sid == int(request.form['pin'])):
			session['sid'] = user.sid
			session['email'] = user.email
			user_level_list = db.query(Type.level).outerjoin(UserLocation).filter(UserLocation.sid == session['sid']).all()
			user_max_level = max([item for t in user_level_list for item in t])
			if user_max_level > 75:
				session['admin'] = user_max_level
			else:
				session['admin'] = None
			return redirect(url_for('index'))
		else:
			flash("User / Pin combonation incorrect.", 'danger')
			return render_template('login.html')
	else:
		return render_template('login.html')


@app.route('/logout')
def logout():
	session.clear()
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

	if request.method == 'GET':
		return render_template('quiz.html', training=training, questions=questions)
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
				wrong_questions.append(str(question.prompt))
		quiz_percent = round(((quiz_current_score / quiz_max_score) * 100),2)
		training.quiz_score = quiz_percent
		training.quiz_date = sa.func.now()
		if training.quiz_attempts:
			training.quiz_attempts += 1
		else: training.quiz_attempts = 1
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
	app.run(host='0.0.0.0', debug=True, port=app.config['PORT'])
	app.jinja_env.auto_reload = True
	app.config['TEMPLATES_AUTO_RELOAD'] = True
