import {Component, CUSTOM_ELEMENTS_SCHEMA} from '@angular/core';
import {CommonModule} from '@angular/common';
import {FormsModule} from '@angular/forms';
import {ArticleService} from '../article-list/service/article.service';
import {tap} from 'rxjs';
import {HistoryService} from '../history/services/history.service';

@Component({
  selector: 'app-search',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './search.component.html',
  styleUrls: ['./search.component.scss'],
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class SearchComponent {
  product: string = '';
  disable: boolean = false;

  constructor(private articleService: ArticleService, private historyService: HistoryService) {}

  clearQuery(): void {
    this.product = '';
  }

  find(term?: string): void {
    if (term) {
      this.product = term;
    }
    if (!this.product.trim() || this.disable) return;

    console.log("Recherche de :", this.product);
    this.articleService.findProduct(this.product)
      .pipe(
        tap({
          subscribe: () => this.disable = true,
          next: () => {
            console.log("Données reçues");
            this.historyService.add(this.product);
          },
          finalize: () => this.disable = false,
        })
      )
      .subscribe({
        next: () => this.articleService.next(),
        error: () => this.articleService.errorSubject.next()
      });
  }
}

