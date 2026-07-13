import {Component, CUSTOM_ELEMENTS_SCHEMA} from '@angular/core';
import {ArticleListComponent} from './article-list/article-list.component';
import {SearchComponent} from './search/search.component';
import {HistoryComponent} from './history/history.component';
import {ArticleService} from './article-list/service/article.service';
import {AuthService} from '../../shareds/AuthModule/auth.service';
import {CommonModule} from '@angular/common';

@Component({
  selector: 'app-home',
  imports: [
    ArticleListComponent,
    SearchComponent,
    HistoryComponent,
    CommonModule
  ],
  templateUrl: './home.component.html',
  standalone: true,
  styleUrl: './home.component.scss',
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class HomeComponent {
  constructor(public articleService: ArticleService, public authService: AuthService) {}

  clearSearch() {
    this.articleService.clearArticles();
  }
}
