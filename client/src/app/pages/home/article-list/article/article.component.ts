import {Component, CUSTOM_ELEMENTS_SCHEMA, Input} from '@angular/core';
import {Article} from '../service/article';
import {CommonModule} from '@angular/common';
import {HttpClient} from '@angular/common/http';
import {environment} from '../../../../../environments/environment';
import {AuthService} from '../../../../shareds/AuthModule/auth.service';

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

  isFavorite: boolean = false;
  apiUrl = environment.apiUrl;

  constructor(private http: HttpClient, public authService: AuthService) {
  }

  goToUrl() {
    window.open(this.article.productURL, "_blank");
  }

  toggleFavorite(event: Event) {
    event.stopPropagation();
    if (!this.authService.isAuth) {
      // Optionnel : rediriger vers login ou afficher un message
      return;
    }

    if (this.isFavorite) {
      this.http.post(`${this.apiUrl}/favorites/remove`, { productURL: this.article.productURL }, { withCredentials: true })
        .subscribe(() => {
          this.isFavorite = false;
        });
    } else {
      this.http.post(`${this.apiUrl}/favorites`, this.article, { withCredentials: true })
        .subscribe(() => {
          this.isFavorite = true;
        });
    }
  }
}
