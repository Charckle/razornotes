from app.memory_module.models import Mem_, Grp_
import json
import hashlib

class Export_im:
    # Export_im
    @staticmethod
    def import_(raw_json_f):
        ditc_ = json.load(raw_json_f)
        
        people = ditc_["people"]
        groups = ditc_["tags"]
        
        return Export_im.process_memory(people, groups)
    
    # Export_im
    @staticmethod
    def process_memory(people, groups):
        to_process = len(people)
        added = 0
        
        grp_ids = {}
        
       
        for id_, group in groups.items():
            id_ = int(id_)
            grp_name = group["ime_skupine"]
            comment_ = group["opis_skupine"]
            show_ = group["prikaz_s"]
            
            grp = Grp_.get_one_by_name(grp_name)
            
            if grp is None:
                new_grp_id = Grp_.create(grp_name, comment_, show_)
                grp_ids[id_] = new_grp_id
            else:
                grp_ids[id_] = grp["id"]
                
            
        
        
        for id_, person in people.items():
            old_id = id_
            ime = person["ime"]
            priimek = person["priimek"]
            comment_ = person["komentar"]
            question = person["vprasanje"]
            
            m_group_id = grp_ids[person["skupina"]]
            m_group_name = person["ime_skupine"]
            
            answer = f"{ime} {priimek}"
            
            new_id = Mem_.create(answer, question, comment_, m_group_id)
            added += 1
        
        return {"to_process": to_process, "added": added}
