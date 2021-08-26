from flask import request, session, redirect, url_for, render_template, flash, jsonify, g, Blueprint
from flask import current_app
from checkIn.model import *
from datetime import date, timedelta, datetime, time

reservation_bp = Blueprint('reservation', __name__)


@reservation_bp.route('/reservation/<training_id>', methods=['GET','POST']) # KEEP THIS
def reservations(training_id):
    if request.method == 'GET':
        ##temp disable reservations since users can still reserve time for current day even if in disbaled range
        if current_app.config['ALLOW_RESERVATIONS'] != 'True':
            flash("Reservations are currently unavailable.",'warning')
            return redirect(url_for('public.index'))
        db = g.db_session()
        training = db.query(Training).filter_by(id=training_id).one_or_none()
        if not training:
            flash("Training object not found.", 'danger')
            return redirect(url_for('userflow.training_interface'))
        reservation_type = training.machine.reservation_type
        if len(reservation_type) is not 1:
            flash("Cannot find reservation type.", 'warning')
            return redirect(url_for('userflow.training_interface'))
        else:
            reservation_type = reservation_type[0]
        user = db.query(User).filter_by(sid=session['sid']).one_or_none()
        return render_template('reservations.html', reservation_type=reservation_type, user=user, openDate=date(2020, 9, 8), dateWindows=get_window(reservation_type))
    if request.method == 'POST':
        db = g.db_session()
        training = db.query(Training).filter_by(id=training_id).one_or_none()
        if not training:
            flash("Training not found.", 'danger')
            return redirect('/')
        new_reservation = ReservationInpersontraining(reservation_window_id=int(request.form['windows']), training_id=training.id)
        db.add(new_reservation)
        db.flush()
        flash("Created %s in-person training for: %s" % (new_reservation.window.window_type.name, new_reservation.window.start),'success')
        db.commit()
        return redirect(url_for('userflow.training_interface'))

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
    x = g.g.reservation_db.query(ReservationTypes).filter_by(id=int(request.args['type_id'])).one_or_none()
    if x :
        return jsonify({'id':x.id,'name':x.name,'quantity':x.quantity,'capacity':x.capacity})
    else:
        return ''''''


@reservation_bp.route('/reservations/api/times', methods=['GET'])
def times():
    db = g.db_session()
    if not all(x in ['reservation_type', 'date'] for x in request.args.keys()):
        return jsonify(['Wrong arguments.'])
    requested_date = datetime.strptime(request.args['date'][:15], "%a %b %d %Y").date()
    windows = db.query(ReservationWindows).filter_by(type_id=int(request.args['reservation_type'])).filter(ReservationWindows.start >= requested_date).filter(ReservationWindows.end < requested_date+timedelta(days=1)).all()
    for index, window in enumerate(windows):
        if len(db.query(ReservationInpersontraining).filter_by(reservation_window_id=window.id).all()) >= window.window_type.capacity:
            windows.pop(index)
    return jsonify([{'id': x.id, 'start': str(x.start.time()), 'end': str(x.end.time())} for x in windows])

@reservation_bp.route('/reservations/api/start_times', methods=['GET'])
def start_times():
    db = g.db_session()
    requested_date = datetime.strptime(request.args['date'][:15], "%a %b %d %Y").date()
    reservation_type = db.query(ReservationTypes).filter_by(id=int(request.args['type_id'])).one()
    existing_reservations = db.query(ReservationInpersontraining).filter(ReservationInpersontraining.start >= requested_date).filter(ReservationInpersontraining.end < requested_date+timedelta(days=1)).filter(ReservationInpersontraining.type_id == reservation_type.id).all()
    open = True
    if open:
        open_time = datetime.combine(requested_date,datetime.time(9,0))
        close_time = datetime.combine(requested_date,datetime.time(17,0))
        delta_time = timedelta(hours=0,minutes=15)
        start_times = []
        for i in range(open_time.hour*60+open_time.minute,close_time.hour*60+close_time.minute,int(delta_time.seconds / 60)):
            i = datetime.combine(requested_date,datetime.time(int(i/60),int(i%60)))
            availability = reservation_type.quantity
            for each in existing_reservations:
                if i > (each.start - (2*delta_time)) and i < (each.end + (2*delta_time)):
                    availability -= 1
            if availability > 0:
                start_times.append(i)
        return jsonify([{'date': str(x.date()), 'time': str(x.time())} for x in start_times])

@reservation_bp.route('/reservations/api/end_times', methods=['GET'])
def end_times():
    db = g.db_session()
    reservation_type = db.query(ReservationTypes).filter_by(id = int(request.args['type_id'])).one()
    start_time = datetime.strptime(request.args['start_time'],"%Y-%m-%d %X")
    existing_reservations = db.query(ReservationInpersontraining).filter(ReservationInpersontraining.start >= start_time).filter(ReservationInpersontraining.end < start_time.date() + timedelta(days=1)).filter(ReservationInpersontraining.type_id == reservation_type.id).all()
    close_time = datetime.combine(start_time.date(), datetime.time(17, 0))
    delta_time = timedelta(hours=0, minutes=15)
    max_reservation_minutes = 180
    end_times = []
    for i in range(((start_time+delta_time).hour * 60) + (start_time+delta_time).minute, min((close_time.hour * 60) + close_time.minute,((start_time+delta_time).hour * 60) + (start_time+delta_time).minute + max_reservation_minutes), int(delta_time.seconds / 60)):
        i = datetime.combine(start_time.date(), datetime.time(int(i / 60), int(i % 60)))
        availability = reservation_type.quantity
        for each in existing_reservations:
            if i > (each.start - (2*delta_time)):
                availability -= 1
        if availability > 0:
            end_times.append(i)
        else: break
    return jsonify([{'date': str(x.date()), 'time': str(x.time())} for x in end_times])

@reservation_bp.route('/reservations/api/windows', methods=['GET'])
def get_window(reservation_type):
    db = g.db_session()
    temp = db.query(ReservationWindows)\
        .filter_by(type_id=reservation_type.id).filter(ReservationWindows.start >= datetime.today().date()).all()
    return [x.start.strftime('%m %d %Y') for x in temp]

@reservation_bp.route('/reservations/view')
def view_reservations():
    db = g.db_session()
    start = datetime.combine(datetime.now().date(), time(0,0,0))
    end = datetime.combine(datetime.now().date() + timedelta(days=7), time(23,59,59))
    reservation_windows = db.query(ReservationWindows).filter(ReservationWindows.start > start).filter(ReservationWindows.end < end).order_by(ReservationWindows.start.asc()).all()
    return render_template('view_reservations.html', reservation_windows=reservation_windows)

