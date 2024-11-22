from app import app
import os
import math

from app.main_page_module.p_objects.audit_log import AuditLog

from app.main_page_module.models import Notes, Tag
from app.main_page_module.other import Randoms
from app.main_page_module.argus import WSearch


class N_obj:
    path_u = "app/" + app.config['UPLOAD_FOLDER']
    
    n_id = None
    qrry = None
    files = None
    tags = None
    type_ = None
    type_clr = None
    
    def __init__(self, n_id):
        self.n_id = n_id
        
        self.qrry = Notes.get_one(n_id)
        self.files = Notes.get_all_files_of(n_id)
        self.tags = Tag.get_all_of_note(n_id)
        self.type_ = self.qrry["note_type"]
        self.type_clr = self.get_type_clr()
    
    # N_obj
    @staticmethod
    def file_type(file_name):
        return os.path.splitext(file_name)[1].strip(".")
    
    # N_obj
    @staticmethod
    def file_is_pdf(file_name):
        return N_obj.file_type(file_name) in ["pdf", "PDF"]
    
    
    # N_obj
    @staticmethod
    def argus_add_note(note_):
        if not WSearch.index_exists():
            N_obj.argus_create_index()
        WSearch.add_item(note_)    
    
    # N_obj
    @staticmethod
    def argus_edit_note(note_):
        if not WSearch.index_exists():
            N_obj.argus_create_index()
        WSearch.edit_item(note_)
        
    # N_obj
    @staticmethod
    def argus_delete_note(note_id):
        if not WSearch.index_exists():
            N_obj.argus_create_index()
        WSearch.delete_item(note_id)        
    
    # N_obj
    @staticmethod
    def argus_create_index():
        #create argus index
        notes = Notes.get_all_active()
        new_index = WSearch()
        new_index.index_create(notes)        
        
    # N_obj
    def delete(self):
        for file_u in self.files:
            self.file_delete(file_u)
            Notes.delete_one_file(file_u["file_id_name"])
            
        for tag in self.tags:
            Tag.remove_note_tag(self.n_id, tag["t_id"])
        
        # remove recently viewed
        Notes.delete_recently_viewed(self.n_id)
            
        AuditLog.create(f"Note Deleted, id: {self.n_id}: {self.qrry['title'][:10]}")        
        
        Notes.delete_one(self.n_id)
        
        N_obj.argus_delete_note(self.n_id)
        
    
    def get_type_clr(self):    
        colors = {0: ["Note","warning"],
                    1: ["Task", "dark"]}
        
        return colors[self.type_]    
    
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
            print(file_path)
            return "Missing"
    
    def file_delete(self, file_u):
        file_id_name = file_u["file_id_name"]
        file_path = f"{self.path_u}/{file_id_name}"
        
        if os.path.exists(file_path):
            os.remove(file_path) 
    
    def similar_notes(self, key_):
        res, user_notes = N_obj.notes_n_index(key_) 
        
        return {r[0]: [r[1], r[2]] for r in res if (int(r[0]) in user_notes) and int(r[0]) != self.n_id}
    
    @staticmethod
    def search(key_):
        res, user_notes = N_obj.notes_n_index(key_) 
        
        return {r[0]: [r[1], r[2]] for r in res if (int(r[0]) in user_notes)}
    
    @staticmethod
    def notes_n_index(key_):
        index_n = WSearch()
        res = index_n.index_search(key_)
        #get IDs of the notes the user can access
        user_notes = [i["id"] for i in Notes.get_all_active()]        
        
        return res, user_notes
    
    @staticmethod
    def notes_viewed(note_id):
        # add the note to the list, and remove all but the last 15 inserts
        if Notes.get_one_viewed(note_id) is None:
            Notes.create_viewed(note_id)
        else:
            Notes.change_viewed(note_id)
        Notes.delete_last_x(15)

    # N_obj
    @staticmethod
    def pagination_all_active(page_display, page_offset):
        #print(page_offset)
        #print(page_display)
        if page_offset < 0:
            page_offset = 0

        notes_len = len(Notes.get_all_active())

        all_pages_len = math.ceil(notes_len / page_display)
        all_pages = range(0, all_pages_len)
        
        previous = page_offset - 1
        
        next_ = page_offset + 1
        
        page = {"previous": previous,
                "current": page_offset,
                "next": next_,
                "all_pages": all_pages,
                "all_pages_len": all_pages_len,
                "page_display": page_display}

        return page