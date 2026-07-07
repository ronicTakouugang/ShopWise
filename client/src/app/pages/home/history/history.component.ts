import {Component, CUSTOM_ELEMENTS_SCHEMA, Input, OnInit} from '@angular/core';
import {Panel} from 'primeng/panel';
import {AuthService} from '../../../shareds/AuthModule/auth.service';
import {Checkbox} from 'primeng/checkbox';
import {Histor} from './services/histor';
import {FormsModule} from '@angular/forms';
import {HistoryService} from './services/history.service';
import {SearchComponent} from '../search/search.component';


@Component({
  selector: 'app-history',
  imports: [
    Panel,
    Checkbox,
    FormsModule
  ],
  templateUrl: './history.component.html',
  standalone: true,
  styleUrl: './history.component.scss',
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class HistoryComponent implements OnInit{

  @Input() searchCmp!: SearchComponent;

  constructor(public authService: AuthService,public historyService: HistoryService) {
  }

  ngOnInit() {
  }

  save(histor: Histor) {
    this.historyService.saveToLocal(); // Sauvegarder l'état de la checkbox localement
    if(histor.notifications)
      this.historyService.save(histor).subscribe();
  }

  protected readonly history = history;
}
