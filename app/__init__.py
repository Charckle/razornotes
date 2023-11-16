# Import flask and template operators
from flask import Flask, render_template, jsonify
from os import path, mkdir, environ 
import logging
from logging.handlers import RotatingFileHandler

from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, JWTManager

from datab import DBcreate, check_database_active
from app.main_page_module.p_objects.db_migration import DB_upgrade
from app.main_page_module.argus import WSearch
from app.main_page_module.models import Notes

# Define the WSGI application object
app = Flask(__name__)


clipboard = {"clipboard": ""}

# Configurations
if environ.get('ENVCONFIG', "DEV") != 'PROD':
    app.config.from_object("config.DevelopmentConfig")
else:
    app.config.from_object("config.ProductionConfig")

jwt = JWTManager(app)

# Sample HTTP error handling
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.route('/health')
def static_file():
    if check_database_active():
        return jsonify(status="healthy"), 200
    else:
        return jsonify(status="not healthy"), 500




# Import a module / component using its blueprint handler variable (mod_auth)
from app.main_page_module.controllers import main_page_module as main_module
from app.main_page_module.controllers_api import razor_api as api_module
from app.main_page_module.controllers_api_jwt import razor_api as api_module_v2
from app.memory_module.controllers import memory_module

# Register blueprint(s)
app.register_blueprint(main_module)
app.register_blueprint(api_module)
app.register_blueprint(api_module_v2)
app.register_blueprint(memory_module)
# app.register_blueprint(xyz_module)
# ..

# Check if database exists. if not, create it
DBcreate.check_all_db_OK()
DB_upgrade.update_database()

# create search index
# this is very much NOT OK, but...I have to stop somewhere, or else I wont have time for my real job :D
notes = Notes.get_all_active()
new_index = WSearch()
new_index.index_create(notes)

# activate logging

if not path.exists('logs'):
    mkdir('logs')
file_handler = RotatingFileHandler('logs/error.log', maxBytes=10240,
                                   backupCount=5)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
file_handler.setLevel(logging.DEBUG)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.DEBUG)
app.logger.info('Application startup')