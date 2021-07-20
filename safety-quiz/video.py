# imports
import flask
from flask import Flask, request, session, redirect, url_for, render_template, flash, send_from_directory, Markup, jsonify, g
import sqlalchemy as sa
from checkIn.model import User, UserLocation, Type, Training, Machine, Quiz, Question, Option, MissedQuestion, init_db, Major, College, HawkCard, Video
from flask import Blueprint, current_app

video = Blueprint('video', __name__)

@video.route('/video/<machine_id>/<video_id>', methods=['GET', 'POST'])
def safety(machine_id, video_id):
    db = g.db_session()
    if request.method == 'GET':
        #flash("Video safety training is not currently available. Please check back on September 14th, 2020.", 'warning')
        #return render_template('layout.html')
        video_object=db.query(Video).filter_by(id=video_id).one_or_none()
        if(not video_object):
            return 'bad request', 447
        video_time_seconds=video_object.length
        print(video_object.filepath)
        return render_template('safety_video.html', youtube_id=str(video_object.filepath), video_time_seconds=int(video_time_seconds))
    elif request.method == 'POST':
        print(session['sid'])
        db.add(Training(trainee_id = int(session['sid']), machine_id=machine_id, trainer_id=20000000))
        db.commit()
        flash("Thank you for watching an Idea Shop Training Video. Your verification quiz will be available on this site in one week. \
                You can re-watch the video at any time by visiting the Training Video Library Page",
              'success')
        return render_template('layout.html')

