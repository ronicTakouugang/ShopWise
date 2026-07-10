import {Component, CUSTOM_ELEMENTS_SCHEMA, OnInit} from '@angular/core';
import {ArticleComponent} from './article/article.component';
import {ArticleService} from './service/article.service';
import {Article} from './service/article';
import {FormsModule} from '@angular/forms';
import {CommonModule} from '@angular/common';
import {LoaderService} from '../../../shareds/loader/services/loader.service';

@Component({
  selector: 'app-article-list',
  imports: [
    ArticleComponent,
    FormsModule,
    CommonModule
  ],
  templateUrl: './article-list.component.html',
  standalone: true,
  styleUrl: './article-list.component.scss',
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class ArticleListComponent implements OnInit{
  allArticles:Article[]=[];
  filteredArticles:Article[]=[];
  paginatedArticles:Article[]=[];

  // Filtres et Tri
  sortBy: string = 'relevance';
  filterSource: string = 'all';

  // Pagination
  currentPage: number = 1;
  pageSize: number = 10;
  totalPages: number = 0;
  isLoading: boolean = false;
  hasError: boolean = false;

  constructor(private articlesService:ArticleService, private loaderService: LoaderService) {
  }

  ngOnInit(): void {
    this.loaderService.loadingSubject.subscribe(loading => {
      this.isLoading = loading;
      if (loading) {
        this.hasError = false;
      }
    });
    this.articlesService.articleSubject.subscribe(articles => {
      this.allArticles = articles;
      this.applyFiltersAndSort();
    });
    this.articlesService.errorSubject.subscribe(() => {
      this.hasError = true;
    });
    this.articlesService.next();
  }

  applyFiltersAndSort(): void {
    let result = [...this.allArticles];

    // Filtrage par site
    if (this.filterSource !== 'all') {
      result = result.filter(a => a.source.toLowerCase() === this.filterSource.toLowerCase());
    }

    // Tri
    if (this.sortBy === 'price_asc') {
      result.sort((a, b) => (a.numeric_price || 0) - (b.numeric_price || 0));
    } else if (this.sortBy === 'price_desc') {
      result.sort((a, b) => (b.numeric_price || 0) - (a.numeric_price || 0));
    } else if (this.sortBy === 'relevance') {
      result.sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0));
    }

    this.filteredArticles = result;
    this.totalPages = Math.ceil(this.filteredArticles.length / this.pageSize);
    this.currentPage = 1;
    this.updatePagination();
  }

  updatePagination(): void {
    const startIndex = (this.currentPage - 1) * this.pageSize;
    this.paginatedArticles = this.filteredArticles.slice(startIndex, startIndex + this.pageSize);
  }

  nextPage(): void {
    if (this.currentPage < this.totalPages) {
      this.currentPage++;
      this.updatePagination();
    }
  }

  prevPage(): void {
    if (this.currentPage > 1) {
      this.currentPage--;
      this.updatePagination();
    }
  }

  get sources(): string[] {
    return [...new Set(this.allArticles.map(a => a.source))];
  }
}
