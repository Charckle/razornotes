from requests import get, post, delete, put

import sys, tempfile, os
from subprocess import call
import hashlib
import sys, tempfile, os
from subprocess import call

from gears import Gears


configs_ = {}

class Notes:
    @staticmethod
    def search_(search_term):        
        headers = {'x-access-tokens': configs_["api_key"]}
        
        try:
            server_address = configs_['server_addr']
            server_port = configs_['server_port']            
            r = post(f"{server_address}:{server_port}/api/search", data = {'key': search_term}, headers=headers)
        except:
            print("----")
            print("Server unreachable. ¯\(ツ)/¯")
            print("----")
            quit()
        
        if r.status_code != 200:
            print(r.text)
        
        else:
            results_ = r.json()
            print("----")
            print(f"Found {len(results_.keys())} hits")
            notes = [int(key) for key, value in results_.items()]
            print("----")
            for key, value in results_.items():
                print(f"{key}: {value[0]}")
            
            print("----")
            
            
            while True:
                selected_note = input("Select the note: ")
                if selected_note != "":
                    try:
                        selected_note = int(selected_note)
                    except:
                        print("Wrong format inserted, bye!")
                        quit()
                    
                    if selected_note in notes:
                        Notes.get_(selected_note)
                else:
                    break

    
    @staticmethod
    def get_(n_id):
        headers = {'x-access-tokens': configs_["api_key"]}
        server_address = configs_['server_addr']
        server_port = configs_['server_port']
        r = get(f"{server_address}:{server_port}/api/note/{n_id}", headers=headers)
        
        if r.status_code != 200:
            print(r.text)        
        else:
            note_ = r.json()
            n_id = note_["id"]
            n_title = note_["title"]
            n_text = note_["text"]
            
            EDITOR = os.environ.get('EDITOR', 'vim')
            initial_message = n_text
            
            with tempfile.NamedTemporaryFile(suffix=".tmp") as tf:
                v_hash_old = hashlib.md5(initial_message.encode()).hexdigest()
                
                tf.write(bytes(initial_message, 'utf-8'))
                tf.flush()
                call([EDITOR, tf.name])
              
                # after it closes, you can read what is inserted and save it
                tf.seek(0)
                edited_message = tf.read()
                v_hash_new = hashlib.md5(edited_message).hexdigest()
                
                # check for changes
                if v_hash_old != v_hash_new:
                    print("----")
                    print("Changes found, saving to server")
                    #print(edited_message)
                    data_ = {"note_id": n_id, "note_text": edited_message}                  
                    r = put(f"{server_address}:{server_port}/api/note/{n_id}", data = data_, headers=headers)
                    print("Saved")
                    print("----")

if __name__ == "__main__":
    configs_ = Gears.load_config()
    
    Gears.razor_logo()
    while True:
        search_term = input("Razor Search: ")
        
        if search_term == "":
            print("cannot search nothing. Bye!")
            quit()
        
        Notes.search_(search_term)
