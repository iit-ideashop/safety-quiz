# imports
import datetime
import json

import flask
from flask import Flask, request, session, redirect, url_for, render_template, flash, send_from_directory, Markup, jsonify, g
import sqlalchemy as sa
from checkIn.model import User, UserLocation, TrainingVideosBridge, Type, Training, Machine, Quiz, Question, Option, MissedQuestion, init_db, Major, College, HawkCard, Video, VideoMachineBridge
from flask import Blueprint, current_app

video = Blueprint('video', __name__)

@video.route('/video/<video_id>', methods=['GET', 'POST'])
def safety(video_id):
    db = g.db_session()
    if request.method == 'GET':
        video_object=db.query(Video).filter_by(id=video_id).one_or_none()
        if(not video_object):
            return 'bad request', 447
        return render_template('safety_video.html', youtube_id=str(video_object.filepath), video_time_seconds=video_object.length)
    elif request.method == 'POST':
        machines = [each.machine for each in db.query(VideoMachineBridge).filter_by(video_id=video_id).all()]
        new_trainings = []
        existing_trainings = []
        for machine in machines:
            training = db.query(Training).filter_by(trainee_id = session['sid']).filter_by(machine_id=machine.id).filter(Training.invalidation_date == None).order_by(sa.desc(Training.id)).first()
            if not training:
                new_trainings.append(Training(trainee_id=session['sid'], machine_id=machine.id))
            else:
                existing_trainings.append(training)
        db.add_all(new_trainings)
        db.flush()
        for training in (new_trainings + existing_trainings):
            if not training.watched_videos or video_id not in [x.video_id for x in training.watched_videos]:
                if not db.query(TrainingVideosBridge).filter_by(training_id=training.id).filter_by(video_id=video_id).one_or_none():
                    db.add(TrainingVideosBridge(training_id=training.id, video_id=video_id))
        db.commit()
        flash("Thank you for watching an Idea Shop Training Video.", 'success')
        return redirect(url_for('userflow.training_interface'))

