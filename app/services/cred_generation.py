#!/usr/bin/env python3
"""
provision_token.py
──────────────────
One‑time script to generate token.json (access + refresh token) for the Gmail API.

How to use:
    1. Place this file and your Google OAuth client‑secret JSON
       (downloaded from Cloud Console) in the same folder.
       The client‑secret must be named  ➜  credentials.json
    2. Run:   python provision_token.py
    3. A browser window opens – sign in and grant consent.
    4. token.json is created. Copy / mount this file next to mailer_service.py
       in production (or upload it to your secret manager).
"""

from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

# Gmail scopes required to send mail
SCOPES = ["https://mail.google.com/"]
CLIENT_SECRET_FILE = "credentials.json"
TOKEN_FILE = "token.json"


def main() -> None:
    # Launch the OAuth consent flow in a local browser
    flow = InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES,
    )
    creds = flow.run_local_server(
        port=8080,
        access_type="offline",  # ensures we get a refresh_token
        prompt="consent",       # forces Google to return refresh_token every time
        include_granted_scopes="true",
    )

    # Persist credentials to token.json
    Path(TOKEN_FILE).write_text(creds.to_json())
    print(f"✅  {TOKEN_FILE} saved – copy it next to mailer_service.py in production.")


if __name__ == "__main__":
    main()
