import {Component, CUSTOM_ELEMENTS_SCHEMA} from '@angular/core';
import {ArticleListComponent} from './article-list/article-list.component';
import {SearchComponent} from './search/search.component';
import {LoaderComponent} from '../../shareds/loader/loader.component';
import {HistoryComponent} from './history/history.component';

@Component({
  selector: 'app-home',
  imports: [
    ArticleListComponent,
    SearchComponent,
    LoaderComponent,
    HistoryComponent,
  ],
  templateUrl: './home.component.html',
  standalone: true,
  styleUrl: './home.component.scss',
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class HomeComponent{

}
