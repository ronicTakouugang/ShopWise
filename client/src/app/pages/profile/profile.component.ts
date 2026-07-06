import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../../shareds/AuthModule/auth.service';
import { InputTextModule } from 'primeng/inputtext';
import { CheckboxModule } from 'primeng/checkbox';
import { ButtonModule } from 'primeng/button';
import { MessageService } from 'primeng/api';
import { ToastModule } from 'primeng/toast';

import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, FormsModule, InputTextModule, CheckboxModule, ButtonModule, ToastModule, RouterLink],
  providers: [MessageService],
  templateUrl: './profile.component.html',
  styleUrl: './profile.component.scss'
})
export class ProfileComponent implements OnInit {
  profile = {
    display_name: '',
    notifications_enabled: true
  };
  apiUrl = environment.apiUrl;
  loading: boolean = false;

  constructor(
    private http: HttpClient,
    public authService: AuthService,
    private messageService: MessageService
  ) {}

  ngOnInit(): void {
    this.loadProfile();
  }

  loadProfile() {
    this.http.get<any>(`${this.apiUrl}/profile`, { withCredentials: true })
      .subscribe(data => {
        this.profile.display_name = data.display_name;
        this.profile.notifications_enabled = !!data.notifications_enabled;
      });
  }

  saveProfile() {
    this.loading = true;
    this.http.post(`${this.apiUrl}/profile`, this.profile, { withCredentials: true })
      .subscribe({
        next: () => {
          this.loading = false;
          this.messageService.add({severity:'success', summary: 'Succès', detail: 'Profil mis à jour'});
          // Optionnel : mettre à jour le nom dans le service d'auth pour le header
          this.authService.username = this.authService.username.includes('@') ? this.profile.display_name + '@' + this.authService.username.split('@')[1] : this.profile.display_name;
        },
        error: () => {
          this.loading = false;
          this.messageService.add({severity:'error', summary: 'Erreur', detail: 'Échec de la mise à jour'});
        }
      });
  }

  changePassword() {
    this.http.post(`${this.apiUrl}/forgot_password`, { email: this.authService.username }, { withCredentials: true })
      .subscribe({
        next: () => {
          this.messageService.add({severity:'info', summary: 'Email envoyé', detail: 'Un lien de réinitialisation a été envoyé à votre email'});
        },
        error: () => {
          this.messageService.add({severity:'error', summary: 'Erreur', detail: 'Échec de l\'envoi de l\'email'});
        }
      });
  }
}
