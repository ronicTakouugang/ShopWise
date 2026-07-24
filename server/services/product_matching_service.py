"""
Rapprochement heuristique d'un même produit vendu sur plusieurs enseignes.
Aucun scraper n'expose d'identifiant produit officiel (EAN/GTIN/SKU), donc le
rapprochement se fait par similarité textuelle sur la description normalisée.
"""
import difflib

from repositories import product_groups_repository
from utils import normalize_text

# Seuil volontairement élevé : on privilégie la précision (peu de faux rapprochements)
# au rappel (manquer un vrai rapprochement n'est pas grave, un produit reste juste
# affiché seul dans les stats). A ajuster si l'usage réel montre trop de faux
# positifs/négatifs.
MATCH_THRESHOLD = 0.82

# Mots trop peu discriminants pour servir de clé de blocking : les garder produirait
# un bucket géant régulièrement traversé par des produits sans rapport.
_STOPWORDS = {"le", "la", "les", "un", "une", "des", "de", "du", "pour", "et", "avec"}

# Nombre de mots significatifs retenus par description pour le blocking. Les 3 premiers
# mots utiles suffisent à faire se recouper deux formulations d'un même produit (marque,
# modèle, ...) sans faire grossir démesurément product_group_words à chaque article.
_MAX_BLOCKING_WORDS = 3


def _significant_words(normalized_text: str) -> list:
    """Mots non triviaux d'un texte déjà normalisé (voir utils.normalize_text), dédupliqués."""
    seen = []
    for word in normalized_text.split():
        if word not in _STOPWORDS and word not in seen:
            seen.append(word)
        if len(seen) >= _MAX_BLOCKING_WORDS:
            break
    return seen


def resolve_product_group(description: str) -> int:
    """
    Retourne l'id du groupe de produits correspondant à cette description : un groupe
    existant si un candidat suffisamment proche est trouvé, sinon un nouveau groupe.
    """
    normalized = normalize_text(description)
    words = _significant_words(normalized)

    candidates = product_groups_repository.find_candidate_groups(words)

    best_group_id = None
    best_score = 0.0
    for candidate in candidates:
        score = difflib.SequenceMatcher(
            None, normalized, normalize_text(candidate["canonical_title"])
        ).ratio()
        if score > best_score:
            best_score = score
            best_group_id = candidate["id"]

    if best_group_id is not None and best_score >= MATCH_THRESHOLD:
        return best_group_id

    return product_groups_repository.create_group(description, words)
