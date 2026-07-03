import {Component, CUSTOM_ELEMENTS_SCHEMA, OnInit} from '@angular/core';
import {Panel} from 'primeng/panel';
import {AuthService} from '../../../shareds/AuthModule/auth.service';
import {RadioButton} from 'primeng/radiobutton';
import {Checkbox} from 'primeng/checkbox';
import {Histor} from './services/histor';
import {FormsModule} from '@angular/forms';
import {HistoryService} from './services/history.service';


@Component({
  selector: 'app-history',
  imports: [
    Panel,
    RadioButton,
    Checkbox,
    FormsModule
  ],
  templateUrl: './history.component.html',
  standalone: true,
  styleUrl: './history.component.scss',
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class HistoryComponent implements OnInit{

  constructor(public authService: AuthService,public historyService: HistoryService) {
  }

  ngOnInit() {
  }

  save(histor: Histor) {
    if(histor.notifications)
      this.historyService.save(histor).subscribe();
  }

  protected readonly history = history;
}
