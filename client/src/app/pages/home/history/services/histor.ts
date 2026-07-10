export interface Histor {
  id: number;
  search: string;
  notifications:boolean;
  // Baisse minimale (%) pour déclencher une alerte. undefined/null = toute baisse alerte.
  thresholdPercent?: number | null;
}
