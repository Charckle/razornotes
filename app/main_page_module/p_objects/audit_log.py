from flask import session
from app.main_page_module.models import AuditLM



class AuditLog:
    @staticmethod
    def create(change_):
        user_id = session['user_id']
        
        AuditLM.add(user_id, change_)
    
    # DB_upgrade
    @staticmethod
    def add_task_basics():
        #check if table exists
        if not check_column_exists("notes", "note_type"):
            db = DB()
            sql_command = f"""
            ALTER TABLE `notes` ADD `note_type` INT NOT NULL DEFAULT 0; """
            db.q_exe_segment(sql_command, ())
            
            db.finish_()
            
            return True
        else:
            return False

    # DB_upgrade
    @staticmethod
    def create_template_table():
        if not check_table_exists("notes_tmpl"):
            db = DB()
            sql_command = f"""
            CREATE TABLE notes_tmpl (
            `id` INT NOT NULL AUTO_INCREMENT,
            `name` VARCHAR(100) NOT NULL,
            `text_` TEXT NOT NULL,
            PRIMARY KEY (`id`)
            )"""
            db.q_exe_segment(sql_command, ())
            
            db.finish_()
    
    # DB_upgrade
    @staticmethod
    def create_note_files_table():
        if not check_table_exists("notes_files"):
            db = DB()
            sql_command = f"""
            CREATE TABLE notes_files (
            `note_id` INT NOT NULL,
            `file_name` VARCHAR(100) NOT NULL,
            `file_id_name` VARCHAR(50) NOT NULL,
            FOREIGN KEY (note_id) REFERENCES notes(id)
            )"""
            db.q_exe_segment(sql_command, ())
            
            db.finish_()            