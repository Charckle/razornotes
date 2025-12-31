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
    
    WTF_CSRF_ENABLED = environ.get('WTF_CSRF_ENABLED', 'True').lower() in ['true', '1', 't', 'y', 'yes']

    

    # Application threads. A common general assumption is
    # using 2 per available processor cores - to handle
    # incoming requests using one and performing background
    # operations using the other.
    THREADS_PER_PAGE = 2
    
    # Enable protection agains *Cross-site Request Forgery (CSRF)*
    # CSRF_ENABLED = environ.get('CSRF_ENABLED', False)
    
    # App name
    APP_NAME = environ.get('APP_NAME', "Razor Notes")
    APP_LOGGING = environ.get('APP_LOGGING', "DEBUG")
    # Enable modules
    #MODULE_MEMORY = environ.get('MODULE_MEMORY', None)
    MODULE_MEMORY = environ.get('MODULE_MEMORY', 'False').lower() in ['true', '1', 't', 'y', 'yes']
    #MODULE_SECRETS= environ.get('MODULE_SECRETS', None)
    MODULE_SECRETS = environ.get('MODULE_SECRETS', 'False').lower() in ['true', '1', 't', 'y', 'yes']
    
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

    # Website URL for email links
    WEBSITE_URL = environ.get('WEBSITE_URL', '')
    
    # Email configuration for memory reminders
    EMAIL_SMTP_HOST = environ.get('EMAIL_SMTP_HOST', '')
    EMAIL_SMTP_PORT = int(environ.get('EMAIL_SMTP_PORT', '465'))
    EMAIL_SMTP_USER = environ.get('EMAIL_SMTP_USER', '')
    EMAIL_SMTP_PASSWORD = environ.get('EMAIL_SMTP_PASSWORD', '')
    EMAIL_FROM_ADDRESS = environ.get('EMAIL_FROM_ADDRESS', '')

    
class ProductionConfig(Config):
    TESTING = False

class DevelopmentConfig(Config):
    DEBUG = True

    SESSION_COOKIE_SECURE = False

class TestingConfig(Config):
    TESTING = True

    SESSION_COOKIE_SECURE = False