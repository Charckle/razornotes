import json

# Import flask dependencies
from flask import Blueprint, request, render_template, \
                  flash, g, session, redirect, url_for, jsonify, send_file, Response, abort

from wrappers import login_required
from app import app, secrets
from app.pylavor import Pylavor
import datetime
import base64

secrets_module = Blueprint('secrets_module', __name__, url_prefix='/secrets')


@app.context_processor
def inject_to_every_page():
    
    return dict(Pylavor=Pylavor, app=app)


@secrets_module.route('/<secret_id>', methods=['GET'])
def secrets_one(secret_id):
    
    if (secret_id in secrets):
        secret = secrets[secret_id]
        
        if secret["onetime_view"] == 1:
            del secrets[secret_id]
        
        return render_template("secrets_module/secrets_one.html", secret=secret)
    
    else:
        return render_template('404.html'), 404
   

@secrets_module.route('/all', methods=['GET'])
@login_required
def secrets_all():

    return render_template("secrets_module/secrets_all.html", secrets=secrets, request=request)

@secrets_module.route('/create', methods=['POST'])
@login_required
def secrets_create():    
    # Check if the request contains JSON data
    if request.is_json:
        try:
            json_data = request.get_json()
            #print(type(json_data))
            #print(json_data["response"])
            secret_name = str(json_data['secret_name']) 
            secret_string = str(json_data['secret_string']) 
            expiry_date = json_data["expiry_date"]
            onetime_view = json_data["onetime_view"]
            
            max_length = 100
            
            if len(secret_string) > max_length:            
                raise ValueError(f"The string is too long. Maximum allowed length is {max_length}.")
            
            base64_secret = base64.b64encode(secret_string.encode("utf-8")).decode("utf-8")
            secret_id = generate_unique_string(secrets=secrets)
            
            expiry_date = get_expiry_date(expiry_date)
            
            secrets[secret_id] = {"secret_name": secret_name,
                                      "secret": secret_string,
                                      "expiry_date": expiry_date,
                                      "onetime_view": onetime_view,
                                      "base64_secret": base64_secret}
            
            return jsonify({"message": "Creation successfull!",
                            "secret": secrets[secret_id] }), 200
        
        except ValueError as e:
            app.logger.error(e)
            return jsonify({f"message": "{e}"}), 500
        
        except Exception as e:
            app.logger.error(e)
            return jsonify({"message": "Error on the server side"}), 500

    else:
        return jsonify({"message": "Invalid JSON data"}), 400


@secrets_module.route('/delete/<secret_id>', methods=['DELETE'])
@login_required
def secrets_delete(secret_id):    
    if (secret_id in secrets):
        del secrets[secret_id]
            
        return jsonify({"message": "Deletion successfull!"}), 200

    else:
        return jsonify({"message": "Secret does not exist"}), 400


@secrets_module.route('/view_secret/<secret_id>', methods=['GET'])
@login_required
def view_secret(secret_id):    
    if (secret_id in secrets):
        secret =  secrets[secret_id]
        base64_secret = secret["base64_secret"]
            
        return jsonify({"message": base64_secret}), 200

    else:
        return jsonify({"message": "Secret does not exist"}), 400

from datetime import datetime, timedelta

def get_expiry_date(expiry_date_var: str) -> datetime:
    expiry_date_var = int(expiry_date_var)
    
    if expiry_date_var == 2:
        current_time = datetime.now()
        expiry_date = current_time + timedelta(hours=8)
        
    elif expiry_date_var == 3:
        current_time = datetime.now()
        expiry_date = current_time + timedelta(days=1)
        
    elif expiry_date_var == 4:
        current_time = datetime.now()
        expiry_date = current_time + timedelta(days=7)
        
    elif expiry_date_var == 5:
        current_time = datetime.now()
        expiry_date = current_time + timedelta(days=30)
        
    else:
        current_time = datetime.now()
        expiry_date = current_time + timedelta(hours=1)
        
    
    return expiry_date

import random
import string

def generate_unique_string(secrets, length=9):
    while True:
        # Generate a string of random letters and numbers
        random_chars = string.ascii_letters + string.digits
        unique_string = ''.join(random.choice(random_chars) for _ in range(length))
        
        if (unique_string not in secrets):
            break
    
    return unique_string