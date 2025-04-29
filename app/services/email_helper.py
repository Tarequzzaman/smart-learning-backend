from config import get_email_cred
from email.message import EmailMessage
import smtplib

email_cred=get_email_cred()

def send_email(recipient_email: str, code: str, user_name: str):
    msg = EmailMessage()
    msg['Subject'] = f'Your Account Reset Code {code}'
    msg['From'] = email_cred.GMAIL_USER
    msg['To'] = recipient_email

    content = f"""
        Hello {user_name},

        You requested to reset your password. 

        Here is your password reset code:

        🔒 Code: {code}

        ⚡ This code will expire in 10 minutes.

        If you did not request a password reset, please ignore this email.

        Thank you,
        Smart Learning Companion Team
        """
    msg.set_content(content)
    with smtplib.SMTP(email_cred.SMTP_SERVER, email_cred.SMTP_PORT) as server:
        server.starttls()  # Secure connection
        server.login(email_cred.GMAIL_USER, email_cred.GMAIL_PASSWORD)
        server.send_message(msg)

