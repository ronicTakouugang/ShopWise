import { Injectable } from '@angular/core';
import { Article } from '../../pages/home/article-list/service/article';
import { ToastService } from '../toast/services/toast.service';

/**
 * État partagé de la comparaison de produits : utilisé à la fois depuis les
 * résultats de recherche et depuis la page favoris, pour que la sélection
 * survive à la navigation entre les deux.
 */
@Injectable({
  providedIn: 'root'
})
export class CompareService {
  compareList: Article[] = [];
  readonly maxCompare = 3;

  constructor(private toastService: ToastService) {}

  toggle(article: Article): void {
    const index = this.compareList.findIndex(a => a.productURL === article.productURL);
    if (index > -1) {
      this.compareList.splice(index, 1);
    } else if (this.compareList.length < this.maxCompare) {
      this.compareList.push(article);
    } else {
      this.toastService.showWarnCustom(
        `Vous pouvez comparer ${this.maxCompare} produits maximum. Retirez-en un pour en ajouter un autre.`,
        'Limite atteinte'
      );
    }
  }

  isComparing(article: Article): boolean {
    return this.compareList.some(a => a.productURL === article.productURL);
  }

  remove(article: Article): void {
    this.compareList = this.compareList.filter(a => a.productURL !== article.productURL);
  }

  clear(): void {
    this.compareList = [];
  }
}
