import markdown2
import json
import base64

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
main_page_module = Blueprint('main_page_module', __name__, url_prefix='/')


@app.context_processor
def inject_to_every_page():
    
    return dict(Randoms=Randoms, Notes=Notes, Tag=Tag, Tmpl=Tmpl,
                NotesS=NotesS, N_obj=N_obj, markdown2=markdown2, UserM=UserM, GroupsAccessM=GroupsAccessM)


# Set the route and accepted methods
@main_page_module.route('/', methods=['GET'])
@access_required()
def index():
    
    pinned_notes = Notes.get_all_active_index_pinned()

    notes = Notes.get_all_active_for_index()

    return render_template("main_page_module/index.html", notes=notes, 
                           pinned_notes=pinned_notes)


@main_page_module.route('/get_clipboard/', methods=['POST'])
@access_required()
def get_clipboard():
    
    return jsonify(clipboard)

@main_page_module.route('/set_clipboard/', methods=['POST'])
@access_required()
def set_clipboard():
    clipboard["clipboard"] = request.form["clipboard"]
    
    return jsonify({"result":"All OK!"})


# Set the route and accepted methods
@main_page_module.route('/login/<w_url>', methods=['GET', 'POST'])
@main_page_module.route('/login/', methods=['GET', 'POST'])
def login(w_url=None):
    if ('user_id' in session):
        return redirect(url_for("main_page_module.index"))
    
    # If sign in form is submitted
    form = form_dicts["Login"]()

    # Verify the sign in form
    if form.validate_on_submit():
        user = UserM.login_check(form.username_or_email.data, form.password.data)
        form.password.data = None        
        
        if user is not False:
            # check the IP restriction
            if app.config['IP_RESTRICTION'] == "1":

                if "X-Forwarded-For" in request.headers:
                    client_ip = request.headers['X-Forwarded-For']                    
                    app.logger.info(f"User trying to login from: {client_ip}")
                else:
                    client_ip = request.remote_addr
                    app.logger.info(f"User trying to login from: {client_ip}")
                
                if not ip_restrict.is_ip_allowed(client_ip):
                    flash('Your IP is restricted. Contact an Admin', 'error')
                    return redirect(url_for("main_page_module.login"))
            
            session['user_id'] = user["id"]
            session['name'] = user["name"]
            session['username'] = user["username"]
            
            #set permanent login, if selected
            if form.remember.data == True:
                session.permanent = True
    
            flash('Welcome %s' % user["username"], 'success')
            
            if (w_url != None):
                decoded_bytes = base64.urlsafe_b64decode(w_url.encode("utf-8"))
                decoded_url=  "/" + decoded_bytes.decode("utf-8")

                return redirect(decoded_url)            
            
            return redirect(url_for('main_page_module.index'))
    
        flash('Wrong email or password', 'error')
    
    for field, errors in form.errors.items():
        print(f'Field: {field}')
        for error in errors:
            flash(f'Invalid Data for {field}: {error}', 'error')
        
    return render_template("main_page_module/auth/login.html", form=form, w_url=w_url)
        

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
    
    
@main_page_module.route('/user_profile/', methods=['GET', 'POST'])
@access_required()
def user_profile_edit():
    user_id = session['user_id']
    user = UserM.get_one(user_id)
    if not user:
        flash('User does not exist.', 'error')
        return redirect(url_for("main_page_module.index"))      
    
    form = form_dicts["UserProfileF"]()    
    
    if request.method == 'GET':
        form.process(id = user["id"],
                     name = user["name"],
                     username = user["username"],
                     email = user["email"],
                     api_key = user["api_key"])
    
    # POST
    else:
        if form.validate_on_submit():        
            UserM.change_profile(user_id, form.name.data, form.email.data,
                            form.api_key.data)
            
            if form.password.data != "":
                UserM.change_passw(user_id, form.password.data)
                
            flash('Profile successfully Eddited!', 'success')
            
            return redirect(url_for("main_page_module.user_profile_edit"))
    
    for field, errors in form.errors.items():
        print(f'Field: {field}')
        for error in errors:
            flash(f'Invalid Data for {field}: {error}', 'error')    
    
    
    return render_template("main_page_module/user_profile/profile_edit.html", form=form, user=user)    


@main_page_module.route('/fido2_register', methods=['GET'])
@access_required(UserRole.ADMIN)
def user_register_fido():
    user_id = session['user_id']
    user_sql = UserM.get_one(user_id)
    
    json_opt, challenge = webauthn_stp.generate_registration(app, user_sql)
    session['fido2_challenge'] = challenge
    
    return render_template("main_page_module/user_profile/fido2_reg.html", json_opt=json_opt,
                           user_sql=user_sql, challenge=challenge)


@main_page_module.route('/fido2_save_registration', methods=['POST'])
@access_required(UserRole.ADMIN)
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
    

@main_page_module.route('/fibo2_delete', methods=['POST'])
@access_required(UserRole.ADMIN)
def user_delete_fibo2():
    cred_id_bs64 = request.form["cred_id_bs64"]
    fido2_cred = UserM.get_fido2(cred_id_bs64)
    
    user_id = fido2_cred["user_id"]
    
    if fido2_cred is None:
        flash('No credentials with this ID found to delete.', 'error')
        
        return redirect(url_for("main_page_module.index"))  
    
    UserM.delete_one_fido2(cred_id_bs64)
    
    flash(f'Credential successfully deleted.', 'success')  
    
    return redirect(url_for("main_page_module.user_profile_edit"))      
