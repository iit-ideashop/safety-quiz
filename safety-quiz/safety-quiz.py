# imports
from flask import Flask, request, session, g, redirect, url_for, render_template, abort, flash, get_flashed_messages, \
    jsonify
from flask_bootstrap import Bootstrap
import sqlalchemy as sa
from sqlalchemy.orm import relationship, scoped_session, sessionmaker, joinedload
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.mysql import INTEGER
from datetime import datetime
from typing import Optional, Tuple, List, Callable, Union
import decimal
import json

# app setup
app = Flask(__name__, static_url_path='/static', static_folder='static')  # create the application instance :)
app.config.from_object(__name__)
app.config.from_pyfile('config.cfg')
app.config.from_envvar('FLASKR_SETTINGS', silent=True)

# application
Bootstrap(app)

# DB Setup
engine = sa.create_engine(app.config['DB'], pool_recycle=3600, encoding='utf-8')
Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    sid = sa.Column(sa.Integer, primary_key=True, autoincrement=False, nullable=False)
    email = sa.Column(sa.String(length=50), nullable=False)
    admin = sa.Column(sa.Boolean, nullable=False, default=False)

    user_quizes = relationship('User_Quizes')

    def __repr__(self):
        return self.email


class Quiz(Base):
    __tablename__ = 'quizes'
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    name = sa.Column(sa.String(length=100), nullable=False)
    check_in_machine_id = sa.Column(sa.Integer, nullable=False)

    user_quizes = relationship('User_Quizes')

    def __repr__(self):
        return self.name


class User_Quizes(Base):
    __tablename__ = 'user_quizes'
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    user_id = sa.Column(sa.Integer, sa.ForeignKey('users.sid'), nullable=False)
    quiz_id = sa.Column(sa.Integer, sa.ForeignKey('quizes.id'), nullable=False)
    last_score = sa.Column(sa.DECIMAL(5, 2), nullable=True)
    last_taken = sa.Column(sa.DateTime, nullable=True)

    user = relationship('User', lazy="joined")
    quiz = relationship('Quiz', lazy="joined")

    def __repr__(self):
        return "%s scored %s on quiz %s on %s." % (self.user.email, self.last_score, self.quiz.name, self.last_taken)


class Question(Base):
    __tablename__ = 'questions'
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    quiz_id = sa.Column(sa.Integer, sa.ForeignKey('quizes.id'), nullable=False)
    prompt = sa.Column(sa.String(length=250))
    description = sa.Column(sa.String(length=250))
    image = sa.Column(sa.String(length=100))
    option_type = sa.Column(sa.String(length=50), nullable=False)

    quiz = relationship('Quiz', lazy="joined")
    option = relationship('Option')

    def __repr__(self):
        return self.prompt


class Option(Base):
    __tablename__ = 'options'
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    question_id = sa.Column(sa.Integer, sa.ForeignKey('questions.id'), nullable=False)
    text = sa.Column(sa.String(length=250), nullable=False)
    image = sa.Column(sa.String(length=100))
    correct = sa.Column(sa.Boolean, default=False, nullable=False)

    question = relationship('Question', lazy="joined")

    def __repr__(self):
        return self.text


# Just for type-hinting, if you know a better way please fix
class HasRemoveMethod:
    def remove(self):
        pass


# create tables if they don't exist & define db_sessions
db_session: Union[Callable[[], sa.orm.Session], HasRemoveMethod] = scoped_session(sessionmaker(bind=engine))
Base.metadata.create_all(engine)

@app.before_request
def before_request():
    if 'sid' not in session \
            and request.endpoint != 'login':
        return redirect(url_for('login'))

@app.route('/')
def index():
    db = db_session()
    available = db.query(User_Quizes).filter_by(user_id=session['sid']).all()
    if db.query(User).filter_by(sid=session['sid']).one().admin:
        return render_template('admin/index.html', available=available)
    else:
        return render_template('index.html', available=available)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        db = db_session()
        user = db.query(User).filter_by(email=request.form['email']).one_or_none()
        if user:
            session['sid'] = user.sid
            session['email'] = user.email
            return redirect(url_for('index'))
        else:
            flash("User not found.", 'danger')
            return render_template('login.html')
    else:
        return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/quiz/<id>', methods=['GET','POST'])
def quiz(id):
    db = db_session()
    questions = db.query(Question).filter_by(quiz_id=id).all()
    if request.method == 'GET':
        return render_template('quiz.html', questions=questions)
    elif request.method == 'POST':
        quiz_max_score = 0.0
        quiz_current_score = 0.0
        #print(request.form)
        for question in questions:
            quiz_max_score += 1
            question_current_score = 0
            question_max_score = 0
            for option in question.option:
                if (option.correct == 1) and (str(option.id) in request.form.getlist(str(question.id))):
                    #print("Correct: %s" % option.id)
                    question_current_score += 1
                    question_max_score += 1
                elif (str(option.id) in request.form.getlist(str(question.id))):
                    #print("Incorrect: %s" % option.id)
                    question_current_score -= 1
                elif (option.correct ==1):
                    #print("Missed: %s" % option.id)
                    question_max_score += 1
            if question_max_score == question_current_score:
                quiz_current_score += 1.0
        quiz_percent = ((quiz_current_score/quiz_max_score)*100)
        quiz = db.query(User_Quizes).filter_by(user_id=session['sid']).one()
        quiz.last_score = quiz_percent
        quiz.last_taken = sa.func.now()
        db.commit()
        flash(("Score: %s/%s aka %s%%" % (quiz_current_score,quiz_max_score,((quiz_current_score/quiz_max_score)*100))), 'info')
        return redirect(url_for('index'))

# app routes end

@app.teardown_appcontext
def close_db(error):
    db_session.remove()


# end teardown

# main
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=app.config['PORT'])
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
