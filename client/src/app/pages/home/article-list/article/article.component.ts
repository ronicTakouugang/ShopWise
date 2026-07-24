import {Component, CUSTOM_ELEMENTS_SCHEMA, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {Article} from '../service/article';
import {CommonModule, DatePipe} from '@angular/common';
import {FormsModule} from '@angular/forms';
import {HttpClient, HttpContext} from '@angular/common/http';
import { environment } from '../../../../../environments/environment';
import {AuthService} from '../../../../shareds/AuthModule/auth.service';
import {ToastService} from '../../../../shareds/toast/services/toast.service';
import {CompareService} from '../../../../shareds/compare/compare.service';
import {ChartModule} from 'primeng/chart';
import {SKIP_LOADER} from '../../../../shareds/loader/services/loader.interceptor';

// Palette fixe par enseigne pour que la couleur d'une source reste la même d'un
// graphique à l'autre (historique groupé multi-enseignes). Fallback neutre pour
// une source inconnue (nouveau scraper, etc.).
const SOURCE_COLORS: Record<string, string> = {
  'Amazon': '#ff9900',
  'Leclerc': '#0055a4',
  'Auchan': '#e2001a',
  'Glotelho': '#22c55e',
  'Materiel.net': '#7c3aed',
};
const DEFAULT_SOURCE_COLOR = '#6b7280';

@Component({
  selector: 'app-article',
  imports: [
    CommonModule,
    FormsModule,
    ChartModule
  ],
  templateUrl: './article.component.html',
  standalone: true,
  styleUrl: './article.component.scss',
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class ArticleComponent {

  @Input("article")
  article!:Article;

  @Output() favoriteChanged = new EventEmitter<boolean>();

  isFavorite: boolean = false;
  isSubscribed: boolean = false;
  thresholdPercent: number | null = null;
  showHistory: boolean = false;
  priceHistory: any[] = [];
  chartData: any = null;
  chartOptions: any = {
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: '#666' } },
      y: { ticks: { color: '#666' } }
    }
  };
  alternatives: any[] = [];
  loadingAlternatives: boolean = false;
  private alternativesLoaded: boolean = false;
  apiUrl = environment.apiUrl;
  private datePipe = new DatePipe('en-US');

  constructor(
    private http: HttpClient,
    public authService: AuthService,
    private toastService: ToastService,
    private compareService: CompareService,
  ) {
  }

  ngOnInit() {
    this.isFavorite = this.article.isFavorite || false;
    this.isSubscribed = this.article.isSubscribed || false;
  }

  goToUrl() {
    window.open(this.article.productURL, "_blank");
  }

  toggleFavorite(event: Event) {
    event.stopPropagation();
    if (!this.authService.isAuth) {
      this.toastService.showWarnCustom('Connectez-vous pour ajouter ce produit à vos favoris.', 'Connexion requise');
      return;
    }

    const context = new HttpContext().set(SKIP_LOADER, true);
    if (this.isFavorite) {
      this.http.post(`${this.apiUrl}/favorites/remove`, { productURL: this.article.productURL }, { withCredentials: true, context })
        .subscribe(() => {
          this.isFavorite = false;
          this.favoriteChanged.emit(false);
          this.toastService.showSuccessCustom('Produit retiré des favoris', 'Favoris');
        });
    } else {
      this.http.post(`${this.apiUrl}/favorites`, this.article, { withCredentials: true, context })
        .subscribe(() => {
          this.isFavorite = true;
          this.favoriteChanged.emit(true);
          this.toastService.showSuccessCustom('Produit ajouté aux favoris', 'Favoris');
        });
    }
  }

  toggleSubscription(event: Event) {
    event.stopPropagation();
    if (!this.authService.isAuth) {
      this.toastService.showWarnCustom('Connectez-vous pour activer les alertes de prix.', 'Connexion requise');
      return;
    }

    const context = new HttpContext().set(SKIP_LOADER, true);
    if (this.isSubscribed) {
      this.http.post(`${this.apiUrl}/subscribe/remove`, { productURL: this.article.productURL }, { withCredentials: true, context })
        .subscribe(() => {
          this.isSubscribed = false;
          this.toastService.showSuccessCustom('Alerte de prix désactivée', 'Alertes');
        });
    } else {
      this.http.post(`${this.apiUrl}/subscribe`, {
        productURL: this.article.productURL,
        price: this.article.price,
        threshold_percent: this.thresholdPercent
      }, { withCredentials: true, context })
        .subscribe(() => {
          this.isSubscribed = true;
          this.toastService.showSuccessCustom('Alerte de prix activée', 'Alertes');
        });
    }
  }

  onThresholdChange(value: number) {
    this.thresholdPercent = value > 0 ? value : null;
    if (this.isSubscribed) {
      const context = new HttpContext().set(SKIP_LOADER, true);
      this.http.post(`${this.apiUrl}/subscribe`, {
        productURL: this.article.productURL,
        price: this.article.price,
        threshold_percent: this.thresholdPercent
      }, { withCredentials: true, context }).subscribe();
    }
  }

  toggleHistory(event: Event) {
    event.stopPropagation();
    this.showHistory = !this.showHistory;
    if (this.showHistory && this.priceHistory.length === 0) {
      this.loadHistory();
    }
    if (this.showHistory && !this.alternativesLoaded && !this.loadingAlternatives) {
      this.loadAlternatives();
    }
  }

  loadHistory() {
    // Historique groupé (toutes enseignes rapprochées, voir product_matching_service côté
    // serveur) plutôt que le seul historique de cet article : pour un article non rapproché
    // avec un autre, le groupe ne contient que lui-même, donc le résultat est identique à
    // l'ancien /price_history - aucune régression pour le cas majoritaire.
    this.http.get<any[]>(`${this.apiUrl}/price_history/group?productURL=${encodeURIComponent(this.article.productURL)}`, {
      context: new HttpContext().set(SKIP_LOADER, true)
    })
      .subscribe(data => {
        this.priceHistory = data;
        this.chartData = this.buildGroupedChartData(data);
      });
  }

  private buildGroupedChartData(data: any[]) {
    const pointsBySource = new Map<string, any[]>();
    for (const point of data) {
      const source = point.source || this.article.source;
      if (!pointsBySource.has(source)) {
        pointsBySource.set(source, []);
      }
      pointsBySource.get(source)!.push(point);
    }

    // Les dates viennent déjà triées par le backend (ORDER BY date ASC) : l'ordre
    // d'insertion dans ce Set reste donc chronologique.
    const labels = [...new Set(data.map(h => this.datePipe.transform(h.date, 'dd/MM/yy')))];

    const datasets = Array.from(pointsBySource.entries()).map(([source, points]) => {
      const color = SOURCE_COLORS[source] || DEFAULT_SOURCE_COLOR;
      return {
        label: source,
        data: labels.map(label => {
          const point = points.find(p => this.datePipe.transform(p.date, 'dd/MM/yy') === label);
          return point ? point.price : null;
        }),
        borderColor: color,
        backgroundColor: color,
        fill: false,
        tension: 0.3,
        spanGaps: true,
      };
    });

    // Légende utile seulement à partir de 2 courbes (produit rapproché avec une autre
    // enseigne) : avec une seule source, elle n'apporterait rien (comportement identique
    // à l'ancien graphique mono-source).
    this.chartOptions = {
      ...this.chartOptions,
      plugins: { legend: { display: datasets.length > 1 } },
    };

    return { labels, datasets };
  }

  loadAlternatives() {
    this.loadingAlternatives = true;
    this.http.get<any[]>(`${this.apiUrl}/articles/alternatives?productURL=${encodeURIComponent(this.article.productURL)}`, {
      context: new HttpContext().set(SKIP_LOADER, true)
    }).subscribe({
      next: (data) => {
        this.alternatives = data;
        this.alternativesLoaded = true;
        this.loadingAlternatives = false;
      },
      error: () => {
        this.loadingAlternatives = false;
      }
    });
  }

  addToCompare(alt: any, event: Event) {
    event.stopPropagation();
    const alternativeArticle: Article = {
      description: alt.description || this.article.description,
      price: `${alt.last_price} €`,
      productURL: alt.productURL,
      imageURL: alt.imageURL || this.article.imageURL,
      source: alt.source,
      sourceLogo: alt.sourceLogo,
    };
    this.compareService.toggle(alternativeArticle);
    this.toastService.showSuccessCustom(`${alt.source} ajouté au comparateur`, 'Comparateur');
  }
}
