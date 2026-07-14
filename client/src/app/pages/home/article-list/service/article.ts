export interface Article {
  description: string;
  price: string;
  // Pas toutes les sources n'exposent une note (Leclerc/Auchan/Materiel.net ne l'ont
  // pas sur leurs pages de résultats) : absent, pas juste "No Rating", pour ces cas.
  rating?: string;
  reviewCount?: string;
  productURL: string;
  imageURL: string;
  source: string;
  sourceLogo: string;
  hiddenFees?: string;
  oldPrice?: string;
  numeric_price?: number;
  relevance_score?: number;
  isFavorite?: boolean;
  isSubscribed?: boolean;
}
