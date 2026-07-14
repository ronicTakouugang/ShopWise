import {Component, CUSTOM_ELEMENTS_SCHEMA, OnInit} from '@angular/core';
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
export class SearchComponent implements OnInit {
  product: string = '';
  disable: boolean = false;

  suggestions: string[] = [];
  showSuggestions: boolean = false;
  activeIndex: number = -1;
  private topSearches: string[] = [];

  constructor(private articleService: ArticleService, private historyService: HistoryService) {}

  ngOnInit(): void {
    this.articleService.getTopSearches().subscribe(terms => this.topSearches = terms);
  }

  clearQuery(): void {
    this.product = '';
    this.suggestions = [];
    this.showSuggestions = false;
    this.activeIndex = -1;
  }

  onQueryChange(): void {
    const query = this.product.trim().toLowerCase();
    this.activeIndex = -1;
    if (!query) {
      this.suggestions = [];
      this.showSuggestions = false;
      return;
    }

    const historyMatches = this.historyService.history
      .map(h => h.search)
      .filter(s => s.toLowerCase().includes(query));
    const popularMatches = this.topSearches.filter(s => s.toLowerCase().includes(query));

    // Fusionne historique local (priorité) et recherches populaires, en dédupliquant
    // (insensible à la casse) et en excluant la requête déjà tapée telle quelle.
    const seen = new Set<string>();
    this.suggestions = [...historyMatches, ...popularMatches]
      .filter(s => {
        const key = s.toLowerCase();
        if (key === query || seen.has(key)) return false;
        seen.add(key);
        return true;
      })
      .slice(0, 6);
    this.showSuggestions = this.suggestions.length > 0;
  }

  selectSuggestion(term: string): void {
    this.showSuggestions = false;
    this.activeIndex = -1;
    this.find(term);
  }

  onKeydown(event: KeyboardEvent): void {
    if (event.key === 'ArrowDown') {
      if (!this.showSuggestions) return;
      event.preventDefault();
      this.activeIndex = (this.activeIndex + 1) % this.suggestions.length;
    } else if (event.key === 'ArrowUp') {
      if (!this.showSuggestions) return;
      event.preventDefault();
      this.activeIndex = this.activeIndex <= 0 ? this.suggestions.length - 1 : this.activeIndex - 1;
    } else if (event.key === 'Enter') {
      event.preventDefault();
      if (this.showSuggestions && this.activeIndex >= 0) {
        this.selectSuggestion(this.suggestions[this.activeIndex]);
      } else {
        this.showSuggestions = false;
        this.find();
      }
    } else if (event.key === 'Escape') {
      this.showSuggestions = false;
      this.activeIndex = -1;
    }
  }

  onBlur(): void {
    // Délai pour laisser le (mousedown) d'une suggestion se déclencher avant
    // que la liste ne disparaisse (le blur de l'input arrive sinon en premier).
    setTimeout(() => this.showSuggestions = false, 150);
  }

  find(term?: string): void {
    if (term) {
      this.product = term;
    }
    if (!this.product.trim() || this.disable) return;
    this.showSuggestions = false;

    this.articleService.findProduct(this.product)
      .pipe(
        tap({
          subscribe: () => this.disable = true,
          next: () => this.historyService.add(this.product),
          finalize: () => this.disable = false,
        })
      )
      .subscribe({
        next: () => this.articleService.next(),
        error: () => this.articleService.errorSubject.next()
      });
  }
}

