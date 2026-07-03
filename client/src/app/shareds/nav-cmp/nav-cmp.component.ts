import {Component, CUSTOM_ELEMENTS_SCHEMA, EventEmitter, Output} from '@angular/core';
import {Button} from 'primeng/button';
import {Toolbar} from 'primeng/toolbar';
import {AuthService} from '../AuthModule/auth.service';

@Component({
  selector: 'app-nav-cmp',
  imports: [
    Button,
    Toolbar,
  ],
  templateUrl: './nav-cmp.component.html',
  standalone: true,
  styleUrl: './nav-cmp.component.scss',
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class NavCmpComponent {

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
