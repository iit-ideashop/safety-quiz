# imports
import flask
from flask import Flask, request, session, redirect, url_for, render_template, flash, send_from_directory, Markup, jsonify, g
import sqlalchemy as sa
from checkIn.model import User, UserLocation, Type, Training, Machine, Quiz, Question, Option, MissedQuestion, init_db, Major, College, HawkCard
from flask import Blueprint, current_app

userflow = Blueprint('userflow', __name__)

@userflow.route('/training')
def training_interface():
    db = g.db_session()

    trainings = db.query(Training).outerjoin(Machine).filter(Training.trainee_id == session['sid']).filter(\
    Training.invalidation_date == None).filter(Machine.location_id.in_((2, 3))).order_by(Training.in_person_date).all()
    quizzes = db.query(Machine).filter(Machine.quiz_id != None).order_by(Machine.quiz_id).all()
    training_count = len(trainings)
    return render_template('trainings.html', trainings=trainings, quizzes=quizzes, training_count = training_count)
