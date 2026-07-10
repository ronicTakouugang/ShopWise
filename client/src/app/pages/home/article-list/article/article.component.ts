import {Component, CUSTOM_ELEMENTS_SCHEMA, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {Article} from '../service/article';
import {CommonModule, DatePipe} from '@angular/common';
import {HttpClient, HttpContext} from '@angular/common/http';
import { environment } from '../../../../../environments/environment';
import {AuthService} from '../../../../shareds/AuthModule/auth.service';
import {ToastService} from '../../../../shareds/toast/services/toast.service';
import {ChartModule} from 'primeng/chart';
import {SKIP_LOADER} from '../../../../shareds/loader/services/loader.interceptor';

@Component({
  selector: 'app-article',
  imports: [
    CommonModule,
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
  apiUrl = environment.apiUrl;
  private datePipe = new DatePipe('en-US');

  constructor(private http: HttpClient, public authService: AuthService, private toastService: ToastService) {
  }

  ngOnInit() {
    this.isFavorite = this.article.isFavorite || false;
  }

  goToUrl() {
    window.open(this.article.productURL, "_blank");
  }

  toggleFavorite(event: Event) {
    event.stopPropagation();
    if (!this.authService.isAuth) {
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

  toggleHistory(event: Event) {
    event.stopPropagation();
    this.showHistory = !this.showHistory;
    if (this.showHistory && this.priceHistory.length === 0) {
      this.loadHistory();
    }
  }

  loadHistory() {
    this.http.get<any[]>(`${this.apiUrl}/price_history?productURL=${encodeURIComponent(this.article.productURL)}`, {
      context: new HttpContext().set(SKIP_LOADER, true)
    })
      .subscribe(data => {
        this.priceHistory = data;
        this.chartData = {
          labels: data.map(h => this.datePipe.transform(h.date, 'dd/MM/yy')),
          datasets: [{
            label: 'Prix',
            data: data.map(h => h.price),
            fill: false,
            borderColor: '#2563eb',
            tension: 0.3
          }]
        };
      });
  }
}
