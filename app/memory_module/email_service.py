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

