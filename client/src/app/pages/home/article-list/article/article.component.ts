import {Component, CUSTOM_ELEMENTS_SCHEMA, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {Article} from '../service/article';
import {CommonModule} from '@angular/common';
import {HttpClient} from '@angular/common/http';
import { environment } from '../../../../../environments/environment';
import {AuthService} from '../../../../shareds/AuthModule/auth.service';
import {ToastService} from '../../../../shareds/toast/services/toast.service';

@Component({
  selector: 'app-article',
  imports: [
    CommonModule
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
  apiUrl = environment.apiUrl;

  constructor(private http: HttpClient, public authService: AuthService, private toastService: ToastService) {
  }

  ngOnInit() {
    this.isFavorite = (this.article as any).isFavorite || false;
  }

  goToUrl() {
    window.open(this.article.productURL, "_blank");
  }

  toggleFavorite(event: Event) {
    event.stopPropagation();
    if (!this.authService.isAuth) {
      return;
    }

    if (this.isFavorite) {
      this.http.post(`${this.apiUrl}/favorites/remove`, { productURL: this.article.productURL }, { withCredentials: true })
        .subscribe(() => {
          this.isFavorite = false;
          this.favoriteChanged.emit(false);
          this.toastService.showSuccessCustom('Produit retiré des favoris', 'Favoris');
        });
    } else {
      this.http.post(`${this.apiUrl}/favorites`, this.article, { withCredentials: true })
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
    this.http.get<any[]>(`${this.apiUrl}/price_history?productURL=${encodeURIComponent(this.article.productURL)}`)
      .subscribe(data => {
        this.priceHistory = data;
      });
  }
}
