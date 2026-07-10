import {Component, CUSTOM_ELEMENTS_SCHEMA, OnInit} from '@angular/core';
import {ArticleListComponent} from './article-list/article-list.component';
import {SearchComponent} from './search/search.component';
import {HistoryComponent} from './history/history.component';
import {ArticleService} from './article-list/service/article.service';
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
export class HomeComponent implements OnInit {
  // true dès qu'une recherche a été effectuée (même sans résultat), pour ne pas
  // ré-afficher la page d'accueil par-dessus l'état "aucun résultat"/erreur.
  hasSearched: boolean = false;

  constructor(public articleService: ArticleService) {}

  ngOnInit() {
    this.articleService.articleSubject.subscribe(() => {
      this.hasSearched = true;
    });
    this.articleService.errorSubject.subscribe(() => {
      this.hasSearched = true;
    });
  }

  clearSearch() {
    this.articleService.clearArticles();
    this.hasSearched = false;
  }
}
