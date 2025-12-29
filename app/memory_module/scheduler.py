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
    
    # Start scheduler if not already running
    if not scheduler.running:
        scheduler.start()

