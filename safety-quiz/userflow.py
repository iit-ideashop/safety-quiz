# imports
import flask
from flask import Flask, request, session, redirect, url_for, render_template, flash, send_from_directory, Markup, \
    jsonify, g
import sqlalchemy as sa
from checkIn.model import User, UserLocation, Type, Training, Machine, Quiz, Question, Option, MissedQuestion, init_db, \
    Major, College, HawkCard
from flask import Blueprint, current_app

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
    passing_score = 100.00
    completed_list = []
    in_progress_list = []
    locked_list = []
    available_list = []

    # For Completed and In-progress
    overall_training = db.query(Training).outerjoin(Machine).filter(Training.trainee_id == session['sid']) \
        .filter(Training.quiz_score == passing_score).filter(Training.invalidation_date == None) \
        .filter(Training.in_person_date is not None).all()

    for training in overall_training:
        if Training.completed(training):
            completed_list.append(training.machine.name)
        else:
            in_progress_list.append(training.machine.name)

    # For Locked and available
    locked_query = db.query(Machine).outerjoin(Training).filter(Training.trainee_id == session['sid']) \
        .filter(Machine.parent_id != None).all()


    for i in locked_query:

        search_if_complete = db.query(Machine).outerjoin(Training).filter(Training.trainee_id == session['sid']) \
            .filter(Machine.parent_id != None).filter(Training.machine_id == i.parent_id) \
            .filter(Training.quiz_score != passing_score).all()
        if search_if_complete != None:
            locked_list.append(i)
        else:
            available_list.append(i)

    return render_template('trainings.html', completed=completed_list, in_progress=in_progress_list,
                           available=available_list, locked=locked_list)
