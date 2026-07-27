from app.main_page_module.models import Notes, Tag
from app.main_page_module.other import Randoms
from app.main_page_module.argus import WSearch
import json
import hashlib


class Import_Ex:

    @staticmethod
    def export():
        active_notes = Notes.get_all_active()
        data_ = {
            "version": Randoms.get_version().strip(),
            "notes": {
                n["id"]: {
                    "title": n["title"],
                    "text": n["text"],
                    "pinned": n["pinned"],
                    "relevant": n["relevant"],
                    "note_type": n["note_type"],
                    "hash": n["v_hash"],
                }
                for n in active_notes
            },
            "tags": {
                t["id"]: {"name": t["name"], "color": t["color"]}
                for t in Tag.get_all()
            },
            "tag_note": {},
        }

        for n in active_notes:
            note_id = n["id"]
            all_tags = [t["t_id"] for t in Tag.get_all_of_note(note_id)]
            if len(all_tags) > 0:
                data_["tag_note"][note_id] = all_tags

        return data_

    # Import_Ex
    @staticmethod
    def import_(raw_json_f):
        ditc_ = json.load(raw_json_f)

        export_version = ditc_.get("version")
        app_version = Randoms.get_version().strip()
        version_warning = None
        if export_version != app_version:
            version_warning = (
                f"Export version ({export_version or 'unknown'}) differs from "
                f"app version ({app_version}). Import continued anyway."
            )

        notes = ditc_["notes"]
        tags = ditc_["tags"]
        tag_note = ditc_["tag_note"]

        result = Import_Ex.process_notes(notes, tags, tag_note)
        result["version_warning"] = version_warning

        # Rebuild search index so imported notes are searchable
        WSearch().index_create(Notes.get_all_active())

        return result

    # Import_Ex
    @staticmethod
    def _resolve_tag(tag_name, tag_color, tag_cache):
        if tag_name in tag_cache:
            return tag_cache[tag_name]

        existing = Tag.get_by_name(tag_name)
        if existing is not None:
            tag_cache[tag_name] = existing["id"]
            return existing["id"]

        new_tag_id = Tag.add(tag_name, tag_color)
        tag_cache[tag_name] = new_tag_id
        return new_tag_id

    # Import_Ex
    @staticmethod
    def process_notes(notes, tags, tag_note):
        to_process = len(notes)
        added = 0
        tag_cache = {}

        for id_, note in notes.items():
            old_id = str(id_)
            v_hash = note["hash"]
            existing_note = Notes.get_one_w_hash(v_hash)

            if existing_note is None:
                note_id = Notes.create(
                    note["title"],
                    note["text"],
                    note["note_type"],
                    pinned=note["pinned"],
                    relevant=note["relevant"],
                )
                added += 1

                # tag_note keys may be int or str depending on JSON source
                note_tags = tag_note.get(old_id) or tag_note.get(id_)
                if note_tags:
                    for tag_id in note_tags:
                        tag_id = str(tag_id)
                        tag_name = tags[tag_id]["name"]
                        tag_color = tags[tag_id]["color"]
                        local_tag_id = Import_Ex._resolve_tag(
                            tag_name, tag_color, tag_cache
                        )
                        Tag.connect_tag(note_id, local_tag_id)

        return {"to_process": to_process, "added": added}


class HL_proc:
    @staticmethod
    def create_hashes_():
        all_notes = Notes.get_all()

        for no in all_notes:
            note_id = no["id"]
            v_hash = hashlib.md5(no["text"].encode()).hexdigest()
            Notes.set_hash(note_id, v_hash)
