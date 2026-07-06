import {Component, CUSTOM_ELEMENTS_SCHEMA} from '@angular/core';
import {ArticleListComponent} from './article-list/article-list.component';
import {SearchComponent} from './search/search.component';
import {HistoryComponent} from './history/history.component';

@Component({
  selector: 'app-home',
  imports: [
    ArticleListComponent,
    SearchComponent,
    HistoryComponent,
  ],
  templateUrl: './home.component.html',
  standalone: true,
  styleUrl: './home.component.scss',
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class HomeComponent{

}
