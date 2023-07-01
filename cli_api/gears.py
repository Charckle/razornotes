from pylavor import Pylavor
import os
from os.path import exists
from os.path import abspath
from inspect import getsourcefile
import pathlib
#import jwt

class Gears:
    @staticmethod
    def load_config():
        confs_file = "razor.conf"
        path_ = abspath(getsourcefile(lambda:0))
        path_ = os.path.dirname(abspath(getsourcefile(lambda:0)))
        
        if exists(f"{path_}/{confs_file}"):
            return Pylavor.json_read(path_, confs_file)
        else:
            print("----")
            print("Config file not found, please follow the steps to configure it:")
            print("----")
            server_addr = input("Razor Notes server address: ")
            api_key = input("Api key: ")
            
            #salt = Pylavor.gen_passwd(14)
            #token = "bang3w4svdffg32tz"#jwt.encode({"status": "OK", "saltz": salt}, api_encrypt_key, algorithm="HS256")
            
            configs_ ={"server_addr": server_addr,
                       "api_key": api_key}
            
            Pylavor.json_write(path_, confs_file, configs_)
            
            print("----")
            print("Config file saved. If you want to change it in the future, you can find it:")
            print(f"{path_}/{confs_file}")
            print("----")            
            
            return configs_
    
    @staticmethod
    def razor_logo():
        # Created on this page: https://patorjk.com/software/taag/
        # be carefull to skip the escaping of strings, with "r"
        
        print(" ___                     ")
        print("| _ \ __ _  ___ ___  _ _ ")
        print("|   // _` ||_ // _ \| '_|")
        print(r'|_|_\\__,_|/__|\___/|_|  ')
        print("                         ")
        