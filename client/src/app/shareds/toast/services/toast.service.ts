import { Injectable } from '@angular/core';
import { MessageService } from 'primeng/api';
import {HttpResponse} from '@angular/common/http';


@Injectable({
  providedIn: 'root'
})
export class ToastService {

  constructor(public messageService: MessageService) { }

  showSuccess() {
    console.log("showSuccess");
    this.messageService.add({ severity: 'success', summary: 'Succès', detail: 'Opération réussie' });
  }

  showSuccessCustom(detail: string, summary: string = 'Succès') {
    this.messageService.add({ severity: 'success', summary: summary, detail: detail });
  }

  showInfo(response:HttpResponse<any>) {
    console.log("showInfo");
    this.messageService.add({ severity: 'info', summary: 'Information', detail: response.statusText});
  }

  showWarn() {
    this.messageService.add({ severity: 'warn', summary: 'Attention', detail: 'Action requise' });
  }

  showError(s: string, summary: string = 'Erreur') {
    this.messageService.add({ severity: 'error', summary: summary, detail: s });
  }

  showContrast() {
    this.messageService.add({ severity: 'contrast', summary: 'Error', detail: 'Message Content' });
  }

  showSecondary() {
    this.messageService.add({ severity: 'secondary', summary: 'Secondary', detail: 'Message Content' });
  }


}
