from datab import DB, check_column_exists, check_table_exists
from app.main_page_module.models import Notes


class DB_upgrade:
    @staticmethod
    def update_database():
        DB_upgrade.add_task_basics()
        DB_upgrade.create_template_table()
        DB_upgrade.create_note_files_table()
        DB_upgrade.add_memory_birthday_fields()
        DB_upgrade.add_memory_failure_tracking()
    
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
    
    # DB_upgrade
    @staticmethod
    def add_memory_birthday_fields():
        if not check_column_exists("m_items", "has_birthday"):
            db = DB()
            sql_command = f"""
            ALTER TABLE `m_items` ADD `has_birthday` INT NOT NULL DEFAULT 0;"""
            db.q_exe_segment(sql_command, ())
            db.finish_()
        
        if not check_column_exists("m_items", "birthday"):
            db = DB()
            sql_command = f"""
            ALTER TABLE `m_items` ADD `birthday` DATE NULL;"""
            db.q_exe_segment(sql_command, ())
            db.finish_()
    
    # DB_upgrade
    @staticmethod
    def add_memory_failure_tracking():
        if not check_column_exists("m_items", "failure_count"):
            db = DB()
            sql_command = f"""
            ALTER TABLE `m_items` ADD `failure_count` INT NOT NULL DEFAULT 0;"""
            db.q_exe_segment(sql_command, ())
            db.finish_()            