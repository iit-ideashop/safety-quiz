import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker, relationship
_base_reservation = declarative_base()
from typing import Union, Callable, Tuple, Optional
import datetime
from flask import request, session, redirect, url_for, render_template, flash, jsonify, g, Blueprint
import sqlalchemy as sa
from flask import current_app
#import reservation
from checkIn.model import User, UserLocation, Type, Training, Machine, Quiz, Question, Option, MissedQuestion, init_db, Major, College, HawkCard

reservation_bp = Blueprint('reservation', __name__)

#db_session = init_db(current_app.config['DB'])
# Just for type-hinting, if you know a better way please fix
class HasRemoveMethod:
    def remove(self):
        pass

def init_reservation_db(connection_string: str) -> Union[Callable[[], sa.orm.Session], HasRemoveMethod]:
    global engine
    engine = sa.create_engine(connection_string, pool_size=50, max_overflow=150, pool_recycle=3600, encoding='utf-8')
    db_session = scoped_session(sessionmaker(bind=engine))
    _base_reservation.metadata.create_all(engine)
    db = db_session()
    db.close()
    return db_session



class ReservationType(_base_reservation):
    __tablename__ = 'reservation_types'
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    name = sa.Column(sa.VARCHAR(100), nullable=False)
    quantity = sa.Column(sa.Integer, nullable=False, default=1)
    capacity = sa.Column(sa.Integer, nullable=False, default=1)

    reservations = relationship("Reservations", lazy='joined')

    def __repr__(self):
        return self.name

class ReservationWindow(_base_reservation):
    __tablename__ = 'reservation_windows'
    start = sa.Column(sa.DateTime, nullable=False, primary_key=True)
    end = sa.Column(sa.DateTime, nullable=False, primary_key=True)

    def __repr__(self):
        return ("Reservation window %s -> %s" % (self.start,self.end))

class Reservations(_base_reservation):
    __tablename__ = 'reservations'
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    start = sa.Column(sa.DateTime, nullable=False)
    end = sa.Column(sa.DateTime, nullable=False)
    sid = sa.Column(sa.Integer, nullable=False)
    type_id = sa.Column(sa.Integer, sa.ForeignKey('reservation_types.id'), nullable=False)
    parent_id = sa.Column(sa.Integer, sa.ForeignKey('reservations.id'), nullable=True)

    type = relationship('ReservationType')

    def __repr__(self):
        return "%s has a %s reservation from %s to %s" % (self.sid, self.type.name, self.start, self.end)

@reservation_bp.before_request
def before_request():
    db_reservations = init_reservation_db(current_app.config['DB_RESERVATION'])
    g.reservation_db = db_reservations()

@reservation_bp.route('/reservations', methods=['GET','POST']) # KEEP THIS
def reservations():
    if request.method == 'GET':
        ##temp disable reservations since users can still reserve time for current day even if in disbaled range
        if current_app.config['ALLOW_RESERVATIONS'] != 'True':
            flash("Reservations are currently unavailable and will resume for the Spring 2021 semester.",'warning')
            return render_template('layout.html')
        db = g.db_session()
        temp = db.query(UserLocation).filter_by(sid=session['sid']).filter_by(location_id=2).one_or_none().get_missing_trainings(db)
        if (9 in [each[0].id for each in temp]):
            flash("You are not cleared to make reservations at this time. Please chcek the status of your safety trainings or contact Idea Shop staff for assistance.",'warning')
            return render_template('layout.html')
        user = db.query(User).filter_by(sid=session['sid']).one_or_none()
        reservation_types = g.reservation_db.query(ReservationType).order_by(ReservationType.id.asc()).all()
        db.close()
        return render_template('reservations.html', reservation_types=reservation_types, user=user, openDate=datetime.date(2020, 9, 8), dateWindows=get_window())
    if request.method == 'POST':
        user = g.db_session().query(User).filter_by(sid=session['sid']).one_or_none()
        start_time = datetime.datetime.strptime(request.form['start_time'],"%Y-%m-%d %X")
        end_time = datetime.datetime.strptime(request.form['end_time'],"%Y-%m-%d %X")
        db = g.reservation_db
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
    db = g.db_session()
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

@reservation_bp.route('/reservations/api/checkEmail')
def checkEmail():
    db = g.db_session()
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

@reservation_bp.route('/reservations/api/type')
def get_type():
    x = g.g.reservation_db.query(ReservationType).filter_by(id=int(request.args['type_id'])).one_or_none()
    if x :
        return jsonify({'id':x.id,'name':x.name,'quantity':x.quantity,'capacity':x.capacity})
    else:
        return ''''''

@reservation_bp.route('/reservations/api/start_times', methods=['GET'])
def start_times():
    db = g.g.reservation_db
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

@reservation_bp.route('/reservations/api/end_times', methods=['GET'])
def end_times():
    db = g.reservation_db
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

@reservation_bp.route('/reservations/api/windows', methods=['GET'])
def get_window():
    db = g.reservation_db
    temp = db.query(ReservationWindow).filter(ReservationWindow.start >= datetime.datetime.today().date()).all()
    return [x.start.strftime('%m %d %Y') for x in temp]

@reservation_bp.route('/reservations/view')
def view_reservations():
    db = g.reservation_db
    start = datetime.datetime.combine(datetime.datetime.now().date(),datetime.time(0,0,0))
    end = datetime.datetime.combine(datetime.datetime.now().date(),datetime.time(23,59,59))
    reservations = db.query(Reservations).filter(Reservations.start > start).filter(Reservations.end < end).order_by(Reservations.start.asc()).all()
    return render_template('view_reservations.html', reservations=reservations)

@reservation_bp.route('/api/machine_access', methods=['POST'])
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
