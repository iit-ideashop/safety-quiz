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
from checkIn.model import User, UserLocation, Type, Energizer, Training, Machine, Quiz, Question, Option, MissedQuestion, init_db, Major, College, HawkCard, ReservationInpersontraining

api = Blueprint('api', __name__)

@api.route('/api/machine_access', methods=['POST'])
def get_machine_access():
    if not request.form or not all(items in request.form.keys() for items in ['machine_name', 'machine_id']):
        return jsonify({'response': 'Invalid request.'})
    machine_id = int(request.form['machine_id'])
    machine_name = request.form['machine_name']
    db = g.db_session()
    machine = db.query(Machine).filter_by(id=machine_id).one_or_none()
    if machine and machine.name != machine_name:
        return jsonify({'response': 'Invalid request.'})
    sid_list = [item[0] for item in db.query(Training.trainee_id).filter_by(machine_id=machine_id).filter_by(invalidation_date=None)\
        .filter_by(quiz_score=100.0).all()]
    partial_complete = db.query(Training).filter_by(machine_id=machine_id).filter_by(Training.in_person_date != None). \
        filter_by(invalidation_date=None).filter(Training.quiz_score == None).all()
    for each in partial_complete:
        if not each.quiz_available():
            sid_list.append(each.trainee_id)
            print(each.trainee.name)
    access_list = db.query(HawkCard).filter(HawkCard.sid.in_(sid_list)).all()
    return jsonify({'response': 'Request Successful', 'users':[{'sid': card.sid, 'name': card.user.name, 'facility': card.facility, 'card_number': card.card} for card in access_list]})

@api.route('/api/energizer_status', methods=['POST'])
def update_energizer():
    if not request.form or not all(items in request.form.keys() for items in ['machine_id', 'name', 'timestamp', 'status', 'machine_enabled', 'active_user']):
        return jsonify({'response': 'Invalid request.'})
    machine_id=int(request.form['machine_id'])
    name=request.form['name']
    status=request.form['status']
    active_user=request.form['active_user']
    enabled=request.form['machine_enabled']
    timestamp=request.form['timestamp']
    db = g.db_session()
    machine = db.query(Machine).filter_by(id=machine_id).one_or_none()
    if machine and machine.name != name:
        return jsonify({'response': 'Invalid request'})
    energizer_row = db.query(Energizer).filter_by(machine_id=machine_id, name=name).one_or_none()
    if energizer_row is not None:
        energizer_row.name=name
        energizer_row.status=status
        energizer_row.timestamp=timestamp
        energizer_row.machine_enabled=enabled
        energizer_row.active_user=active_user
    else:
        db.add(Energizer(machine_id=machine_id, name=name, status=status,timestamp=timestamp,active_user=active_user, machine_enabled=1))
    db.commit()
    return jsonify({'response': 'Request Successful'})


@api.route('/api/delete_in_person_reservation', methods=['POST'])
def delete_in_person_reservation():
    if not 'id' in request.form.keys():
        flash("Invalid request.", 'danger')
        redirect(url_for('userflow.training_interface'))
    db = g.db_session()
    window = db.query(ReservationInpersontraining).filter_by(id=int(request.form['id'])).one_or_none()
    if not window:
        flash("Could not find reservation #%s" % request.form['id'], 'warning')
        redirect(url_for('userflow.training_interface'))
    else:
        db.delete(window)
        db.commit()
    return redirect(url_for('userflow.training_interface'))
