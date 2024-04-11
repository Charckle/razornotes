import re
import json
import ctypes, os
import logging
from os.path import exists
import string
import random
import pickle
from datetime import datetime
from typing import Union, Optional
import bleach


from unidecode import unidecode

class Pylavor:
    @staticmethod
    def zerodivision(n, d):
        n = float(n)
        d = float(d)
        
        return n / d if d else 0    

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

    # Pylavor
    def pickle_write(location, filename, data_, sanitation=True):    
        location = location.strip()
        
        if sanitation == True:
            filename = get_valid_filename(filename)
        
        location_filename = location + "/" + filename
        logging.debug(f"Saving to: {location_filename}")
        
        with open(f'{location_filename}', 'wb') as file:
            pickle.dump(data_, file)
    
    # Pylavor
    def pickle_read(location, filename):
        
        location_filename = location + "/" + filename
        logging.debug(f"Reading from: {location_filename}")
    
        with open(f'{location_filename}', 'rb') as file:
            return pickle.load(file)

    # Pylavor
    @staticmethod
    def json_write(location, filename, dictio, sanitation=True):
        
        location = location.strip()

        if sanitation == True:
            filename = Pylavor.get_valid_filename(filename)
        
        location_filename = location + "/" + filename
        logging.debug(f"Saving to: {location_filename}")

        with open(f'{location_filename}', 'w') as outfile:
            json.dump(dictio, outfile)

    # Pylavor
    @staticmethod
    def json_read(location, filename):
        
        location_filename = location + "/" + filename
        logging.debug(f"Reading from: {location_filename}")

        with open(f'{location_filename}') as json_file:
            data = json.load(json_file)
            
            return data
    
    # Pylavor
    @staticmethod
    def isAdmin():
        try:
            is_admin = (os.getuid() == 0)
        except AttributeError:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        return is_admin

    # Pylavor
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
    
    # Pylavor
    @staticmethod
    def gen_passwd(len_):
        choices_list = string.ascii_letters + string.digits + "?!"
        return "".join(random.choices(choices_list, k=len_))
    
    # Pylavor
    @staticmethod
    def perc_no_zeros_totext(value_x):
        if value_x >= 1:
            new_value = str("{:.2f}".format(value_x * 100)).strip("0").strip(".")
            
            if new_value == "":
                new_value = "0"
        else:
            new_value = str("{:.2f}".format(value_x * 100))
        
        new_value = new_value.replace(".", ",")
        
        if new_value == "01":
            print(str(value_x*100))
            print(new_value)
        
        return new_value    

    # Pylavor
    @staticmethod
    def english_to_slo_num(number):
        try:
            with_dots = "{:,.2f}".format(float(number))
            
            return with_dots.replace(".", "*").replace(",", ".").replace("*", ",")
        except:
            return "ERROR"
    
    # Pylavor
    @staticmethod
    def english_to_slo_num_nodec(number):    
        with_dots = "{:,.2f}".format(float(number))
        with_dots = with_dots.replace(".", "*").replace(",", ".").replace("*", ",") 
        with_dots = with_dots.split(",")
        
        return with_dots[0]  

    # Pylavor
    @staticmethod
    def english_to_slo_num_4(number):    
        with_dots = "{:,.4f}".format(float(number))
        
        return with_dots.replace(".", "*").replace(",", ".").replace("*", ",")
    
    # takes string or date and returns a date in string
    @staticmethod
    def date_to_string(date_: Union[datetime, str]) -> str:
        if date_ == None:
            return "None"
        if not isinstance(date_, str):
            date_ = date_.strftime('%d.%m.%Y')
        else:
            d_arr = date_.split("-")
            date_ = f"{d_arr[2]}.{d_arr[1]}.{d_arr[0]}"
        
        return date_
    
    # Pylavor
    @staticmethod
    def datetime_to_string(date_n_time) -> str:
        if not isinstance(date_n_time, str):
            date_n_time = date_n_time.strftime('%d.%m.%Y - %H:%M:%S')
        else:
            date_n_time = "uff, something got broke :'("
        
        return date_n_time
    
    # Pylavor
    @staticmethod
    def list_months():    
        months = {1: "January",
                    2: "February",
                    3: "March",
                    4: "April",
                    5: "May",
                    6: "June",
                    7: "July",
                    8: "August",
                    9: "September",
                    10: "October",
                    11: "November",
                    12: "December"}
        
        return months    
    
    # Pylavor
    @staticmethod        
    def clean_rich_text(input_text):
        # Define allowed tags and attributes
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'br', 'hr']
        allowed_attributes = {'a': ['href', 'title']}
    
        # Use bleach to clean the input text
        cleaned_text = bleach.clean(input_text, tags=allowed_tags, attributes=allowed_attributes)
        
        return cleaned_text        