"""
Tests unitaires pour services/auth_service.py : le client Firebase (Pyrebase) est
mocké, aucun appel réseau réel n'est fait.
"""
from unittest.mock import patch

from services import auth_service


class TestRegisterUser:
    @patch("services.auth_service._firebase_auth")
    def test_delegates_to_firebase_create_user(self, mock_firebase_auth):
        mock_firebase_auth.create_user_with_email_and_password.return_value = {"idToken": "abc"}
        result = auth_service.register_user("user@example.com", "password123")
        mock_firebase_auth.create_user_with_email_and_password.assert_called_once_with(
            "user@example.com", "password123"
        )
        assert result == {"idToken": "abc"}

    @patch("services.auth_service._firebase_auth")
    def test_propagates_firebase_errors(self, mock_firebase_auth):
        mock_firebase_auth.create_user_with_email_and_password.side_effect = Exception("EMAIL_EXISTS")
        try:
            auth_service.register_user("user@example.com", "password123")
            assert False, "expected an exception"
        except Exception as e:
            assert "EMAIL_EXISTS" in str(e)


class TestLoginUser:
    @patch("services.auth_service._firebase_auth")
    def test_delegates_to_firebase_sign_in(self, mock_firebase_auth):
        mock_firebase_auth.sign_in_with_email_and_password.return_value = {"idToken": "xyz"}
        result = auth_service.login_user("user@example.com", "password123")
        mock_firebase_auth.sign_in_with_email_and_password.assert_called_once_with(
            "user@example.com", "password123"
        )
        assert result == {"idToken": "xyz"}


class TestSendPasswordResetEmail:
    @patch("services.auth_service._firebase_auth")
    def test_delegates_to_firebase_reset(self, mock_firebase_auth):
        auth_service.send_password_reset_email("user@example.com")
        mock_firebase_auth.send_password_reset_email.assert_called_once_with("user@example.com")
