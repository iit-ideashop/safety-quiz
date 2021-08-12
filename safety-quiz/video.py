# imports
import datetime
import json

import flask
from flask import Flask, request, session, redirect, url_for, render_template, flash, send_from_directory, Markup, jsonify, g
import sqlalchemy as sa
from checkIn.model import User, UserLocation, TrainingVideosBridge, Type, Training, Machine, Quiz, Question, Option, MissedQuestion, init_db, Major, College, HawkCard, Video
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
        # print(video_object.filepath)
        return render_template('safety_video.html', youtube_id=str(video_object.filepath), video_time_seconds=int(video_time_seconds))
    elif request.method == 'POST':
        print(session['sid'])
        videoUpdateQuery = db.query(TrainingVideosBridge).filter_by(user_id=int(session['sid'])).one_or_none()
        if (videoUpdateQuery is None):
            videoUpdateQuery = db.add(TrainingVideosBridge(user_id=int(session['sid']), videos_watched=json.dumps([int(video_id)])))
        else:
            # print("Videos watched before change:", videoUpdateQuery.videos_watched)
            videos = json.loads(videoUpdateQuery.videos_watched)
            if(not int(video_id) in videos):
                videos.append(int(video_id))
                # print("Videos during change:", videos)
                newVideos = json.dumps(videos)
                videoUpdateQuery.videos_watched=newVideos
                # print("Videos watched after change:", newVideos)
            # else:
                # print("video", video_id, "already in list, not appending")
        machineIdList = Machine.getMachineVideoIds(db)
        machineEnabledList = Machine.getMachinesEnabled(db)
        trainingQuery = db.query(Training).filter_by(trainee_id=session['sid'])
        timestamp = datetime.datetime.now()
        for each, value in machineIdList.items():
            video_ids = json.dumps(value)
            if video_id in video_ids:
                if (not trainingQuery.filter_by(machine_id=each).all()) and machineEnabledList[each]:
                    db.add(Training(trainee_id=session['sid'], trainer_id=20000000, in_person_date=sa.null(), machine_id=each, video_watch_date=timestamp))
                # else:
                #     for training in (trainingQuery.filter_by(machine_id=each).all()):
                #         training.video_watch_date=timestamp
        db.commit()
        flash("Thank you for watching an Idea Shop Training Video. Your verification quiz will be available on this site in one week. \
                You can re-watch the video at any time by visiting the Training Video Library Page",
              'success')
        return redirect(url_for('userflow.training_interface'))

