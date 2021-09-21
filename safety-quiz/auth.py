import requests
from flask import Flask, request, session, redirect, url_for, render_template, flash, g
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
from flask import Blueprint

from checkIn.model import User, UserLocation, Type

# This variable specifies the name of a file that contains the OAuth 2.0
# information for this application, including its client_id and client_secret.
CLIENT_SECRETS_FILE = "client_secret.json"
CLIENT_SECRETS_FILE_ID = "client_secret_id.json"

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account and requires requests to use an SSL connection.
SCOPES = ["https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile", 'openid']
API_SERVICE_NAME = 'oauth2'
API_VERSION = 'v2'

auth = Blueprint('auth', __name__)

@auth.route('/oauth2callback')
def oauth2callback(): # AUTH
    # Specify the state when creating the flow in the callback so that it can
    # verified in the authorization server response.
    state = session['state']

    if session['design']:
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE_ID, scopes=SCOPES)
    else:
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, scopes=SCOPES)
    flow.redirect_uri = url_for('auth.oauth2callback', _external=True, _scheme='https') #if insecure dev change scheme to 'http'

    # Use the authorization server's response to fetch the OAuth 2.0 tokens.
    authorization_response = request.url.replace('http://','https://',1) #if insecure dev remove .replace('http://','https://',1)
    flow.fetch_token(authorization_response=authorization_response)

    # Store credentials in the session.
    # ACTION ITEM: In a production app, you likely want to save these
    #              credentials in a persistent database instead.
    credentials = flow.credentials
    session['credentials'] = credentials_to_dict(credentials)
    return redirect(url_for('auth.login_google'))

def credentials_to_dict(credentials): # AUTH
    return {'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes}

@auth.route('/login', methods=['GET','POST'])
def login(): # AUTH
    if request.method == 'GET' :
        if 'legacy' in request.args and bool(request.args['legacy']) is True:
            return render_template('login.html', legacy=True)
        else :
            return render_template('login.html', legacy=False)
    if request.method == 'POST':
        db = g.db_session()
        user = db.query(User).filter_by(sid=request.form['pin']).one_or_none()
        if user:
            if user.email != request.form['email']:
                flash("Account Register with . Please contact Idea Shop staff for assistance.", 'danger')
                return render_template('login.html', legacy=False)
            session['sid'] = user.sid
            session['email'] = user.email
            session['name'] = user.name
            if user.major:
                session['major'] = user.major.name
            user_level_list = db.query(Type.level).outerjoin(UserLocation).filter(UserLocation.sid == session['sid']).all()
            if not user_level_list:
                db.add(UserLocation(sid=user.sid, location_id=2, type_id=0, waiverSigned=None))
                db.add(UserLocation(sid=user.sid, location_id=3, type_id=0, waiverSigned=None))
            user_max_level = max([item for t in user_level_list for item in t])
            if user_max_level > 0:
                session['admin'] = user_max_level
            else:
                session['admin'] = None
            return redirect(url_for('public.index'))
        else:
            user = db.query(User).filter_by(email=request.form['email']).one_or_none()
            if user:
                flash("Email linked with an account. Please contact Idea Shop staff for assistance.", 'danger')
                return render_template('login.html', legacy=False)
            else:
                flash("Please register before continuing.", 'warning')
                return redirect(url_for('register', email=request.form['email'], name=""))

@auth.route('/login_google', methods=['GET'])
def login_google(): # AUTH
    if request.args['design']:
        session['design'] = True

    if 'credentials' not in session:
        return redirect('authorize')

    # Load credentials from the session.
    credentials = google.oauth2.credentials.Credentials(
        **session['credentials'])

    profile = googleapiclient.discovery.build(API_SERVICE_NAME, API_VERSION, credentials=credentials)

    gSuite = profile.userinfo().get().execute()

    # Save credentials back to session in case access token was refreshed.
    # ACTION ITEM: In a production app, you likely want to save these
    #              credentials in a persistent database instead.
    session['credentials'] = credentials_to_dict(credentials)

    db = g.db_session()
    user = db.query(User).filter_by(email=gSuite['email']).one_or_none()
    if user:
        session['sid'] = user.sid
        session['email'] = user.email
        session['name'] = user.name
        if user.major:
            session['major'] = user.major.name
        user_level_list = db.query(Type.level).outerjoin(UserLocation).filter(UserLocation.sid == session['sid']).all()
        if not user_level_list:
            db.add(UserLocation(sid=user.sid, location_id=2, type_id=2))
            db.add(UserLocation(sid=user.sid, location_id=3, type_id=2))
            db.commit()
            user_level_list = db.query(Type.level).outerjoin(UserLocation).filter(UserLocation.sid == session['sid']).all()
        elif not {2, 3}.issubset([x for y in db.query(UserLocation.location_id).filter_by(sid=user.sid).all() for x in y]):
            if 2 not in [x for y in db.query(UserLocation.location_id).filter_by(sid=user.sid).all() for x in y]:
                db.add(UserLocation(sid=user.sid, location_id=2, type_id=2))
            elif 3 not in [x for y in db.query(UserLocation.location_id).filter_by(sid=user.sid).all() for x in y]:
                db.add(UserLocation(sid=user.sid, location_id=3, type_id=2))
            db.commit()
            user_level_list = db.query(Type.level).outerjoin(UserLocation).filter(UserLocation.sid == session['sid']).all()
        if not user_level_list:
            flash("Error with automatic UserLocation creation.", 'danger')
            return redirect(url_for('public.index'))
        user_max_level = max([item for t in user_level_list for item in t])
        if user_max_level > 0:
            session['admin'] = user_max_level
        else:
            session['admin'] = None
        return redirect(url_for('public.index'))
    else:
        if 'iit.edu' in gSuite['email']:
            flash("Please register before continuing.", 'warning')
            return redirect(url_for('register', email=gSuite['email'], name=gSuite['name']))
        else:
            flash("User not found. Be sure to log in with your Illinois Tech Google Account. If you continue to encounter this error, please contact Idea Shop staff for assistance.", 'danger')
            return render_template('login.html', legacy=False)

@auth.route('/authorize')
def authorize(): # AUTH
    # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
    if session['design']:
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE_ID, scopes=SCOPES)
    else:
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, scopes=SCOPES)

    # The URI created here must exactly match one of the authorized redirect URIs
    # for the OAuth 2.0 client, which you configured in the API Console. If this
    # value doesn't match an authorized URI, you will get a 'redirect_uri_mismatch'
    # error.
    flow.redirect_uri = url_for('auth.oauth2callback', _external=True, _scheme='https') #if insecure dev change scheme to 'http'

    authorization_url, state = flow.authorization_url(
        # Enable offline access so that you can refresh an access token without
        # re-prompting the user for permission. Recommended for web server apps.
        access_type='offline',
        # Enable incremental authorization. Recommended as a best practice.
        include_granted_scopes='true')

    # Store the state so the callback can verify the auth server response.
    session['state'] = state

    return redirect(authorization_url)

@auth.route('/logout')
def logout():
    revoke()
    clear_credentials()
    session.clear()
    return redirect(url_for('public.index'))

def revoke():
  if 'credentials' not in session:
    return ('You need to <a href="/auth.authorize">authorize</a> before ' +
            'testing the code to revoke credentials.')

  credentials = google.oauth2.credentials.Credentials(
    **session['credentials'])

  revoke = requests.post('https://oauth2.googleapis.com/revoke',
      params={'token': credentials.token},
      headers={'content-type': 'application/x-www-form-urlencoded'})

  status_code = getattr(revoke, 'status_code')
  if status_code == 200:
    return('Credentials successfully revoked.')
  else:
    return('An error occurred.')

def clear_credentials():
    if 'credentials' in session:
        del session['credentials']
    return ('Credentials have been cleared.<br><br>')
