import {Component, CUSTOM_ELEMENTS_SCHEMA, OnInit, ViewChild} from '@angular/core';
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
  @ViewChild('searchCmp') searchCmp!: SearchComponent;
  @ViewChild('searchCmpResults') searchCmpResults!: SearchComponent;

  hasResults: boolean = false;

  constructor(private articleService: ArticleService) {}

  ngOnInit() {
    this.articleService.articleSubject.subscribe(articles => {
      this.hasResults = articles.length > 0;
    });
  }

  clearSearch() {
    this.articleService.clearArticles();
  }
}
