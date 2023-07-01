from flask import Flask, Blueprint, request
import flask_restful
from flask_restful import Api, url_for, reqparse, abort

import jwt
from functools import wraps
from app.main_page_module.argus import WSearch
from app.main_page_module.models import Notes, Tag, UserM

from app import app

razor_api = Blueprint('api', __name__, url_prefix='/api')
api = Api(razor_api)

parser = reqparse.RequestParser()
parser.add_argument('key')
parser.add_argument('note_id')
parser.add_argument('note_text')
#API_SECRET = app.config['API_SECRET']


def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        api_key = None
        
        if 'x-access-tokens' in request.headers:
            api_key = request.headers['x-access-tokens']
        
        if not api_key:
            abort(404, message="A token is required.")
        
        try:
            #data = jwt.decode(encoded_jwt, API_SECRET, algorithms=["HS256"])
            user = UserM.check_api_access(api_key)
            
            if user is None:
                raise Exception("Wrong access key, or no access granted.")
            
        except Exception as e:
            print(e)
            abort(404, message="The token is invalid.")

        return f(*args, **kwargs)
    return decorator



class Resource(flask_restful.Resource):
    method_decorators = [token_required]   # applies to all inherited resources


class NoteItem(Resource):
    def get(self, n_id):

        note = Notes.get_one(n_id)
        if note == None:
            abort(404, message="No note found for this id.")
            
        note_dic = {'id': note["id"],
                    "title": note["title"],
                    "text": note["text"]}
        
        return note_dic
    
    def put(self, n_id):
        args = parser.parse_args()
        note_id = args["note_id"]
        note_text = args["note_text"]

        if note_text == "":
            abort(404, message="You cannot totally empty a note, sry. Use the web access to do it.")
        
        Notes.edit_api(note_id, note_text)

class SearchNote(Resource):    
    def post(self):
        args = parser.parse_args()
        key = args["key"]

        if key == "":
            asterix = ""
            abort(404, message="Search value cannot be None")
        
        banana = WSearch()
        res = banana.index_api_search("*" + key + "*")
        
        results = {r[0]: [r[1], r[2]] for r in res}
        
        return results  
    

api.add_resource(SearchNote, '/search')
api.add_resource(NoteItem, '/note/<int:n_id>')
