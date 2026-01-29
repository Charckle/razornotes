# Import flask dependencies
from flask import Blueprint, request, render_template, \
                  flash, g, session, redirect, url_for, jsonify, send_file
from app import app

import random
import json
from itertools import groupby
from datetime import date, datetime

from app.memory_module.models import Grp_, Mem_
from app.memory_module.forms import f_d
from app.memory_module.r_proc import Export_im
from app.memory_module.email_service import EmailService
from app.main_page_module.models import UserM

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
    
    # Filter out items where show_ = 0 (not displayed in game)
    m_items = [item for item in m_items if item.get('show_', 1) == 1]
    
    # Sort by failure_count (descending) - items with more failures come first
    m_items.sort(key=lambda x: x.get('failure_count', 0), reverse=True)
    
    # Group items by failure_count and shuffle within each group
    # This preserves priority while adding randomness for items with same failure_count
    shuffled_items = []
    for failure_count, group_items in groupby(m_items, key=lambda x: x.get('failure_count', 0)):
        group_list = list(group_items)
        random.shuffle(group_list)
        shuffled_items.extend(group_list)
    
    # Take first 20 items (prioritizing those with higher failure_count)
    prioritized = shuffled_items[:20]
    
    m_items = {i["id"]: {"answer": i["answer"], 
                      "question": i["question"], 
                       "comment_": i["comment_"],
                       "m_group_id": i["m_group_id"],
                       "mg_name": i["mg_name"]} for i in prioritized}

    return render_template("memory_module/game.html", m_items=m_items)


@memory_module.route('/game/submit_failures', methods=['POST'])
@access_required()
def submit_failures():
    data = request.get_json()
    failed_ids = data.get('failed_ids', [])
    session_ids = data.get('session_ids', [])
    
    try:
        # Validate that IDs are integers
        failed_ids = [int(id) for id in failed_ids] if failed_ids else []
        session_ids = [int(id) for id in session_ids] if session_ids else []
        
        # Increment failure_count for failed items
        if failed_ids:
            Mem_.increment_failure_count(failed_ids)
        
        # Decrement failure_count for successfully guessed items
        # (items in session but not in failed list)
        if session_ids:
            successful_ids = [id for id in session_ids if id not in failed_ids]
            if successful_ids:
                Mem_.decrement_failure_count(successful_ids)
        
        return jsonify({
            "status": "success", 
            "failed_count": len(failed_ids),
            "successful_count": len(successful_ids) if session_ids else 0
        })
    except (ValueError, TypeError) as e:
        return jsonify({"status": "error", "message": f"Invalid IDs: {str(e)}"}), 400


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
        show_bool = bool(m_item.get("show_", 1))  # Default to 1 (show) if not set

        form.process(id = m_item["id"],
                     answer = m_item["answer"],
                     question = m_item["question"],
                     comment_ = m_item["comment_"],
                     m_group_id = m_item["m_group_id"],
                     has_birthday = has_birthday_bool,
                     birthday = birthday_date,
                     show_ = show_bool)

    if form.validate_on_submit():
        # Convert boolean to int (0/1) for database
        has_birthday_int = 1 if form.has_birthday.data else 0
        show_int = 1 if form.show_.data else 0
        # Only save birthday if has_birthday is True
        birthday_date = form.birthday.data if form.has_birthday.data else None
        
        Mem_.edit_one(form.id.data, form.answer.data,
                        form.question.data, form.comment_.data, 
                        form.m_group_id.data, has_birthday_int, birthday_date, show_int)        
       
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
        # Set show_ to True by default for new items
        form.show_.data = True
    
    if form.validate_on_submit():
        # Convert boolean to int (0/1) for database
        has_birthday_int = 1 if form.has_birthday.data else 0
        show_int = 1 if form.show_.data else 0
        # Only save birthday if has_birthday is True
        birthday_date = form.birthday.data if form.has_birthday.data else None
        
        new_mi_id = Mem_.create(form.answer.data,
                               form.question.data, form.comment_.data, 
                               g_id, has_birthday_int, birthday_date, show_int)
        
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


@memory_module.route('/email_settings/', methods=['GET', 'POST'])
@access_required()
def email_settings():
    """View and test email settings"""
    if request.method == 'POST':
        if 'test_email' in request.form:
            # Test email connection
            success, message = EmailService.test_email_connection()
            if success:
                flash('Email connection test successful!', 'success')
            else:
                flash(f'Email connection test failed: {message}', 'error')
            return redirect(url_for('memory_module.email_settings'))
        
        elif 'send_test_email' in request.form:
            # Send test reminder email to current user
            user_id = session.get('user_id')
            if user_id:
                user = UserM.get_one(user_id)
                if user and user.get('email'):
                    game_url = EmailService.get_game_url()
                    if game_url:
                        success = EmailService.send_reminder_email(
                            user['email'],
                            user['name'],
                            game_url
                        )
                        if success:
                            flash(f'Test reminder email sent to {user["email"]}!', 'success')
                        else:
                            flash('Failed to send test email. Check server logs for details.', 'error')
                    else:
                        flash('No memory groups available to generate game URL.', 'error')
                else:
                    flash('Your user account does not have an email address configured.', 'error')
            else:
                flash('User session not found.', 'error')
            return redirect(url_for('memory_module.email_settings'))
        
        elif 'send_test_monthly_birthday' in request.form:
            # Send test monthly birthday reminder email to current user
            from app.memory_module.models import Mem_
            from datetime import date
            
            user_id = session.get('user_id')
           
            user = UserM.get_one(user_id)
            if user and user.get('email'):
                today = date.today()
                birthdays = Mem_.get_birthdays_for_month(today.month)
                if birthdays:
                    success = EmailService.send_monthly_birthday_reminder(
                        user['email'],
                        user['name'],
                        birthdays
                    )
                    if success:
                        flash(f'Test monthly birthday reminder sent to {user["email"]}!', 'success')
                    else:
                        flash('Failed to send test email. Check server logs for details.', 'error')
                else:
                    flash('No birthdays found for current month.', 'info')
            else:
                flash('Your user account does not have an email address configured.', 'error')
            
            return redirect(url_for('memory_module.email_settings'))
        
        elif 'send_test_daily_birthday' in request.form:
            # Send test daily birthday reminder email to current user
            from app.memory_module.models import Mem_
            
            user_id = session.get('user_id')
            if user_id:
                user = UserM.get_one(user_id)
                if user and user.get('email'):
                    birthdays = Mem_.get_birthdays_for_today()
                    if birthdays:
                        success = EmailService.send_daily_birthday_reminder(
                            user['email'],
                            user['name'],
                            birthdays
                        )
                        if success:
                            flash(f'Test daily birthday reminder sent to {user["email"]}!', 'success')
                        else:
                            flash('Failed to send test email. Check server logs for details.', 'error')
                    else:
                        flash('No birthdays found for today.', 'info')
                else:
                    flash('Your user account does not have an email address configured.', 'error')
            else:
                flash('User session not found.', 'error')
            return redirect(url_for('memory_module.email_settings'))
    
    # Get current user's email for test email
    user_email = None
    user_id = session.get('user_id')
    if user_id:
        user = UserM.get_one(user_id)
        if user:
            user_email = user.get('email')
    
    config = {
        'smtp_host': app.config.get('EMAIL_SMTP_HOST', ''),
        'smtp_port': app.config.get('EMAIL_SMTP_PORT', ''),
        'smtp_user': app.config.get('EMAIL_SMTP_USER', ''),
        'from_address': app.config.get('EMAIL_FROM_ADDRESS', ''),
        'app_name': app.config.get('APP_NAME', 'Razor Notes'),
        'password_set': bool(app.config.get('EMAIL_SMTP_PASSWORD', '')),
        'user_email': user_email
    }
    
    return render_template("memory_module/email_settings.html", config=config)


@memory_module.route('/scores/', methods=['GET'])
@access_required()
def scores():
    """View all memory items with their failure_count scores"""
    # Get all memory items (including hidden) sorted by failure_count (descending)
    m_items = list(Mem_.get_all_admin())
    m_items.sort(key=lambda x: x.get('failure_count', 0), reverse=True)
    
    return render_template("memory_module/scores.html", m_items=m_items)


@memory_module.route('/scores/update', methods=['POST'])
@access_required()
def update_score():
    """Update failure_count for a specific memory item"""
    data = request.get_json()
    item_id = data.get('item_id')
    failure_count = data.get('failure_count')
    
    if item_id is None or failure_count is None:
        return jsonify({"status": "error", "message": "Missing item_id or failure_count"}), 400
    
    try:
        item_id = int(item_id)
        failure_count = int(failure_count)
        
        # Verify item exists
        m_item = Mem_.get_one(item_id)
        if m_item is None:
            return jsonify({"status": "error", "message": "Item not found"}), 404
        
        # Update failure_count
        Mem_.update_failure_count(item_id, failure_count)
        
        return jsonify({
            "status": "success",
            "item_id": item_id,
            "failure_count": failure_count
        })
    except (ValueError, TypeError) as e:
        return jsonify({"status": "error", "message": f"Invalid data: {str(e)}"}), 400


@memory_module.route('/reminder_preferences/', methods=['GET', 'POST'])
@access_required()
def reminder_preferences():
    """User reminder preferences"""
    user_id = session.get('user_id')

    user = UserM.get_one(user_id)
    form = f_d["ReminderPreferences"]()
    
    if request.method == 'GET':
        # Load current preferences
        frequency = user.get('memory_reminder_frequency', 0)
        form.memory_reminder_frequency.data = str(frequency)
    
    if form.validate_on_submit():
        frequency = int(form.memory_reminder_frequency.data)
        UserM.update_reminder_preferences(user_id, frequency)
        flash('Reminder preferences updated!', 'success')
        return redirect(url_for('memory_module.reminder_preferences'))
    
    for error in form.errors:
        flash(f'Invalid Data: {error}', 'error')
    
    return render_template("memory_module/reminder_preferences.html", form=form, user=user)    