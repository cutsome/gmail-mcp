"""Class for managing Gmail API authentication"""

import json
import os
from pathlib import Path

from google.auth.credentials import Credentials as GoogleCredentials
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Gmail API scopes
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailAuth:
    """Class for managing Gmail API authentication credentials"""

    def __init__(
        self,
        client_secret_path: str | Path | None = None,
        token_path: str | Path | None = None,
    ) -> None:
        """
        Initialize authentication management class

        Args:
            client_secret_path: Path to client_secret.json (auto-detect if None)
            token_path: Path to save token.json (default: "token.json" if None)
        """
        self.client_secret_path = (
            Path(client_secret_path)
            if client_secret_path
            else self._get_client_secret_path()
        )
        self.token_path = Path(
            token_path or os.getenv("GOOGLE_TOKEN_PATH", "token.json")
        )

    def get_credentials(self) -> GoogleCredentials:
        """
        Get authenticated Credentials

        Returns:
            Authenticated Credentials object

        Raises:
            FileNotFoundError: If client_secret.json is not found
        """
        creds = None

        # Load existing token
        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)

        # If token is invalid or doesn't exist
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # Refresh using refresh token
                creds.refresh(Request())
            else:
                # Load credentials from client_secret.json file
                if not self.client_secret_path.exists():
                    raise FileNotFoundError(
                        f"Credentials file not found: {self.client_secret_path}\n"
                        "Please place client_secret.json in the mcp-gmail-server directory, or "
                        "specify the path using the GOOGLE_CLIENT_SECRET_PATH environment variable."
                    )

                with open(self.client_secret_path, "r", encoding="utf-8") as f:
                    client_config = json.load(f)

                # Execute OAuth2 flow
                flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
                creds = flow.run_local_server(port=0)

            # Save token
            with open(self.token_path, "w", encoding="utf-8") as token:
                token.write(creds.to_json())

        return creds

    def _get_client_secret_path(self) -> Path:
        """Get path to client_secret.json"""
        # Use environment variable if specified
        if env_path := os.getenv("GOOGLE_CLIENT_SECRET_PATH"):
            return Path(env_path)

        # Default: reference client_secret.json in mcp-gmail-server directory
        # From mcp-gmail-server/mcp_gmail_server/gmail_auth.py, go to ../client_secret.json
        current_file = Path(__file__)
        mcp_gmail_server_dir = current_file.parent.parent
        return mcp_gmail_server_dir / "client_secret.json"
