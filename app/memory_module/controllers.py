# Import flask dependencies
from flask import Blueprint, request, render_template, \
                  flash, g, session, redirect, url_for, jsonify, send_file
from app import app

import random
import json
from datetime import date, datetime

from app.memory_module.models import Grp_, Mem_
from app.memory_module.forms import f_d
from app.memory_module.r_proc import Export_im

from wrappers import access_required

# Define the blueprint: 'auth', set its url prefix: app.url/auth
memory_module = Blueprint('memory_module', __name__, url_prefix='/memory/')

def calculate_birthday_info(birthday_date, has_birthday):
    """Calculate age and days until next birthday"""
    if not has_birthday or not birthday_date:
        return None
    
    # Handle different date formats from database
    if isinstance(birthday_date, str):
        birthday_date = datetime.strptime(birthday_date, '%Y-%m-%d').date()
    elif isinstance(birthday_date, datetime):
        birthday_date = birthday_date.date()
    elif not isinstance(birthday_date, date):
        return None
    
    today = date.today()
    age = today.year - birthday_date.year - ((today.month, today.day) < (birthday_date.month, birthday_date.day))
    
    # Calculate next birthday
    next_birthday = date(today.year, birthday_date.month, birthday_date.day)
    if next_birthday < today:
        next_birthday = date(today.year + 1, birthday_date.month, birthday_date.day)
    
    days_until = (next_birthday - today).days
    
    return {
        'age': age,
        'days_until': days_until,
        'birthday_date': birthday_date
    }

@app.context_processor
def inject_to_every_page():
    
    return dict(Grp_=Grp_, Mem_=Mem_, calculate_birthday_info=calculate_birthday_info)

    
# Set the route and accepted methods
@memory_module.route('/', methods=['GET'])
@access_required()
def index():

    return render_template("memory_module/index.html")


@memory_module.route('/game/<group_id>', methods=['GET'])
@access_required()
def game(group_id):
    if group_id == "99999999":
        m_items = list(Mem_.get_all())
        
    else:    
        m_items = list(Mem_.get_all_from(group_id))
        
    random.shuffle(m_items)
    
    m_items = {i["id"]: {"answer": i["answer"], 
                      "question": i["question"], 
                       "comment_": i["comment_"],
                       "m_group_id": i["m_group_id"],
                       "mg_name": i["mg_name"]} for i in m_items[:20]}

    return render_template("memory_module/game.html", m_items=m_items)


@memory_module.route('/m_item_edit/<mi_id>', methods=['GET', 'POST'])
@memory_module.route('/m_item_edit/', methods=['POST'])
@access_required()
def m_item_edit(mi_id=None):
    form = f_d["Memory"]()
    mi_id = mi_id if request.method == 'GET' else form.id.data
    m_item = Mem_.get_one(mi_id)
    
    if m_item is None:
        flash('Item does not exist', 'error')
        
        return redirect(url_for("memory_module.index"))    
    
    if request.method == 'GET':
        # Convert has_birthday (int 0/1) to boolean for form
        has_birthday_bool = bool(m_item.get("has_birthday", 0))
        birthday_date = m_item.get("birthday")

        form.process(id = m_item["id"],
                     answer = m_item["answer"],
                     question = m_item["question"],
                     comment_ = m_item["comment_"],
                     m_group_id = m_item["m_group_id"],
                     has_birthday = has_birthday_bool,
                     birthday = birthday_date)

    if form.validate_on_submit():
        # Convert boolean to int (0/1) for database
        has_birthday_int = 1 if form.has_birthday.data else 0
        # Only save birthday if has_birthday is True
        birthday_date = form.birthday.data if form.has_birthday.data else None
        
        Mem_.edit_one(form.id.data, form.answer.data,
                        form.question.data, form.comment_.data, 
                        form.m_group_id.data, has_birthday_int, birthday_date)        
       
        flash('Item Updated!', 'success')
        
        return redirect(url_for("memory_module.m_item_edit", mi_id=mi_id))

    return render_template("memory_module/m_items/m_item_edit.html", form=form, m_item=m_item)



@memory_module.route('/m_item_new/<g_id>', methods=['GET'])
@memory_module.route('/m_item_new', methods=['POST'])
@access_required()
def m_item_new(g_id=None):
    form = f_d["Memory"]()
    # Verify the sign in form
    if g_id == None:
        g_id = form.m_group_id.data
    else:
        form.process(m_group_id = g_id)
    
    if form.validate_on_submit():
        # Convert boolean to int (0/1) for database
        has_birthday_int = 1 if form.has_birthday.data else 0
        # Only save birthday if has_birthday is True
        birthday_date = form.birthday.data if form.has_birthday.data else None
        
        new_mi_id = Mem_.create(form.answer.data,
                               form.question.data, form.comment_.data, 
                               g_id, has_birthday_int, birthday_date)
        
        flash('Memory added!', 'success')
        
        return redirect(url_for("memory_module.m_item_edit", mi_id=new_mi_id))
    
    for error in form.errors:
        print(error)
    
        flash(f'Invalid Data: {error}', 'error')    
    
    return render_template("memory_module/m_items/m_item_new.html", form=form, g_id=g_id)


@memory_module.route('/m_item_delete/<mi_id>/', methods=['get'])
@access_required()
def m_item_delete(mi_id):
    m_item = Mem_.get_one(mi_id)
    
    if m_item is None:
        flash('Item does not exist', 'error')
        
        return redirect(url_for("memory_module.index"))    
    
    else:
        m_group_id = m_item["m_group_id"]
        Mem_.delete(mi_id)
        flash(f'The Memory {m_item["answer"]} was successfully deleted.', 'success')
        
        return redirect(url_for("memory_module.group_view", g_id=m_group_id))
    
    
@memory_module.route('/group_new', methods=['GET', 'POST'])
@access_required()
def group_new():
    form = f_d["Group"]()
    
    # Verify the sign in form
    if form.validate_on_submit():
       
        new_g_id = Grp_.create(form.name.data, 
                                   form.comment_.data, form.show_.data)
        
        flash('Group successfully added!', 'success')
        
        return redirect(url_for("memory_module.group_edit", g_id=new_g_id))
    
    for error in form.errors:
        print(error)
    
        flash(f'Invalid Data: {error}', 'error')    
    
    return render_template("memory_module/groups/group_new.html", form=form)    

@memory_module.route('/group_all/', methods=['GET'])
@access_required()
def group_all():

    return render_template("memory_module/groups/group_all.html")


@memory_module.route('/group_view/<g_id>', methods=['GET'])
@access_required()
def group_view(g_id):

    return render_template("memory_module/groups/group_view.html", g_id=g_id)


@memory_module.route('/group_edit/<g_id>', methods=['GET', 'POST'])
@memory_module.route('/group_edit/', methods=['POST'])
@access_required()
def group_edit(g_id=None):
    form = f_d["Group"]()
    g_id = g_id if request.method == 'GET' else form.id.data
    group = Grp_.get_one(g_id)
    
    if group is None:
        flash('Group does not exist', 'error')
        
        return redirect(url_for("memory_module.group_all"))
    
    if request.method == 'GET':
        form.process(id = group["id"],
                     name = group["name"],
                     comment_ = group["comment_"],
                     show_ = group["show_"])

    if form.validate_on_submit():
        Grp_.edit_one(g_id, form.name.data, 
                    form.comment_.data, form.show_.data)        
        
        flash("Group eddited!", 'success')
        
        return redirect(url_for("memory_module.group_edit", g_id=g_id))
    
    for error in form.errors:
        print(error)
    
        flash(f'Invalid Data: {error}', 'error')
    
    return render_template("memory_module/groups/group_edit.html", form=form,
                           g_id=g_id)


@memory_module.route('/group_delete/<g_id>/', methods=['get'])
@access_required()
def group_delete(g_id):
    group = Grp_.get_one(g_id)
    
    if not group:
        flash('The Group does not exist.', 'error')
        
        return redirect(url_for("memory_module.group_all"))
    
    else:
        Grp_.delete(g_id)
        flash(f'The Group {group["name"]} was successfully deleted.', 'success')
        
        return redirect(url_for("memory_module.group_all"))


@memory_module.route('/memory_import/', methods=['GET', 'POST'])
@access_required()
def memory_import():    
    form = f_d["ImportMemories"]()
    
    if form.validate_on_submit():
        ditc_ = Export_im.import_(form.import_file.data)
        flash(f"Import holds {ditc_['to_process']} Memories, {ditc_['added']} added.", "success")
        
        return redirect(url_for("memory_module.index"))
    
    for error in form.errors:
        print(error)
        flash(f'Invalid Data: {error}', 'error')    
    
    return render_template("memory_module/memory_import.html", form=form)    