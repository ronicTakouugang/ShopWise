"""
Tests unitaires pour services/product_matching_service.py, avec le repository mocké :
aucune écriture en base ici, seule la logique de blocking + score de similarité est testée.
"""
from unittest.mock import patch

from services import product_matching_service


class TestResolveProductGroup:
    @patch("services.product_matching_service.product_groups_repository")
    def test_no_candidates_creates_a_new_group(self, mock_repo):
        mock_repo.find_candidate_groups.return_value = []
        mock_repo.create_group.return_value = 42

        result = product_matching_service.resolve_product_group("iPhone 15 Pro Max 256Go Titane Noir")

        assert result == 42
        mock_repo.create_group.assert_called_once()

    @patch("services.product_matching_service.product_groups_repository")
    def test_near_identical_description_matches_existing_group(self, mock_repo):
        """Un même produit décrit légèrement différemment par deux enseignes doit être rapproché."""
        mock_repo.find_candidate_groups.return_value = [
            {"id": 7, "canonical_title": "iPhone 15 Pro Max 256Go Titane Noir"}
        ]

        result = product_matching_service.resolve_product_group("Apple iPhone 15 Pro Max 256 Go Titane Noir")

        assert result == 7
        mock_repo.create_group.assert_not_called()

    @patch("services.product_matching_service.product_groups_repository")
    def test_dissimilar_candidate_below_threshold_creates_new_group(self, mock_repo):
        mock_repo.find_candidate_groups.return_value = [
            {"id": 7, "canonical_title": "Aspirateur robot Roomba i3"}
        ]
        mock_repo.create_group.return_value = 99

        result = product_matching_service.resolve_product_group("iPhone 15 Pro Max 256Go Titane Noir")

        assert result == 99
        mock_repo.create_group.assert_called_once()

    @patch("services.product_matching_service.product_groups_repository")
    def test_picks_best_scoring_candidate_among_several(self, mock_repo):
        mock_repo.find_candidate_groups.return_value = [
            {"id": 1, "canonical_title": "Samsung Televiseur QLED 55 pouces"},
            {"id": 2, "canonical_title": "Samsung Galaxy S24 Ultra 512Go"},
        ]

        result = product_matching_service.resolve_product_group("Samsung Galaxy S24 Ultra 512 Go")

        assert result == 2
        mock_repo.create_group.assert_not_called()


class TestSignificantWords:
    def test_stopwords_and_duplicates_are_excluded(self):
        words = product_matching_service._significant_words(
            product_matching_service.normalize_text("le casque pour le casque bluetooth")
        )
        assert "le" not in words
        assert "pour" not in words
        assert words.count("casque") == 1

    def test_capped_at_max_blocking_words(self):
        words = product_matching_service._significant_words(
            product_matching_service.normalize_text("un deux trois quatre cinq six")
        )
        assert len(words) == product_matching_service._MAX_BLOCKING_WORDS
