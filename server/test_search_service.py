"""
Tests unitaires pour services/search_service.py, avec repositories et scrapers
mockés : aucune requête réseau ni écriture en base ici.
"""
from unittest.mock import patch, MagicMock

from services import search_service


class TestComputeDealAttributes:
    def test_valid_price_sets_numeric_price(self):
        record = {"price": "19,99 €", "description": "Un super produit"}
        result = search_service.compute_deal_attributes(record, query="super produit")
        assert result["numeric_price"] == 19.99

    def test_unparseable_price_uses_sentinel(self):
        record = {"price": "N/A", "description": "Un produit"}
        result = search_service.compute_deal_attributes(record, query="produit")
        assert result["numeric_price"] == 999999999.0

    def test_relevance_score_rewards_matching_words(self):
        matching = search_service.compute_deal_attributes(
            {"price": "10 €", "description": "casque bluetooth sans fil"}, query="casque bluetooth"
        )
        non_matching = search_service.compute_deal_attributes(
            {"price": "10 €", "description": "chaussures de sport"}, query="casque bluetooth"
        )
        assert matching["relevance_score"] > non_matching["relevance_score"]

    def test_no_query_gives_zero_relevance(self):
        result = search_service.compute_deal_attributes({"price": "10 €", "description": "produit"}, query="")
        assert result["relevance_score"] == 0


class TestPersistArticles:
    @patch("services.search_service.price_history_repository")
    @patch("services.search_service.articles_repository")
    def test_skips_records_without_url_or_unknown_price(self, mock_articles_repo, mock_history_repo):
        mock_articles_repo.MAX_PLAUSIBLE_PRICE_EUR = 500_000
        search_service.persist_articles([
            {"productURL": "", "numeric_price": 10.0},
            {"productURL": "https://x", "numeric_price": float('inf')},
        ])
        mock_articles_repo.upsert_article.assert_not_called()

    @patch("services.search_service.price_history_repository")
    @patch("services.search_service.articles_repository")
    def test_skips_implausible_prices(self, mock_articles_repo, mock_history_repo):
        mock_articles_repo.MAX_PLAUSIBLE_PRICE_EUR = 500_000
        search_service.persist_articles([
            {"productURL": "https://x", "numeric_price": 999_999.0, "description": "x"},
            {"productURL": "https://y", "numeric_price": 0, "description": "y"},
        ])
        mock_articles_repo.upsert_article.assert_not_called()

    @patch("services.search_service.price_history_repository")
    @patch("services.search_service.articles_repository")
    def test_persists_valid_record_and_inserts_history_point_on_price_change(
        self, mock_articles_repo, mock_history_repo
    ):
        mock_articles_repo.MAX_PLAUSIBLE_PRICE_EUR = 500_000
        mock_history_repo.get_last_price_point.return_value = 15.0
        search_service.persist_articles([{
            "productURL": "https://x", "numeric_price": 19.99, "description": "x",
            "imageURL": "img", "source": "Amazon", "sourceLogo": "logo",
            "rating": "4.5", "reviewCount": "10",
        }])
        mock_articles_repo.upsert_article.assert_called_once()
        mock_history_repo.insert_price_point.assert_called_once_with("https://x", 19.99)

    @patch("services.search_service.price_history_repository")
    @patch("services.search_service.articles_repository")
    def test_does_not_duplicate_history_point_when_price_unchanged(
        self, mock_articles_repo, mock_history_repo
    ):
        mock_articles_repo.MAX_PLAUSIBLE_PRICE_EUR = 500_000
        mock_history_repo.get_last_price_point.return_value = 19.99
        search_service.persist_articles([{
            "productURL": "https://x", "numeric_price": 19.99, "description": "x",
        }])
        mock_history_repo.insert_price_point.assert_not_called()


class TestDoSearch:
    @patch("services.search_service.persist_articles")
    @patch("services.search_service.scrape_auchan")
    @patch("services.search_service.scrape_leclerc")
    @patch("services.search_service.scrape_materielnet")
    @patch("services.search_service.scrape_glotelho")
    @patch("services.search_service.scrape_amazon")
    def test_combines_dedupes_and_sorts_by_relevance_then_price(
        self, mock_amazon, mock_glotelho, mock_materielnet, mock_leclerc, mock_auchan, mock_persist
    ):
        mock_amazon.return_value = [
            {"description": "casque bluetooth", "price": "50 €", "productURL": "https://dup", "source": "Amazon"},
        ]
        mock_glotelho.return_value = [
            # Doublon exact de productURL : ne doit apparaître qu'une fois.
            {"description": "casque bluetooth", "price": "45 €", "productURL": "https://dup", "source": "Glotehlo"},
            {"description": "casque bluetooth pas cher", "price": "20 €", "productURL": "https://cheap", "source": "Glotehlo"},
        ]
        mock_materielnet.return_value = []
        mock_leclerc.return_value = []
        mock_auchan.return_value = []

        results = search_service.do_search("casque bluetooth")

        urls = [r["productURL"] for r in results]
        assert urls.count("https://dup") == 1
        mock_persist.assert_called_once()

    @patch("services.search_service.persist_articles")
    @patch("services.search_service.scrape_auchan")
    @patch("services.search_service.scrape_leclerc")
    @patch("services.search_service.scrape_materielnet")
    @patch("services.search_service.scrape_glotelho")
    @patch("services.search_service.scrape_amazon")
    def test_scraper_exception_does_not_break_other_results(
        self, mock_amazon, mock_glotelho, mock_materielnet, mock_leclerc, mock_auchan, mock_persist
    ):
        mock_amazon.side_effect = RuntimeError("boom")
        mock_glotelho.return_value = [{"description": "x", "price": "10 €", "productURL": "https://ok", "source": "Glotehlo"}]
        mock_materielnet.return_value = []
        mock_leclerc.return_value = []
        mock_auchan.return_value = []

        results = search_service.do_search("x")
        assert len(results) == 1
        assert results[0]["productURL"] == "https://ok"

    @patch("services.search_service.persist_articles")
    @patch("services.search_service.scrape_auchan")
    @patch("services.search_service.scrape_leclerc")
    @patch("services.search_service.scrape_materielnet")
    @patch("services.search_service.scrape_glotelho")
    @patch("services.search_service.scrape_amazon")
    def test_records_without_description_are_dropped(
        self, mock_amazon, mock_glotelho, mock_materielnet, mock_leclerc, mock_auchan, mock_persist
    ):
        mock_amazon.return_value = [{"description": "", "price": "10 €", "productURL": "https://x"}]
        mock_glotelho.return_value = []
        mock_materielnet.return_value = []
        mock_leclerc.return_value = []
        mock_auchan.return_value = []

        results = search_service.do_search("x")
        assert results == []


class TestDoSearchCached:
    def setup_method(self):
        search_service._search_cache.clear()

    @patch("services.search_service.log_search")
    @patch("services.search_service.do_search")
    def test_cache_hit_does_not_call_do_search_again(self, mock_do_search, mock_log_search):
        mock_do_search.return_value = [{"productURL": "https://x"}]

        first = search_service.do_search_cached("query", "user@example.com")
        second = search_service.do_search_cached("query", "user@example.com")

        assert first == second
        mock_do_search.assert_called_once()

    @patch("services.search_service.log_search")
    @patch("services.search_service.do_search")
    def test_different_queries_are_not_conflated(self, mock_do_search, mock_log_search):
        mock_do_search.side_effect = [[{"productURL": "https://a"}], [{"productURL": "https://b"}]]

        result_a = search_service.do_search_cached("query a", None)
        result_b = search_service.do_search_cached("query b", None)

        assert result_a != result_b
        assert mock_do_search.call_count == 2


class TestLogSearch:
    @patch("services.search_service.search_log_repository")
    def test_logs_normalized_query_and_email(self, mock_repo):
        search_service.log_search("Téléphone", "user@example.com")
        mock_repo.insert_search_log.assert_called_once()
        args = mock_repo.insert_search_log.call_args[0]
        assert args[1] == "user@example.com"

    @patch("services.search_service.search_log_repository")
    def test_repository_exception_is_swallowed(self, mock_repo):
        mock_repo.insert_search_log.side_effect = RuntimeError("db down")
        # Ne doit pas lever : une recherche ne doit jamais échouer à cause des stats.
        search_service.log_search("query", None)


class TestMarkFavorites:
    def test_no_email_returns_copies_without_marking(self):
        results = [{"productURL": "https://x"}]
        copies = search_service.mark_favorites(results, None)
        assert copies[0].get("isFavorite") is None
        assert copies is not results

    @patch("services.search_service.favorites_repository")
    def test_marks_known_favorite_urls(self, mock_repo):
        mock_repo.get_favorite_urls_by_email.return_value = {"https://x"}
        results = [{"productURL": "https://x"}, {"productURL": "https://y"}]
        copies = search_service.mark_favorites(results, "user@example.com")
        assert copies[0]["isFavorite"] is True
        assert copies[1]["isFavorite"] is False

    def test_does_not_mutate_original_records(self):
        original = [{"productURL": "https://x"}]
        search_service.mark_favorites(original, None)
        assert "isFavorite" not in original[0]


class TestMarkSubscriptions:
    @patch("services.search_service.subscriptions_repository")
    def test_marks_known_subscribed_urls(self, mock_repo):
        mock_repo.get_subscribed_urls_by_email.return_value = {"https://x"}
        results = [{"productURL": "https://x"}, {"productURL": "https://y"}]
        copies = search_service.mark_subscriptions(results, "user@example.com")
        assert copies[0]["isSubscribed"] is True
        assert copies[1]["isSubscribed"] is False

    def test_no_email_returns_copies_without_marking(self):
        results = [{"productURL": "https://x"}]
        copies = search_service.mark_subscriptions(results, None)
        assert copies[0].get("isSubscribed") is None
