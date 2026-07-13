"""
Tests unitaires pour services/price_alert_service.py, avec repositories, scrapers
et SMTP mockés : aucune requête réseau, aucun email réel, aucune écriture en base.
"""
from unittest.mock import patch, MagicMock

from services import price_alert_service


class TestParseThresholdPercent:
    def test_none_returns_none(self):
        assert price_alert_service.parse_threshold_percent(None) is None

    def test_invalid_value_returns_none(self):
        assert price_alert_service.parse_threshold_percent("abc") is None

    def test_zero_or_negative_returns_none(self):
        assert price_alert_service.parse_threshold_percent(0) is None
        assert price_alert_service.parse_threshold_percent(-5) is None

    def test_valid_positive_value_returns_float(self):
        assert price_alert_service.parse_threshold_percent("10") == 10.0


class TestGetCurrentPrice:
    @patch("services.price_alert_service.articles_repository")
    def test_unknown_product_returns_inf(self, mock_articles_repo):
        mock_articles_repo.get_article_by_url.return_value = None
        assert price_alert_service.get_current_price("https://x") == float('inf')

    @patch("services.price_alert_service.articles_repository")
    def test_source_without_live_recheck_returns_last_known_price(self, mock_articles_repo):
        mock_articles_repo.get_article_by_url.return_value = {
            "source": "Amazon", "description": "produit", "last_price": 42.0
        }
        assert price_alert_service.get_current_price("https://x") == 42.0

    @patch("services.price_alert_service.articles_repository")
    def test_live_recheck_finds_matching_product_and_returns_new_price(self, mock_articles_repo):
        mock_articles_repo.get_article_by_url.return_value = {
            "source": "Glotehlo", "description": "produit", "last_price": 42.0
        }
        mock_scraper = MagicMock(return_value=[
            {"productURL": "https://other", "price": "99 €"},
            {"productURL": "https://x", "price": "30 €"},
        ])
        with patch.dict(price_alert_service._LIVE_RECHECK_SCRAPERS, {"Glotehlo": mock_scraper}):
            assert price_alert_service.get_current_price("https://x") == 30.0

    @patch("services.price_alert_service.articles_repository")
    def test_live_recheck_product_not_found_falls_back_to_last_price(self, mock_articles_repo):
        mock_articles_repo.get_article_by_url.return_value = {
            "source": "Glotehlo", "description": "produit", "last_price": 42.0
        }
        mock_scraper = MagicMock(return_value=[])
        with patch.dict(price_alert_service._LIVE_RECHECK_SCRAPERS, {"Glotehlo": mock_scraper}):
            assert price_alert_service.get_current_price("https://x") == 42.0

    @patch("services.price_alert_service.articles_repository")
    def test_exception_returns_inf_instead_of_raising(self, mock_articles_repo):
        mock_articles_repo.get_article_by_url.side_effect = RuntimeError("db down")
        assert price_alert_service.get_current_price("https://x") == float('inf')


class TestSendEmailAlert:
    @patch("services.price_alert_service.config")
    @patch("services.price_alert_service.smtplib.SMTP")
    def test_missing_smtp_config_does_not_attempt_send(self, mock_smtp, mock_config):
        mock_config.SMTP_SERVER = None
        mock_config.SMTP_USERNAME = None
        mock_config.SMTP_PASSWORD = None
        mock_config.SMTP_FROM_EMAIL = None
        price_alert_service.send_email_alert("user@example.com", "https://x", 10.0)
        mock_smtp.assert_not_called()

    @patch("services.price_alert_service.config")
    @patch("services.price_alert_service.smtplib.SMTP")
    def test_valid_config_sends_via_smtp(self, mock_smtp, mock_config):
        mock_config.SMTP_SERVER = "smtp.example.com"
        mock_config.SMTP_PORT = 587
        mock_config.SMTP_USERNAME = "user"
        mock_config.SMTP_PASSWORD = "pass"
        mock_config.SMTP_FROM_EMAIL = "from@example.com"
        server_instance = mock_smtp.return_value.__enter__.return_value

        price_alert_service.send_email_alert("user@example.com", "https://x", 10.0)

        server_instance.starttls.assert_called_once()
        server_instance.login.assert_called_once_with("user", "pass")
        server_instance.send_message.assert_called_once()


class TestRunPriceCheck:
    @patch("services.price_alert_service.subscriptions_repository")
    @patch("services.price_alert_service.get_current_price")
    def test_unresolvable_price_is_skipped_without_touching_history(
        self, mock_get_price, mock_sub_repo
    ):
        mock_sub_repo.get_all_subscriptions.return_value = [
            (1, "https://x", 50.0, "user@example.com", None)
        ]
        mock_get_price.return_value = float('inf')

        with patch("services.price_alert_service.price_history_repository") as mock_history_repo:
            alerts = price_alert_service.run_price_check()

        assert alerts == []
        mock_history_repo.insert_price_point.assert_not_called()

    @patch("services.price_alert_service.notifications_repository")
    @patch("services.price_alert_service.profile_repository")
    @patch("services.price_alert_service.price_history_repository")
    @patch("services.price_alert_service.subscriptions_repository")
    @patch("services.price_alert_service.get_current_price")
    @patch("services.price_alert_service.send_email_alert")
    def test_price_drop_below_threshold_percent_is_ignored(
        self, mock_send_email, mock_get_price, mock_sub_repo, mock_history_repo,
        mock_profile_repo, mock_notif_repo
    ):
        # Seuil de 50% requis, mais la baisse réelle n'est que de 10%.
        mock_sub_repo.get_all_subscriptions.return_value = [
            (1, "https://x", 100.0, "user@example.com", 50.0)
        ]
        mock_get_price.return_value = 90.0

        alerts = price_alert_service.run_price_check()

        assert alerts == []
        mock_history_repo.insert_price_point.assert_called_once_with("https://x", 90.0)
        mock_send_email.assert_not_called()
        mock_notif_repo.insert_notification.assert_not_called()

    @patch("services.price_alert_service.notifications_repository")
    @patch("services.price_alert_service.profile_repository")
    @patch("services.price_alert_service.price_history_repository")
    @patch("services.price_alert_service.subscriptions_repository")
    @patch("services.price_alert_service.get_current_price")
    @patch("services.price_alert_service.send_email_alert")
    def test_price_drop_meeting_threshold_triggers_alert_and_updates_baseline(
        self, mock_send_email, mock_get_price, mock_sub_repo, mock_history_repo,
        mock_profile_repo, mock_notif_repo
    ):
        mock_sub_repo.get_all_subscriptions.return_value = [
            (1, "https://x", 100.0, "user@example.com", 10.0)
        ]
        mock_get_price.return_value = 80.0  # baisse de 20%, seuil de 10% atteint
        mock_profile_repo.get_email_notifications_enabled.return_value = True

        alerts = price_alert_service.run_price_check()

        assert len(alerts) == 1
        mock_send_email.assert_called_once_with("user@example.com", "https://x", 80.0)
        mock_notif_repo.insert_notification.assert_called_once()
        mock_sub_repo.update_subscription_reference_price.assert_called_once_with(1, 80.0)

    @patch("services.price_alert_service.notifications_repository")
    @patch("services.price_alert_service.profile_repository")
    @patch("services.price_alert_service.price_history_repository")
    @patch("services.price_alert_service.subscriptions_repository")
    @patch("services.price_alert_service.get_current_price")
    @patch("services.price_alert_service.send_email_alert")
    def test_email_alert_skipped_when_user_disabled_notifications_but_in_app_still_sent(
        self, mock_send_email, mock_get_price, mock_sub_repo, mock_history_repo,
        mock_profile_repo, mock_notif_repo
    ):
        mock_sub_repo.get_all_subscriptions.return_value = [
            (1, "https://x", 100.0, "user@example.com", None)
        ]
        mock_get_price.return_value = 90.0
        mock_profile_repo.get_email_notifications_enabled.return_value = False

        alerts = price_alert_service.run_price_check()

        assert len(alerts) == 1
        mock_send_email.assert_not_called()
        mock_notif_repo.insert_notification.assert_called_once()

    @patch("services.price_alert_service.notifications_repository")
    @patch("services.price_alert_service.profile_repository")
    @patch("services.price_alert_service.price_history_repository")
    @patch("services.price_alert_service.subscriptions_repository")
    @patch("services.price_alert_service.get_current_price")
    @patch("services.price_alert_service.send_email_alert")
    def test_price_increase_does_not_trigger_alert(
        self, mock_send_email, mock_get_price, mock_sub_repo, mock_history_repo,
        mock_profile_repo, mock_notif_repo
    ):
        mock_sub_repo.get_all_subscriptions.return_value = [
            (1, "https://x", 100.0, "user@example.com", None)
        ]
        mock_get_price.return_value = 110.0

        alerts = price_alert_service.run_price_check()

        assert alerts == []
        mock_send_email.assert_not_called()
        mock_notif_repo.insert_notification.assert_not_called()
