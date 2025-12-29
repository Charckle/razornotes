import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app import app


class EmailService:
    @staticmethod
    def send_reminder_email(user_email, user_name, game_url):
        """Send memory game reminder email"""
        try:
            # Get and validate configuration
            smtp_host = app.config.get('EMAIL_SMTP_HOST', '').strip()
            smtp_port = app.config.get('EMAIL_SMTP_PORT', '')
            smtp_user = app.config.get('EMAIL_SMTP_USER', '').strip()
            smtp_password = app.config.get('EMAIL_SMTP_PASSWORD', '').strip()
            from_address = app.config.get('EMAIL_FROM_ADDRESS', '').strip()
            
            if not all([smtp_host, smtp_port, smtp_user, smtp_password, from_address]):
                app.logger.error("Email configuration incomplete")
                return False
            
            msg = MIMEMultipart()
            # Use APP_NAME instead of separate EMAIL_FROM_NAME
            msg['From'] = f"{app.config['APP_NAME']} <{from_address}>"
            msg['To'] = user_email
            msg['Subject'] = "Time to practice your memory!"
            
            body = f"""
Hi {user_name},

It's time to practice your memory! Click the link below to start a random memory game:

{game_url}

Keep your memory sharp!
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Convert port to int if it's a string
            port = int(smtp_port) if isinstance(smtp_port, str) else smtp_port
            
            # Use SSL/TLS connection
            server = smtplib.SMTP_SSL(smtp_host, port, timeout=10)
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            server.quit()
            
            return True
        except Exception as e:
            app.logger.error(f"Error sending email to {user_email}: {str(e)}")
            return False
    
    @staticmethod
    def test_email_connection():
        """Test email connection without sending an email"""
        # Check if required configuration is set
        smtp_host = app.config.get('EMAIL_SMTP_HOST', '').strip()
        smtp_port = app.config.get('EMAIL_SMTP_PORT', '')
        smtp_user = app.config.get('EMAIL_SMTP_USER', '').strip()
        smtp_password = app.config.get('EMAIL_SMTP_PASSWORD', '').strip()
        
        if not smtp_host:
            return False, "SMTP host is not configured"
        if not smtp_port:
            return False, "SMTP port is not configured"
        if not smtp_user:
            return False, "SMTP username is not configured"
        if not smtp_password:
            return False, "SMTP password is not configured"
        
        try:
            # Convert port to int if it's a string
            port = int(smtp_port) if isinstance(smtp_port, str) else smtp_port
            
            # Use SSL/TLS connection
            server = smtplib.SMTP_SSL(smtp_host, port, timeout=10)
            server.login(smtp_user, smtp_password)
            server.quit()
            return True, "Connection successful"
        except smtplib.SMTPAuthenticationError as e:
            return False, f"Authentication failed: {str(e)}"
        except smtplib.SMTPConnectError as e:
            return False, f"Cannot connect to {smtp_host}:{port} - Check host/port and network connectivity"
        except (ConnectionRefusedError, OSError) as e:
            return False, f"Connection refused to {smtp_host}:{port} - Port may be closed or firewall blocking"
        except TimeoutError as e:
            return False, f"Connection timeout to {smtp_host}:{port} - Server not reachable or port blocked"
        except smtplib.SMTPException as e:
            return False, f"SMTP error: {str(e)}"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    @staticmethod
    def get_game_url():
        """Get URL for memory game (uses group_id 99999999 for random selection)"""
        website_url = app.config.get('WEBSITE_URL', '').strip()
        if not website_url:
            app.logger.error("WEBSITE_URL is not configured")
            return None
        
        # Remove trailing slash if present
        website_url = website_url.rstrip('/')
        # Use group_id 99999999 which selects random groups
        return f"{website_url}/memory/game/99999999"
    
    @staticmethod
    def send_monthly_birthday_reminder(user_email, user_name, birthdays):
        """Send monthly birthday reminder with list of all birthdays for the month"""
        try:
            from datetime import date
            from calendar import month_name
            
            # Get and validate configuration
            smtp_host = app.config.get('EMAIL_SMTP_HOST', '').strip()
            smtp_port = app.config.get('EMAIL_SMTP_PORT', '')
            smtp_user = app.config.get('EMAIL_SMTP_USER', '').strip()
            smtp_password = app.config.get('EMAIL_SMTP_PASSWORD', '').strip()
            from_address = app.config.get('EMAIL_FROM_ADDRESS', '').strip()
            
            if not all([smtp_host, smtp_port, smtp_user, smtp_password, from_address]):
                app.logger.error("Email configuration incomplete")
                return False
            
            if not birthdays:
                return True  # No birthdays to send
            
            today = date.today()
            month_name_str = month_name[today.month]
            
            msg = MIMEMultipart()
            msg['From'] = f"{app.config['APP_NAME']} <{from_address}>"
            msg['To'] = user_email
            msg['Subject'] = f"Birthday Reminders for {month_name_str}"
            
            # Format birthday list
            birthday_list = []
            for bday in birthdays:
                if not isinstance(bday, dict):
                    continue
                    
                birthday_date = bday.get('birthday')
                if not birthday_date:
                    continue
                    
                # Handle different date formats
                if isinstance(birthday_date, str):
                    from datetime import datetime
                    try:
                        birthday_date = datetime.strptime(birthday_date, '%Y-%m-%d').date()
                    except ValueError:
                        continue
                elif hasattr(birthday_date, 'date'):
                    birthday_date = birthday_date.date()
                elif hasattr(birthday_date, 'day'):
                    # Already a date object
                    pass
                else:
                    continue
                
                day = birthday_date.day
                name = bday.get('answer', 'Unknown')
                group = bday.get('mg_name', '')
                birthday_list.append(f"  • {day:2d} {month_name_str}: {name}" + (f" ({group})" if group else ""))
            
            body = f"""Hi {user_name},

Here are the birthdays coming up in {month_name_str}:

{chr(10).join(birthday_list)}

Don't forget to wish them a happy birthday!

Best regards,
{app.config['APP_NAME']}
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            port = int(smtp_port) if isinstance(smtp_port, str) else smtp_port
            server = smtplib.SMTP_SSL(smtp_host, port, timeout=10)
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            server.quit()
            
            return True
        except Exception as e:
            app.logger.error(f"Error sending monthly birthday reminder to {user_email}: {str(e)}")
            return False
    
    @staticmethod
    def send_daily_birthday_reminder(user_email, user_name, birthdays):
        """Send daily birthday reminder for birthdays happening today"""
        try:
            # Get and validate configuration
            smtp_host = app.config.get('EMAIL_SMTP_HOST', '').strip()
            smtp_port = app.config.get('EMAIL_SMTP_PORT', '')
            smtp_user = app.config.get('EMAIL_SMTP_USER', '').strip()
            smtp_password = app.config.get('EMAIL_SMTP_PASSWORD', '').strip()
            from_address = app.config.get('EMAIL_FROM_ADDRESS', '').strip()
            
            if not all([smtp_host, smtp_port, smtp_user, smtp_password, from_address]):
                app.logger.error("Email configuration incomplete")
                return False
            
            if not birthdays:
                return True  # No birthdays today
            
            msg = MIMEMultipart()
            msg['From'] = f"{app.config['APP_NAME']} <{from_address}>"
            msg['To'] = user_email
            
            if len(birthdays) == 1:
                name = birthdays[0].get('answer', 'Someone')
                msg['Subject'] = f"🎉 Today is {name}'s Birthday!"
                body = f"""Hi {user_name},

Today is {name}'s birthday! 🎂

Don't forget to wish them a happy birthday!

Best regards,
{app.config['APP_NAME']}
"""
            else:
                names = [b.get('answer', 'Unknown') for b in birthdays]
                msg['Subject'] = f"🎉 {len(birthdays)} Birthdays Today!"
                name_list = ', '.join(names[:-1]) + f" and {names[-1]}" if len(names) > 1 else names[0]
                body = f"""Hi {user_name},

Today is the birthday of: {name_list}! 🎂

Don't forget to wish them a happy birthday!

Best regards,
{app.config['APP_NAME']}
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            port = int(smtp_port) if isinstance(smtp_port, str) else smtp_port
            server = smtplib.SMTP_SSL(smtp_host, port, timeout=10)
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            server.quit()
            
            return True
        except Exception as e:
            app.logger.error(f"Error sending daily birthday reminder to {user_email}: {str(e)}")
            return False

