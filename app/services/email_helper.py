import os
import base64
from email.message import EmailMessage
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Required Gmail API scope
SCOPES = ['https://www.googleapis.com/auth/gmail.send']


def get_gmail_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES
            )
            creds = flow.run_local_server(port=8080)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)


def send_mail(to_email: str, subject: str, body: str):
    """Reusable function to send email using Gmail API"""
    msg = EmailMessage()
    msg['To'] = to_email
    msg['From'] = 'me'
    msg['Subject'] = subject
    msg.set_content(body)

    raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service = get_gmail_service()
    try:
        message = service.users().messages().send(userId='me', body={'raw': raw_message}).execute()
        print(f"✅ Email sent to {to_email}. Message ID: {message['id']}")
    except Exception as e:
        print(f"❌ Failed to send email: {str(e)}")


def send_email(recipient_email: str, code: str, user_name: str):
    subject = f'Your Account Reset Code {code}'
    body = f"""
        Hello {user_name},

        You requested to reset your password. 

        Here is your password reset code:

        🔒 Code: {code}

        ⚡ This code will expire in 10 minutes.

        If you did not request a password reset, please ignore this email.

        Thank you,
        Smart Learning Companion Team
    """
    send_mail(recipient_email, subject, body)


def send_registration_email(recipient_email: str, code: str, user_name: str):
    subject = f'Your Registration Verification Code {code}'
    body = f"""
        Hello {user_name},

        Thank you for registering with Smart Learning Companion.

        Here is your registration verification code:

        🔒 Code: {code}

        ⚡ This code will expire in 10 minutes.

        If you did not request a registration, please ignore this email.

        Thank you,
        Smart Learning Companion Team
    """
    send_mail(recipient_email, subject, body)
