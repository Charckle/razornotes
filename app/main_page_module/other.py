from unidecode import unidecode
import re
import os
import secrets
import string

class Randoms():
    @staticmethod
    def zerodivision(n, d):
        n = float(n)
        d = float(d)
        
        return n / d if d else 0
    
    # Randoms
    #sanitize the code for saving to a file on the OS
    @staticmethod
    def get_valid_filename(s):
    
        """
        Stolen from Django, me thinks?
        Return the given string converted to a string that can be used for a clean
        filename. Remove leading and trailing spaces; convert other spaces to
        underscores; and remove anything that is not an alphanumeric, dash,
        underscore, or dot.
        >>> get_valid_filename("john's portrait in 2004.jpg")
        'johns_portrait_in_2004.jpg'
        """
    
        s = unidecode(str(s).strip().replace(' ', '_'))
    
        return re.sub(r'(?u)[^-\w.]', '', s)
    
    # Randoms
    def generate_file_id(length=15):
        # Define the character set from which to generate the ID
        characters = string.ascii_letters + string.digits  # You can include other characters if needed
        
        # Generate the random ID
        file_id = ''.join(secrets.choice(characters) for i in range(length))
        
        return file_id    
    
    # Randoms
    @staticmethod
    def icon_name(config):
        env_color = config['ICON_COLOR']
        favicon_name = f"favicon_{env_color}.ico"
        static_path = "app/static"
        file_path = f"{static_path}/{favicon_name}"
        
        if not os.path.exists(file_path):
            favicon_name = f"favicon_RED.ico"
        
        return favicon_name

class NotesS():
    # NotesS
    @staticmethod
    def list_tag_colors():    
        colors = {0: "primary",
                    1: "secondary",
                    2: "success",
                    3: "danger",
                    4: "warning",
                    5: "info",
                    6: "light",
                    7: "dark"}
        
        return colors
    
    # NotesS
    @staticmethod
    def n_types(note_type):    
        colors = {0: ["Note","warning"],
                    1: ["Task", "dark"]}
        
        return colors[note_type]
    
    # NotesS
    @staticmethod
    def save_file(app, file_u):    
        filename = Randoms.get_valid_filename(file_u.filename)[:100]
        path_u = app.config['UPLOAD_FOLDER']
        
        while True:
            file_id_name = Randoms.generate_file_id()
            file_path = f'{path_u}/{file_id_name}'
            if not os.path.exists(file_path):
                break
        
        file_u.save(os.path.join(path_u, file_id_name))
        
        return filename, file_id_name

    # NotesS
    def format_file_size(file_size):
        if file_size < 1024:
            return f"{file_size} KB"
        else:
            return f"{file_size / 1024:.2f} MB"
    
    # NotesS
    @staticmethod
    def file_size(path_u, file_u):
        file_id_name = file_u["file_id_name"]
        file_path = f"{path_u}/{file_id_name}"
        
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
        
            return NotesS.format_file_size(file_size)
        
        else:
            return "Missing"
    
    # NotesS
    @staticmethod
    def file_delete(path_u, file_u):
        file_id_name = file_u["file_id_name"]
        file_path = f"{path_u}/{file_id_name}"
        
        if os.path.exists(file_path):
            os.remove(file_path)
 