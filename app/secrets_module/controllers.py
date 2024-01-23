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
    
    return dict(Pylavor=Pylavor)


@secrets_module.route('/<secret_id>', methods=['GET'])
def secrets_one(secret_id):
    
    if (secret_id in secrets):
        return render_template("secrets_module/secrets_one.html", secrets=secrets)
    
    else:
        return render_template('404.html'), 404
   

@secrets_module.route('/all', methods=['GET'])
@login_required
def secrets_all():

    return render_template("secrets_module/secrets_all.html", secrets=secrets)

@secrets_module.route('/create', methods=['POST'])
@login_required
def secrets_create():    
    # Check if the request contains JSON data
    if request.is_json:
        try:
            json_data = request.get_json()
            #print(json_data["response"])
            secret_name = str(session['secret_name']) 
            secret_string = str(session['secret_string']) 
            expiry_date = json_data["expiry_date"]
            onetime_view = json_data["onetime_view"]
            
            max_length = 100
            
            if len(secret_string) > max_length:            
                raise ValueError(f"The string is too long. Maximum allowed length is {max_length}.")
            
            base64_secret = base64.b64encode(secret_string.encode("utf-8")).decode("utf-8")
            
            secrets[base64_secret] = {"secret_name": secret_name,
                                      "secret": secret_string,
                                      "expiry_date": expiry_date,
                                      "onetime_view": onetime_view,
                                      "base64_secret": base64_secret}
            
            return jsonify({"message": "Creation successfull!",
                            "secret": secrets[base64_secret] }), 200
        
        except ValueError as e:
            app.logger.info(e)
            return jsonify({f"message": "{e}"}), 500
        
        except Exception as e:
            app.logger.info(e)
            return jsonify({"message": "Error on the server side"}), 500

    else:
        return jsonify({"message": "Invalid JSON data"}), 400

