import {Component, CUSTOM_ELEMENTS_SCHEMA, EventEmitter, Output} from '@angular/core';
import {Button} from 'primeng/button';
import {Toolbar} from 'primeng/toolbar';
import {AuthService} from '../AuthModule/auth.service';
import {Avatar} from 'primeng/avatar';
import {Menu} from 'primeng/menu';
import {MenuItem} from 'primeng/api';
import {CommonModule} from '@angular/common';

@Component({
  selector: 'app-nav-cmp',
  imports: [
    Button,
    Toolbar,
    Avatar,
    Menu,
    CommonModule
  ],
  templateUrl: './nav-cmp.component.html',
  standalone: true,
  styleUrl: './nav-cmp.component.scss',
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class NavCmpComponent {

  userMenuItems: MenuItem[] = [
    {
      label: 'Mon Profil',
      icon: 'pi pi-user',
    },
    {
      label: 'Mes Favoris',
      icon: 'pi pi-heart',
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

  constructor(public authSer:AuthService) {
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
    this.authSer.signOut().subscribe();
  }
}
