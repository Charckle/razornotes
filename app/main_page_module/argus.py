import os.path
from whoosh import index
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, NUMERIC
from whoosh.query import *
from whoosh.qparser import MultifieldParser #QueryParser

class WSearch():
    #def __init__(self, storage_location = "app//main_page_module//data//"):
        
        #self.storage_location = storage_location
    
    @staticmethod
    def index_exists():
        if not os.path.exists(".index"):
            return False
        else:
            return True
    
        
    def index_create(self, notes):
        #print(notes)
        
        schema = Schema(note_id=NUMERIC(stored=True), note_name=TEXT(stored=True), content=TEXT(stored=True))            

        ix = create_in(".index", schema)
        writer = ix.writer()
        
        
        for f in notes:
            writer.add_document(note_id=u"{}".format(f["id"]),note_name=u"{}".format(f["title"]), content=u"{}".format(f["text"]))                
            
        writer.commit()
        
        
    @staticmethod
    def add_item(note):        
        ix = index.open_dir(".index")   
    
        writer = ix.writer()
        writer.add_document(note_id=u"{}".format(note["id"]),note_name=u"{}".format(note["title"]), content=u"{}".format(note["text"]))
        writer.commit()
        
        
    @staticmethod
    def delete_item(note_id):        
        ix = index.open_dir(".index")   
    
        writer = ix.writer()
        writer.delete_by_term("note_id", u"{}".format(note_id))
        writer.commit()
        
        
    @staticmethod
    def edit_item(note):        
        ix = index.open_dir(".index")   
    
        writer = ix.writer()
        writer.update_document(note_id=u"{}".format(note["id"]),note_name=u"{}".format(note["title"]), content=u"{}".format(note["text"]))
        writer.commit()          


    def index_search(self, querystring):
        ix = open_dir(".index")
        parser = MultifieldParser(["note_name", "content"], ix.schema,
                                  fieldboosts={"note_name": 3.0, "content": 1.0})
        
        # it seems that it does not work like this
        #querystring = f"{querystring}~{mistakes}"
        myquery = parser.parse(querystring)
        
        file_names = []
        with ix.searcher() as searcher:
            results = searcher.search(myquery, limit=30)
            # print(f"Found {len(results)} results.")
            for found in results:
                file_names.append([found["note_id"], found["note_name"], found.highlights("content")])
                #print(found.highlights("content"))
            
            return file_names
        