import MySQLdb
from MySQLdb.cursors import DictCursor
from os import environ 
import logging
from app.pylavor import Pylavor

from datetime import date

sql_host = environ.get('DB_HOST', "127.0.0.1")
sql_user = environ.get('DB_USERNAME', "razornotes")
sql_passwrd = environ.get('DB_PASSWORD', "")
sql_db = environ.get('DB_NAME', "razor_notes")
sql_db_port = int(environ.get('DB_PORT', 3306))

# the class allows you to execute single querries, or segmented ones
# single querries can rollback, if an error accures
# segmented ones are build such, that allows stacking them, and if one fails, all get rolled back

def error_log_(sql, variables):
    logging.error(f"""Error while working on a sql querry, and error accured.
    Querry: {sql}
    Variables: {variables}""")
    
def error_log_segment(sql, variables):
    logging.error(f"""Error while working on a segmented sql querry, and error accured. The changes to the database have been reverses, so no damaghe was done.
    Querry: {sql}
    Variables: {variables}""")    


class DB:
    conn = None
    cursor = None
    successful = True

    def __init__(self):
        self.connect()
        self.cursor = self.conn.cursor()
        
    def connect(self):
        self.conn = MySQLdb.connect(use_unicode = True,
                                    charset = "utf8",
                                    host = sql_host,
                                    user = sql_user,
                                    passwd = sql_passwrd,
                                    db = sql_db,
                                    cursorclass=DictCursor,
                                    port=sql_db_port)
    
    #rollbackable querry segment
    def q_exe_segment_new(self, sql, variables):
        result = None
        try:
            self.cursor.execute(sql, variables)
            result = self.cursor.lastrowid
            #print(self.cursor._executed)
            
        except Exception as e:
            print(e)
            result = "error in querry"
            self.conn.rollback()
            self.successful = False
            error_log_segment(sql, variables)
            self.cursor.close()
            self.conn.close()            
        
        finally:
            return result
        
        
    #rollbackable querry segment
    def q_exe_segment(self, sql, variables):
        try:
            self.cursor.execute(sql, variables)
            #print(cursor._executed)
            
        except Exception as e:
            print(e)
            self.conn.rollback()
            self.successful = False
            error_log_segment(sql, variables)
            self.cursor.close()
            self.conn.close()
    
    #rollbackable querry segment
    def finish_(self):
        if self.conn != None:
            if self.successful == True:
                self.conn.commit()            
            self.cursor.close()
            self.conn.close()
    
    #standalone querry
    def q_exe(self, sql, variables):
        success = True
        try:
            self.cursor.execute(sql, variables)
            #print(self.cursor._executed)
            
        except Exception as e:
            print(e)
            result = "error in querry"
            error_log_(sql, variables)
            success = False
        
        finally:
            if self.conn != None:
                self.conn.commit()            
                self.cursor.close()
                
                return success
            else:
                return False
    
    #standalone querry get index
    def q_exe_new(self, sql, variables):
        result = None
        
        try:
            #print(sql)
            #print(variables)
            self.cursor.execute(sql, variables)
            result = self.cursor.lastrowid
            #print(self.cursor._executed)
            #print(f"result: {result}")
            
            
        except Exception as e:
            print(e)
            result = "error in querry"
            error_log_(sql, variables)
        
        finally:
            if self.conn != None:
                self.conn.commit()            
                self.cursor.close()    

            return result
    
    #standalone querry
    def q_r_one(self, sql, variables):
        result = None
        
        try:       
            self.cursor.execute(sql, variables)
            result = self.cursor.fetchone()
            #print(self.cursor._executed)
            
        except Exception as e:
            print(e)
            result = "error in querry"
            error_log_(sql, variables)
        
        finally:
            if self.conn != None:
                self.conn.commit()            
                self.cursor.close()
            
            return result    
    
    #standalone querry
    def q_r_all(self, sql, variables):
        result = None
        
        try:         
            self.cursor.execute(sql, variables)
            result = self.cursor.fetchall()
            #print(self.cursor._executed)
            
        except Exception as e:
            print(e)
            result = "error in querry"
            error_log_(sql, variables)
        
        finally:
            if self.conn != None:
                self.conn.commit()            
                self.cursor.close()
            
            return result

class DBcreate:
    @staticmethod
    def create_base_tables():
        #check if table exists
        
        db = DB()
        #set the defaults
        sql_command = f"""ALTER DATABASE razor_notes CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci"""
        db.q_exe(sql_command, ())
        
        if not check_table_exists("tags"):
            db = DB()
            sql_command = f"""
            CREATE TABLE `tags` (
            `id` INT NOT NULL AUTO_INCREMENT,
            `name` varchar(50) NOT NULL,
            `color` INT NOT NULL,
            PRIMARY KEY (`id`)
            )
            ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;"""
            db.q_exe(sql_command, ())

        
        if not check_table_exists("users"):
            db = DB()
            sql_command = f"""
            CREATE TABLE `users` (
            `id` INT NOT NULL AUTO_INCREMENT,
            `name` varchar(128) NOT NULL,
            `username` varchar(128) NOT NULL UNIQUE,
            `email` varchar(128) NOT NULL UNIQUE,
            `password` varchar(192) NOT NULL,
            `status` INT NOT NULL DEFAULT 0,
            `created_date` DATE NOT NULL,
            `api_key` varchar(20) NOT NULL,
            PRIMARY KEY (`id`)
            )
            ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;"""
            db.q_exe(sql_command, ())
        
        
        if not check_table_exists("notes"):
            db = DB()
            sql_command = f"""
            CREATE TABLE `notes` (
            `id` INT NOT NULL AUTO_INCREMENT,
            `title` varchar(128) NOT NULL,
            `text` text NOT NULL,
            `v_hash` varchar(32) NOT NULL,
            `pinned` INT DEFAULT 0 ,
            `active` INT DEFAULT 1,
            `relevant` INT DEFAULT 1,
            `date_mod` TIMESTAMP DEFAULT (CURRENT_TIMESTAMP),
            PRIMARY KEY (`id`)
            )
            ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;"""
            db.q_exe(sql_command, ())

        
        if not check_table_exists("note_tags"):
            db = DB()
            sql_command = f"""
            CREATE TABLE `note_tags` (
            `note_id` INT NOT NULL,
            `tag_id` INT NOT NULL,
            PRIMARY KEY (`note_id`,`tag_id`),
            FOREIGN KEY (note_id) REFERENCES notes(id),
            FOREIGN KEY (tag_id) REFERENCES tags(id)
            ) 
            ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;"""
            db.q_exe(sql_command, ())
    
    
    @staticmethod
    def create_base_memory_tables():
        #check if table exists
        
        if not check_table_exists("m_groups"):
            db = DB()
            sql_command = f"""
            CREATE TABLE `m_groups` (
            `id` INT NOT NULL AUTO_INCREMENT,
            `name` varchar(150) NOT NULL,
            `comment_` varchar(250) NOT NULL,
            `show_` INT NOT NULL DEFAULT 1,
            PRIMARY KEY (`id`)
            )
            ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;"""
            db.q_exe(sql_command, ())        
        
        if not check_table_exists("m_items"):
            db = DB()
            sql_command = f"""
            CREATE TABLE `m_items` (
            `id` INT NOT NULL AUTO_INCREMENT,
            `question` varchar(150) NOT NULL,
            `answer` TEXT NOT NULL,
            `comment_` varchar(250) NOT NULL,
            `m_group_id` INT NOT NULL,
            PRIMARY KEY (`id`),
            FOREIGN KEY (m_group_id) REFERENCES m_groups(id)
            )
            ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;"""
            db.q_exe(sql_command, ())
        
        if not check_table_exists("notes_tmpl"):
            db = DB()
            sql_command = f"""
            CREATE TABLE notes_tmpl (
            `id` INT NOT NULL AUTO_INCREMENT,
            `name` VARCHAR(100) NOT NULL,
            `text_` TEXT NOT NULL,
            PRIMARY KEY (`id`)
            )"""            
            db.q_exe(sql_command, ())
        
        if not check_table_exists("notes_files"):
            db = DB()
            sql_command = f"""
            CREATE TABLE notes_files (
            `note_id` INT NOT NULL,
            `file_name` VARCHAR(100) NOT NULL,
            `file_id_name` VARCHAR(50) NOT NULL,
            PRIMARY KEY (`note_id`),
            FOREIGN KEY (note_id) REFERENCES notes(id)
            )"""            
            db.q_exe(sql_command, ())            
   

    @staticmethod
    def create_base_user():
        #check if table exists
        today = date.today()
        db = DB()
        #set the defaults
        # admin
        # banana
        api_key = Pylavor.gen_passwd(20)
        sql_command = f"""INSERT INTO `users` VALUES (1,'admin','admin','','pbkdf2:sha256:260000$vnE6xPAiuRLVweYe$986824300bfc489a4274bcb604cee7eaf9bc77838e4c90ed04f2d38ca6edae7f',1,%s, %s)"""
        db.q_exe(sql_command, (today, api_key))    

    # DBcreate
    @staticmethod
    def create_tables():
        DBcreate.create_base_tables()
        DBcreate.create_base_memory_tables()
    
    # DBcreate
    @staticmethod
    def check_all_db_OK():
        tables_to_exist = ["tags",
                           "users",
                           "notes",
                           "note_tags",
                           "m_items",
                           "m_groups"]
        
        for t in tables_to_exist:
            if not check_table_exists(t):
                DBcreate.create_tables()
                DBcreate.create_base_user()


def check_database_active():
    db = DB()
    sql_command = f"""SELECT 1;"""
    
    result = db.q_r_one(sql_command, ())
    
    if result["1"] == 1:
        return True
    else:
        return False


    
def check_table_exists(table_name):
    db = DB()
    sql_command = f"""
    SELECT EXISTS (
    SELECT  TABLE_NAME
    FROM information_schema.TABLES 
    WHERE 
    TABLE_SCHEMA LIKE %s AND 
        TABLE_TYPE LIKE 'BASE TABLE' AND
        TABLE_NAME = %s
    );"""
    result = db.q_r_one(sql_command, (sql_db, table_name))
    
    if list(result.values())[0] == 0:
        return False
    else:
        return True
    
def check_column_exists(table_name, column_name):
    db = DB()
    sql_command = f"""SELECT * 
    FROM information_schema.COLUMNS 
    WHERE 
        TABLE_SCHEMA = %s 
    AND TABLE_NAME = %s
    AND COLUMN_NAME = %s"""
    result = db.q_r_one(sql_command, (sql_db, table_name, column_name))
    
    if result is None:
        return False
    else:
        return True