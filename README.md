# safety-quiz

## About
This project was intended to be utilized as a new webfront/feature site for the Idea Shop Prototyping Lab. Functionality of the site includes
* Rich, informative landing page
* Machine safety training quizzes
  * Watch Training Video
  * Take Quiz
  * Enforce Sequencing of trainings
  * In-Person component of trainings optional
* Live Status page for equipment and shop hours
  * Google Calendar embedded for shop hours and events
  * Connected to Database with Machine "Energizers" to monitor current status of shop equipment
  * Live User and Staff Count in separate areas of Idea Shop
* Access to wiki site
* Animated content using [anime.js](https://animejs.com/)
* Integration with Illinois Tech SSO Portal

This site has lots of content that is specific to the Illinois Tech Idea Shop. Files in the ```/safety-quiz/templates/``` directory should be edited as needed.

## Dependencies
This project utilized the Flask Web Framework to host the static and dynamic content on the website.
* Python 3.7 - Flask framework runs on Python
* SQLAlchemy - for database access
* Flask-bootstrap - Enable bootstrap theme integration with Flask
* Flask-fontawesome - icons
* Jinja - template language utilized by flask

## Installation
Python and python components needed should be installed using
```sudo apt-get install python3 python3-pip python3-venv```

Create a virtual environment to install flask in using
```python -m venv /path/to/project/dir```

Then, activate the virtual environment from the project directory using
``` venv/bin/activate ```

Install flask and flask-bootstrap in the venv
``` pip install Flask flask-bootstrap Flask-SQLAlchemy Flask-FontAwesome```

## Other Info
This site was taken out of use by Illinois Tech after the Fall 2021 Semester. These instructions are by no means complete, and this specific repo is tailored to the Idea Shop specifically.  

**Major Refactoring of code will necessary to adapt this site to other institutions/uses**
