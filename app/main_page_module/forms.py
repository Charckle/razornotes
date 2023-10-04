# Import Form and RecaptchaField (optional)
from flask_wtf import FlaskForm # , RecaptchaField
from flask_wtf.file import FileField, FileAllowed, FileRequired

# Import Form elements such as TextField and BooleanField (optional)
from wtforms import BooleanField, StringField, TextAreaField, SelectField, PasswordField, HiddenField, SubmitField, validators # BooleanField

# Import Form validators
from wtforms.validators import Email, EqualTo, ValidationError

from app.main_page_module.models import UserM
from app.main_page_module.other import NotesS

#email verification
import re
import os.path
    
    
class Note(FlaskForm):
    id = HiddenField('id', [validators.InputRequired(message='Dont fiddle around with the code!')])
    
    title = StringField('Title of new note', [validators.InputRequired(message='You need to specify a title'),
                                             validators.Length(max=128)])    

    note_text = TextAreaField('Entry Text', [validators.InputRequired(message='You need to fill something.')])
    
    relevant = BooleanField('Show in index')
    
    pinned = BooleanField('Pin the note?')
    
    note_type = SelectField(u'Type of note', choices=[(str(0), "Note"), (str(1), "Task")])
    
    file_u = FileField("File to upload")   
    
    submit = SubmitField('Submit changes')
    
    
class Note_tmpl(FlaskForm):
    id = HiddenField('id', [validators.InputRequired(message='Dont fiddle around with the code!')])
    
    name = StringField('Template title', [validators.InputRequired(message='You need to specify a title'),
                                             validators.Length(max=100)])    

    text_ = TextAreaField('Enter Template', [validators.InputRequired(message='You need to fill something.')])
    
    
    submit = SubmitField('Submit changes')    


class Login(FlaskForm):
    username_or_email = StringField('Username or Email', [validators.InputRequired(message='Forgot your email address?')])
    password = PasswordField('Password', [validators.InputRequired(message='Must provide a password.')])
    remember = BooleanField()
    
    submit = SubmitField('Login')

class UserF(FlaskForm):

    id = HiddenField('id', [validators.InputRequired(message='Dont fiddle around with the code!')])
    name   = StringField('Identification name', [validators.InputRequired(message='We need a name for the user.')])
    
    username   = StringField('Username', [validators.InputRequired(message='We need a username for your account.')])
    email    = StringField('Email', [validators.InputRequired(message='We need an email for your account.')])
    password  = PasswordField('Password')    
    password_2 = PasswordField('Repeat password', [EqualTo('password', message='Passwords must match')])
    
    status = SelectField(u'User Status?', [
        validators.InputRequired(message='You need to specify the status')], 
                         choices=[('0', 'Disabled'), ('1', 'Enabled')])      
    
    api_key = StringField('Api Key', [validators.InputRequired(message='We need an api key.'),
                                      validators.Length(max=20)])    
    
    submit = SubmitField('Submit changes')
    
    def validate_email(self, email):
        
        regex = '^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$'
        
        #check if it is a real email
        if(re.search(regex,email.data)):  
            #if it is, check if there is another user with the same email
        
            if len(UserM.check_email(email.data)) > 1:
                raise ValidationError('Please use a different email address.')     
        
        else:  
            raise ValidationError('Please use a valid email address.')            
    

class Register(FlaskForm):
    username   = StringField('Username', [validators.InputRequired(message='We need a username for your account.')])
    email    = StringField('Email', [validators.InputRequired(message='We need an email for your account.')])
    password  = PasswordField('Password')    
    password_2 = PasswordField('Repeat password', [validators.InputRequired(), EqualTo('password', message='Passwords must match')])
    
    submit = SubmitField('Register')
    
    #When you add any methods that match the pattern validate_<field_name>, WTForms takes those as custom validators and invokes them in addition to the stock validators
    def validate_username(self, username):
            if UserM.check_username(username.data) is not False:
                raise ValidationError('Please use a different username.')
    
    def validate_email(self, email):
        
        regex = '^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$'
        
        #check if it is a real email
        if(re.search(regex,email.data)):  
            #if it is, check if there is another user with the same email
        
            if UserM.check_username(email.data) is not False:
                raise ValidationError('Please use a different email address.')     
        
        else:  
            raise ValidationError('Please use a valid email address.')          
    

class Tag(FlaskForm):
    name = StringField('Name of Tag', [validators.InputRequired(message='You need to specify a name'),
                                             validators.Length(max=50)])
    
    color = SelectField(u"Tag Color", [validators.InputRequired(message="You need to fill something")], choices=[])
    
    submit = SubmitField("Add Tag")

    def __init__(self, *args, **kwargs):
        super(TagForm, self).__init__(*args, **kwargs)
        self.color.choices = [(str(key), str(value)) for key, value in NotesS.list_tag_colors().items()]
    
    
class ImportNotes(FlaskForm):
    import_file = FileField("Note's .RNXF file", validators=[
        FileAllowed(["rnxf", "RNXF"], "Only RNXF allowed!")])         

    submit = SubmitField('Submit File')
 
form_dicts = {"Note": Note,
              "Login": Login,
              "User": UserF,
              "Register": Register,
              "Tag": Tag,
              "ImportNotes": ImportNotes,
              "Note_tmpl": Note_tmpl
              } 