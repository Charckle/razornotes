from functools import wraps
from flask import session, redirect, url_for, request, flash
from app.main_page_module.models import UserM, Notes, Tag, GroupsAccessM

from app.main_page_module.other import UserRole

# access decorator
# add id's of groups. if any id matches the id of the users group, access is granted
def access_required(groups_=None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            groups = None
            if 'user_id' in session:
                user_id = session['user_id']
                user = UserM.get_one(user_id)
                
                if not user:
                    return redirect(url_for("main_page_module.logout"))
                
                disabled = user["status"]

                if disabled == 1:
                    if groups_ is None:
                        return f(*args, **kwargs)
                    
                    groups = [UserRole.ADMIN]
                    if isinstance(groups_, UserRole):
                        groups.append(groups_)
                    else:
                        groups += groups_
                    
                    # Check if user is part of any of the specified groups
                    user_groups = [UserRole(i["group_a_id"]) for i in GroupsAccessM.get_access_all_of_user(user_id)]
                    if any(group_id in user_groups for group_id in groups):
                        return f(*args, **kwargs)
                    else:
                        flash("You don't have access to this page.", "error")
                        return redirect(url_for("main_page_module.index"))

            session.clear()
            requestUrl = request.url
            requested_url = "/".join(requestUrl.split("/")[3:])
            session['requested_url'] = "/" + requested_url

            flash("Please login to access the site.", "error")

            return redirect(url_for("main_page_module.login"))

        return wrapper
    return decorator


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