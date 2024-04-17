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
from app.main_page_module.p_objects.audit_log import AuditLog

# Import module models (i.e. User)
from app.main_page_module.models import UserM, Notes, Tag, Tmpl, GroupsAccessM

from app import app, clipboard
from wrappers import access_required
from app.pylavor import Pylavor
from app.main_page_module.argus import WSearch
from app.main_page_module.other import Randoms, NotesS, UserRole

#import os
import re
import os
import zipfile
import io
import pathlib
import datetime



# Define the blueprint: 'auth', set its url prefix: app.url/auth
notes_module = Blueprint('notes_module', __name__, url_prefix='/')


@app.context_processor
def inject_to_every_page():
    
    return dict(Randoms=Randoms, Notes=Notes, Tag=Tag, Tmpl=Tmpl,
                NotesS=NotesS, N_obj=N_obj, markdown2=markdown2, UserM=UserM, GroupsAccessM=GroupsAccessM)



@notes_module.route('/search/', methods=['GET'])
@access_required()
def search():

    return render_template("main_page_module/search.html")

@notes_module.route('/search/', methods=['POST'])
@access_required()
def search_results():
    key = request.form["key"]

    if key == "":
        asterix = ""
    else:
        asterix = "*"
        
    key = key + asterix

    return jsonify(N_obj.search(key))


@notes_module.route('/note_delete/', methods=['POST'])
@access_required(UserRole.READWRITE)
def note_delete():
    note_id = request.form["id"]
    note = Notes.get_one(note_id)
    
    if note is None:
        flash('No entries with this ID found to delete.', 'error')
        
        return redirect(url_for("notes_module.notes_all"))  
    
    note_o = N_obj(note_id)
    note_o.delete()
    
    flash(f'Note {note["title"]} successfully deleted.', 'success')  
    
    return redirect(url_for("notes_module.notes_all_trashed"))   
    
@notes_module.route('/notes_delete_all_trashed/', methods=['GET'])
@access_required(UserRole.READWRITE)
def notes_delete_all_trashed():
    
    trashed_notes = Notes.get_all_trashed()     
    for ixc in trashed_notes:
        note_o = N_obj(ixc["id"])
        note_o.delete()        
        
    
    flash(f'All trashed notes deleted.', 'success')  
    
    return redirect(url_for("notes_module.notes_all_trashed"))      
    
@notes_module.route('/note_trash/', methods=['POST'])
@access_required(UserRole.READWRITE)
def note_trash():
    note_id = request.form["id"]
    note = Notes.get_one(note_id)
    
    if note is None:
        flash('No notes with this ID found to trash.', 'error')
        
        return redirect(url_for("notes_module.notes_all"))  
    
    Notes.trash_one(note_id)     
    
    AuditLog.create(f"Note Trashed, id: {note_id}: {note['title'][:10]}")        
    
    
    flash(f'Note -{note["title"]}- successfully trashed.', 'success')  
    
    return redirect(url_for("notes_module.notes_all"))  

@notes_module.route('/note_reactivate/<note_id>', methods=['get'])
@access_required(UserRole.READWRITE)
def note_reactivate(note_id):
    note = Notes.get_one(note_id)
    
    if note is None:
        flash('No notes with this ID found to reactivate.', 'error')
        
        return redirect(url_for("notes_module.notes_all_trashed"))  
    
    
    Notes.reactivate_one(note_id)     
    
    AuditLog.create(f"Note Reactivated, id: {note_id}: {note['title'][:10]}")        
    
    
    flash(f'Note -{note["title"]}- successfully reActivated!', 'success')  
    
    return redirect(url_for("notes_module.notes_all_trashed"))  


@notes_module.route('/notes_all_trashed/')
@access_required(UserRole.READWRITE)
def notes_all_trashed():
    notes = Notes.get_all_trashed()
   
    return render_template("main_page_module/notes/notes_all_trashed.html", notes=notes)


@notes_module.route('/note_new/<int:tmpl_id>', methods=['GET'])
@notes_module.route('/note_new', methods=['GET', 'POST'])
@access_required(UserRole.READWRITE)
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
        
        return redirect(url_for("notes_module.note_view", note_id=note_id))
    
    tmpl = Tmpl.get_one(tmpl_id)
    
    if tmpl != None:
        tmpl = Tmpl.get_one(tmpl_id)
        form.note_text.data = tmpl["text_"]
    
    return render_template("main_page_module/notes/note_new.html", form=form)

@notes_module.route('/notes_all/')
@access_required()
def notes_all():
    notes = Notes.get_all_active()

    return render_template("main_page_module/notes/notes_all.html", notes=notes)

@notes_module.route('/note_view/<note_id>', methods=['GET'])
@access_required()
def note_view(note_id):
    note = Notes.get_one(note_id)
    
    if note is None:
        flash('No entrie found', 'error')
        
        return redirect(url_for("main_page_module.index"))
    
    # set note as viewed
    N_obj.notes_viewed(note_id)

    return render_template("main_page_module/notes/note_view.html", note=note)


@notes_module.route('/note_edit/<note_id>', methods=['GET', 'POST'])
@notes_module.route('/note_edit/', methods=['POST', 'GET'])
@access_required(UserRole.READWRITE)
def note_edit(note_id=None):
    form = form_dicts["Note"]()
    if note_id == None:
        note_id = form.id.data
    else:
        form.id.data = note_id
        
    note = Notes.get_one(note_id)
    if note is None:
        flash('No entrie found or you do not have permissions to edit the note.', 'error')
        return redirect(url_for("notes_module.notes_all"))    

    # GET
    if request.method == 'GET':
        form.process(id = note["id"],
                     title = note["title"],
                     note_type = note["note_type"],
                     note_text = note["text"],
                     relevant = note["relevant"],
                     pinned = note["pinned"])      
    
    # POST
    if form.validate_on_submit():        
        Notes.update_one(note_id, form.title.data, form.note_type.data, form.note_text.data, 
                                  form.relevant.data, form.pinned.data)
        
        if form.file_u.data != None:
            file_u = form.file_u.data
            note_o = N_obj(note_id)            
            note_o.save_file_to_note(file_u)
        
        #create argus index
        notes = Notes.get_all_active()
        new_index = WSearch()
        new_index.index_create(notes)
        
        AuditLog.create(f"Note Edited, id: {note_id}: {note['title'][:10]}")        
        
        
        flash('Entry successfully Eddited!', 'success')
        #flash('Argus index successfully updated', 'success')
        
        return redirect(url_for("notes_module.note_view", note_id=form.id.data))
    
    for field, errors in form.errors.items():
        print(f'Field: {field}')
        for error in errors:
            flash(f'Invalid Data for {field}: {error}', 'error')    
            
    return render_template("main_page_module/notes/note_edit.html", note=note, form=form)    


@notes_module.route('/note_delete_file/', methods=['POST'])
@access_required(UserRole.READWRITE)
def note_delete_file():
    file_id_name = request.form["file_id_name"]
    file_u = Notes.get_one_file(file_id_name)
    
    if file_u is None:
        flash('No note file with this ID found to trash.', 'error')
        
        return redirect(url_for("notes_module.notes_all"))  
    
    note_id = file_u["note_id"]
    note_o = N_obj(note_id)
    # here, make this, but with failsafe
    Notes.delete_one_file(file_id_name)
    path_u = app.config['UPLOAD_FOLDER']
    note_o.file_delete(file_u)
    
    AuditLog.create(f"Note file deleted, note id: {note_id}: {file_u['file_name'][:15]}")        
    

    flash(f'{file_u["file_name"]} - File deleted successfully .', 'success')  
    
    return redirect(url_for("notes_module.note_view", note_id=note_id))


@notes_module.route('/download/<note_id>', methods=['GET'])
@access_required()
def note_download(note_id):
    note = Notes.get_one(note_id)
    
    if note is None:
        flash('No entrie found or you do not have permissions to edit the note.', 'error')
        
        return redirect(url_for("notes_module.notes_all"))
    
    n_title = Randoms.get_valid_filename(note["title"])
    markdown_text = note["text"]
    # Set headers for the downloadable file
    response = Response(markdown_text, content_type='text/markdown')
    response.headers['Content-Disposition'] = f'attachment; filename={n_title}.md'

    return response


@notes_module.route('/download_file/<filename>', methods=['GET'])
@access_required()
def note_download_file(filename):
    file_u = Notes.get_one_file(filename)
    
    if file_u is None:
        abort(404)
    
    path_u = app.config['UPLOAD_FOLDER'] + "/" +  filename
    file_name = file_u["file_name"]
    
    return send_file(path_u, as_attachment=True, attachment_filename=file_name)

@notes_module.route('/preview_file/<filename>', methods=['GET'])
@access_required()
def preview_file(filename):
    file_u = Notes.get_one_file(filename)
    
    if file_u is None:
        abort(404)
    
    path_u = app.config['UPLOAD_FOLDER'] + "/" +  filename
    file_name = file_u["file_name"]
    
    return render_template("main_page_module/notes/preview_image.html", filename=filename, file_name=file_name)


@notes_module.route('/all_templates/')
@access_required()
def tmpl_all():
    tmpls = Tmpl.get_all()
   
    return render_template("main_page_module/notes/templates/tmpl_all.html", tmpls=tmpls)


@notes_module.route('/create_template/', methods=['GET', 'POST'])
@access_required(UserRole.READWRITE)
def tmpl_new():
    form = form_dicts["Note_tmpl"]()
    
    # Verify the sign in form
    if form.validate_on_submit():
        tmpl_id = Tmpl.new(form.name.data, form.text_.data)
        
        flash('Template successfully added!', 'success')
        
        return redirect(url_for("notes_module.tmpl_edit", tmpl_id=tmpl_id))
    
    for field, errors in form.errors.items():
        print(f'Field: {field}')
        for error in errors:
            flash(f'Invalid Data for {field}: {error}', 'error')
    
    return render_template("main_page_module/notes/templates/tmpl_new.html", form=form)


@notes_module.route('/tmpl_edit/<tmpl_id>', methods=['GET', 'POST'])
@notes_module.route('/tmpl_edit/', methods=['POST', 'GET'])
@access_required(UserRole.READWRITE)
def tmpl_edit(tmpl_id=None):
    form = form_dicts["Note_tmpl"]()
    
    if tmpl_id == None:
        tmpl_id = form.id.data
    else:
        form.id.data = tmpl_id
        
    tmpl = Tmpl.get_one(tmpl_id)
    
    if tmpl is None:
        flash('No entrie found or you do not have permissions to edit the template.', 'error')
        
        return redirect(url_for("notes_module.tmpl_all"))
    
    # GET
    if request.method == 'GET':       
        form.process(id = tmpl["id"],
                     name = tmpl["name"],
                     text_ = tmpl["text_"])
    
    # POST    
    if form.validate_on_submit():
        Tmpl.update_one(tmpl_id, form.name.data, form.text_.data)
        
        flash('Template successfully Eddited!', 'success')
        
        return redirect(url_for("notes_module.tmpl_edit", tmpl_id=form.id.data))
    
    for field, errors in form.errors.items():
        print(f'Field: {field}')
        for error in errors:
            flash(f'Invalid Data for {field}: {error}', 'error')    
    
    return render_template("main_page_module/notes/templates/tmpl_edit.html", tmpl=tmpl, form=form)


@notes_module.route('/tmpl_delete/<tmpl_id>', methods=['GET'])
@access_required(UserRole.READWRITE)
def tmpl_delete(tmpl_id):
    tmpl = Tmpl.get_one(tmpl_id)
    
    if tmpl is None:
        flash('No entries with this ID found to delete.', 'error')
        
        return redirect(url_for("notes_module.tmpl_all"))  
    
    Tmpl.delete_one(tmpl_id)
    
    flash(f'Template {tmpl["name"]} successfully deleted.', 'success')  
    
    return redirect(url_for("notes_module.tmpl_all"))   


@notes_module.route('/tags_all/')
@access_required()
def tags_all():
    tags = Tag.get_all()
   
    return render_template("main_page_module/notes/tags/tags_all.html", tags=tags)


@notes_module.route('/tag_edit/<tag_id>', methods=['GET', 'POST'])
@notes_module.route('/tag_edit/', methods=['POST', 'GET'])
@access_required(UserRole.READWRITE)
def tag_edit(tag_id=None):
    form = form_dicts["Note_tag"]()
    
    if tag_id == None:
        tag_id = form.id.data
    else:
        form.id.data = tag_id
    
    tag_sql = Tag.get_one(tag_id)
    
    if not tag_sql:
        flash('Tag does not exist.', 'error')
    
        return redirect(url_for("notes_module.tags_all"))    
    
    # GET
    if request.method == 'GET':        
        form.process(id = tag_sql["id"],
                     name = tag_sql["name"],
                     color = tag_sql["color"])    
        
    # POST
    if form.validate_on_submit():        
        Tag.change_one(form.id.data, form.name.data, form.color.data)
            
        flash('Tag successfully Eddited!', 'success')
        
        return redirect(url_for("notes_module.tag_edit", tag_id=form.id.data))
    
    for field, errors in form.errors.items():
        print(f'Field: {field}')
        for error in errors:
            flash(f'Invalid Data for {field}: {error}', 'error')    
   
    return render_template("main_page_module/notes/tags/tag_edit.html", form=form)


@notes_module.route('/tag_create/', methods=['POST'])
@access_required(UserRole.READWRITE)
def tag_create():

    note_id = request.form["note_id"]
    tagName = request.form["tagName"]
    tagColor = request.form["tagColor"]
    
    note = Notes.get_one(note_id)
    
    if note is not None:
        try:        
            if str(tagName) == "":
                tagName = "Forgot to add the name"            
            tag_id = Tag.add(tagName, tagColor)
            
            Tag.connect_tag(note_id, tag_id)
            
            result_concatinate = str(tagName) + "++++__++++++" + str(tagColor) + "++++__++++++" + str(tag_id)
           
            json_response = {"a": result_concatinate}        
            
        except Exception as e:
            print(e)
            json_response = {"a": "no"}
        
        return jsonify(json_response)
    
    return "Limona"


@notes_module.route('/tag_add/', methods=['POST'])
@access_required(UserRole.READWRITE)
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


@notes_module.route('/tag_remove/', methods=['POST'])
@access_required(UserRole.READWRITE)
def tag_remove():
    note_id = request.form["note_id"]
    tag_id = request.form["tag_id"]
    
    note = Notes.get_one(note_id)
    tag = Tag.note_tag_get_one(note_id, tag_id)
    
    if (note is None) or (tag is None):
        flash('No note found or you do not have permissions to edit the note.', 'error')
        
        return redirect(url_for("notes_module.notes_all"))    
    
    Tag.remove_note_tag(note_id, tag_id)
    
    json_response = {"a": "OK"}
    
    return jsonify(json_response)

@notes_module.route('/tag_delete/', methods=['POST'])
@access_required(UserRole.READWRITE)
def tag_delete():
    try:
        tag_id = request.form["tag_id"]
    except:
        flash('Something wrong with the tag or note id.', 'error')
        return redirect(url_for("notes_module.tags_all"))       
    
    tag = Tag.get_one(tag_id)
    
    if tag is None:
        flash('No note found or you do not have permissions to edit the tag.', 'error')
        
        return redirect(url_for("notes_module.tags_all"))    
    
    Tag.delete(tag_id)
    
    AuditLog.create(f"Tag deleted, id: {tag_id}: {tag['name'][:15]}")        
    

    flash(f'{tag["name"]} - Tag successfully .', 'success')  
    
    return redirect(url_for("notes_module.tags_all"))
