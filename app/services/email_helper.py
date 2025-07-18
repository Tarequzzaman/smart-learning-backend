#!/usr/bin/env python3
"""
gmail_mailer.py

Single-file Gmail API mail sender with automatic OAuth2 token refresh.

Usage (first run will open browser for consent and create token.json):
    python gmail_mailer.py --to you@example.com --subject "Hi" --body "Test"

Send password-reset template:
    python gmail_mailer.py --reset --to you@example.com --code 123456 --name Alice

Send registration template:
    python gmail_mailer.py --register --to you@example.com --code 654321 --name Bob
"""

import argparse
import base64
import logging
import os
import sys
import textwrap
from email.message import EmailMessage
from pathlib import Path
from typing import Final

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
SCOPES: Final[list[str]] = ["https://www.googleapis.com/auth/gmail.send"]
BASE_DIR = Path(__file__).resolve().parent
CRED_FILE = BASE_DIR / "credentials.json"  # Downloaded from Google Cloud Console
TOKEN_FILE = BASE_DIR / "token.json"  # Will be created after first auth

# Optional: override port via env (handy if 8080 busy)
AUTH_PORT = int(os.getenv("GOOGLE_AUTH_PORT", "8080"))

log = logging.getLogger("gmail_mailer")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def _load_creds() -> Credentials:
    """Load creds from token.json, refresh if needed, never open browser."""
    if not TOKEN_FILE.exists():
        raise RuntimeError("token.json missing – generate offline and redeploy.")

    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # Valid → done
    if creds and creds.valid:
        return creds

    # Expired but refreshable
    if creds and creds.expired and creds.refresh_token:
        log.info("Access token expired – refreshing …")
        try:
            creds.refresh(Request())
        except RefreshError as exc:
            raise RuntimeError(
                "Refresh token invalid or revoked – "
                "regenerate token.json offline and redeploy."
            ) from exc
        TOKEN_FILE.write_text(creds.to_json())
        return creds

    # No refresh token → unrecoverable in headless mode
    raise RuntimeError(
        "token.json has no refresh_token – regenerate offline and redeploy."
    )


# ─────────────────────────────────────────────────────────────
# GMAIL SERVICE
# ─────────────────────────────────────────────────────────────
def _gmail_service():
    creds = _load_creds()
    # cache_discovery=False avoids writing to ~/.cache on some serverless platforms
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


# ─────────────────────────────────────────────────────────────
# LOW-LEVEL SEND
# ─────────────────────────────────────────────────────────────
def _compose_raw_message(to_email: str, subject: str, body: str) -> str:
    """
    Build RFC-822 message and return base64url-encoded string required by Gmail API.
    """
    msg = EmailMessage()
    msg["To"] = to_email
    msg["From"] = "me"  # 'me' tells Gmail to use the authenticated user
    msg["Subject"] = subject
    msg.set_content(body)
    return base64.urlsafe_b64encode(msg.as_bytes()).decode()


def _send_raw(raw_message: str):
    service = _gmail_service()
    return (
        service.users()
        .messages()
        .send(userId="me", body={"raw": raw_message})
        .execute()
    )


# ─────────────────────────────────────────────────────────────
# PUBLIC API – matches your original function names
# ─────────────────────────────────────────────────────────────
def send_mail(to_email: str, subject: str, body: str) -> bool:
    """
    Send a plain-text email. Returns True if sent, False otherwise.
    """
    raw = _compose_raw_message(to_email, subject, body)
    try:
        resp = _send_raw(raw)
        log.info("📤 Email sent to %s. Message ID: %s", to_email, resp.get("id"))
        return True
    except HttpError as api_err:
        log.error("❌ Gmail API error: %s", api_err)
    except Exception as exc:  # noqa: BLE001
        log.exception("❌ Unexpected error sending mail: %s", exc)
    return False


# Domain templates (trim indentation w/ textwrap.dedent to keep code readable)
RESET_TEMPLATE = textwrap.dedent("""\
    Hello {user_name},

    You requested to reset your password.

    🔒 Code: {code}

    ⚡ This code will expire in 10 minutes.

    If you did not request a password reset, please ignore this email.

    Thank you,
    Smart Learning Companion Team
""")

REG_TEMPLATE = textwrap.dedent("""\
    Hello {user_name},

    Thank you for registering with Smart Learning Companion.

    Here is your registration verification code:

    🔒 Code: {code}

    ⚡ This code will expire in 10 minutes.

    If you did not request a registration, please ignore this email.

    Thank you,
    Smart Learning Companion Team
""")


def send_email(recipient_email: str, code: str, user_name: str) -> bool:
    """
    Password reset email (kept name from your original code).
    """
    subject = f"Your Account Reset Code {code}"
    body = RESET_TEMPLATE.format(user_name=user_name, code=code)
    return send_mail(recipient_email, subject, body)


def send_registration_email(recipient_email: str, code: str, user_name: str) -> bool:
    """
    Registration verification email (kept name from your original code).
    """
    subject = f"Your Registration Verification Code {code}"
    body = REG_TEMPLATE.format(user_name=user_name, code=code)
    return send_mail(recipient_email, subject, body)


# ─────────────────────────────────────────────────────────────
# CLI ENTRYPOINT (handy for smoke tests & provisioning)
# ─────────────────────────────────────────────────────────────
def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Send email via Gmail API.")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument(
        "--reset", action="store_true", help="Send password-reset template."
    )
    mode.add_argument(
        "--register", action="store_true", help="Send registration template."
    )

    p.add_argument("--to", dest="to_email", help="Recipient email address.")
    p.add_argument("--subject", help="Subject (ignored in template modes).")
    p.add_argument("--body", help="Body text (ignored in template modes).")
    p.add_argument("--code", help="One-time code for template modes.")
    p.add_argument(
        "--name", dest="user_name", help="User name for template modes.", default="User"
    )

    return p.parse_args()


def _cli_main() -> int:
    args = _parse_args()

    if not args.to_email:
        print("--to is required.", file=sys.stderr)
        return 2

    if args.reset:
        if not args.code:
            print("--code required with --reset.", file=sys.stderr)
            return 2
        ok = send_email(args.to_email, args.code, args.user_name)
        return 0 if ok else 1

    if args.register:
        if not args.code:
            print("--code required with --register.", file=sys.stderr)
            return 2
        ok = send_registration_email(args.to_email, args.code, args.user_name)
        return 0 if ok else 1

    # Plain send
    if not args.subject or not args.body:
        print("--subject and --body required for plain send.", file=sys.stderr)
        return 2
    ok = send_mail(args.to_email, args.subject, args.body)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(_cli_main())
