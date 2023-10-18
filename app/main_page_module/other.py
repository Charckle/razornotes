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
    
    # Randoms    
    @staticmethod    
    def format_file_size(file_size):
        file_size = file_size / 1024
        if file_size < 1024:
            return f"{file_size} KB"
        else:
            return f"{file_size / 1024:.2f} MB"    
        
    
    # Randoms    
    @staticmethod    
    def verify_folder(folder_path):
        if not os.path.exists(folder_path):
            # If it doesn't exist, create it
            os.makedirs(folder_path)
    
    # Randoms
    @staticmethod    
    def get_version():    
        with open('VERSION') as f:
            lines = f.readlines()
        
        return lines[0]    

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
    
    
    
 