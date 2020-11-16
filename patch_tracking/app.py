"""
flask app
"""
import logging.config
import os
import sys
from flask import Flask
from patch_tracking.api.issue import issue
from patch_tracking.api.tracking import tracking
from patch_tracking.database import db
from patch_tracking.task import task

logging.config.fileConfig('logging.conf', disable_existing_loggers=False)

app = Flask(__name__)
logger = logging.getLogger(__name__)


def check_listen(listen_param):
    """ check LISTEN """
    check_ret = True
    if ":" in listen_param and listen_param.count(":") == 1:
        host, port = listen_param.split(":")
        if int(port) > 65535 or int(port) <= 0:
            check_ret = False
        if "." in host and host.count(".") == 3:
            for item in host.split("."):
                if int(item) < 0 or int(item) > 255:
                    check_ret = False
        else:
            check_ret = False
    else:
        check_ret = False
    return check_ret


def check_settings_conf():
    """
    check settings.conf
    """
    setting_error = False
    required_settings = ['LISTEN', 'GITEE_ACCESS_TOKEN', 'SCAN_DB_INTERVAL', 'USER', 'PASSWORD']
    for setting in required_settings:
        if setting in app.config:
            if app.config[setting] == "":
                logger.error('%s is empty in settings.conf.', setting)
                setting_error = True
            else:
                if setting == "LISTEN" and (not check_listen(app.config[setting])):
                    logger.error('LISTEN error: illegal param in /etc/patch-tracking/settings.conf.')
                    setting_error = True
                if setting == "SCAN_DB_INTERVAL" and int(app.config[setting]) <= 0:
                    logger.error(
                        'SCAN_DB_INTERVAL error: must be greater than zero in /etc/patch-tracking/settings.conf.'
                    )
                    setting_error = True
                if setting == "USER" and len(app.config[setting]) > 32:
                    logger.error('USER value error: user name too long, USER character should less than 32.')
                    setting_error = True
        else:
            logger.error('%s not configured in settings.conf.', setting)
            setting_error = True
    if setting_error:
        sys.exit(1)


settings_file = os.path.join(os.path.abspath(os.curdir), "settings.conf")
try:
    app.config.from_pyfile(settings_file)
    check_settings_conf()
    app.config["LISTEN"] = app.config["LISTEN"].strip()
    app.config["GITHUB_ACCESS_TOKEN"] = app.config["GITHUB_ACCESS_TOKEN"].strip()
    app.config["GITEE_ACCESS_TOKEN"] = app.config["GITEE_ACCESS_TOKEN"].strip()
    app.config["USER"] = app.config["USER"].strip()
    app.config["PASSWORD"] = app.config["PASSWORD"].strip()
except (SyntaxError, NameError):
    logger.error('settings.conf content format error.')
    sys.exit(1)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite?check_same_thread=False&timeout=30'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SCHEDULER_EXECUTORS'] = {'default': {'type': 'threadpool', 'max_workers': 100}}
app.config['GIT_BASE_PATH'] = "GIT_REPO_PATH"

app.register_blueprint(issue, url_prefix="/issue")
app.register_blueprint(tracking, url_prefix="/tracking")

db.init_app(app)

task.init(app)

if __name__ == "__main__":
    app.run(ssl_context="adhoc")
