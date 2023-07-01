from functools import wraps
from flask import session, redirect, url_for, request, flash
from app.main_page_module.models import UserM, Notes, Tag

#login decorator
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if ('user_id' in session):
            user_access = UserM.get_one(session["user_id"])["status"]
            if user_access != 0:
                return f(*args, **kwargs)

        session.clear()
        requestUrl = request.url
        requested_url = "/".join(requestUrl.split("/")[3:])
        session['requested_url'] = "/" + requested_url
        
        flash("Please login to access the site.", "error")
        
        return redirect(url_for("main_page_module.login"))
    
    return wrapper