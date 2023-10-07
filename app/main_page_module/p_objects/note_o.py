from app import app
import os

from app.main_page_module.models import Notes, Tag
from app.main_page_module.other import Randoms

class N_obj:
    path_u = app.config['UPLOAD_FOLDER']
    
    n_id = None
    qrry = None
    files = None
    tags = None
    
    def __init__(self, n_id):
        self.n_id = n_id
        
        self.qrry = Notes.get_one(n_id)
        self.files = Notes.get_all_files_of(n_id)
        self.tags = Tag.get_all_of_note(n_id)
        note_type = self.type_()
        
    

    def delete(self):
        for file_u in self.files:
            self.file_delete(file_u)
            Notes.delete_one_file(file_u["file_id_name"])
            
        for tag in self.tags:
            Tag.remove_note_tag(self.n_id, tag["t_id"])
            
        Notes.delete_one(self.n_id)
        
    
    def type_(self):    
        colors = {0: ["Note","warning"],
                    1: ["Task", "dark"]}
        
        return colors[self.qrry["note_type"]]    
    
    def save_file_to_note(self, file_u):
        file_name, file_id_name = self.save_file(file_u)
        Notes.connect_file(self.n_id, file_name, file_id_name)
    
    def save_file(self, file_u):    
        filename = Randoms.get_valid_filename(file_u.filename)[:100]
        
        while True:
            file_id_name = Randoms.generate_file_id()
            file_path = f'{self.path_u}/{file_id_name}'
            if not os.path.exists(file_path):
                break
        
        Randoms.verify_folder(self.path_u)
        file_u.save(os.path.join(self.path_u, file_id_name))
        
        return filename, file_id_name    
    
    
    def file_size(self, file_u):
        file_id_name = file_u["file_id_name"]
        file_path = f"{self.path_u}/{file_id_name}"
        
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
        
            return Randoms.format_file_size(file_size)
        
        else:
            return "Missing"
    
    def file_delete(self, file_u):
        file_id_name = file_u["file_id_name"]
        file_path = f"{self.path_u}/{file_id_name}"
        
        if os.path.exists(file_path):
            os.remove(file_path)    