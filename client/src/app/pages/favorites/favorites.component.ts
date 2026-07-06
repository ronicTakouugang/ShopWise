import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { Article } from '../home/article-list/service/article';
import { ArticleComponent } from '../home/article-list/article/article.component';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-favorites',
  standalone: true,
  imports: [CommonModule, ArticleComponent, RouterLink],
  templateUrl: './favorites.component.html',
  styleUrl: './favorites.component.scss'
})
export class FavoritesComponent implements OnInit {
  favorites: Article[] = [];
  apiUrl = environment.apiUrl;
  loading: boolean = true;

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.loadFavorites();
  }

  loadFavorites() {
    this.loading = true;
    this.http.get<Article[]>(`${this.apiUrl}/favorites`, { withCredentials: true })
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
}
