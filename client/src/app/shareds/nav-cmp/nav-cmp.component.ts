import {Component, CUSTOM_ELEMENTS_SCHEMA, EventEmitter, Output, OnInit} from '@angular/core';
import {Button} from 'primeng/button';
import {Toolbar} from 'primeng/toolbar';
import {AuthService} from '../AuthModule/auth.service';
import {HistoryService} from '../../pages/home/history/services/history.service';
import {Avatar} from 'primeng/avatar';
import {Menu} from 'primeng/menu';
import {MenuItem} from 'primeng/api';
import {BadgeModule} from 'primeng/badge';
import {Badge} from 'primeng/badge';
import {Popover} from 'primeng/popover';
import {CommonModule} from '@angular/common';
import {Router, RouterLink, RouterLinkActive} from '@angular/router';
import {HttpClient} from '@angular/common/http';
import {environment} from '../../../environments/environment';
import {ThemeService} from '../theme/theme.service';

interface AppNotification {
  id: number;
  message: string;
  productURL: string;
  date: string;
  is_read: number;
}

@Component({
  selector: 'app-nav-cmp',
  imports: [
    Button,
    Toolbar,
    Avatar,
    Menu,
    CommonModule,
    BadgeModule,
    Badge,
    Popover,
    RouterLink,
    RouterLinkActive
  ],
  templateUrl: './nav-cmp.component.html',
  standalone: true,
  styleUrl: './nav-cmp.component.scss',
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class NavCmpComponent implements OnInit {
  notifications: AppNotification[] = [];
  apiUrl = environment.apiUrl;

  get unreadCount(): number {
    return this.notifications.filter(n => !n.is_read).length;
  }

  userMenuItems: MenuItem[] = [
    {
      label: 'Mon Profil',
      icon: 'pi pi-user',
      command: () => {
        this.router.navigate(['/profile']);
      }
    },
    {
      separator: true
    },
    {
      label: 'Déconnexion',
      icon: 'pi pi-power-off',
      command: () => {
        this.signOut();
      }
    }
  ];

  constructor(public authSer:AuthService, public router: Router, private historyService: HistoryService, private http: HttpClient, public themeService: ThemeService) {
  }

  ngOnInit() {
    this.authSer.whenAuthChecked().subscribe(isAuth => {
      if (isAuth) {
        this.loadNotifications();
      }
    });
  }

  loadNotifications() {
    this.http.get<AppNotification[]>(`${this.apiUrl}/notifications`, { withCredentials: true })
      .subscribe(data => {
        this.notifications = data;
      });
  }

  markAsRead() {
    if (this.unreadCount === 0) return;
    this.http.post(`${this.apiUrl}/notifications/read`, null, { withCredentials: true })
      .subscribe(() => {
        this.notifications = this.notifications.map(n => ({ ...n, is_read: 1 }));
      });
  }

  openNotification(notification: AppNotification) {
    if (notification.productURL) {
      window.open(notification.productURL, '_blank');
    }
  }

  relativeTime(dateStr: string): string {
    const parsed = new Date(dateStr.replace(' ', 'T') + 'Z');
    const diffMs = Date.now() - parsed.getTime();
    const minutes = Math.floor(diffMs / 60000);
    if (minutes < 1) return 'à l\'instant';
    if (minutes < 60) return `il y a ${minutes} min`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `il y a ${hours} h`;
    const days = Math.floor(hours / 24);
    if (days === 1) return 'hier';
    return `il y a ${days} j`;
  }

  @Output()
  inFormEvent = new EventEmitter<boolean>();
  @Output()
  onFormEvent = new EventEmitter<boolean>();

  signIn() {
    this.inFormEvent.emit(true);
  }

  signOn() {
    this.onFormEvent.emit(true);
  }

  signOut() {
    this.authSer.signOut().subscribe({
      next: () => {
        // On ne vide plus l'historique local à la déconnexion pour qu'il persiste
        // this.historyService.clearHistory();
        this.router.navigate(['/home']).then(() => {
          // Utiliser reload si nécessaire pour réinitialiser complètement l'état de l'application
          // ou s'assurer que tous les services sont au courant du changement d'état.
          window.location.reload();
        });
      },
      error: () => {
        // Même en cas d'erreur côté serveur, on redirige et on reset l'état local
        this.authSer.isAuth = false;
        this.router.navigate(['/home']).then(() => {
          window.location.reload();
        });
      }
    });
  }
}
