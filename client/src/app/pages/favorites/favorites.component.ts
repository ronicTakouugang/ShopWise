import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { Article } from '../home/article-list/service/article';
import { ArticleComponent } from '../home/article-list/article/article.component';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import {ToastService} from '../../shareds/toast/services/toast.service';

@Component({
  selector: 'app-favorites',
  standalone: true,
  imports: [CommonModule, ArticleComponent, RouterLink, FormsModule],
  templateUrl: './favorites.component.html',
  styleUrl: './favorites.component.scss'
})
export class FavoritesComponent implements OnInit {
  favorites: Article[] = [];
  compareList: Article[] = [];
  apiUrl = environment.apiUrl;
  loading: boolean = true;
  sortBy: string = 'date_added';
  showComparisonPanel: boolean = false;

  constructor(private http: HttpClient, private toastService: ToastService) {}

  ngOnInit(): void {
    this.loadFavorites();
  }

  loadFavorites() {
    this.loading = true;
    this.http.get<Article[]>(`${this.apiUrl}/favorites?sort=${this.sortBy}`, { withCredentials: true })
      .subscribe({
        next: (data) => {
          this.favorites = data.map(item => ({...item, isFavorite: true}));
          this.loading = false;
        },
        error: (err) => {
          console.error('Erreur lors du chargement des favoris', err);
          this.loading = false;
        }
      });
  }

  onSortChange() {
    this.loadFavorites();
  }

  toggleCompare(article: Article) {
    const index = this.compareList.findIndex(a => a.productURL === article.productURL);
    if (index > -1) {
      this.compareList.splice(index, 1);
    } else {
      if (this.compareList.length < 3) {
        this.compareList.push(article);
      }
    }
  }

  isComparing(article: Article): boolean {
    return this.compareList.some(a => a.productURL === article.productURL);
  }

  onFavoriteChanged(article: Article, isFav: boolean) {
    if (!isFav) {
      // Si le produit est retiré des favoris, on l'enlève de la liste locale
      this.favorites = this.favorites.filter(f => f.productURL !== article.productURL);

      // On l'enlève aussi de la liste de comparaison s'il y était
      this.compareList = this.compareList.filter(f => f.productURL !== article.productURL);
    }
  }
}
