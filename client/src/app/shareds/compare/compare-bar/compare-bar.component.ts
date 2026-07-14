import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CompareService } from '../compare.service';
import { Article } from '../../../pages/home/article-list/service/article';

@Component({
  selector: 'app-compare-bar',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './compare-bar.component.html',
  styleUrl: './compare-bar.component.scss'
})
export class CompareBarComponent {
  showComparisonPanel = false;

  constructor(public compareService: CompareService) {}

  remove(article: Article): void {
    this.compareService.remove(article);
  }
}
