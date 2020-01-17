#To run nightly to send quiz notifications to users.
#imports
from flask import Flask, render_template
from flask_mail import Mail, Message
from checkIn import db_session, User, Training, Machine, Quiz, Question, Option
from datetime import datetime, date, timedelta

app = Flask(__name__)


app.config.update(dict(MAIL_SERVER = '10.0.8.18'),MAIL_DEFAULT_SENDER = "ideashop@iit.edu")

mail = Mail(app)

@app.route('/new_quiz')
def new_quiz():
    db = db_session()
    sid = '20313392'
    trainings = db.query(Training).filter_by(trainee_id=sid).filter_by(quiz_notification_sent=None).all()
    new_quizzes = []
    for index, training in enumerate(trainings):
        if date.today() >= ((training.date).date() + timedelta(days=training.machine.quiz_issue_days)):
            new_quizzes.append(training)
    if new_quizzes:
        return render_template('/emails/new_quiz.html', new_quizzes=new_quizzes)


def send_quizzes():
    with app.app_context():
        db = db_session()
        user_list = db.query(Training.trainee_id).filter_by(quiz_notification_sent=None).filter_by(trainee_id='20313392').distinct().all()
        if user_list:
            user_list = user_list[0]
        else:
            print("No quizzes to send today, %s" % date.today())
            return
        with mail.connect() as conn:
            for sid in user_list:
                trainings = db.query(Training).filter_by(trainee_id=sid).filter_by(quiz_notification_sent=None).all()
                new_quizzes = []
                for index, training in enumerate(trainings):
                    if date.today() >= ((training.date).date() + timedelta(days=training.machine.quiz_issue_days)):
                        new_quizzes.append(training)
                print(new_quizzes)
                print("Sending email to: %s, %s"%(training.trainee.name,training.trainee.email))
                input("Press Enter to continue...")
                subject = "Idea Shop Safety Quiz"
                msg = Message(recipients=[training.trainee.email],
                              html=render_template('/emails/new_quiz.html', new_quizzes=new_quizzes),
                              subject=subject)
                conn.send(msg)
                for training in new_quizzes:
                    db.merge(Training(id=training.id,quiz_notification_sent=datetime.now()))
                db.commit()
    return

if __name__ == '__main__':
    send_quizzes()
    app.run(host='0.0.0.0', debug=True)
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True