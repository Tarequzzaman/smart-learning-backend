import base64
import logging
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
CRED_FILE = BASE_DIR / "mail_cred.json"  # OAuth client secrets (downloaded from GCP)
TOKEN_FILE = BASE_DIR / "token.json"  # Contains *access* + *refresh* tokens

log = logging.getLogger("gmail")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


# ─────────────────────────────────────────────────────────────
# TOKEN / SERVICE INITIALISATION
# ─────────────────────────────────────────────────────────────
def _load_creds() -> Credentials:
    """Return valid, refreshed Credentials or raise if refresh token is absent."""
    creds: Credentials | None = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds:
        raise RuntimeError(
            "token.json not found – generate it once with the provisoner script below."
        )

    if creds.valid:
        return creds

    if creds.expired and creds.refresh_token:
        log.info("⚙️  Access‑token expired – refreshing …")
        try:
            creds.refresh(Request())
        except RefreshError as exc:
            raise RuntimeError(
                "Refresh token invalid or revoked – re‑authorise the account."
            ) from exc

        # persist the new access_token / expiry
        TOKEN_FILE.write_text(creds.to_json())
        log.info("✅ Token refreshed. Expires at %s", creds.expiry)
        return creds

    # We reached here => token expired *and* no refresh token ‑‑ unrecoverable
    raise RuntimeError(
        "No refresh_token present – re‑run the provisioning flow with "
        "`access_type='offline' & prompt='consent'`."
    )


def _gmail_service():
    creds = _load_creds()
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


# ─────────────────────────────────────────────────────────────
# PUBLIC SEND FUNCTIONS
# ─────────────────────────────────────────────────────────────
def _send_raw(raw_message: str):
    svc = _gmail_service()
    return svc.users().messages().send(userId="me", body={"raw": raw_message}).execute()


def _compose(to_email: str, subject: str, body: str) -> str:
    """Return base64url‑encoded RFC‑822 message."""
    msg = EmailMessage()
    msg["To"] = to_email
    msg["From"] = "me"
    msg["Subject"] = subject
    msg.set_content(body)
    return base64.urlsafe_b64encode(msg.as_bytes()).decode()


def send_mail(to_email: str, subject: str, body: str) -> bool:
    raw = _compose(to_email, subject, body)
    try:
        resp = _send_raw(raw)
        log.info("📤 Sent mail to %s (id=%s)", to_email, resp["id"])
        return True
    except HttpError as api_err:
        log.error("❌ Gmail API error: %s", api_err)
    except Exception as exc:
        log.exception("❌ Unexpected error while sending mail: %s", exc)
    return False


# ─────────────────────────────────────────────────────────────
# DOMAIN‑SPECIFIC HELPERS
# ─────────────────────────────────────────────────────────────
RESET_TEMPLATE = """\
Hello {user},

You requested to reset your password.

🔒 Code: {code}

⚡ This code expires in 10 minutes.

If you did not request a password reset, please ignore this email.

Thank you,
Smart Learning Companion Team
"""


def send_password_reset(recipient_email: str, code: str, user_name: str) -> bool:
    return send_mail(
        recipient_email,
        f"Your Account Reset Code {code}",
        RESET_TEMPLATE.format(user=user_name, code=code),
    )
