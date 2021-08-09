# imports
import flask
from flask import Flask, request, session, redirect, url_for, render_template, flash, send_from_directory, Markup, \
    jsonify, g
import sqlalchemy as sa
from checkIn.model import User, UserLocation, Type, Training, TrainingVideosBridge, Machine, Quiz, Question, Option, MissedQuestion, init_db, \
    Major, College, HawkCard
from flask import Blueprint, current_app
import json
from checkIn.iitlookup import IITLookup

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

@userflow.context_processor
def utility_processor():
    def quizAvailable(machine_id):
        db=g.db_session()
        quiz=db.query(Training).filter_by(trainee_id=session['sid'], machine_id=machine_id, invalidation_date=None).one()
        return quiz.quiz_available()
    return dict(quizAvailable=quizAvailable)

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

    machine_query = db.query(Machine).filter_by(machineEnabled=1)
    userVideosWatched = TrainingVideosBridge.getWatchedVideos(session['sid'])
    machine_video_ids = Machine.getMachineVideoIds(db)
    # For Completed and In-progress
    overall_training = db.query(Training).outerjoin(Machine).filter(Training.trainee_id == session['sid']) \
        .filter(Training.invalidation_date == None).order_by(Training.video_watch_date).all()
    in_progress_machineIds = []
    completed_machine_ids = []
    # iterate through training objects created for user,
    # add completed ones to list
    for training in overall_training:
        if training.completed():
            completed_list.append(training)
            completed_machine_ids.append(training.machine_id)
            # print("added to completed: ", training)


    # iterate through training objects created for user, identify trainings that are in-progress
    # when all machine_parents are in completed machine ids list
    for training in overall_training:
        machine = machine_query.filter_by(id=training.machine_id).one_or_none()
        if not machine: #handle exisitng trainings for machine objects which may be disabled.
            break
        # if machine parents in completed_list or no parents but not in completed list
        # show in in_progress trainings
        # print("training machine = ", machine.id, "parent =", machine.parent_id)
        if (machine.parent_id is None):
            if machine.id not in completed_machine_ids:
                in_progress_list.append(training)
                in_progress_machineIds.append(int(training.machine_id))
                # print("added to in_progress: ", training)
        else:
            parents = json.loads(machine.parent_id)
            parents = [i for i in parents]
            print("parents =", parents)
            print("user videos watched =", userVideosWatched)
            print("completed machine ids =", completed_machine_ids)
            if not training.completed():
                if all(x in completed_machine_ids for x in parents) and any(x in userVideosWatched for x in machine_video_ids[machine.id]):
                    in_progress_list.append(training)
                    in_progress_machineIds.append(int(training.machine_id))
                # print("added to in_progress: ", training)

    locked_query=machine_query.all()
    # For Locked and available

    temp_parents = None

    for i in locked_query:
        # print("in locked query: ",i)
        if(i.parent_id is not None):
            temp_parents = json.loads(i.parent_id)
        locked_flag = False
        if(temp_parents):
            for j in temp_parents:
                if int(j) not in (completed_machine_ids):
                    locked_flag = True
                    break
        if locked_flag:
            locked_list.append(i)
            # print("in locked list:", i)
        elif(i.id not in in_progress_machineIds):
            available_list.append(i)
            # print("in available list:", i, "p_id=", i.parent_id)

    return render_template('trainings.html', machine_video_ids=machine_video_ids,
           completed_machine_ids=completed_machine_ids, completed=completed_list,
           in_progress=in_progress_list, available=available_list, locked=locked_list, watched = userVideosWatched)


@userflow.route('/otsname', methods=['GET'])
def otsname_interface():
    il = IITLookup(current_app.config['IITLOOKUPURL'], current_app.config['IITLOOKUPUSER'], current_app.config['IITLOOKUPPASS'])
    user = il.nameByID(str('A' + request.args['user_id']))
    if user:
        return jsonify({'name': (user['first_name'] + " " + user['last_name'])})
    else:
        return jsonify({'failed': 'Failed to retrieve user object from OTS for ID A%s' % request.args['user_id']})
