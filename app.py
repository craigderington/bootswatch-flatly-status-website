from flask import Flask, make_response, redirect, request, Response, render_template, url_for, flash, g
from flask_mail import Mail, Message
from flask_sslify import SSLify
from flask_session import Session
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy, Pagination
from sqlalchemy import text, and_, exc, func
from database import db_session
from celery import Celery
from models import User, Store, Campaign, CampaignType, Visitor, AppendedVisitor, Lead, PixelTracker, Contact
import config
import random
import datetime
import requests

# debug
debug = config.DEBUG

# app config
app = Flask(__name__)
sslify = SSLify(app)
app.secret_key = config.SECRET_KEY

# SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.SQLALCHEMY_TRACK_MODIFICATIONS
db = SQLAlchemy(app)

# disable strict slashes
app.url_map.strict_slashes = False

# Celery config
app.config['CELERY_BROKER_URL'] = config.CELERY_BROKER_URL
app.config['CELERY_RESULT_BACKEND'] = config.CELERY_RESULT_BACKEND
app.config['CELERY_ACCEPT_CONTENT'] = config.CELERY_ACCEPT_CONTENT
app.config.update(accept_content=['json', 'pickle'])

# Initialize Celery
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)


# clear all db sessions at the end of each request
@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()


# app default route
@app.route('/', methods=['GET'])
@app.route('/index', methods=['GET'])
def index():
    """
    The default view.   EARL System Status
    :return: databoxes
    """
    overall_status = "OPERATIONAL"
    service_status = {}
    service_list = [config.earl_auto, config.earl_data_admin, config.earl_pixel_tracker,
                    config.earl_dealer_portal, config.earl_web_admin, config.earl_api]

    for service in service_list:

        if get_service(service):
            service_status[service] = 1
            overall_status = "OPERATIONAL"
        else:
            service_status[service] = 0
            overall_status = "DEGRADED"

    return render_template(
        'index.html',
        today=get_date(),
        status=service_status,
        overall_status=overall_status
    )


@app.route('/pixeltracker', methods=['GET'])
def pixeltracker():
    """
    return the status page for the pixel-tracker
    :return: template
    """

    return render_template(
        'pixeltracker.html',
        today=get_date(),
        status=get_service(config.earl_pixel_tracker),
        pixel_tracker=config.earl_pixel_tracker
    )


@app.route('/webadmin', methods=['GET'])
def webadmin():
    """
    EARL Web Admin status page
    :return:
    """
    return render_template(
        'webadmin.html',
        today=get_date(),
        status=get_service(config.earl_web_admin),
        web_admin=config.earl_web_admin
    )


@app.route('/dealerportal', methods=['GET'])
def dealerportal():
    """
    Dealer Portal page
    :return: template
    """
    return render_template(
        'dealerportal.html',
        today=get_date(),
        status=get_service(config.earl_dealer_portal),
        dealer_portal=config.earl_dealer_portal
    )


@app.route('/modeladmin', methods=['GET'])
def modeladmin():
    """
    EARL Model Admin Page
    :return: template
    """

    return render_template(
        'modeladmin.html',
        today=get_date(),
        status=get_service(config.earl_data_admin),
        model_admin=config.earl_data_admin
    )


@app.route('/automation', methods=['GET'])
def automation():
    """
    EARL Automation status page
    :return: template
    """
    return render_template(
        'automation.html',
        today=get_date(),
        status=get_service(config.earl_auto),
        automation=config.earl_auto
    )


@app.route('/api', methods=['GET'])
def automation():
    """
    EARL Automation status page
    :return: template
    """
    return render_template(
        'api.html',
        today=get_date(),
        status=get_service(config.earl_api),
        api=config.earl_api
    )


@app.errorhandler(404)
def page_not_found(err):
    return render_template('error-404.html'), 404


@app.errorhandler(500)
def internal_server_error(err):
    return render_template('error-500.html'), 500


def flash_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            flash(u"Error in the %s field - %s" % (
                getattr(form, field).label.text,
                error
            ))


def get_service(service_name):
    """
    Call the service and return True or False
    :param service_name:
    :return: boolean
    """

    # until we have https in auto
    if '52.23.77.251' in service_name:
        service_prefix = 'http://'
    else:
        service_prefix = 'https://'

    # create the url to call
    service_url = service_prefix + service_name

    # http headers
    hdr = {
        'user-agent': 'EARL System Status v.01',
        'content-type': 'application/json'
    }

    # make the call
    r = requests.get(service_url, headers=hdr, verify=False)

    # handle the response
    if r.status_code == 200:
        return True
    else:
        return False


def get_date():
    # set the current date time for each page
    today = datetime.datetime.now().strftime('%c')
    return '{}'.format(today)


@app.template_filter('formatdate')
def format_date(value):
    dt = value
    return dt.strftime('%Y-%m-%d %H:%M')


@app.template_filter('datemdy')
def format_date(value):
    dt = value
    return dt.strftime('%m/%d/%Y')


if __name__ == '__main__':

    port = 5580

    # start the application
    app.run(
        debug=debug,
        port=port
    )
