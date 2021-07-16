# imports
import flask
from flask import Flask, request, session, redirect, url_for, render_template, flash, send_from_directory, Markup, jsonify, g
import sqlalchemy as sa
from checkIn.model import User, UserLocation, Type, Training, Machine, Quiz, Question, Option, MissedQuestion, init_db, Major, College, HawkCard, Video
from flask import Blueprint, current_app

video = Blueprint('video', __name__)

@video.route('/video', methods=['GET', 'POST'])
def safety():
    if request.method == 'GET':
        db = g.db_session()
        #flash("Video safety training is not currently available. Please check back on September 14th, 2020.", 'warning')
        #return render_template('layout.html')
        youtube_id=db.query(Video).get(Video.filepath)
        video_time_seconds=db.query(Video).get(Video.length)
        return render_template('safety_video.html', youtube_id=str(youtube_id), video_time_seconds=int(video_time_seconds))
    elif request.method == 'POST':
        db = g.db_session()
        print(request.form['sid'])
        db.add(Training(trainee_id=int(request.form['sid']), trainer_id=20000000, machine_id=9, date=sa.func.now()))
        db.commit()
        flash("Thank you for participating in the Assembly Area Fall 2020 COVID training. Your verification quiz will be available on this site in one week. \
            You can re-watch the video at any time by visiting https://wiki.ideashop.iit.edu/index.php?title=Safety_Training",'success')
        return render_template('layout.html')
