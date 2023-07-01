from flask_wtf import FlaskForm # , RecaptchaField
from flask_wtf.file import FileField, FileAllowed, FileRequired


# Import Form elements such as TextField and BooleanField (optional)
from wtforms import HiddenField, StringField, PasswordField, TextAreaField, SelectField, \
     SubmitField, validators# BooleanField

# Import Form validators
from wtforms.validators import DataRequired, Email, EqualTo

from app.memory_module.models import Grp_, Mem_


class Memory(FlaskForm):
    id = HiddenField('hidden ID', [validators.InputRequired(message='dont mess with this'),
                                             validators.Length(max=4)])
    
    answer = StringField('Answer', [DataRequired(message='The Answer'),
                                          validators.Length(max=30)])
    
    question = StringField('Question', [DataRequired(message='The Question'),
                                          validators.Length(max=150)])
    
    comment_ = TextAreaField('Comment')
    
    groups = []
    
    m_group_id = SelectField(u'Choose a group.', [validators.InputRequired(message='Specify the Group')], 
                              choices=groups) 

    submit = SubmitField('Submit')
    
    
    def __init__(self, *args, **kwargs):
        super(Memory, self).__init__(*args, **kwargs)
        self.m_group_id.choices = [(str(i["id"]), i["name"]) for i in Grp_.get_all()]
        
    
    
class Group(FlaskForm):
    id = HiddenField('hidden ID', [validators.InputRequired(message='dont mess with this'),
                                             validators.Length(max=4)])
    
    name = StringField('Group Name', [DataRequired(message='Group Name.'),
                                          validators.Length(max=30)])
    
    comment_ = StringField('Comment', [DataRequired(message='Group Comment'),
                                          validators.Length(max=150)])
    
    stanje = [('1', 'Yes'), ('0', 'No'), ]
    
    show_ = SelectField(u'Prikaz med igro?', [validators.InputRequired(message='Specify the Group')], 
                              choices=stanje) 
          

    submit = SubmitField('Submit')


class ImportMemories(FlaskForm):
    import_file = FileField("Memories .PFXF file", validators=[
        FileAllowed(["pfxf", "PFXF"], "Only PFXF allowed!")])         

    submit = SubmitField('Submit File')
 
f_d = {"Memory": Memory,
              "Group": Group,
              "ImportMemories": ImportMemories
              } 