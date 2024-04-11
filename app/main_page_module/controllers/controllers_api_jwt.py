from flask import Flask, Blueprint, request, jsonify
import flask_restful
from flask_restful import Api, url_for, reqparse, abort

from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

from functools import wraps
from app.main_page_module.argus import WSearch
from app.main_page_module.models import Notes, Tag, UserM

from app import app

razor_api = Blueprint('api_2', __name__, url_prefix='/api/v2')
api = Api(razor_api)

parser = reqparse.RequestParser()
parser.add_argument('key')
parser.add_argument('note_id')
parser.add_argument('note_text')


class Resource(flask_restful.Resource):
    method_decorators = [jwt_required()]   # applies to all inherited resources


class NoteAllItem(Resource):
    def get(self, type_n):
        if type_n  == 1:
            notes = [{'_id':note_["id"], 'title':note_["title"],
                       'text':note_["text"]} for note_ in Notes.get_all_active_for_index()]
        elif type_n  == 2:
            notes = [{'_id':note_["id"], 'title':note_["title"],
                       'text':note_["text"]} for note_ in Notes.get_all_active_index_pinned()]
        else:
            notes = [{'_id':note_["id"], 'title':note_["title"],
                       'text':note_["text"]} for note_ in Notes.get_all_active()]

        return notes

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

class LoginM(flask_restful.Resource):    
    def post(self):

        username = request.form["username"]
        password = request.form["password"]
        user = UserM.login_check(username, password)
        
        if user == False:
            abort(404, message="Username or password not correct.")
        
        user_id = user["id"]
        additional_claims = {"username": "username", "_id": "user_id"}
        access_token = create_access_token(identity=username, additional_claims=additional_claims)
        password = "redacted" # remove from memory

        return jsonify(token=access_token)
    
# comment out because I must fix the access prvileges and the api

#api.add_resource(LoginM, '/login')
#api.add_resource(SearchNote, '/search')
#api.add_resource(NoteAllItem, '/notes/<int:type_n>')
#api.add_resource(NoteItem, '/note/<int:n_id>')


