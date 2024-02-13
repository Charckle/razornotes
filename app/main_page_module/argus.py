import os.path
from whoosh.index import create_in
from whoosh.fields import Schema, TEXT, NUMERIC
from whoosh.index import open_dir
from whoosh.query import *
from whoosh.qparser import QueryParser

class WSearch():
    #def __init__(self, storage_location = "app//main_page_module//data//"):
        
        #self.storage_location = storage_location
        
    def index_create(self, notes):
        #print(notes)
        
        schema = Schema(note_id=NUMERIC(stored=True), note_name=TEXT(stored=True), content=TEXT(stored=True))
        
        if not os.path.exists(".index"):
            os.mkdir(".index")
            

        ix = create_in(".index", schema)
        writer = ix.writer()
        
        
        for f in notes:
            writer.add_document(note_id=u"{}".format(f["id"]),note_name=u"{}".format(f["title"]), content=u"{}".format(f["text"]))                
            
        writer.commit()

    def index_search(self, querystring):
        #print(querystring)
        ix = open_dir(".index")
        
        parser = QueryParser("content", ix.schema)
        myquery = parser.parse(querystring)
        
        file_names = []
        with ix.searcher() as searcher:
            results = searcher.search(myquery)
            # print(f"Found {len(results)} results.")
            for found in results:
                file_names.append([found["note_id"], found["note_name"], found.highlights("content")])
                #print(found.highlights("content"))
            
            return file_names
        
    def index_api_search(self, querystring):
        #print(querystring)
        ix = open_dir(".index")
        
        parser = QueryParser("content", ix.schema)
        myquery = parser.parse(querystring)
        
        file_names = []
        with ix.searcher() as searcher:
            results = searcher.search(myquery)
            #print(f"Found {len(results)} results.")
            for found in results:
                file_names.append([found["note_id"], found["note_name"], found.highlights("content")])
                #print(found.highlights("content"))
            
            return file_names        