# Import flask and template operators
from flask import Flask, render_template, jsonify
from flask_cors import CORS
from os import path, mkdir, environ 
import logging
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv, find_dotenv, dotenv_values

from flask_jwt_extended import JWTManager

from datab import DBcreate, check_database_active
from app.main_page_module.p_objects.db_migration import DB_upgrade
from app.main_page_module.argus import WSearch
from app.main_page_module.models import Notes
from app.main_page_module.other import Randoms

# Define the WSGI application object
app = Flask(__name__)

# Enable CORS for all routes
CORS(app) #allow any source
#CORS(app, origins='http://127.0.0.1:4200')  # Replace with your Angular app's URL

clipboard = {"clipboard": ""}
secrets = {}

# load the .env environment variables
load_dotenv()

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
from app.main_page_module.controllers.controllers import main_page_module as main_module
from app.main_page_module.controllers.controllers_notes import notes_module as notes_module
from app.main_page_module.controllers.controllers_admin import admin_module as admin_module
from app.main_page_module.controllers.controllers_api_jwt import razor_api as api_module_v1
from app.memory_module.controllers import memory_module
from app.secrets_module.controllers import secrets_module

# Register blueprint(s)
app.register_blueprint(main_module)
app.register_blueprint(notes_module)
app.register_blueprint(admin_module)
app.register_blueprint(api_module_v1)
app.register_blueprint(memory_module)
app.register_blueprint(secrets_module)
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

logging_level_str = app.config['APP_LOGGING']
logging_level = getattr(logging, logging_level_str, logging.INFO)
app.logger.setLevel(logging_level)

#logging.basicConfig(level=logging_level, format='%(asctime)s - %(levelname)s - %(message)s')
#app.logger.info(f"Logging Level set to: {logging.getLevelName(app.logger.getEffectiveLevel())}")

app.logger.info('Application startup')

logo_ascii = r"""
---------------------------+
  _____                       _   _       _            
 |  __ \                     | \ | |     | |           
 | |__) |__ _ _______  _ __  |  \| | ___ | |_ ___  ___ 
 |  _  // _` |_  / _ \| '__| | . ` |/ _ \| __/ _ \/ __|
 | | \ \ (_| |/ / (_) | |    | |\  | (_) | ||  __/\__ \
 |_|  \_\__,_/___\___/|_|    |_| \_|\___/ \__\___||___/ 
------------------+
"""


logo = logo_ascii.split("\n")
for line in logo:
    app.logger.info(line)  

app.logger.info("Razor Notes: for notes and shit")    
app.logger.info(f"Version: {Randoms.get_version()}")    
app.logger.info("--------------------------------------------+ \n")    
app.logger.info(f"Instance Name: {app.config['APP_NAME']}")
app.logger.info(f"Logging Level: {logging.getLevelName(app.logger.getEffectiveLevel())}")
app.logger.info("--------------------------------------------+ \n\n")

if app.config['IP_RESTRICTION'] == "1":
    app.logger.info('Login will be restricted based on IP and network')

if app.config['WTF_CSRF_ENABLED'] == False:
    app.logger.info('WTF CSRF is Disabled')    

if app.config['MODULE_MEMORY'] == True:
    app.logger.info('Memory module is Enabled')    
    
if app.config['MODULE_SECRETS'] == True:
    app.logger.info('Secrets module is Enabled')    