import {
  Component,
  CUSTOM_ELEMENTS_SCHEMA,
  EventEmitter,
  Input,
  Output,
} from '@angular/core';
import {SignOnComponent} from "./sign-on/sign-on.component";
import {DialogModule} from "primeng/dialog";
import {ButtonModule} from "primeng/button";
import {SignInComponent} from "./sign-in/sign-in.component";

@Component({
  selector: 'app-auth-form',
  standalone: true,
  imports: [
    SignOnComponent,
    DialogModule,
    ButtonModule,
    SignInComponent,
  ],
  schemas:[CUSTOM_ELEMENTS_SCHEMA],
  templateUrl: './auth-form.component.html',
  styleUrl: './auth-form.component.scss'
})
export class AuthFormComponent{

  @Input("authForm")
  isVisible!:boolean;
  @Input("hadAcc")
  hadAccount!:boolean;
  @Output()
  closeEvent = new EventEmitter<boolean>()
  @Output()
  changeFormEvent = new EventEmitter<boolean>();


  constructor() {
  }

  close($event: any) {
    this.closeEvent.emit(false);
  }

  change($event: boolean) {
    this.changeFormEvent.emit($event);
  }
}
