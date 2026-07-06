import {Component, EventEmitter, Output} from '@angular/core';
import {ButtonModule} from "primeng/button";
import {CardModule} from "primeng/card";
import {InputGroupAddonModule} from "primeng/inputgroupaddon";
import {InputGroupModule} from "primeng/inputgroup";
import {InputTextModule} from "primeng/inputtext";
import {PasswordModule} from "primeng/password";
import {SharedModule} from "primeng/api";
import {AuthService} from '../../auth.service';
import {ToastService} from '../../../toast/services/toast.service';
import {catchError, tap, throwError} from 'rxjs';
import {FormsModule} from '@angular/forms';

@Component({
  selector: 'app-sign-on',
  standalone: true,
  imports: [
    ButtonModule,
    CardModule,
    InputGroupAddonModule,
    InputGroupModule,
    InputTextModule,
    PasswordModule,
    SharedModule,
    FormsModule
  ],
  templateUrl: './sign-on.component.html',
  styleUrl: './sign-on.component.scss'
})
export class SignOnComponent {

  email: string="";
  password: string="";

  constructor(private authService: AuthService, private toastService: ToastService) {
  }

  @Output()
  closeEvent = new EventEmitter<boolean>();
  closeModal() {
    this.closeEvent.emit(false);
  }

  @Output()
  changeFormEvent = new EventEmitter<boolean>();
  changeFormModal() {
    this.changeFormEvent.emit(true);
  }
  loading: boolean = false;
  errorMessage: string = "";

  signOn(){
    this.loading = true;
    this.errorMessage = "";
    this.authService.signOn(this.email,this.password).pipe(
      tap(data =>{
          this.loading = false;
          this.toastService.showSuccess();
          this.closeModal();
        }
      ),
      catchError((err: any) => {
        this.loading = false;
        // L'intercepteur gère déjà l'affichage du toast d'erreur
        return throwError(() => err);
      })
    ).subscribe();
  }
}
