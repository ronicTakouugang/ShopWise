import { Injectable } from '@angular/core';
import { MessageService } from 'primeng/api';
import {HttpResponse} from '@angular/common/http';


@Injectable({
  providedIn: 'root'
})
export class ToastService {

  constructor(private messageService: MessageService) { }

  showSuccess() {
    console.log("showSuccess");
    this.messageService.add({ severity: 'success', summary: 'Success', detail: 'Message Content' });
  }

  showInfo(response:HttpResponse<any>) {
    console.log("showInfo");
    this.messageService.add({ severity: 'info', summary: 'Info', detail: response.statusText});
  }

  showWarn() {
    this.messageService.add({ severity: 'warn', summary: 'Warn', detail: 'Message Content' });
  }

  showError(s: string) {
    this.messageService.add({ severity: 'error', summary: 'Error', detail: s });
  }

  showContrast() {
    this.messageService.add({ severity: 'contrast', summary: 'Error', detail: 'Message Content' });
  }

  showSecondary() {
    this.messageService.add({ severity: 'secondary', summary: 'Secondary', detail: 'Message Content' });
  }


}
