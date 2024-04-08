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
admin_module = Blueprint('admin_module', __name__, url_prefix='/')


@app.context_processor
def inject_to_every_page():
    
    return dict(Randoms=Randoms, Notes=Notes, Tag=Tag, Tmpl=Tmpl,
                NotesS=NotesS, N_obj=N_obj, markdown2=markdown2, UserM=UserM, GroupsAccessM=GroupsAccessM)


@admin_module.route('/get_zipped_entries/')
@access_required()
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

@admin_module.route('/create_hashes/')
@access_required()
def create_hashes():
    HL_proc.create_hashes_()
   
    return redirect(url_for("main_page_module.index"))

@admin_module.route('/notes_import/', methods=['GET', 'POST'])
@access_required()
def notes_import():    
    form = form_dicts["ImportNotes"]()
    
    if form.validate_on_submit():
        ditc_ = Import_Ex.import_(form.import_file.data)
        flash(f"Import holds {ditc_['to_process']} Notes, {ditc_['added']} added.", "success")
        
        return redirect(url_for("main_page_module.index"))
    
    for field, errors in form.errors.items():
        print(f'Field: {field}')
        for error in errors:
            flash(f'Invalid Data for {field}: {error}', 'error')
    
    return render_template("main_page_module/notes_import.html", form=form)


@admin_module.route('/notes_export/', methods=['GET'])
@access_required()
def notes_export():
    data_ = Import_Ex.export()
    
    notes_j = jsonify(data_)
    notes_j.mimetype = "application/json"
    notes_j.headers = {"Content-Disposition":
                                    "attachment;filename=razor_notes.rnxf"}
    
    return notes_j


@admin_module.route('/admin/users_all/')
@access_required(UserRole.ADMIN)
def users_all():
    users = UserM.get_all()
   
    return render_template("main_page_module/admin/users_all.html", users=users)

@admin_module.route('/user_new', methods=['GET', 'POST'])
@access_required(UserRole.ADMIN)
def user_new():
    # If sign in form is submitted
    form = form_dicts["User"]()
    
    # Verify the sign in form
    if form.validate_on_submit():
        u_id = UserM.create(form.name.data, form.username.data, form.email.data,
                           form.password.data, form.status.data, form.api_key.data)
        
        flash('User Successfully Created', 'success')
        
        return redirect(url_for("admin_module.user_edit", user_id=u_id))
    
    
    for field, errors in form.errors.items():
        print(f'Field: {field}')
        for error in errors:
            flash(f'Invalid Data for {field}: {error}', 'error')
    
    return render_template("main_page_module/admin/user_new.html", form=form, Pylavor=Pylavor)

@admin_module.route('/admin/user_edit/<user_id>', methods=['GET', 'POST'])
@admin_module.route('/admin/user_edit/', methods=['POST'])
@access_required(UserRole.ADMIN)
def user_edit(user_id=None):
    form = form_dicts["User"]()
    
    if request.method == 'GET':
        user = UserM.get_one(user_id)
        if not user:
            flash('User does not exist.', 'error')
            
            return redirect(url_for("admin_module.users_all"))     
        
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
        
            return redirect(url_for("admin_module.users_all"))         
    
    if form.validate_on_submit():
        if user["status"] == 1 and form.status.data == "0" and len(UserM.get_all_w_status(1)) < 2:
            flash('You cannot take access from the last remaining user with access, sry!', 'error')
            
            return redirect(url_for("admin_module.user_edit", user_id=form.id.data))            
        
        UserM.change_one(form.id.data, form.username.data, form.name.data, form.email.data,
                        form.api_key.data, form.status.data)
        
        if form.password.data != "":
            UserM.change_passw(form.id.data, form.password.data)
            
        flash('User successfully Eddited!', 'success')
        
        return redirect(url_for("admin_module.user_edit", user_id=form.id.data))
    
    for field, errors in form.errors.items():
        print(f'Field: {field}')
        for error in errors:
            flash(f'Invalid Data for {field}: {error}', 'error')    
    
    
    return render_template("main_page_module/admin/user_edit.html", form=form, user=user)
    

@admin_module.route('/admin/delete/', methods=['POST'])
@access_required(UserRole.ADMIN)
def user_delete():
    user = UserM.get_one(request.form["id"])
    
    if not user:
        flash('User does not exist.', 'error')
        
        return redirect(url_for("admin_module.users_all")) 
    
    if len(UserM.get_all()) < 2:
        flash('Cannot delete the last user, sry :/', 'error')
        
        return redirect(url_for("admin_module.users_all"))     
    
    else:
        UserM.delete_one(user["id"])
        
        flash(f'User {user["name"]} - {user["username"]} successfully deleted.', 'success')
        
        return redirect(url_for("admin_module.users_all")) 


@admin_module.route('/user_add_group', methods=['POST'])
@access_required(UserRole.ADMIN)
def user_add_group():
    try:
        user_id = request.form["id"]
        g_id = request.form["g_id"]
    except:
        flash('Missing post stuff.', 'error')
        return redirect(url_for("admin_module.users_all"))      
    
    user = UserM.get_one(user_id)
    
    if not user:
        flash('User does not exist.', 'error')
        
        return redirect(url_for("admin_module.users_all"))     
    
    group_ = GroupsAccessM.get_one(g_id)
    
    if not group_:
        flash('Group does not exist.', 'error')
        return redirect(url_for("admin_module.user_edit", user_id=user_id))
 
    
    GroupsAccessM.create_access_conn(user_id, g_id)
        
    flash('Group Added', 'success')
            
    return redirect(url_for("admin_module.user_edit", user_id=user_id))


@admin_module.route('/user_remove_group', methods=['POST'])
@access_required(UserRole.ADMIN)
def user_remove_group():
    try:
        user_id = request.form["id"]
        g_id = request.form["g_id"]
    except Exception as e:
        flash(f'Missing post stuff {e}.', 'error')
        return redirect(url_for("admin_module.users_all"))      
    
    user = UserM.get_one(user_id)
    
    if not user:
        flash('User does not exist.', 'error')
        
        return redirect(url_for("admin_module.users_all"))     

    group_ = GroupsAccessM.get_one(g_id)
    
    if not group_:
        flash('Group does not exist.', 'error')
        return redirect(url_for("admin_module.user_edit", user_id=user_id))
 
    if int(g_id) == 1:
        # get all the users with admin, and if there is only one, fail
        admins_ = GroupsAccessM.get_access_all_of_group(g_id)
        if len(admins_)== 1:
            flash('You cannot remove the last admin from the site.', 'error')
            return redirect(url_for("admin_module.user_edit", user_id=user_id))            
    
    
    GroupsAccessM.delete_access_conn(user_id, g_id)
        
    flash(f"Group {group_['name']} Removed", 'success')
            
    return redirect(url_for("admin_module.user_edit", user_id=user_id))


@admin_module.route('/admin/user_register_fido', methods=['GET'])
@access_required()
def user_register_fido():
    user_id = session['user_id']
    user_sql = UserM.get_one(user_id)
    
    json_opt, challenge = webauthn_stp.generate_registration(app, user_sql)
    session['fido2_challenge'] = challenge
    
    return render_template("main_page_module/admin/user_fido2_reg.html", json_opt=json_opt,
                           user_sql=user_sql, challenge=challenge)


@admin_module.route('/admin/user_save_registration_fido', methods=['POST'])
@access_required()
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
    

@admin_module.route('/admin//user_delete_fibo2', methods=['POST'])
@access_required()
def user_delete_fibo2():
    cred_id_bs64 = request.form["cred_id_bs64"]
    fido2_cred = UserM.get_fido2(cred_id_bs64)
    
    user_id = fido2_cred["user_id"]
    
    if fido2_cred is None:
        flash('No credentials with this ID found to delete.', 'error')
        
        return redirect(url_for("admin_module.user_all"))  
    
    UserM.delete_one_fido2(cred_id_bs64)
    
    flash(f'Credential successfully deleted.', 'success')  
    
    return redirect(url_for("admin_module.user_edit", user_id=user_id))       
