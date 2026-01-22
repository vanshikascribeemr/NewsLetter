import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import structlog

logger = structlog.get_logger()

class EmailClient:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_pass = os.getenv("SMTP_PASS")
        self.sender_email = os.getenv("SENDER_EMAIL", self.smtp_user)

    def send_newsletter(self, recipients: str, content: str, subject: str) -> bool:
        if not all([self.smtp_user, self.smtp_pass]):
            logger.warning("SMTP credentials not set. Skipping email send.")
            print(f"\n--- DRY RUN: Email Content for [{recipients}] ---\nSubject: {subject}\n\n{content}\n--- END DRY RUN ---")
            return False

        # Split string by comma and clean whitespace
        recipient_list = [email.strip() for email in recipients.split(',') if email.strip()]

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                
                for email in recipient_list:
                    msg = MIMEMultipart()
                    msg['From'] = self.sender_email
                    msg['To'] = email
                    msg['Subject'] = subject
                    msg.attach(MIMEText(content, 'plain'))
                    
                    server.send_message(msg)
                    logger.info("Email sent successfully", recipient=email)
            
            return True
        except Exception as e:
            logger.error("Failed to send email", error=str(e))
            return False
