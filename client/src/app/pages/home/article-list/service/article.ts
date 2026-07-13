export interface Article {
  description: string;
  price: string;
  rating: string;
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
