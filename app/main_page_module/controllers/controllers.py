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
@main_page_module.route('/login/', methods=['GET', 'POST'])
def login():
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
            
            if ('requested_url' in session):
                requested_url = session['requested_url']
                session['requested_url'] = ""
                
                return redirect(requested_url)            
            
            return redirect(url_for('main_page_module.index'))
    
        flash('Wrong email or password', 'error')

    for field, errors in form.errors.items():
        print(f'Field: {field}')
        for error in errors:
            flash(f'Invalid Data for {field}: {error}', 'error')
        
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
    
