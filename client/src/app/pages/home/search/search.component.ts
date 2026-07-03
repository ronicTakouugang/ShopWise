import {Component, CUSTOM_ELEMENTS_SCHEMA} from '@angular/core';
import {InputIcon} from 'primeng/inputicon';
import {IconField} from 'primeng/iconfield';
import {FormsModule} from '@angular/forms';
import {InputText} from 'primeng/inputtext';
import {Button} from 'primeng/button';
import {ArticleService} from '../article-list/service/article.service';
import {tap} from 'rxjs';
import {HistoryService} from '../history/services/history.service';

@Component({
  selector: 'app-search',
  imports: [
    InputIcon,
    IconField,
    FormsModule,
    InputText,
    Button
  ],
  templateUrl: './search.component.html',
  standalone: true,
  styleUrl: './search.component.scss',
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class SearchComponent {
  product:string="";
  disable=false;
  constructor(private articleService: ArticleService,private historyService: HistoryService) {
  }
  find(){
    console.log("find",this.product);
    this.articleService.findProduct(this.product)
      .pipe(
        tap(
          {
            subscribe: () => this.disable=true, // Action au début
            next: () => {
              console.log("Données reçues");
              this.historyService.add(this.product); // Ajoute la recherche dans l'historique'
            },// Optionnel, si tu veux suivre les valeurs
            finalize: () => this.disable=false, // Action à la fin
          }
        )
      )
      .subscribe(
      data => this.articleService.next()
    );
  }
}
