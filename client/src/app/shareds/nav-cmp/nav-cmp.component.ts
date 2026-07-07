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
import {CommonModule} from '@angular/common';
import {Router} from '@angular/router';
import {HttpClient} from '@angular/common/http';
import {environment} from '../../../environments/environment';

@Component({
  selector: 'app-nav-cmp',
  imports: [
    Button,
    Toolbar,
    Avatar,
    Menu,
    CommonModule,
    BadgeModule,
    Badge
  ],
  templateUrl: './nav-cmp.component.html',
  standalone: true,
  styleUrl: './nav-cmp.component.scss',
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class NavCmpComponent implements OnInit {
  notifications: any[] = [];
  apiUrl = environment.apiUrl;

  userMenuItems: MenuItem[] = [
    {
      label: 'Mon Profil',
      icon: 'pi pi-user',
      command: () => {
        this.router.navigate(['/profile']);
      }
    },
    {
      label: 'Mes Favoris',
      icon: 'pi pi-heart',
      command: () => {
        this.router.navigate(['/favorites']);
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

  constructor(public authSer:AuthService, public router: Router, private historyService: HistoryService, private http: HttpClient) {
  }

  ngOnInit() {
    if (this.authSer.isAuth) {
      this.loadNotifications();
    }
  }

  loadNotifications() {
    this.http.get<any[]>(`${this.apiUrl}/notifications`, { withCredentials: true })
      .subscribe(data => {
        this.notifications = data;
      });
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
