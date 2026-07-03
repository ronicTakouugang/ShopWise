import {Component, EventEmitter, Output} from '@angular/core';
import {CardModule} from "primeng/card";
import {ButtonModule} from "primeng/button";
import {InputGroupModule} from "primeng/inputgroup";
import {InputGroupAddonModule} from "primeng/inputgroupaddon";
import {InputTextModule} from "primeng/inputtext";
import {PasswordModule} from "primeng/password";
import {DividerModule} from "primeng/divider";
import {AuthService} from '../../auth.service';
import {FormsModule} from '@angular/forms';
import {catchError, tap, throwError} from 'rxjs';

@Component({
  selector: 'app-sign-in',
  standalone: true,
  imports: [
    CardModule,
    ButtonModule,
    InputGroupModule,
    InputGroupAddonModule,
    InputTextModule,
    PasswordModule,
    DividerModule,
    FormsModule
  ],
  templateUrl: './sign-in.component.html',
  styleUrl: './sign-in.component.scss'
})
export class SignInComponent {

  email: string = "";
  password: string = "";
  constructor(private authService:AuthService) {
  }

  @Output()
  closeEvent = new EventEmitter<boolean>();
  @Output()
  changeFormEvent = new EventEmitter<boolean>();

  closeModal() {
    this.closeEvent.emit(false);
  }

  changeFormModal() {
    this.changeFormEvent.emit(false);
  }

  loading: boolean = false;
  errorMessage: string = "";

  auth(){
    this.loading = true;
    this.errorMessage = "";
    this.authService.signIn(this.email,this.password).pipe(
      tap(data =>{
          this.loading = false;
          this.closeModal();
        }
      ),
      catchError((err: any) => {
        this.loading = false;
        this.errorMessage = err.error?.error || err.message || "Erreur de connexion.";
        return throwError(() => err);
      })
    ).subscribe();
  }
}
