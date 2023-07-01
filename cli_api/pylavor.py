import re
import json
import ctypes, os
import logging
from os.path import exists
import string
import random


from unidecode import unidecode

class Pylavor:

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
    def json_write(location, filename, dictio, sanitation=True):
        
        location = location.strip()

        if sanitation == True:
            filename = Pylavor.get_valid_filename(filename)
        
        location_filename = location + "/" + filename
        logging.debug(f"Saving to: {location_filename}")

        with open(f'{location_filename}', 'w') as outfile:
            json.dump(dictio, outfile)

    @staticmethod
    def json_read(location, filename):
        
        location_filename = location + "/" + filename
        logging.debug(f"Reading from: {location_filename}")

        with open(f'{location_filename}') as json_file:
            data = json.load(json_file)
            
            return data
    @staticmethod
    def isAdmin():
        try:
            is_admin = (os.getuid() == 0)
        except AttributeError:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        return is_admin

    @staticmethod
    def check_file_exists(filenameLocation):
        if exists(filenameLocation):
            return True
        else:
            return False
        """
        try:
            with open(filenameLocation) as f:
                return True
        except IOError:
            return False
        """
    @staticmethod
    def gen_passwd(len_):
        choices_list = string.ascii_letters + string.digits + "?!"
        return "".join(random.choices(choices_list, k=len_))
        
