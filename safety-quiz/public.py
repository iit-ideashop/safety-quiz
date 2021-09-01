# imports
import flask
from flask import Flask, request, session, redirect, url_for, render_template, flash, send_from_directory, Markup, jsonify, g
import sqlalchemy as sa
from checkIn.model import User, Energizer, Location, Access, UserLocation, Type, Training, Machine, Quiz, Question, Option, MissedQuestion, init_db, Major, College, HawkCard
from flask import Blueprint, current_app

public = Blueprint('public', __name__)

@public.route('/')
def index():
    return render_template('welcome.html')

@public.route('/welcome')
def welcome():
    return render_template('welcome.html')

@public.route('/shop_status', methods=['GET'])
def shop_status():
    db = g.db_session()
    user_count = db.query(Location.id, Location.name, Location.staff_ratio).all()
    energizers = db.query(Energizer).all()
    in_lab = [Access.getUserCount(db,2),Access.getUserCount(db,3)]
    staff = [Access.getStaffCount(db,2), Access.getStaffCount(db,3)]

    if request.method =='GET':
        return render_template('shop_status.html', user_count=user_count, in_lab=in_lab, staff=staff, energizers = energizers)

@public.route('/scripts/custom_styles.css')
def custom_css():
    return send_from_directory('scripts', 'custom_styles.css')

@public.route('/scripts/animations.js')
def animation_js():
    return send_from_directory('scripts', 'animations.js')

@public.route('/scripts/landing.js')
def landing_js():
    return send_from_directory('scripts', 'landing.js')

@public.route('/scripts/video.js')
def video_js():
   return send_from_directory('scripts', 'video.js')