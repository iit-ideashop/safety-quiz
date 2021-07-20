# imports
import flask
from flask import Flask, request, session, redirect, url_for, render_template, flash, send_from_directory, Markup, \
    jsonify, g
import sqlalchemy as sa
from checkIn.model import User, UserLocation, Type, Training, Machine, Quiz, Question, Option, MissedQuestion, init_db, \
    Major, College, HawkCard
from flask import Blueprint, current_app
import json

userflow = Blueprint('userflow', __name__)


# @userflow.route('/training')
# def training_interface():
#     db = g.db_session()
#
#     trainings = db.query(Training).outerjoin(Machine).filter(Training.trainee_id == session['sid']).filter( \
#         Training.invalidation_date == None).filter(Machine.location_id.in_((2, 3))).order_by(
#         Training.in_person_date).all()
#     quizzes = db.query(Machine).filter(Machine.quiz_id != None).order_by(Machine.quiz_id).all()
#     training_count = len(trainings)
#     return render_template('trainings.html', trainings=trainings, quizzes=quizzes, training_count=training_count)

@userflow.route('/training')
def training_interface():
    """Gives the List of completed, in_progress, locked and available trainings.
    Query can return empty lists if there are no trainings for a user

    Completed: Any which pass Training.Completed() func
    In_Progress: Any which do not pass Training.Completed() func
    Locked: Machines for which user hasn't completed trainings for listed parent_id's
    Available: Machines for which user has no training objects"""

    db = g.db_session()
    completed_list = []
    in_progress_list = []
    locked_list = []
    available_list = []

    # For Completed and In-progress
    overall_training = db.query(Training).outerjoin(Machine).filter(Training.trainee_id == session['sid']) \
        .filter(Training.invalidation_date == None).all()
    for training in overall_training:
        if training.completed():
            completed_list.append(training)
            print("added to completed: ", training)
        else:
            in_progress_list.append(training)
            print("added to in_progress: ", training)


    # For Locked and available
    locked_query = db.query(Machine).filter_by(machineEnabled=1).all()
    temp_parents = None
    completed_machine_ids = list()
    for completed in completed_list:
        completed_machine_ids.append(completed.machine_id)
    for i in locked_query:
        # print("in locked query: ",i)
        if(i.parent_id is not None):
            temp_parents = json.loads(i.parent_id)
        locked_flag = False
        if(temp_parents):
            for j in temp_parents:
                if int(j) not in completed_machine_ids:
                    locked_flag = True
                    break
        if locked_flag:
            locked_list.append(i)
            # print("in locked list:", i)
        else:
            available_list.append(i)
            # print("in available list:", i)

    machine_video_ids = Machine.getMachineVideoIds()

    return render_template('trainings.html', machine_video_ids=machine_video_ids, completed=completed_list, in_progress=in_progress_list,
                           available=available_list, locked=locked_list)