#To run nightly to send quiz notifications to users.
#imports
from flask import Flask, render_template
from flask_mail import Mail, Message
from model import db_session, User, Training, Machine, init_db
from datetime import datetime, date, timedelta

app = Flask(__name__)

app.config.from_pyfile('config.cfg')
db_session = init_db(app.config['DB'])

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
                            .join(User, Training.trainee) \
                            .filter(User.status != 'inactive') \
                            .filter(Training.quiz_notification_sent == None) \
                            .filter(Training.invalidation_date == None) \
                            .distinct().all()
        if user_list:
            print("Sending emails to:")
            user_list = [i[0] for i in user_list]
            print("Sending to %s users." % len(user_list))
        else:
            print("No quizzes to send today, %s" % date.today())
            return
        input("Press Enter to continue...")
        with mail.connect() as conn:
            for sid in user_list:
                if db.query(User).filter_by(sid=sid).one().email:
                    trainings = db.query(Training).filter_by(trainee_id=sid).filter_by(invalidation_date=None).filter_by(quiz_notification_sent=None).all()
                    new_quizzes = []
                    for index, training in enumerate(trainings):
                        if date.today() >= ((training.date).date() + timedelta(days=training.machine.quiz_issue_days)):
                            new_quizzes.append(training)
                    if new_quizzes:
                        try:
                            print("Sending email to: %s, %s"%(training.trainee.name,training.trainee.email))
                            subject = "Idea Shop Safety Quiz"
                            msg = Message(recipients=[training.trainee.email],
                                        html=render_template('/emails/new_quiz.html', new_quizzes=new_quizzes),
                                        subject=subject)
                            #conn.send(msg)
                            for training in new_quizzes:
                                db.merge(Training(id=training.id, quiz_notification_sent=datetime.now()))
                            #db.commit()
                        except Exception as e:
                            print("Error sending email to user %s." % trainings[0].trainee.name)
                            print(e)
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
    send_quizzes()
    #back_add_trainings()
    #back_add_from_users()
    '''app.run(host='0.0.0.0', debug=True)
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True'''