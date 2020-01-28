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
        user_list = db.query(Training.trainee_id) \
                            .filter_by(quiz_notification_sent=None) \
                            .filter_by(trainee_id='20313392').distinct().all()
        if user_list:
            user_list = user_list[0]
            print("Sending emails to:")
            print(user_list)
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
                    db.merge(Training(id=training.id, quiz_notification_sent=datetime.now()))
                db.commit()
    return

def back_add_trainings():
    db = db_session()
    back_add_training_id_list = [9400,9401,9402,9403,9404,9405,10669,10670,10671,10672,10673]
    base_training_list = db.query(Training).filter(Training.id.in_(back_add_training_id_list)).filter(Training.date > '2020-01-01').group_by(Training.trainee_id).all()
    for base_training in base_training_list:
        back_add_list = db.query(Machine.id).filter_by(location_id = 3).filter_by(required = 1).all()
        for each in back_add_list:
            print("%s : adding %s" % (base_training.trainee.name,each.id))
            new = Training(trainee_id=base_training.trainee_id, trainer_id=base_training.trainer_id, date=base_training.date, machine_id=each.id)
            #db.add(new)
    #db.commit()
    return


if __name__ == '__main__':
    #send_quizzes()
    back_add_trainings()
    '''app.run(host='0.0.0.0', debug=True)
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True'''