from flask import session
from app.main_page_module.models import AuditLM



class AuditLog:
    @staticmethod
    def create(change_):
        user_id = session['user_id']
        
        AuditLM.add(user_id, change_)
