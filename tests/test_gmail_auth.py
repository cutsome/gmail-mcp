"""Unit tests for gmail_auth.py"""

import os
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from mcp_gmail_server.gmail_auth import GmailAuth


class TestGmailAuthInit:
    """Tests for GmailAuth.__init__"""

    def test_init_with_default_paths(self):
        """Should initialize with default paths"""
        auth = GmailAuth()
        assert auth.client_secret_path is not None
        assert auth.token_path == Path("token.json")

    def test_init_with_custom_client_secret_path(self):
        """Should initialize with custom client_secret_path"""
        custom_path = Path("/custom/path/client_secret.json")
        auth = GmailAuth(client_secret_path=custom_path)
        assert auth.client_secret_path == custom_path

    def test_init_with_custom_token_path(self):
        """Should initialize with custom token_path"""
        custom_path = Path("/custom/path/token.json")
        auth = GmailAuth(token_path=custom_path)
        assert auth.token_path == custom_path

    @patch.dict(os.environ, {"GOOGLE_TOKEN_PATH": "/env/token.json"})
    def test_init_with_env_token_path(self):
        """Should use GOOGLE_TOKEN_PATH environment variable if set"""
        auth = GmailAuth()
        assert auth.token_path == Path("/env/token.json")

    @patch.dict(os.environ, {"GOOGLE_CLIENT_SECRET_PATH": "/env/client_secret.json"})
    def test_init_with_env_client_secret_path(self):
        """Should use GOOGLE_CLIENT_SECRET_PATH environment variable if set"""
        auth = GmailAuth()
        assert auth.client_secret_path == Path("/env/client_secret.json")


class TestGmailAuthGetClientSecretPath:
    """Tests for GmailAuth._get_client_secret_path"""

    @patch.dict(os.environ, {}, clear=True)
    def test_get_client_secret_path_default(self):
        """Should return default path when environment variable is not set"""
        auth = GmailAuth()
        path = auth._get_client_secret_path()
        assert isinstance(path, Path)
        assert path.name == "client_secret.json"

    @patch.dict(os.environ, {"GOOGLE_CLIENT_SECRET_PATH": "/custom/path.json"})
    def test_get_client_secret_path_from_env(self):
        """Should get path from environment variable"""
        auth = GmailAuth()
        path = auth._get_client_secret_path()
        assert path == Path("/custom/path.json")


class TestGmailAuthGetCredentials:
    """Tests for GmailAuth.get_credentials"""

    @patch("mcp_gmail_server.gmail_auth.Credentials")
    @patch("builtins.open", create=True)
    def test_get_credentials_with_valid_token(self, mock_open, mock_credentials_class):
        """Should return valid token when present"""
        # Mock setup
        mock_token_path = Path("token.json")
        mock_creds = Mock()
        mock_creds.valid = True
        mock_creds.expired = False

        mock_credentials_class.from_authorized_user_file.return_value = mock_creds

        # Mock token file existence
        with patch.object(Path, "exists", return_value=True):
            auth = GmailAuth(token_path=mock_token_path)
            creds = auth.get_credentials()

        assert creds == mock_creds
        mock_credentials_class.from_authorized_user_file.assert_called_once()

    @patch("mcp_gmail_server.gmail_auth.Credentials")
    @patch("mcp_gmail_server.gmail_auth.Request")
    @patch("builtins.open", create=True)
    def test_get_credentials_with_expired_token_refresh(
        self, mock_open, mock_request, mock_credentials_class
    ):
        """Should refresh when expired token is present"""
        mock_token_path = Path("token.json")
        mock_creds = Mock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh_token"

        mock_credentials_class.from_authorized_user_file.return_value = mock_creds

        with patch.object(Path, "exists", return_value=True):
            auth = GmailAuth(token_path=mock_token_path)
            creds = auth.get_credentials()

        assert creds == mock_creds
        mock_creds.refresh.assert_called_once()

    @patch("pathlib.Path.exists")
    @patch("builtins.open", create=True)
    def test_get_credentials_file_not_found_error(self, mock_open, mock_path_exists):
        """Should raise FileNotFoundError when client_secret.json is not found"""
        mock_token_path = Path("token.json")
        mock_client_secret_path = Path("nonexistent.json")

        # Path.exists always returns False
        mock_path_exists.return_value = False

        mock_credentials_class = Mock()
        mock_credentials_class.from_authorized_user_file.return_value = None

        with patch("mcp_gmail_server.gmail_auth.Credentials", mock_credentials_class):
            auth = GmailAuth(
                client_secret_path=mock_client_secret_path,
                token_path=mock_token_path,
            )
            with pytest.raises(FileNotFoundError) as exc_info:
                auth.get_credentials()

            assert "Credentials file not found" in str(exc_info.value)

    @patch("mcp_gmail_server.gmail_auth.Credentials")
    @patch("builtins.open", create=True)
    def test_get_credentials_saves_token_after_refresh(
        self, mock_open, mock_credentials_class
    ):
        """Should save token after refreshing"""
        mock_token_path = Path("token.json")
        mock_creds = Mock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh_token"
        mock_creds.to_json.return_value = '{"token": "new_token"}'

        mock_credentials_class.from_authorized_user_file.return_value = mock_creds

        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        with patch.object(Path, "exists", return_value=True):
            with patch("mcp_gmail_server.gmail_auth.Request"):
                auth = GmailAuth(token_path=mock_token_path)
                auth.get_credentials()

        # Verify token was saved
        assert mock_open.call_count >= 1
