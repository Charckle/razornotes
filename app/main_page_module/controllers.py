import markdown2
import json

# Import flask dependencies
from flask import Blueprint, request, render_template, \
                  flash, g, session, redirect, url_for, jsonify, send_file, Response, abort

# Import module forms
from app.main_page_module.forms import form_dicts
from app.main_page_module.r_proc import Import_Ex, HL_proc
from app.main_page_module.p_objects.note_o import N_obj
from app.main_page_module.p_objects import webauthn_stp, ip_restrict

# Import module models (i.e. User)
from app.main_page_module.models import UserM, Notes, Tag, Tmpl

from app import app, clipboard
from wrappers import login_required
from app.pylavor import Pylavor
from app.main_page_module.argus import WSearch
from app.main_page_module.other import Randoms, NotesS

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
    
    return dict(Randoms=Randoms, Notes=Notes, Tag=Tag, Tmpl=Tmpl,
                NotesS=NotesS, N_obj=N_obj, markdown2=markdown2, UserM=UserM)


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

    if key == "":
        asterix = ""
    else:
        asterix = "*"
        
    key = key + asterix

    return jsonify(N_obj.search(key))


@main_page_module.route('/note_delete/', methods=['POST'])
@login_required
def note_delete():
    note_id = request.form["id"]
    note = Notes.get_one(note_id)
    
    if note is None:
        flash('No entries with this ID found to delete.', 'error')
        
        return redirect(url_for("main_page_module.notes_all"))  
    
    note_o = N_obj(note_id)
    note_o.delete()
    
    flash(f'Note {note["title"]} successfully deleted.', 'success')  
    
    return redirect(url_for("main_page_module.index"))   
    
@main_page_module.route('/notes_delete_all_trashed/', methods=['GET'])
@login_required
def notes_delete_all_trashed():
    
    Notes.delete_all_trashed()     
    
    flash(f'All trashed notes deleted.', 'success')  
    
    return redirect(url_for("main_page_module.notes_all_trashed"))      
    
@main_page_module.route('/note_trash/', methods=['POST'])
@login_required
def note_trash():
    note_id = request.form["id"]
    note = Notes.get_one(note_id)
    
    if note is None:
        flash('No notes with this ID found to trash.', 'error')
        
        return redirect(url_for("main_page_module.notes_all"))  
    
    Notes.trash_one(note_id)     
    
    flash(f'Note -{note["title"]}- successfully trashed.', 'success')  
    
    return redirect(url_for("main_page_module.notes_all"))  

@main_page_module.route('/note_reactivate/<note_id>', methods=['get'])
@login_required
def note_reactivate(note_id):
    note = Notes.get_one(note_id)
    
    if note is None:
        flash('No notes with this ID found to reactivate.', 'error')
        
        return redirect(url_for("main_page_module.notes_all_trashed"))  
    
    
    Notes.reactivate_one(note_id)     
    
    flash(f'Note -{note["title"]}- successfully reActivated!', 'success')  
    
    return redirect(url_for("main_page_module.notes_all"))  


@main_page_module.route('/notes_all_trashed/')
@login_required
def notes_all_trashed():
    notes = Notes.get_all_trashed()
   
    return render_template("main_page_module/notes/notes_all_trashed.html", notes=notes)


@main_page_module.route('/note_new/<int:tmpl_id>', methods=['GET'])
@main_page_module.route('/note_new', methods=['GET', 'POST'])
@login_required
def note_new(tmpl_id: int =None):   
    # If sign in form is submitted
    form = form_dicts["Note"]()
    
    # Verify the sign in form
    if form.validate_on_submit():
        note_title = str(form.title.data).strip()
        note_id = Notes.create(note_title, form.note_text.data, form.note_type.data)
        
        #create argus index
        notes = Notes.get_all_active()
        new_index = WSearch()
        new_index.index_create(notes)
        
        flash('Entry successfully created!', 'success')
        flash('Argus index successfully updated', 'success')
        
        return redirect(url_for("main_page_module.note_view", note_id=note_id))
    
    tmpl = Tmpl.get_one(tmpl_id)
    
    if tmpl != None:
        tmpl = Tmpl.get_one(tmpl_id)
        form.note_text.data = tmpl["text_"]
    
    return render_template("main_page_module/notes/note_new.html", form=form)

@main_page_module.route('/notes_all/')
@login_required
def notes_all():
    notes = Notes.get_all_active()

    return render_template("main_page_module/notes/notes_all.html", notes=notes)

@main_page_module.route('/note_view/<note_id>', methods=['GET'])
@login_required
def note_view(note_id):
    note = Notes.get_one(note_id)
    
    if note is None:
        flash('No entrie found', 'error')
        
        return redirect(url_for("main_page_module.index"))
    

    return render_template("main_page_module/notes/note_view.html", note=note)

@main_page_module.route('/note_edit/<note_id>', methods=['GET', 'POST'])
@login_required
def note_edit(note_id):
    note = Notes.get_one(note_id)
    
    if note is None:
        flash('No entrie found or you do not have permissions to edit the note.', 'error')
        
        return redirect(url_for("main_page_module.notes_all"))
    
    form = form_dicts["Note"]()
    form.process(id = note["id"],
                 title = note["title"],
                 note_type = note["note_type"],
                 note_text = note["text"],
                 relevant = note["relevant"],
                 pinned = note["pinned"])
    
    tags = Tag.get_all_of_note(note_id)
    all_tags = Tag.get_all()
    
    return render_template("main_page_module/notes/note_edit.html", note=note, form=form, tags=tags, 
                           all_tags=all_tags)

@main_page_module.route('/note_change/', methods=['POST'])
@login_required
def note_change():
    form = form_dicts["Note"]()
    note_id = form.id.data
    
    note = Notes.get_one(note_id)
    
    if note is None:
        flash('No entrie found or you do not have permissions to edit the note.', 'error')
        
        return redirect(url_for("main_page_module.notes_all"))    
    
    note_o = N_obj(note_id)
    
    if form.validate_on_submit():
        Notes.update_one(note_id, form.title.data, form.note_type.data, form.note_text.data, 
                                  form.relevant.data, form.pinned.data)
        
        if form.file_u.data != None:
            file_u = form.file_u.data
            note_o.save_file_to_note(file_u)
        
        #create argus index
        notes = Notes.get_all_active()
        new_index = WSearch()
        new_index.index_create(notes)
        
        flash('Entry successfully Eddited!', 'success')
        #flash('Argus index successfully updated', 'success')
        
        return redirect(url_for("main_page_module.note_view", note_id=form.id.data))
    
    for error in form.errors:
        print(error)
        flash(f'Invalid Data: {error}', 'error')
    
    return render_template("main_page_module/notes/note_edit.html", note=note, form=form, tags=tags, 
                           all_tags=all_tags)


@main_page_module.route('/note_delete_file/', methods=['POST'])
@login_required
def note_delete_file():
    file_id_name = request.form["file_id_name"]
    file_u = Notes.get_one_file(file_id_name)
    
    if file_u is None:
        flash('No note file with this ID found to trash.', 'error')
        
        return redirect(url_for("main_page_module.notes_all"))  
    
    note_id = file_u["note_id"]
    note_o = N_obj(note_id)
    # here, make this, but with failsafe
    Notes.delete_one_file(file_id_name)
    path_u = app.config['UPLOAD_FOLDER']
    note_o.file_delete(file_u)

    flash(f'{file_u["file_name"]} - File deleted successfully .', 'success')  
    
    return redirect(url_for("main_page_module.note_view", note_id=note_id))


@main_page_module.route('/note_download/<note_id>', methods=['GET'])
@login_required
def note_download(note_id):
    note = Notes.get_one(note_id)
    
    if note is None:
        flash('No entrie found or you do not have permissions to edit the note.', 'error')
        
        return redirect(url_for("main_page_module.notes_all"))
    
    n_title = Randoms.get_valid_filename(note["title"])
    markdown_text = note["text"]
    # Set headers for the downloadable file
    response = Response(markdown_text, content_type='text/markdown')
    response.headers['Content-Disposition'] = f'attachment; filename={n_title}.md'

    return response


@main_page_module.route('/note_download_file/<filename>', methods=['GET'])
@login_required
def note_download_file(filename):
    file_u = Notes.get_one_file(filename)
    
    if file_u is None:
        abort(404)
    
    path_u = app.config['UPLOAD_FOLDER'] + "/" +  filename
    file_name = file_u["file_name"]
    
    return send_file(path_u, as_attachment=True, attachment_filename=file_name)


@main_page_module.route('/all_templates/')
@login_required
def tmpl_all():
    tmpls = Tmpl.get_all()
   
    return render_template("main_page_module/notes/templates/tmpl_all.html", tmpls=tmpls)


@main_page_module.route('/create_template/', methods=['GET', 'POST'])
@login_required
def tmpl_new():
    form = form_dicts["Note_tmpl"]()
    
    # Verify the sign in form
    if form.validate_on_submit():
        tmpl_id = Tmpl.new(form.name.data, form.text_.data)
        
        flash('Template successfully added!', 'success')
        
        return redirect(url_for("main_page_module.tmpl_edit", tmpl_id=tmpl_id))
    
    for error in form.errors:
        print(error)
    
        flash(f'Invalid Data: {error}', 'error')    
    
    return render_template("main_page_module/notes/templates/tmpl_new.html", form=form)

@main_page_module.route('/tmpl_edit/<tmpl_id>', methods=['GET', 'POST'])
@login_required
def tmpl_edit(tmpl_id):
    tmpl = Tmpl.get_one(tmpl_id)
    
    if tmpl is None:
        flash('No entrie found or you do not have permissions to edit the template.', 'error')
        
        return redirect(url_for("main_page_module.tmpl_all"))
    
    form = form_dicts["Note_tmpl"]()
    form.process(id = tmpl["id"],
                 name = tmpl["name"],
                 text_ = tmpl["text_"])
    
    
    return render_template("main_page_module/notes/templates/tmpl_edit.html", tmpl=tmpl, form=form)


@main_page_module.route('/tmpl_change/', methods=['POST'])
@login_required
def tmpl_change():
    form = form_dicts["Note_tmpl"]()
    tmpl_id = form.id.data
    
    tmpl = Tmpl.get_one(tmpl_id)
    
    if tmpl is None:
        flash('No entrie found or you do not have permissions to edit the template.', 'error')
        
        return redirect(url_for("main_page_module.tmpl_all"))    
    
    if form.validate_on_submit():
        Tmpl.update_one(tmpl_id, form.name.data, form.text_.data)
        
        flash('Template successfully Eddited!', 'success')
        
        return redirect(url_for("main_page_module.tmpl_edit", tmpl_id=form.id.data))
    
    for error in form.errors:
        print(error)
        flash(f'Invalid Data: {error}', 'error')
    
    return render_template("main_page_module/notes/templates/tmpl_edit.html", tmpl=tmpl, form=form)  


@main_page_module.route('/tmpl_delete/<tmpl_id>', methods=['GET'])
@login_required
def tmpl_delete(tmpl_id):
    tmpl = Tmpl.get_one(tmpl_id)
    
    if tmpl is None:
        flash('No entries with this ID found to delete.', 'error')
        
        return redirect(url_for("main_page_module.tmpl_all"))  
    
    Tmpl.delete_one(tmpl_id)
    
    flash(f'Template {tmpl["name"]} successfully deleted.', 'success')  
    
    return redirect(url_for("main_page_module.tmpl_all"))   


@main_page_module.route('/tags_all/')
@login_required
def tags_all():
    tags = Tag.get_all()
   
    return render_template("main_page_module/tags/tags_all.html", tags=tags)


@main_page_module.route('/tag_view/<tag_id>')
@login_required
def tag_view(tag_id):
    
    tag = Tag.get_one(tag_id)
    
    if (tag is None):
        
        flash('The tag does not exist !', 'error')
        
        return redirect(url_for("main_page_module.index"))        
    
    notes = Tag.notes_get_all_of_tag(tag_id)
    
    return render_template("main_page_module/tags/tag_view.html", tag=tag, notes=notes)


@main_page_module.route('/tag_create/', methods=['POST'])
@login_required
def tag_create():

    note_id = request.form["note_id"]
    tagName = request.form["tagName"]
    tagColor = request.form["tagColor"]
    
    note = Notes.get_one(note_id)
    
    if note is not None:
        try:        
            tag_id = Tag.add(tagName, tagColor)
            
            Tag.connect_tag(note_id, tag_id)
            result_concatinate = str(tagName) + "++++__++++++" + str(tagColor) + "++++__++++++" + str(tag_id)
           
            json_response = {"a": result_concatinate}        
            
        except Exception as e:
            print(e)
            json_response = {"a": "no"}
        
        return jsonify(json_response)
    
    return "Limona"


@main_page_module.route('/tag_add/', methods=['POST'])
@login_required
def tag_add():

    note_id = request.form["note_id"]
    tag_id = request.form["tag_id"]

    note = Notes.get_one(note_id)
    
    if note is not None:
        try:        
            tag = Tag.get_one(tag_id)
            if Tag.note_tag_get_one(note_id, tag_id) is not None:
                return "Limona"
            Tag.connect_tag(note_id, tag_id)
            result_concatinate = str(tag["name"]) + "++++__++++++" + str(tag["color"]) + "++++__++++++" + str(tag_id)
           
            json_response = {"a": result_concatinate}        
            
        except Exception as e:
            print(e)
            json_response = {"a": "no"}
        
        return jsonify(json_response)
    
    return "Limona"


@main_page_module.route('/tag_remove/', methods=['POST'])
@login_required
def tag_remove():
    note_id = request.form["note_id"]
    tag_id = request.form["tag_id"]
    
    note = Notes.get_one(note_id)
    tag = Tag.note_tag_get_one(note_id, tag_id)
    
    if (note is None) or (tag is None):
        flash('No note found or you do not have permissions to edit the note.', 'error')
        
        return redirect(url_for("main_page_module.notes_all"))    
    
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
def user_delete():
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


@main_page_module.route('/admin/user_register_fido', methods=['GET'])
@login_required
def user_register_fido():
    user_id = session['user_id']
    user_sql = UserM.get_one(user_id)
    
    json_opt, challenge = webauthn_stp.generate_registration(app, user_sql)
    session['fido2_challenge'] = challenge
    
    return render_template("main_page_module/admin/user_fido2_reg.html", json_opt=json_opt,
                           user_sql=user_sql, challenge=challenge)


@main_page_module.route('/admin/user_save_registration_fido', methods=['POST'])
@login_required
def user_save_registration_fido():    
        # Check if the request contains JSON data
    if request.is_json:
        try:
            json_data = request.get_json()
            
            challenge = session['fido2_challenge'] 
            credential_id_bs64, credential_public_key_bs4 = webauthn_stp.verify_registration(app, json_data, challenge)
            
            # save the public key
            user_id = session['user_id']
            UserM.save_fido2_creds(user_id, credential_id_bs64, credential_public_key_bs4)
            
            #print(json_data["id"])
            return jsonify({"message": "Fido2 hardware key registered successfully!"}), 200
        except Exception as e:
            app.logger.info(e)
            return jsonify({"message": "Error on the server side"}), 500
    else:
        return jsonify({"message": "Invalid JSON data"}), 400
    

@main_page_module.route('/admin//user_delete_fibo2', methods=['POST'])
@login_required
def user_delete_fibo2():
    cred_id_bs64 = request.form["cred_id_bs64"]
    fido2_cred = UserM.get_fido2(cred_id_bs64)
    
    user_id = fido2_cred["user_id"]
    
    if fido2_cred is None:
        flash('No credentials with this ID found to delete.', 'error')
        
        return redirect(url_for("main_page_module.user_all"))  
    
    UserM.delete_one_fido2(cred_id_bs64)
    
    flash(f'Credential successfully deleted.', 'success')  
    
    return redirect(url_for("main_page_module.user_edit", user_id=user_id))       


# Set the route and accepted methods
@main_page_module.route('/login/', methods=['GET', 'POST'])
def login():
    if ('user_id' in session):
        return redirect(url_for("main_page_module.index"))
    
    # If sign in form is submitted
    form = form_dicts["Login"]()

    # Verify the sign in form
    if form.validate_on_submit():
        user = UserM.login_check(form.username_or_email.data, form.password.data)
        
        if user is not False:
            # check the IP restriction
            if app.config['IP_RESTRICTION'] == "1":
                client_ip = request.remote_addr
                app.logger.info(f"User trying to login from: {client_ip}")
                
                if not ip_restrict.is_ip_allowed(client_ip):
                    flash('Your IP is restricted. Contact an Admin', 'error')
                    return redirect(url_for("main_page_module.login"))
            
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

    for error in form.errors:
        print(error)
        flash(f'Invalid Data: {error}', 'error')
        
    return render_template("main_page_module/auth/login.html", form=form)
        

@main_page_module.route('/logout/')
def logout():
    #session.pop("user_id", None)
    #session.permanent = False
    session.clear()
    flash('You have been logged out. Have a nice day!', 'success')

    return redirect(url_for("main_page_module.login"))


# Set the route and accepted methods
@main_page_module.route('/login_2fa', methods=['GET'])
def login_2fa():
    if ('user_id' in session):
        return redirect(url_for("main_page_module.index"))
    
    json_opt, challenge = webauthn_stp.generate_verification(app)
    session['fido2_challenge'] = challenge

    return render_template("main_page_module/auth/login_2fa.html", json_opt=json_opt)    
         

@main_page_module.route('/verify_login_2fa', methods=['POST'])
def verify_login_2fa():    
        # Check if the request contains JSON data
    if request.is_json:
        try:
            json_data = request.get_json()
            #print(json_data["response"])
            challenge = session['fido2_challenge'] 
            cred_id_bs64 = json_data["id"]
            public_key_bs64 = UserM.get_fido2(cred_id_bs64)["public_key_bs64"]
            
            session['user_id'] = webauthn_stp.verify_verification(app, json_data, challenge, public_key_bs64)
            
            #print(json_data["id"])
            return jsonify({"message": "Validation successfull!"}), 200
        except Exception as e:
            app.logger.info(e)
            return jsonify({"message": "Error on the server side"}), 500

    else:
        return jsonify({"message": "Invalid JSON data"}), 400
    
