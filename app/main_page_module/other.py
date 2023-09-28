from unidecode import unidecode
import re
import os

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
    
    @staticmethod
    def icon_name(config):
        env_color = config['ICON_COLOR']
        favicon_name = f"favicon_{env_color}.ico"
        static_path = "app/static"
        file_path = f"{static_path}/{favicon_name}"
        print(file_path)
        if not os.path.exists(file_path):
            favicon_name = f"favicon_RED.ico"
        
        return favicon_name

class NotesS():
    # NotesS
    @staticmethod
    def list_tag_colors():    
        colors = {0: "Primary",
                    1: "Secondary",
                    2: "Success",
                    3: "Danger",
                    4: "Warning",
                    5: "Info",
                    6: "Light",
                    7: "Dark"}
        
        return colors
    
    # NotesS
    @staticmethod
    def n_types(note_type):    
        colors = {0: ["Note","Warning"],
                    1: ["Task", "Dark"]}
        
        return colors[note_type]
