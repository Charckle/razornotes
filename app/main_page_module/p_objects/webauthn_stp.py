from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
    base64url_to_bytes,
)
from webauthn.helpers.cose import COSEAlgorithmIdentifier
from webauthn.helpers.structs import (
    PYDANTIC_V2,
    AttestationConveyancePreference,
    AuthenticatorAttachment,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement
)
from webauthn.helpers.generate_challenge import generate_challenge

from flask import  request

import secrets
import os
import base64
import json
import random
import string



def generate_registration(app, user_sql):
    #challenge = generate_challenge()
    challenge = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    challenge = challenge.encode('utf-8')

    #print(challenge)
    registration_options = generate_registration_options(
        rp_id=app.config['RP_ID'] ,
        rp_name=app.config['RP_NAME'],
        user_id=str(user_sql["id"]),
        user_name=user_sql["username"],
        user_display_name=user_sql["name"],
        attestation=AttestationConveyancePreference.NONE,
        authenticator_selection=AuthenticatorSelectionCriteria(
            authenticator_attachment=AuthenticatorAttachment.CROSS_PLATFORM,
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.REQUIRED
        ),
        challenge=challenge,
        exclude_credentials=[
            PublicKeyCredentialDescriptor(id=challenge),
        ],
        supported_pub_key_algs=[COSEAlgorithmIdentifier.ECDSA_SHA_256,
                                COSEAlgorithmIdentifier.RSASSA_PSS_SHA_256,
                                COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256],
        timeout=12000,
    )
    
    json_opt = options_to_json(registration_options)
    #print(json_opt)
    
    return json_opt, challenge

def verify_registration(app, json_data, challenge):   
    #print(json_data["id"])
    #print(base64url_to_bytes(json_data["id"]))
    #print(base64url_to_bytes(json_data["rawId"]))
    #print(json.dumps(json_data))
    
    #json_data["rawId"] = base64url_to_bytes(json_data["rawId"])
    protocol = request.scheme
    #hostname = request.host.split(":")[0]
    port = request.host.split(":")[-1]    

    
    registration_verification = verify_registration_response(
        credential = json_data,
        require_user_verification=True,
        supported_pub_key_algs=[COSEAlgorithmIdentifier.ECDSA_SHA_256],
        expected_challenge = challenge,
        expected_rp_id = app.config['RP_ID'],
        expected_origin = f"{app.config['RP_PROTOCOL']}://{app.config['RP_ID']}{app.config['RP_PORT']}"
    )
    
    #print(registration_verification.model_dump_json(indent=2))

    assert registration_verification.credential_id == base64url_to_bytes(json_data["id"]) 
    
    cred_dict = json.loads(registration_verification.model_dump_json())
    credential_id = cred_dict["credential_id"]
    credential_public_key = cred_dict["credential_public_key"]

    return credential_id, credential_public_key


def generate_verification(app):
    #challenge = generate_challenge()
    challenge = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    challenge = challenge.encode('utf-8')
    
    #id_ = "1Yl0tbIdTCg7rtUqbgEmfX4PgttjARrJ_EuBNWRT7qY"
    #id_bytes = base64url_to_bytes(id_)
    
    
    authentication_options = generate_authentication_options(
        rp_id=app.config['RP_ID'] ,
        challenge=challenge,
        timeout=12000,
        allow_credentials=[],
        user_verification=UserVerificationRequirement.REQUIRED,
    )    

    
    json_opt = options_to_json(authentication_options)
    #print(json_opt)
    
    return json_opt, challenge

def verify_verification(app, json_data, challenge, public_key_bs64):   
    #print(json_data["id"])
    #print(base64url_to_bytes(json_data["id"]))
    #print(base64url_to_bytes(json_data["rawId"]))
    #print(json.dumps(json_data))
    
    #json_data["rawId"] = base64url_to_bytes(json_data["rawId"])
    #public_key = "pQECAyYgASFYIEs7W-Afvk1GRfqiFlyot_b7NHb01gzxrcREm1TmShKrIlggNjYju1cYD6eJLZ1hpHE2z9PuKtXhpDu_YDWmJElF70g"
    public_key_bytes = base64url_to_bytes(public_key_bs64)
    
    authentication_verification = verify_authentication_response(
        credential = json_data,
        expected_challenge = challenge,
        expected_rp_id = app.config['RP_ID'],
        expected_origin = f"{app.config['RP_PROTOCOL']}://{app.config['RP_ID']}{app.config['RP_PORT']}",
        credential_current_sign_count=0,
        require_user_verification=True,
        credential_public_key=public_key_bytes
    )
    
    #print(authentication_verification.model_dump_json(indent=2))
    user_id_bs64 = json_data["response"]["userHandle"]
    user_id_b = base64url_to_bytes(user_id_bs64)
    user_id = user_id_b.decode("utf-8")
        
    return user_id
    
    