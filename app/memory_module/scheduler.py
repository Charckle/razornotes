from flask_apscheduler import APScheduler
from flask import current_app


def setup_email_reminder_scheduler(scheduler: APScheduler):
    """Setup email reminder scheduler jobs"""
    
    def send_morning_reminders():
        """Send morning reminders at 7:00 AM to users with frequency 1 or 2"""
        from app.memory_module.email_service import EmailService
        from app.main_page_module.models import UserM
        
        with current_app.app_context():
            users = UserM.get_users_for_morning_reminder()
            for user in users:
                if user.get('email'):
                    game_url = EmailService.get_game_url()
                    if game_url:
                        success = EmailService.send_reminder_email(
                            user['email'], 
                            user['name'], 
                            game_url
                        )
                        if success:
                            current_app.logger.info(f"Morning reminder sent to {user['email']}")
                        else:
                            current_app.logger.error(f"Failed to send morning reminder to {user['email']}")
    
    def send_evening_reminders():
        """Send evening reminders at 8:00 PM to users with frequency 2"""
        from app.memory_module.email_service import EmailService
        from app.main_page_module.models import UserM
        
        with current_app.app_context():
            users = UserM.get_users_for_evening_reminder()
            for user in users:
                if user.get('email'):
                    game_url = EmailService.get_game_url()
                    if game_url:
                        success = EmailService.send_reminder_email(
                            user['email'], 
                            user['name'], 
                            game_url
                        )
                        if success:
                            current_app.logger.info(f"Evening reminder sent to {user['email']}")
                        else:
                            current_app.logger.error(f"Failed to send evening reminder to {user['email']}")
    
    # Schedule morning reminders at 7:00 AM daily
    scheduler.add_job(
        id='morning_reminders',
        func=send_morning_reminders,
        trigger='cron',
        hour=7,
        minute=0,
        replace_existing=True
    )
    
    # Schedule evening reminders at 8:00 PM daily
    scheduler.add_job(
        id='evening_reminders',
        func=send_evening_reminders,
        trigger='cron',
        hour=20,
        minute=0,
        replace_existing=True
    )
    
    def send_monthly_birthday_reminders():
        """Send monthly birthday reminders on the 1st of each month at 7:00 AM"""
        from app.memory_module.email_service import EmailService
        from app.memory_module.models import Mem_
        from app.main_page_module.models import UserM
        from datetime import date
        
        with current_app.app_context():
            today = date.today()
            # Get all birthdays for current month
            birthdays = Mem_.get_birthdays_for_month(today.month)
            
            if birthdays:
                # Get users with memory reminders enabled (frequency 1 or 2)
                users = UserM.get_users_for_morning_reminder()
                for user in users:
                    if user.get('email'):
                        success = EmailService.send_monthly_birthday_reminder(
                            user['email'],
                            user['name'],
                            birthdays
                        )
                        if success:
                            current_app.logger.info(f"Monthly birthday reminder sent to {user['email']}")
                        else:
                            current_app.logger.error(f"Failed to send monthly birthday reminder to {user['email']}")
    
    def send_daily_birthday_reminders():
        """Send daily birthday reminders at 7:00 AM for birthdays happening today"""
        from app.memory_module.email_service import EmailService
        from app.memory_module.models import Mem_
        from app.main_page_module.models import UserM
        
        with current_app.app_context():
            # Get birthdays for today
            birthdays = Mem_.get_birthdays_for_today()
            
            if birthdays:
                # Get users with memory reminders enabled (frequency 1 or 2)
                users = UserM.get_users_for_morning_reminder()
                for user in users:
                    if user.get('email'):
                        success = EmailService.send_daily_birthday_reminder(
                            user['email'],
                            user['name'],
                            birthdays
                        )
                        if success:
                            current_app.logger.info(f"Daily birthday reminder sent to {user['email']}")
                        else:
                            current_app.logger.error(f"Failed to send daily birthday reminder to {user['email']}")
    
    # Schedule monthly birthday reminders on the 1st of each month at 7:00 AM
    scheduler.add_job(
        id='monthly_birthday_reminders',
        func=send_monthly_birthday_reminders,
        trigger='cron',
        day=1,
        hour=7,
        minute=0,
        replace_existing=True
    )
    
    # Schedule daily birthday reminders at 7:00 AM
    scheduler.add_job(
        id='daily_birthday_reminders',
        func=send_daily_birthday_reminders,
        trigger='cron',
        hour=7,
        minute=0,
        replace_existing=True
    )
    
    # Start scheduler if not already running
    if not scheduler.running:
        scheduler.start()

