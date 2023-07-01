# Import flask and template operators
from flask import Flask, render_template
from os import environ 

from datab import DBcreate
from app.main_page_module.models import UserM, Notes, Tag
from app.main_page_module.argus import WSearch

# Define the WSGI application object
app = Flask(__name__)

clipboard = {"clipboard": ""}

# Configurations
if environ.get('ENVCONFIG', "DEV") != 'PROD':
    app.config.from_object("config.DevelopmentConfig")
else:
    app.config.from_object("config.ProductionConfig")

# Sample HTTP error handling
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

# Import a module / component using its blueprint handler variable (mod_auth)
from app.main_page_module.controllers import main_page_module as main_module
from app.main_page_module.controllers_api import razor_api as api_module
from app.memory_module.controllers import memory_module

# Register blueprint(s)
app.register_blueprint(main_module)
app.register_blueprint(api_module)
app.register_blueprint(memory_module)
# app.register_blueprint(xyz_module)
# ..

# Check if database exists. if not, create it
DBcreate.check_all_db_OK()

# create search index
# this is very much NOT OK, but...I have to stop somewhere, or else I wont have time for my real job :D
notes = Notes.get_all_active()
new_index = WSearch()
new_index.index_create(notes)

