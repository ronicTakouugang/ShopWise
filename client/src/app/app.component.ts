import {Component, CUSTOM_ELEMENTS_SCHEMA} from '@angular/core';
import { RouterOutlet } from '@angular/router';
import {NavCmpComponent} from './shareds/nav-cmp/nav-cmp.component';
import {Toast} from 'primeng/toast';
import {MessageService} from 'primeng/api';
import {AuthFormComponent} from './shareds/AuthModule/auth-form/auth-form.component';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, NavCmpComponent, Toast, AuthFormComponent],
  templateUrl: './app.component.html',
  standalone: true,
  styleUrl: './app.component.scss',
  schemas:[CUSTOM_ELEMENTS_SCHEMA]
})
export class AppComponent{
  title = 'ShopWise';
  constructor(private messageService: MessageService) {
  }
  openForm:boolean = false;
  hadAccount:boolean = true;

  openSignInForm($event: boolean) {
    this.openForm=$event;
    this.hadAccount=true;
  }
  openSignOnForm($event: boolean) {
    this.openForm=$event;
    this.hadAccount=false;
  }
  closeModal($event: boolean) {
    this.openForm=false;
  }
  changeForm($event:boolean){
    this.hadAccount=$event;
  }
}
