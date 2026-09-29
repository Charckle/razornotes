import os
import time

from flask import Blueprint, request, jsonify, session, send_file
import flask_restful
from flask_restful import Api, reqparse, abort

from flask_jwt_extended import create_access_token, create_refresh_token, \
    get_jwt_identity, jwt_required, get_jwt

from app.main_page_module.models import Notes, UserM, GroupsAccessM

from app.main_page_module.p_objects.note_o import N_obj
from app.main_page_module.p_objects.todo_o import Todo, TODO_TYPE

from app import clipboard

razor_api = Blueprint('api_1', __name__, url_prefix='/api/v1')
api = Api(razor_api)

parser = reqparse.RequestParser()
parser.add_argument('key')
parser.add_argument('note_id')
parser.add_argument('note_text')
parser.add_argument('note_title')
parser.add_argument('v_hash')
parser.add_argument('pinned')
parser.add_argument('relevant')
parser.add_argument('note_type')
parser.add_argument('client_uuid')
parser.add_argument('op_id')


class Resource(flask_restful.Resource):
    method_decorators = [jwt_required()]   # applies to all inherited resources


# Note response format:
#   _id / id  : int
#   title     : str
#   text      : str    — full text, or truncated for index/pinned/meta
#   pinned    : bool
#   relevant  : bool
#   date_mod  : str
#   v_hash    : str    — hash of title + text + note_type + pinned + relevant
#   active    : bool
#   note_type : int    — 0 note, 1 task, 2 to-do (text is a "- [ ] item" checklist)
#   todo      : dict   — meta only, for to-dos: {"done": int, "total": int}
#
# Writes are idempotent: POST /notes accepts client_uuid and PUT /note/<id>
# accepts op_id, so a retry after a lost response confirms the first write
# instead of duplicating it or reporting a conflict.


def _serialize_note(note, truncate=None):
    if not note:
        return None
    text = note.get("text") or ""
    if truncate is not None:
        text = text[:truncate]
    return {
        "_id": note["id"],
        "id": note["id"],
        "title": note.get("title") or "",
        "text": text,
        "pinned": bool(note.get("pinned")),
        "relevant": bool(note.get("relevant", 1)),
        "date_mod": str(note.get("date_mod", "")),
        "v_hash": note.get("v_hash") or "",
        "active": bool(note.get("active", 1)),
        "note_type": int(note.get("note_type") or 0),
    }


def _body():
    data = request.get_json(silent=True)
    if isinstance(data, dict):
        return data
    return {}


def _arg(name, default=None):
    body = _body()
    if name in body and body[name] is not None:
        return body[name]
    args = parser.parse_args()
    val = args.get(name)
    if val is not None and val != "":
        return val
    return default


def _as_bool(val, default=None):
    if val is None or val == "":
        return default
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    return str(val).strip().lower() in ("1", "true", "yes", "on")


def _require_write(claims=None):
    claims = claims if claims is not None else get_jwt()
    read_access = claims.get("read_access") or []
    # 403, not 401: the token is valid, the user just cannot write. A 401 would
    # make clients throw the token away and send the user back to the login screen.
    if not any(x in read_access for x in [1, 2]):
        abort(403, message="You dont have the permission to edit it.")


def _tokens_for_user(user):
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
    return jsonify(access=access_token, refresh=refresh_token, username=username)


class NoteIndex(Resource):
    """Active, relevant, non-pinned notes — truncated text, last 15 by date_mod."""
    def get(self):
        notes = [_serialize_note(note_, truncate=50)
                 for note_ in Notes.get_all_active_for_index()]
        return notes


class NotePinned(Resource):
    """Active, relevant, pinned notes — truncated text, ordered by date_mod."""
    def get(self):
        notes = [_serialize_note(note_, truncate=50)
                 for note_ in Notes.get_all_active_index_pinned()]
        return notes


class NoteHashes(Resource):
    """All notes — id, v_hash, active. Use for sync checks."""
    def get(self):
        return [{"id": row["id"], "v_hash": row["v_hash"], "active": bool(row.get("active", 1))}
                for row in Notes.get_all_hash()]


class NoteMeta(Resource):
    """All active notes — titles and previews, no full body."""
    def get(self):
        notes = []
        for note_ in Notes.get_all_active():
            item = _serialize_note(note_, truncate=100)
            item["preview"] = item["text"]
            del item["text"]
            if item["note_type"] == TODO_TYPE:
                item["preview"] = Todo.preview(note_["text"])
                item["todo"] = Todo.progress(note_["text"])
            notes.append(item)
        return notes


class NoteAll(Resource):
    """All active notes — full content. POST creates a note."""
    def get(self):
        notes = [_serialize_note(note_) for note_ in Notes.get_all_active()]
        return notes

    def post(self):
        _require_write()

        # A client that lost the response to its first attempt retries with the
        # same client_uuid. Hand back the note it already made.
        client_uuid = _arg("client_uuid")
        if client_uuid:
            client_uuid = str(client_uuid)[:40]
            existing = Notes.get_one_by_client_uuid(client_uuid)
            if existing is not None:
                return _serialize_note(existing), 200

        title = str(_arg("note_title") or _arg("title") or "").strip()
        text = _arg("note_text")
        if text is None:
            text = _arg("text")
        if text is None:
            text = ""
        text = str(text)
        if not title:
            abort(400, message="Title required.")

        note_type = _arg("note_type", 0)
        try:
            note_type = int(note_type)
        except (TypeError, ValueError):
            note_type = 0
        pinned = int(_as_bool(_arg("pinned"), False))
        relevant = int(_as_bool(_arg("relevant"), True))
        if note_type == TODO_TYPE:
            # To-dos never appear in Latest, so "relevant" only decides
            # whether a pinned one shows on the front page.
            relevant = 1
            text = Todo.clean(text)

        note_id = Notes.create(title, text, note_type, pinned, relevant, client_uuid)
        if note_id == "error in querry" or not note_id:
            # A duplicate client_uuid means a concurrent retry won the race.
            if client_uuid:
                existing = Notes.get_one_by_client_uuid(client_uuid)
                if existing is not None:
                    return _serialize_note(existing), 200
            abort(500, message="Could not create note.")

        note = Notes.get_one(note_id)
        N_obj.argus_add_note({"id": note_id, "title": title, "text": note["text"]})
        return _serialize_note(note), 201


class NoteItem(Resource):
    def get(self, n_id):
        note = Notes.get_one(n_id)

        if note is None:
            abort(404, message="No note found for this id.")

        return _serialize_note(note)

    def put(self, n_id):
        """Partial update: any field left out keeps its current value, so a
        client changing only the pin state never has to resend the body."""
        claims = get_jwt()
        _require_write(claims)

        note = Notes.get_one(n_id)
        if note is None:
            abort(404, message="No note found for this id.")

        # Same op_id as the last applied write: this is a retry of a request
        # whose response never made it back. Confirm it instead of conflicting.
        op_id = _arg("op_id")
        if op_id:
            op_id = str(op_id)[:40]
            if note.get("op_id") and note["op_id"] == op_id:
                return _serialize_note(note)

        expected_hash = _arg("v_hash")
        if expected_hash:
            current_hash = note.get("v_hash") or ""
            # legacy_hash covers clients that cached a hash from before v_hash
            # started covering the title, type, pin and relevance.
            known = {current_hash, Notes.legacy_hash(note.get("text"))}
            if current_hash and expected_hash not in known:
                # op_id tells the client whether this version came from one of
                # its own earlier attempts, which is not a conflict at all.
                conflict = _serialize_note(note)
                conflict["op_id"] = note.get("op_id") or ""
                return {"message": "Note changed on server.", "note": conflict}, 409

        title = _arg("note_title")
        if title is None:
            title = _arg("title")
        if title is None:
            title = note["title"]
        title = str(title).strip()
        if not title:
            abort(400, message="Title required.")

        text = _arg("note_text")
        if text is None:
            text = _arg("text")
        if text is None:
            text = note.get("text") or ""
        text = str(text)

        pinned = _as_bool(_arg("pinned"), bool(note.get("pinned")))
        relevant = _as_bool(_arg("relevant"), bool(note.get("relevant", 1)))
        note_type = _arg("note_type", note.get("note_type", 0))
        try:
            note_type = int(note_type)
        except (TypeError, ValueError):
            note_type = note.get("note_type", 0)

        # Notes and to-dos store different kinds of text; switching between
        # them is not supported.
        if (note_type == TODO_TYPE) != (note.get("note_type") == TODO_TYPE):
            note_type = note.get("note_type", 0)
        if note_type == TODO_TYPE:
            relevant = True
            text = Todo.clean(text)

        Notes.update_one(n_id, title, note_type, text, int(relevant), int(pinned), op_id)

        note_ = Notes.get_one(n_id)
        N_obj.argus_edit_note(note_)
        return _serialize_note(note_)


class NoteItemHash(Resource):
    """Returns id and v_hash for a single note. Use to check if local copy is stale."""
    def get(self, n_id):
        note = Notes.get_one(n_id)

        if note is None:
            abort(404, message="No note found for this id.")

        return Notes.get_one_hash(n_id)


class NoteFiles(Resource):
    """Attachments on a note — metadata only."""
    def get(self, n_id):
        note = Notes.get_one(n_id)
        if note is None:
            abort(404, message="No note found for this id.")
        files = Notes.get_all_files_of(n_id) or []
        return [{
            "file_name": f["file_name"],
            "file_id_name": f["file_id_name"]
        } for f in files]


class NoteFile(Resource):
    """Download a single attachment. Online only; not cached by the PWA."""
    def get(self, file_id_name):
        if "/" in file_id_name or "\\" in file_id_name or ".." in file_id_name:
            abort(400, message="Invalid file id.")
        file_u = Notes.get_one_file(file_id_name)
        if file_u is None:
            abort(404, message="No file found.")
        path_u = os.path.join(N_obj.path_u, file_id_name)
        if not os.path.isfile(path_u):
            abort(404, message="File missing on server.")
        return send_file(path_u, as_attachment=True, download_name=file_u["file_name"])


class Clipboard(Resource):
    """Per-user clipboard, keyed by user ID from the JWT."""
    def get(self):
        user_id = get_jwt().get("_id")
        return {"clipboard": clipboard.get(user_id, "")}

    def post(self):
        user_id = get_jwt().get("_id")
        text = _arg("key")
        clipboard[user_id] = "" if text is None else str(text)
        return {"clipboard": clipboard[user_id]}


class SearchNote(Resource):
    def post(self):
        args = parser.parse_args()
        key = args["key"]
        if not key:
            body = _body()
            key = body.get("key")

        if not key:
            abort(404, message="Search value cannot be None")

        key = key.strip()
        if len(key) < 3:
            abort(400, message="Search value must be at least 3 characters")

        return N_obj.search(key + "*")


class LoginM(flask_restful.Resource):
    def post(self):
        username = request.form.get("username") or (_body().get("username"))
        password = request.form.get("password") or (_body().get("password"))
        if not username or not password:
            abort(400, message="Username and password required.")

        user = UserM.login_check(username, password)

        if not user:
            time.sleep(0.5)
            abort(404, message="Username or password not correct.")

        return _tokens_for_user(user)


class RefreshT(flask_restful.Resource):
    method_decorators = [jwt_required(refresh=True)]
    def post(self):
        user_id = get_jwt_identity()
        user = UserM.get_one(user_id)

        if not user:
            abort(404, message="Non existent user")

        username = user["username"]

        user_groups = GroupsAccessM.get_access_all_of_user(user_id)
        read_access = []

        if user_groups:
            for group in user_groups:
                read_access.append(group["group_a_id"])

        additional_claims = {"username": username, "_id": user_id, "read_access": read_access}

        new_access_token = create_access_token(identity=username, additional_claims=additional_claims, fresh=False)

        return jsonify(access=new_access_token)


class PwaToken(flask_restful.Resource):
    """Issue JWT from an existing Flask session so /app can store tokens for offline use."""
    def post(self):
        user_id = session.get("user_id")
        if not user_id:
            abort(401, message="Not logged in.")
        user = UserM.get_one(user_id)
        if not user or user.get("status") != 1:
            abort(401, message="Not logged in.")
        return _tokens_for_user(user)


api.add_resource(Clipboard, '/clipboard')
api.add_resource(LoginM, '/login')
api.add_resource(RefreshT, '/refresh')
api.add_resource(PwaToken, '/pwa/token')
api.add_resource(SearchNote, '/search')
api.add_resource(NoteIndex,  '/notes/index')
api.add_resource(NotePinned, '/notes/pinned')
api.add_resource(NoteHashes, '/notes/hashes')
api.add_resource(NoteMeta,   '/notes/meta')
api.add_resource(NoteAll,    '/notes')
api.add_resource(NoteItem,     '/note/<int:n_id>')
api.add_resource(NoteItemHash, '/note/<int:n_id>/hash')
api.add_resource(NoteFiles,    '/note/<int:n_id>/files')
api.add_resource(NoteFile,     '/file/<string:file_id_name>')
