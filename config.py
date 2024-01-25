import sys
from os import environ 


class Config(object):
    # environmental variables are set in .env, for development purpoises
    DEBUG = False
    TESTING = False
    SECRET_KEY = environ.get('SECRET_KEY', "B\xb2?.\xdf\x9f\xa7m\xf8\x8a%,\xf7\xc4\xfa\x91")
    
    JWT_SECRET_KEY = environ.get('JWT_SECRET_KEY', "sdf34tasdft34")
    
    UPLOAD_FOLDER = environ.get('UPLOAD_FOLDER', "files_u")
    
    SESSION_COOKIE_SECURE = True
    

    # Application threads. A common general assumption is
    # using 2 per available processor cores - to handle
    # incoming requests using one and performing background
    # operations using the other.
    THREADS_PER_PAGE = 2
    
    # Enable protection agains *Cross-site Request Forgery (CSRF)*
    # CSRF_ENABLED = environ.get('CSRF_ENABLED', False)
    
    # App name
    APP_NAME = environ.get('APP_NAME', "Razor Notes")
    # Enable modules
    MODULE_MEMORY = environ.get('MODULE_MEMORY', None)
    MODULE_SECRETS= environ.get('MODULE_SECRETS', None)
    
    # Icon color to differentiate between different instances in use
    ICON_COLOR = environ.get('ICON_COLOR', "RED")
    
    # webauthn settings
    RP_ID = environ.get('RP_ID', "localhost")
    RP_NAME = environ.get('RP_NAME', "Razor Notes zubin")
    RP_PORT = environ.get('RP_PORT', ":5000")
    RP_PROTOCOL = environ.get('RP_PROTOCOL', "http")
    
    # ip and network restriction
    IP_RESTRICTION = environ.get('IP_RESTRICTION', "1")
    IPS_NETWORKS = environ.get('IPS_NETWORKS', "127.0.0.1,127.0.0.0/8")

    
class ProductionConfig(Config):
    TESTING = False

class DevelopmentConfig(Config):
    DEBUG = True

    SESSION_COOKIE_SECURE = False

class TestingConfig(Config):
    TESTING = True

    SESSION_COOKIE_SECURE = False