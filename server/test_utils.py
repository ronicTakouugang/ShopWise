"""
Tests de non-régression pour le parsing/formatage des prix (utils.py).

Couvre en particulier le bug historique de conversion FCFA : "11.814.928,42 FCFA"
(point = séparateur de milliers, virgule = décimale) était mal interprété et
produisait un prix ~656x trop élevé une fois "converti" en euros.
"""
import math

from utils import _parse_localized_number, extract_price, convert_to_euro


class TestParseLocalizedNumber:
    def test_french_format_thousands_and_decimal(self):
        assert _parse_localized_number("11.814.928,42") == 11814928.42

    def test_us_format_thousands_and_decimal(self):
        assert _parse_localized_number("1,234.56") == 1234.56

    def test_french_decimal_only(self):
        assert _parse_localized_number("29,99") == 29.99

    def test_us_decimal_only(self):
        assert _parse_localized_number("29.99") == 29.99

    def test_dot_as_thousands_no_decimal(self):
        # Cas FCFA typique : "45.000" veut dire 45 000, pas 45.0
        assert _parse_localized_number("45.000") == 45000.0

    def test_comma_as_thousands_no_decimal(self):
        assert _parse_localized_number("1,000") == 1000.0

    def test_multiple_dots_no_comma(self):
        assert _parse_localized_number("1.234.567") == 1234567.0

    def test_plain_integer(self):
        assert _parse_localized_number("500") == 500.0

    def test_raises_on_no_digits(self):
        import pytest
        with pytest.raises(ValueError):
            _parse_localized_number("FCFA")


class TestExtractPrice:
    def test_na_returns_inf(self):
        assert extract_price("N/A") == float("inf")

    def test_empty_returns_inf(self):
        assert extract_price("") == float("inf")

    def test_text_only_returns_inf(self):
        assert extract_price("Ships to France") == float("inf")

    def test_french_formatted_fcfa_amount(self):
        assert extract_price("11.814.928,42FCFA") == 11814928.42

    def test_us_formatted_dollar_amount(self):
        assert extract_price("$1,234.56") == 1234.56

    def test_simple_euro_amount(self):
        assert extract_price("29.99 €") == 29.99


class TestConvertToEuro:
    def test_fcfa_thousands_and_decimal_converts_plausibly(self):
        # Bug historique : donnait "11 814 928,42 €" (~656x trop élevé) au lieu de ~18 000 €
        result = convert_to_euro("11.814.928,42 FCFA")
        value = float(result.replace("€", "").replace(",", "").strip())
        assert 15000 < value < 21000

    def test_fcfa_dot_thousands_no_decimal_not_near_zero(self):
        # Bug historique : donnait "0.07 €" au lieu de ~68 €
        result = convert_to_euro("45.000 FCFA")
        value = float(result.replace("€", "").replace(",", "").strip())
        assert 50 < value < 90

    def test_zero_price_returns_na_not_zero_euro(self):
        # "0 FCFA" signifie "prix non renseigné" côté source, jamais un vrai prix gratuit.
        assert convert_to_euro("0 FCFA") == "N/A"

    def test_usd_amount_converts(self):
        result = convert_to_euro("$1,234.56")
        value = float(result.replace("€", "").replace(",", "").strip())
        assert 1000 < value < 1300

    def test_already_euro_passthrough(self):
        result = convert_to_euro("29,99 EUR")
        value = float(result.replace("€", "").replace(",", "").strip())
        assert math.isclose(value, 29.99, abs_tol=0.01)

    def test_na_input_returns_na(self):
        assert convert_to_euro("N/A") == "N/A"

    def test_text_only_input_passthrough_is_safe(self):
        # Aucun chiffre : convert_to_euro renvoie la chaîne telle quelle, mais c'est
        # sans danger car extract_price() a le même garde-fou en aval et renverra
        # `inf` pour cette même chaîne plutôt que de la traiter comme un prix.
        result = convert_to_euro("FCFA")
        assert result == "FCFA"
        assert extract_price(result) == float("inf")
