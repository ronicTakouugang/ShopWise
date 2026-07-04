import {Component, CUSTOM_ELEMENTS_SCHEMA, Input} from '@angular/core';
import {Article} from '../service/article';
import {CommonModule} from '@angular/common';

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

  constructor() {
  }

  goToUrl() {
    window.open(this.article.productURL, "_blank");
  }
}
