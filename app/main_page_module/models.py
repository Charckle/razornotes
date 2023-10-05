from datetime import datetime, date

# Import password / encryption helper tools
#from werkzeug import check_password_hash, generate_password_hash
from werkzeug.security import generate_password_hash, check_password_hash
import hashlib

from datab import DB

class UserM:
    @staticmethod
    def create(name, username, email, password, status, api_key):
        db = DB()
        
        password_hash = generate_password_hash(password)
        
        created_date = date.today()
        
        sql_command = f"""INSERT INTO users (name, username, email, password, status, api_key, created_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s);"""
    
        return db.q_exe_new(sql_command, (name, username, email, password_hash, status, api_key, created_date))
    
    # UserM
    @staticmethod
    def check_username(username):
        db = DB()
        sql_command = f"SELECT id, username, password FROM users WHERE (%s = username);"
        
        results = db.q_r_one(sql_command, (username,))  
        
        #is a user is found, returns its ID
        if results is not None:
            return results
        
        return False
    
    # UserM
    @staticmethod
    def id_from_username(username):
        db = DB()
        sql_command = f"SELECT id FROM users WHERE (%s = username);"
        
        return db.q_r_one(sql_command, (username,))  
    
    # UserM
    @staticmethod
    def check_email(email):
        db = DB()
        sql_command = f"SELECT id, email FROM users WHERE (%s = email);"

        return db.q_r_all(sql_command, (email,))
    
    # UserM
    @staticmethod
    def login_check(username_or_email, password):
        db = DB()
        sql_command = f"SELECT id, username, email, password FROM users WHERE (%s = username) OR (%s = email);"
        
        results = db.q_r_one(sql_command, (username_or_email, username_or_email))  
        
        #is a user is found, returns its ID
        if results is not None:
            if check_password_hash(results["password"], password):
                
                return results
        
        return False
    
    # UserM
    @staticmethod
    def get_all():
        db = DB()
        sql_command = f"SELECT id, name, username FROM users;"

        return db.q_r_all(sql_command, ())  
    
    # UserM
    @staticmethod
    def get_all_w_status(status):
        db = DB()
        sql_command = f"""SELECT id, name, username 
        FROM users
        WHERE status = %s;"""

        return db.q_r_all(sql_command, (status,))      
    
    # UserM
    @staticmethod
    def get_one(user_id):
        db = DB()
        sql_command = f"""SELECT id, name, username, email, password, status, created_date, api_key 
        FROM users WHERE id = %s;"""
        
        return db.q_r_one(sql_command, (user_id, ))
    
    # UserM
    @staticmethod
    def check_api_access(api_key):
        db = DB()
        sql_command = f"""SELECT id, name, username, email, password, status, created_date, api_key 
        FROM users WHERE api_key = %s AND status = 1;"""
        
        return db.q_r_one(sql_command, (api_key,))      
    
    # UserM
    @staticmethod
    def delete_one(user_id):
        db = DB()
        sql_command = f"DELETE FROM users WHERE id = %s;"
        
        db.q_exe(sql_command, (user_id,))
    
    # UserM
    @staticmethod
    def change_one(user_id, username, name, email, api_key, status):
        db = DB()
      
        sql_command = f"""UPDATE users 
        SET name = %s, username = %s,
        email = %s, api_key = %s,
        status = %s
        WHERE id = %s"""
        
        db.q_exe(sql_command, (name, username, email, api_key, status, user_id,))
    
    # UserM
    @staticmethod
    def change_passw(user_id, password):
        db = DB()
        password_hash = generate_password_hash(password)

        sql_command = f"""UPDATE users 
        SET password = %s
        WHERE id = %s"""
        
        db.q_exe(sql_command, (password_hash, user_id,))        


class Notes:
    @staticmethod
    def create(title, text, note_type):
        db = DB()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        v_hash = hashlib.md5(text.encode()).hexdigest()
        
        sql_command = f"""INSERT INTO notes (title, note_type, text, v_hash, date_mod)
                      VALUES (%s, %s, %s, %s, %s);"""
        
        return db.q_exe_new(sql_command, (title, note_type,  text, v_hash, timestamp))

    # Notes
    @staticmethod
    def get_one(note_id):
        db = DB()
        sql_command = f"""SELECT id, title, note_type, text, date_mod, active, relevant, pinned
        FROM notes WHERE id = %s;"""

        return db.q_r_one(sql_command, (note_id, ))

    
    # Notes
    @staticmethod
    def get_one_w_hash(v_hash):
        db = DB()
        sql_command = f"""SELECT id, title, note_type, text, date_mod, active, relevant, pinned, v_hash
        FROM notes WHERE v_hash = %s;"""

        return db.q_r_one(sql_command, (v_hash, ))    
    
    # Notes
    @staticmethod
    def get_all():
        db = DB()
        sql_command = f"""SELECT id, title, text, note_type, date_mod, active, relevant, pinned, v_hash
        FROM notes"""

        return db.q_r_all(sql_command, ())        
    
    # Notes
    @staticmethod    
    def get_all_active():
        db = DB()
        sql_command = f"""SELECT id, title, note_type, text, active, relevant, pinned, v_hash 
        FROM notes WHERE active = 1;"""
        
        return db.q_r_all(sql_command, ())      
    
    # Notes
    @staticmethod    
    def get_all_active_for_index():
        db = DB()
        sql_command = f"""SELECT id, title, note_type, LEFT(notes.text, 50) as text FROM notes 
        WHERE notes.relevant = 1 AND notes.active = 1 AND notes.pinned = 0
        ORDER BY notes.date_mod DESC LIMIT 15 ;"""
        
        return db.q_r_all(sql_command, ())  
    
    # Notes
    @staticmethod    
    def get_all_active_index_pinned():
        db = DB()
        sql_command = f"""SELECT id, title, note_type, LEFT(notes.text, 50) as text FROM notes 
        WHERE active = 1 AND notes.relevant = 1 AND notes.pinned = 1 
        ORDER BY date_mod DESC;"""
        
        return db.q_r_all(sql_command, ())  
    
    # Notes
    @staticmethod    
    def get_all_trashed():
        db = DB()
        sql_command = f"""SELECT id, title, note_type, date_mod, active, relevant, pinned
        FROM notes WHERE active = 0;"""

        return db.q_r_all(sql_command, ())
    
    # Notes
    @staticmethod    
    def delete_all_trashed():
        db = DB()
        sql_command = f"""DELETE FROM notes WHERE active = 0;"""

        return db.q_r_all(sql_command, ())      
        
    
    # Notes
    @staticmethod    
    def delete_one(note_id):
        db = DB()
        sql_command = f"DELETE FROM notes WHERE id = %s;"
        
        db.q_exe(sql_command, (note_id, ))
    
    # Notes
    @staticmethod    
    def trash_one(note_id):
        db = DB()
        sql_command = f"UPDATE notes SET active = False WHERE id = %s;"

        db.q_exe(sql_command, (note_id, ))
    
    # Notes
    @staticmethod    
    def reactivate_one(note_id):
        db = DB()
        sql_command = f"UPDATE notes SET active = True WHERE id = %s;"
        
        db.q_exe(sql_command, (note_id, ))
    
    # Notes
    @staticmethod    
    def set_hash(note_id, v_hash):
        db = DB()
        sql_command = f"UPDATE notes SET v_hash = %s WHERE id = %s;"
        
        db.q_exe(sql_command, (v_hash, note_id, ))        
    
    # Notes
    @staticmethod    
    def update_one(note_id, title, note_type, text, relevant, pinned):
        db = DB()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        v_hash = hashlib.md5(text.encode()).hexdigest()
        
        sql_command = f"""UPDATE notes 
        SET title = %s, note_type = %s, text = %s, relevant = %s, pinned = %s, v_hash = %s, date_mod = %s 
        WHERE id = %s;"""
        
        db.q_exe(sql_command, (title, note_type, text, relevant, pinned, v_hash, timestamp, note_id))
    
    # Notes
    @staticmethod    
    def edit_api(note_id, text):
        db = DB()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        v_hash = hashlib.md5(text.encode()).hexdigest()
        
        sql_command = f"""UPDATE notes 
        SET text = %s, v_hash = %s, date_mod = %s 
        WHERE id = %s;"""
        
        db.q_exe(sql_command, (text, v_hash, timestamp, note_id))
    
    # Notes
    def connect_file(note_id, file_name, file_id_name):
        db = DB()
        sql_command = f"""INSERT INTO notes_files (note_id, file_name, file_id_name)
                      VALUES (%s, %s, %s);"""  
        
        db.q_exe(sql_command, (note_id, file_name, file_id_name))
    
    # Notes
    @staticmethod    
    def get_all_files_of(note_id):
        db = DB()
        sql_command = f"""SELECT note_id, file_name, file_id_name
        FROM notes_files WHERE note_id = %s;"""

        return db.q_r_all(sql_command, (note_id,))
    
    # Notes
    @staticmethod
    def get_one_file(file_id_name):
        db = DB()
        sql_command = f"""SELECT note_id, file_name, file_id_name
        FROM notes_files WHERE file_id_name = %s;"""

        return db.q_r_one(sql_command, (file_id_name, ))
    
    # Notes
    @staticmethod    
    def delete_one_file(file_id_name):
        db = DB()
        sql_command = f"""DELETE FROM notes_files WHERE file_id_name = %s;"""
        
        db.q_exe(sql_command, (file_id_name, ))    


class Tmpl:
    def new(name, text_):
        db = DB()
        sql_command = f"""INSERT INTO notes_tmpl (name, text_)
                      VALUES (%s, %s);"""                
            
        return db.q_exe_new(sql_command, (name, text_))
    
    # Tmpl
    def get_all():
        db = DB()
        sql_command = f"""SELECT id, name FROM notes_tmpl;"""  

        return db.q_r_all(sql_command, ())
    
    # Tmpl
    def get_one(tmpl_id):
        db = DB()
        sql_command = f"""SELECT id, name, text_ FROM notes_tmpl WHERE id = %s ;"""
        
        return db.q_r_one(sql_command, (tmpl_id,))
    
    # Tmpl
    @staticmethod    
    def update_one(tmpl_id, name, text_):
        db = DB()
        
        sql_command = f"""UPDATE notes_tmpl 
        SET name = %s, text_ = %s
        WHERE id = %s;"""
        
        db.q_exe(sql_command, (name, text_, tmpl_id))    
    
    # Tmpl
    @staticmethod    
    def delete_one(tmpl_id):
        db = DB()
        sql_command = f"""DELETE FROM notes_tmpl WHERE id = %s;"""
        
        db.q_exe(sql_command, (tmpl_id, ))        

class Tag:
    def add(tagName, tagColor):
        db = DB()
        sql_command = f"""INSERT INTO tags (name, color)
                      VALUES (%s, %s);"""                
            
        return db.q_exe_new(sql_command, (tagName, tagColor))
    
    # Tag
    def get_one(tag_id):
        db = DB()
        sql_command = f"""SELECT id, name, color FROM tags WHERE id = %s ;"""
        
        return db.q_r_one(sql_command, (tag_id, ))
    
    # Tag
    def connect_tag(note_id, tag_id):
        db = DB()
        sql_command = f"""INSERT INTO note_tags (note_id, tag_id)
                      VALUES (%s, %s);"""  
        
        db.q_exe(sql_command, (note_id, tag_id))
    
    # Tag
    def get_all():
        db = DB()
        sql_command = f"SELECT id, name, color FROM tags;"    

        return db.q_r_all(sql_command, ())  
    
    # Tag
    def get_all_of_note(note_id):
        db = DB()
        sql_command = f"""SELECT tags.name as tag_name, tags.color as tag_color, note_tags.tag_id as t_id
        FROM note_tags 
        LEFT JOIN notes ON note_tags.note_id = notes.id 
        LEFT JOIN tags ON note_tags.tag_id = tags.id 
        WHERE note_tags.note_id = %s;"""

        return db.q_r_all(sql_command, (note_id,))  
    
    # Tag
    def notes_get_all_of_tag(tag_id):
        db = DB()
        sql_command = f"""SELECT notes.id as n_id, notes.title as n_title, LEFT(notes.text, 30) as n_text
        FROM notes 
        LEFT JOIN note_tags ON note_tags.note_id = notes.id 
        WHERE note_tags.tag_id = %s ;"""
        
        return  db.q_r_all(sql_command, (tag_id, )) 
    
    # Tag
    def note_tag_get_one(note_id, tag_id):
        db = DB()
        sql_command = f"SELECT note_id, tag_id FROM note_tags WHERE note_id = %s AND tag_id = %s;"
        
        return db.q_r_one(sql_command, (note_id, tag_id, ))
    
    # Tag
    def note_tag_all():
        db = DB()
        sql_command = f"""SELECT note_id, tag_id  FROM note_tags; """
        
        return  db.q_r_all(sql_command, ())     
    
    # Tag
    def remove_note_tag(note_id, tag_id):
        db = DB()
        #delete the tag connection
        sql_command = f"DELETE FROM note_tags WHERE note_id = %s AND tag_id = %s;"        
        db.q_exe_segment(sql_command, (note_id, tag_id))
        
        #check if the tag is connected to anything anymore
        db1 = DB()
        sql_command = f"SELECT note_id, tag_id FROM note_tags WHERE tag_id = %s;"
        results = db1.q_r_all(sql_command, (tag_id,))
        
        #if not, delete it
        if (len(results) == 0):
            sql_command = f"DELETE FROM tags WHERE id = %s;"
            
            sql_command = f"DELETE FROM note_tags WHERE note_id = %s AND tag_id = %s;"        
            db.q_exe_segment(sql_command, (tag_id, ))
        
        db.finish_()