import markdown2
import json

# Import flask dependencies
from flask import Blueprint, request, render_template, \
                  flash, g, session, redirect, url_for, jsonify, send_file, Response

# Import module forms
from app.main_page_module.forms import form_dicts
from app.main_page_module.r_proc import Import_Ex, HL_proc

# Import module models (i.e. User)
from app.main_page_module.models import UserM, Notes, Tag

from app import app, clipboard
from wrappers import login_required
from app.pylavor import Pylavor
from app.main_page_module.argus import WSearch
from app.main_page_module.other import Randoms

#import os
import re
import os
import zipfile
import io
import pathlib
from functools import wraps
import datetime



# Define the blueprint: 'auth', set its url prefix: app.url/auth
main_page_module = Blueprint('main_page_module', __name__, url_prefix='/')


@app.context_processor
def inject_to_every_page():
    
    return dict(Randoms=Randoms, Notes=Notes, Tag=Tag, markdown2=markdown2)


# Set the route and accepted methods
@main_page_module.route('/', methods=['GET'])
@login_required
def index():
    
    pinned_notes = Notes.get_all_active_index_pinned()

    notes = Notes.get_all_active_for_index()

    return render_template("main_page_module/index.html", notes=notes, 
                           pinned_notes=pinned_notes)

@main_page_module.route('/search/', methods=['GET'])
@login_required
def search():

    return render_template("main_page_module/search.html")

@main_page_module.route('/search/', methods=['POST'])
@login_required
def search_results():
    key = request.form["key"]

    banana = WSearch()
    if key == "":
        asterix = ""
    else:
        asterix = "*"
    res = banana.index_search(key + asterix)
    
    #get IDs of the notes the user can access
    user_notes = [i["id"] for i in Notes.get_all_active()]
    results = {r[0]: [r[1], r[2]] for r in res if (int(r[0]) in user_notes)}

    return jsonify(results)


@main_page_module.route('/all_tags/')
@login_required
def all_tags():
    tags = Tag.get_all()
   
    return render_template("main_page_module/tags/all_tags.html", tags=tags)


@main_page_module.route('/view_tag/<tag_id>')
@login_required
def view_tag(tag_id):
    
    tag = Tag.get_one(tag_id)
    
    if (tag is None):
        
        flash('The tag does not exist !', 'error')
        
        return redirect(url_for("main_page_module.all_locations"))        
    
    notes = Tag.notes_get_all_of_tag(tag_id)
    

    return render_template("main_page_module/tags/view_tag.html", tag=tag, notes=notes)


@main_page_module.route('/delete_note/', methods=['POST'])
@login_required
def delete_note():
    note_id = request.form["id"]
    note = Notes.get_one(note_id)
    
    if note is None:
        flash('No entries with this ID found to delete.', 'error')
        
        return redirect(url_for("main_page_module.all_notes"))  
    
    Notes.delete_one(note_id)
    
    flash(f'Note {note["title"]} successfully deleted.', 'success')  
    
    return redirect(url_for("main_page_module.index"))   
    
@main_page_module.route('/notes_delete_all_trashed/', methods=['GET'])
@login_required
def notes_delete_all_trashed():
    
    Notes.delete_all_trashed()     
    
    flash(f'All trashed notes deleted.', 'success')  
    
    return redirect(url_for("main_page_module.all_notes_trashed"))      
    
@main_page_module.route('/trash_note/', methods=['POST'])
@login_required
def trash_note():
    note_id = request.form["id"]
    note = Notes.get_one(note_id)
    
    if note is None:
        flash('No notes with this ID found to trash.', 'error')
        
        return redirect(url_for("main_page_module.all_notes"))  
    
    Notes.trash_one(note_id)     
    
    flash(f'Note -{note["title"]}- successfully trashed.', 'success')  
    
    return redirect(url_for("main_page_module.all_notes"))  

@main_page_module.route('/reactivate_note/<note_id>', methods=['get'])
@login_required
def reactivate_note(note_id):
    note = Notes.get_one(note_id)
    
    if note is None:
        flash('No notes with this ID found to reactivate.', 'error')
        
        return redirect(url_for("main_page_module.all_notes_trashed"))  
    
    
    Notes.reactivate_one(note_id)     
    
    flash(f'Note -{note["title"]}- successfully reActivated!', 'success')  
    
    return redirect(url_for("main_page_module.all_notes"))  


@main_page_module.route('/all_notes_trashed/')
@login_required
def all_notes_trashed():
    notes = Notes.get_all_trashed()
   
    return render_template("main_page_module/notes/all_notes_trashed.html", notes=notes)


@main_page_module.route('/new_note', methods=['GET', 'POST'])
@login_required
def new_note():
    # If sign in form is submitted
    form = form_dicts["Note"]()
    
    # Verify the sign in form
    if form.validate_on_submit():
        note_title = str(form.title.data).strip()
        note_id = Notes.create(note_title, form.note_text.data)
        
        #create argus index
        notes = Notes.get_all_active()
        new_index = WSearch()
        new_index.index_create(notes)
        
        flash('Entry successfully created!', 'success')
        flash('Argus index successfully updated', 'success')
        
        return redirect(url_for("main_page_module.view_note", note_id=note_id))

    return render_template("main_page_module/notes/new_note.html", form=form)

@main_page_module.route('/all_notes/')
@login_required
def all_notes():
    notes = Notes.get_all_active()

    return render_template("main_page_module/notes/all_notes.html", notes=notes)

@main_page_module.route('/view_note/<note_id>', methods=['GET', 'POST'])
@login_required
def view_note(note_id):
    note = Notes.get_one(note_id)
    
    if note is None:
        flash('No entrie found', 'error')
        
        return redirect(url_for("main_page_module.index"))
    

    return render_template("main_page_module/notes/view_note.html", note=note)

@main_page_module.route('/edit_note/<note_id>', methods=['GET', 'POST'])
@login_required
def edit_note(note_id):
    note = Notes.get_one(note_id)
    
    if note is None:
        flash('No entrie found or you do not have permissions to edit the note.', 'error')
        
        return redirect(url_for("main_page_module.all_notes"))
    
    form = form_dicts["Note"]()
    form.process(id = note["id"],
                 title = note["title"],
                 note_text = note["text"],
                 relevant = note["relevant"],
                 pinned = note["pinned"])
    
    tags = Tag.get_all_of_note(note_id)
    all_tags = Tag.get_all()
    
    return render_template("main_page_module/notes/edit_note.html", note=note, form=form, tags=tags, 
                           all_tags=all_tags)

@main_page_module.route('/change_note/', methods=['POST'])
@login_required
def change_note():
    form = form_dicts["Note"]()
    note_id = form.id.data
    
    note = Notes.get_one(note_id)
    
    if note is None:
        flash('No entrie found or you do not have permissions to edit the note.', 'error')
        
        return redirect(url_for("main_page_module.all_notes"))    
    
    if form.validate_on_submit():
        Notes.update_one(note_id, form.title.data, form.note_text.data, 
                                  form.relevant.data, form.pinned.data)
        
        #create argus index
        notes = Notes.get_all_active()
        new_index = WSearch()
        new_index.index_create(notes)
        
        flash('Entry successfully Eddited!', 'success')
        #flash('Argus index successfully updated', 'success')
        
        return redirect(url_for("main_page_module.view_note", note_id=form.id.data))
    
    for error in form.errors:
        print(error)
        flash(f'Invalid Data: {error}', 'error')
    
    return render_template("main_page_module/notes/edit_note.html", note=note, form=form, tags=tags, 
                           all_tags=all_tags)  


@main_page_module.route('/download_note/<note_id>', methods=['GET'])
@login_required
def download_note(note_id):
    note = Notes.get_one(note_id)
    
    if note is None:
        flash('No entrie found or you do not have permissions to edit the note.', 'error')
        
        return redirect(url_for("main_page_module.all_notes"))
    
    n_title = Randoms.get_valid_filename(note["title"])
    markdown_text = note["text"]
    # Set headers for the downloadable file
    response = Response(markdown_text, content_type='text/markdown')
    response.headers['Content-Disposition'] = f'attachment; filename={n_title}.md'

    return response


@main_page_module.route('/create_tag/', methods=['POST'])
@login_required
def create_tag():

    note_id = request.form["note_id"]
    tagName = request.form["tagName"]
    tagColor = request.form["tagColor"]
    
    note = Notes.get_one(note_id)
    
    if note is not None:
        try:        
            tag_id = Tag.add(tagName, tagColor)
                       
            connect_tag(note_id, tag_id)
            result_concatinate = str(tagName) + "++++__++++++" + str(tagColor) + "++++__++++++" + str(tag_id)
           
            json_response = {"a": result_concatinate}        
            
        except Exception as e:
            print(e)
            json_response = {"a": "no"}
        
        return jsonify(json_response)
    
    return "Limona"


@main_page_module.route('/add_tag/', methods=['POST'])
@login_required
def add_tag():

    note_id = request.form["note_id"]
    tag_id = request.form["tag_id"]

    
    note = Notes.get_one(note_id)
    
    if note is not None:
        try:        
            tag = Tag.get_one(tag_id)
                       
            Tag.connect_tag(note_id, tag_id)
            result_concatinate = str(tag["name"]) + "++++__++++++" + str(tag["color"]) + "++++__++++++" + str(tag_id)
           
            json_response = {"a": result_concatinate}        
            
        except Exception as e:
            print(e)
            json_response = {"a": "no"}
        
        return jsonify(json_response)
    
    return "Limona"


@main_page_module.route('/remove_tag/', methods=['POST'])
@login_required
def remove_tag():
    note_id = request.form["note_id"]
    tag_id = request.form["tag_id"]
    
    note = Notes.get_one(note_id)
    tag = Tag.note_tag_get_one(note_id, tag_id)
    
    if (note is None) or (tag is None):
        flash('No note found or you do not have permissions to edit the note.', 'error')
        
        return redirect(url_for("main_page_module.all_notes"))    
    
    Tag.remove_note_tag(note_id, tag_id)
    
    json_response = {"a": "OK"}
    
    return jsonify(json_response)


@main_page_module.route('/get_zipped_entries/')
@login_required
def get_zipped_entries():
    now = datetime.datetime.now()
    
    base_path = pathlib.Path('app//main_page_module//data//')
    data = io.BytesIO()
    with zipfile.ZipFile(data, mode='w') as z:
        for f_name in base_path.iterdir():
            z.write(f_name, os.path.basename(f_name))
    data.seek(0)
    
    return send_file(
        data,
        mimetype='application/zip',
        as_attachment=True,
        attachment_filename=f'all_entries_{now.strftime("%Y-%m-%d_%H-%M")}.zip',
        cache_timeout=0
    )

@main_page_module.route('/create_hashes/')
@login_required
def create_hashes():
    HL_proc.create_hashes_()
   
    return redirect(url_for("main_page_module.index"))

@main_page_module.route('/notes_import/', methods=['GET', 'POST'])
@login_required
def notes_import():    
    form = form_dicts["ImportNotes"]()
    
    if form.validate_on_submit():
        ditc_ = Import_Ex.import_(form.import_file.data)
        flash(f"Import holds {ditc_['to_process']} Notes, {ditc_['added']} added.", "success")
        
        return redirect(url_for("main_page_module.index"))
    
    for error in form.errors:
        print(error)
        flash(f'Invalid Data: {error}', 'error')    
    
    return render_template("main_page_module/notes_import.html", form=form)


@main_page_module.route('/notes_export/', methods=['GET'])
@login_required
def notes_export():
    data_ = Import_Ex.export()
    
    notes_j = jsonify(data_)
    notes_j.mimetype = "application/json"
    notes_j.headers = {"Content-Disposition":
                                    "attachment;filename=razor_notes.rnxf"}
    
    return notes_j


@main_page_module.route('/get_clipboard/', methods=['POST'])
@login_required
def get_clipboard():
    
    return jsonify(clipboard)

@main_page_module.route('/set_clipboard/', methods=['POST'])
@login_required
def set_clipboard():
    clipboard["clipboard"] = request.form["clipboard"]
    
    return jsonify({"result":"All OK!"})

@main_page_module.route('/admin/users_all/')
@login_required
def users_all():
    users = UserM.get_all()
   
    return render_template("main_page_module/admin/users_all.html", users=users)

@main_page_module.route('/user_new', methods=['GET', 'POST'])
@login_required
def user_new():
    # If sign in form is submitted
    form = form_dicts["User"]()
    
    # Verify the sign in form
    if form.validate_on_submit():
        u_id = UserM.create(form.name.data, form.username.data, form.email.data,
                           form.password.data, form.status.data, form.api_key.data)
        
        flash('User Successfully Created', 'success')
        
        return redirect(url_for("main_page_module.user_edit", user_id=u_id))
    
    
    for error in form.errors:
        print(error)
        flash(f'Invalid Data: {error}', 'error')
    
    return render_template("main_page_module/admin/user_new.html", form=form, Pylavor=Pylavor)

@main_page_module.route('/admin/user_edit/<user_id>', methods=['GET', 'POST'])
@main_page_module.route('/admin/user_edit/', methods=['POST'])
@login_required
def user_edit(user_id=None):
    form = form_dicts["User"]()
    
    if request.method == 'GET':
        user = UserM.get_one(user_id)
        if not user:
            flash('User does not exist.', 'error')
            
            return redirect(url_for("main_page_module.users_all"))     
        
        form.process(id = user["id"],
                     name = user["name"],
                     email = user["email"],
                     username = user["username"],
                     status = user["status"],
                     api_key = user["api_key"])
    
    # POST
    else:
        user = UserM.get_one(form.id.data)
        if not user:
            flash('User does not exist.', 'error')
        
            return redirect(url_for("main_page_module.users_all"))         
    
    if form.validate_on_submit():
        if user["status"] == 1 and form.status.data == "0" and len(UserM.get_all_w_status(1)) < 2:
            flash('You cannot take access from the last remaining user with access, sry!', 'error')
            
            return redirect(url_for("main_page_module.user_edit", user_id=form.id.data))            
        
        UserM.change_one(form.id.data, form.username.data, form.name.data, form.email.data,
                        form.api_key.data, form.status.data)
        
        if form.password.data != "":
            UserM.change_passw(form.id.data, form.password.data)
            
        flash('User successfully Eddited!', 'success')
        
        return redirect(url_for("main_page_module.user_edit", user_id=form.id.data))
    
    for error in form.errors:
        print(error)
        flash(f'Invalid Data: {error}', 'error')        
    
    
    return render_template("main_page_module/admin/user_edit.html", form=form, user=user)
    

@main_page_module.route('/admin/delete/', methods=['POST'])
@login_required
def delete_user():
    user = UserM.get_one(request.form["id"])
    
    if not user:
        flash('User does not exist.', 'error')
        
        return redirect(url_for("main_page_module.users_all")) 
    
    if len(UserM.get_all()) < 2:
        flash('Cannot delete the last user, sry :/', 'error')
        
        return redirect(url_for("main_page_module.users_all"))     
    
    
    else:
        UserM.delete_one(user["id"])
        
        flash(f'User {user["name"]} - {user["username"]} successfully deleted.', 'success')
        
        return redirect(url_for("main_page_module.users_all")) 
    

# Set the route and accepted methods
@main_page_module.route('/login/', methods=['GET', 'POST'])
def login():

    # If sign in form is submitted
    form = form_dicts["Login"]()
    app.logger.debug(f"Posted CSRF {form['csrf_token'].data}")
    app.logger.debug(f"System CSRF {session.get('_csrf_token')}")

    # Verify the sign in form
    if form.validate_on_submit():
        user = UserM.login_check(form.username_or_email.data, form.password.data)
        
        if user is not False:
            session['user_id'] = user["id"]
            
            #set permanent login, if selected
            if form.remember.data == True:
                session.permanent = True

            flash('Welcome %s' % user["username"], 'success')
            
            if ('requested_url' in session):
                requested_url = session['requested_url']
                session['requested_url'] = ""
                
                return redirect(requested_url)            
            
            return redirect(url_for('main_page_module.index'))

        flash('Wrong email or password', 'error')
    
    try:
        if(session['user_id']):
            return redirect(url_for("main_page_module.index"))
  
    except:
        for error in form.errors:
            print(error)
            flash(f'Invalid Data: {error}', 'error')
        
        return render_template("main_page_module/auth/login.html", form=form)

@main_page_module.route('/logout/')
@login_required
def logout():
    #session.pop("user_id", None)
    #session.permanent = False
    session.clear()
    flash('You have been logged out. Have a nice day!', 'success')

    return redirect(url_for("main_page_module.login"))
