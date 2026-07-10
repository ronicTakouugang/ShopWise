import {Component, CUSTOM_ELEMENTS_SCHEMA, OnInit} from '@angular/core';
import {Panel} from 'primeng/panel';
import {FormsModule} from '@angular/forms';
import {AuthService} from '../../../shareds/AuthModule/auth.service';
import {Histor} from './services/histor';
import {HistoryService} from './services/history.service';
import {ArticleService} from '../article-list/service/article.service';
import {ToastService} from '../../../shareds/toast/services/toast.service';


@Component({
  selector: 'app-history',
  imports: [
    Panel,
    FormsModule
  ],
  templateUrl: './history.component.html',
  standalone: true,
  styleUrl: './history.component.scss',
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class HistoryComponent implements OnInit{

  constructor(public authService: AuthService,public historyService: HistoryService, private toastService: ToastService, public articleService: ArticleService) {
  }

  ngOnInit() {
  }

  toggleNotifications(histor: Histor) {
    if (!this.authService.isAuth) {
      this.toastService.showWarnCustom('Connectez-vous pour activer les alertes de prix.', 'Connexion requise');
      return;
    }
    histor.notifications = !histor.notifications;
    this.historyService.saveToLocal();
    if (histor.notifications)
      this.historyService.save(histor).subscribe();
  }

  onThresholdChange(histor: Histor, value: number) {
    histor.thresholdPercent = value > 0 ? value : null;
    this.historyService.saveToLocal();
    if (histor.notifications) {
      this.historyService.save(histor).subscribe();
    }
  }

  remove(histor: Histor) {
    this.historyService.remove(histor.id);
  }

  clear() {
    this.historyService.clearHistory();
  }

  relativeTime(id: number): string {
    const diffMs = Date.now() - id;
    const minutes = Math.floor(diffMs / 60000);
    if (minutes < 1) return 'à l\'instant';
    if (minutes < 60) return `il y a ${minutes} min`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `il y a ${hours} h`;
    const days = Math.floor(hours / 24);
    if (days === 1) return 'hier';
    if (days < 7) return `il y a ${days} j`;
    const weeks = Math.floor(days / 7);
    return `il y a ${weeks} sem`;
  }
}
