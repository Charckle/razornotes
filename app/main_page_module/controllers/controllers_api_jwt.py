from flask import Flask, Blueprint, request, jsonify
import flask_restful
from flask_restful import Api, url_for, reqparse, abort

from flask_jwt_extended import create_access_token, create_refresh_token, \
     get_jwt_identity, jwt_required, get_jwt

from functools import wraps
from app.main_page_module.argus import WSearch
from app.main_page_module.models import Notes, Tag, UserM, GroupsAccessM

from app.main_page_module.p_objects.note_o import N_obj

from app import app

razor_api = Blueprint('api_1', __name__, url_prefix='/api/v1')
api = Api(razor_api)

parser = reqparse.RequestParser()
parser.add_argument('key')
parser.add_argument('note_id')
parser.add_argument('note_text')
parser.add_argument('note_title')



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
        # get only the id and hash
        elif type_n == 3:
            notes = Notes.get_all_hash()
            
        else:
            notes = [{'_id':note_["id"], 'title':note_["title"],
                       'text':note_["text"]} for note_ in Notes.get_all_active()]

        return notes


class NoteItem(Resource):
    def get(self, n_id, type_n):
        note = Notes.get_one(n_id)
        
        if note == None:
            abort(404, message="No note found for this id.")       
            
        # get only the hash
        if type_n == 1:      
            note_dic = Notes.get_one_hash(n_id)
                 
        # get the whole note
        else:
            note_dic = {'id': note["id"],
                        "title": note["title"],
                        "text": note["text"]}
        
        return note_dic
    

    def put(self, n_id, type_n=None):
        claims = get_jwt()
        read_access = claims.get("read_access")  # optional, if you need it 

        if not any(x in read_access for x in [1,2,3]):
            abort(401, message="You dont have the permission to edit it.")
        
        note = Notes.get_one_hash(n_id)
        if note == None:
            abort(404, message="No note found for this id.")            
        
        args = parser.parse_args()
        note_title = args["note_title"]
        note_text = args["note_text"]

        if note_text == "" or note_title == "":
            abort(404, message="You cannot totally empty a note, sry. Use the web access to do it.")
        
        Notes.edit_api(n_id, note_text)
        
        note_ = Notes.get_one(n_id)
        N_obj.argus_edit_note(note_)


class SearchNote(Resource):
    def post(self):
        args = parser.parse_args()
        key = args["key"]
        
        if key == "":
            asterix = ""
            abort(404, message="Search value cannot be None")
        

        if key == "":
            asterix = ""
        else:
            asterix = "*"
            
        key = key + asterix

        
        return jsonify(N_obj.search(key))


class LoginM(flask_restful.Resource):    
    def post(self):

        username = request.form["username"]
        password = request.form["password"]
        user = UserM.login_check(username, password)
        
        if user == False:
            abort(404, message="Username or password not correct.")
        
        
        user_id = user["id"]
        username = user["username"]
        
        user_groups = GroupsAccessM.get_access_all_of_user(user_id)
        
        read_access = []
        
        if user_groups:
            for group in user_groups:
                read_access.append(group["group_a_id"])
        
        additional_claims = {"username": username, "_id": user_id, "read_access": read_access}
        access_token = create_access_token(identity=username, additional_claims=additional_claims, fresh=True)
        refresh_token = create_refresh_token(identity=user_id)
        password = "redacted" # remove from memory

        return jsonify(access=access_token, refresh=refresh_token)
    
class RefreshT(flask_restful.Resource):
    method_decorators = [jwt_required(refresh=True)] 
    def post(self):
        # user ID
        user_id = get_jwt_identity()
        user = UserM.get_one(user_id)
        
        if not user:
            abort(404, message="Non existent user")
            
        username = user["username"]
        # (optional) check token not revoked
        
        user_groups = GroupsAccessM.get_access_all_of_user(user_id)
        read_access = []        
        
        if user_groups:
            for group in user_groups:
                read_access.append(group["group_a_id"])
        
        additional_claims = {"username": username, "_id": user_id, "read_access": read_access}
        
        new_access_token = create_access_token(identity=username, additional_claims=additional_claims, fresh=False)
        
        return jsonify(access=new_access_token)
    
# comment out because I must fix the access prvileges and the api

api.add_resource(LoginM, '/login')
api.add_resource(RefreshT, '/refresh')
api.add_resource(SearchNote, '/search')
api.add_resource(NoteAllItem, '/notes/<int:type_n>')
api.add_resource(NoteItem, '/note/<int:n_id>', '/note/<int:n_id>/<int:type_n>')


