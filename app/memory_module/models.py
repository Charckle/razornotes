from datetime import datetime

# Import password / encryption helper tools
#from werkzeug import check_password_hash, generate_password_hash
from werkzeug.security import generate_password_hash, check_password_hash

from datab import DB

class Mem_:
    def session():
        db = DB()
        sql_command = f"""SELECT mi.id, answer, question, mi.comment_, m_group_id, has_birthday, birthday, failure_count 
        FROM m_items as mi
        LEFT JOIN m_groups ON mi.m_group_id = m_groups.id 
        WHERE m_groups.show_ = 1;"""

        return db.q_r_all(sql_command, ()) 
    
    # Mem_
    def get_all():
        db = DB()
        sql_command = f"""SELECT mi.id, answer, question, mi.comment_, m_group_id,
        m_groups.name as mg_name, has_birthday, birthday, failure_count
        FROM m_items as mi
        LEFT JOIN m_groups ON mi.m_group_id = m_groups.id  ;"""
        
        return db.q_r_all(sql_command, ()) 
    
    # Mem_
    def get_all_from(g_id):
        db = DB()
        sql_command = f"""SELECT mi.id, answer, question, mi.comment_, m_group_id,
        m_groups.name as mg_name, has_birthday, birthday, failure_count
        FROM m_items as mi
        LEFT JOIN m_groups ON mi.m_group_id = m_groups.id 
        WHERE m_groups.id = %s;"""

        return db.q_r_all(sql_command, (g_id,)) 
    
    # Mem_
    def get_one(clovek_id):
        db = DB()
        sql_command = f"""SELECT id, answer, question, comment_, m_group_id, has_birthday, birthday, failure_count 
        FROM m_items 
        WHERE id = %s;"""

        return db.q_r_one(sql_command, (clovek_id, ))       
    
    # Mem_
    def create(answer, question, comment_, m_group_id, has_birthday=0, birthday=None):
        db = DB()
        sql_command = f"""INSERT INTO m_items (answer, question, comment_, m_group_id, has_birthday, birthday)
            VALUES (%s, %s, %s, %s, %s, %s);"""
        
        return db.q_exe_new(sql_command, (answer, question, comment_, m_group_id, has_birthday, birthday))
    
    # Mem_
    def delete(item_id):
        db = DB()
        sql_command = f"""DELETE FROM m_items WHERE id = %s;"""

        db.q_exe(sql_command, (item_id,))
    
    # Mem_
    def edit_one(id_, answer, question, comment_, m_group_id, has_birthday=0, birthday=None):
        db = DB()
        sql_command = f"""UPDATE m_items 
        SET answer = %s, question = %s,
        comment_ = %s, m_group_id = %s, has_birthday = %s, birthday = %s
        WHERE id = %s"""

        db.q_exe(sql_command, (answer, question, comment_, m_group_id, has_birthday, birthday, id_)) 
    
    # Mem_
    @staticmethod
    def increment_failure_count(item_ids):
        """Increment failure_count for multiple items"""
        if not item_ids:
            return
        
        db = DB()
        placeholders = ','.join(['%s'] * len(item_ids))
        sql_command = f"""UPDATE m_items 
        SET failure_count = failure_count + 1
        WHERE id IN ({placeholders})"""
        
        db.q_exe(sql_command, tuple(item_ids))
    
    # Mem_
    @staticmethod
    def get_birthdays_for_month(month):
        """Get all birthdays for a specific month (1-12)"""
        db = DB()
        sql_command = f"""SELECT mi.id, mi.answer, mi.question, mi.comment_, mi.birthday, mi.m_group_id,
        m_groups.name as mg_name
        FROM m_items as mi
        LEFT JOIN m_groups ON mi.m_group_id = m_groups.id
        WHERE mi.has_birthday = 1 
        AND mi.birthday IS NOT NULL
        AND MONTH(mi.birthday) = %s
        ORDER BY DAY(mi.birthday)"""
        
        return db.q_r_all(sql_command, (month,))
    
    # Mem_
    @staticmethod
    def get_birthdays_for_today():
        """Get all birthdays for today"""
        from datetime import date
        today = date.today()
        db = DB()
        sql_command = f"""SELECT mi.id, mi.answer, mi.question, mi.comment_, mi.birthday, mi.m_group_id,
        m_groups.name as mg_name
        FROM m_items as mi
        LEFT JOIN m_groups ON mi.m_group_id = m_groups.id
        WHERE mi.has_birthday = 1 
        AND mi.birthday IS NOT NULL
        AND MONTH(mi.birthday) = %s
        AND DAY(mi.birthday) = %s
        ORDER BY mi.answer"""
        
        return db.q_r_all(sql_command, (today.month, today.day))

class Grp_:
    def get_all():
        db = DB()
        sql_command = f"""SELECT id, name, comment_, show_  
        FROM m_groups;"""
        
        return db.q_r_all(sql_command, ())
    
    # Grp_
    def get_one(grp_id):
        db = DB()
        sql_command = f"""SELECT id, name, comment_, show_ 
        FROM m_groups 
        WHERE id = %s;"""
        
        return db.q_r_one(sql_command, (grp_id,))
    
    # Grp_
    def get_one_by_name(grp_name):
        db = DB()
        sql_command = f"""SELECT  id, name, comment_, show_ 
        FROM m_groups 
        WHERE name = %s;"""
        
        return db.q_r_one(sql_command, (grp_name, ))    
    
    # Grp_
    def create(grp_name, comment_, show_):
        db = DB()
        sql_command = f"""INSERT INTO m_groups (name, comment_, show_)
            VALUES (%s, %s, %s);"""
        
        return db.q_exe_new(sql_command, (grp_name, comment_, show_))    
    
    # Grp_
    def edit_one(id_, grp_name, comment_, show_):
        db = DB()
        sql_command = f"""UPDATE m_groups 
        SET name = %s, comment_ = %s,
        show_ = %s 
        WHERE id = %s"""
        
        db.q_exe(sql_command, (grp_name, comment_, show_, id_,))      
    
    # Grp_
    def delete(id_):
        db = DB()
        sql_command = f"""DELETE FROM m_groups WHERE id = %s;"""
        
        db.q_exe(sql_command, (id_,))     
