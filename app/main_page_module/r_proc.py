from app.main_page_module.models import UserM, Notes, Tag
import json
import hashlib

class Import_Ex:
    
    @staticmethod
    def export():
        active_notes = Notes.get_all_active()
        data_ = {}
        data_["notes"] = {n["id"]: {"title": n["title"],
                               "text": n["text"],
                               "pinned": n["pinned"],
                               "hash": n["v_hash"]} for n in active_notes}
        
        data_["tags"] = {t["id"]: {"name": t["name"],
                               "color": t["color"]} for t in Tag.get_all()}    
        
        data_["tag_note"] = {}
        for n in active_notes:
            note_id = n["id"]
            all_tags = [t["t_id"] for t in Tag.get_all_of_note(note_id)]
            if len(all_tags) > 0:
                data_["tag_note"] [note_id] = all_tags
        
        return data_
    
    # Import_Ex
    @staticmethod
    def import_(raw_json_f):
        ditc_ = json.load(raw_json_f)
        
        notes = ditc_["notes"]
        tags = ditc_["tags"]
        tag_note = ditc_["tag_note"]
        
        return Import_Ex.process_notes(notes, tags, tag_note)
    
    # Import_Ex
    @staticmethod
    def process_notes(notes, tags, tag_note):
        to_process = len(notes)
        added = 0

        for id_, note in notes.items():
            old_id = id_
            v_hash = note["hash"]
            existing_note = Notes.get_one_w_hash(v_hash)
            
            if existing_note is None:
                note_id = Notes.create(note["title"], note["text"], v_hash)
                added += 1
                
                if old_id in tag_note:
                    for tag_id in tag_note[old_id]:
                        tag_id = str(tag_id)
                        tagName = tags[tag_id]["name"]
                        tagColor = tags[tag_id]["color"]
                        new_tag_id = Tag.add(tagName, tagColor)
                        Tag.connect_tag(note_id, new_tag_id)
        
        return {"to_process": to_process, "added": added}

class HL_proc:
    @staticmethod
    def create_hashes_():
        all_notes = Notes.get_all()
        
        for no in all_notes:
            note_id = no["id"]
            v_hash = hashlib.md5(no["text"].encode()).hexdigest()
            Notes.set_hash(note_id, v_hash)