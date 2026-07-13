import { TestBed } from '@angular/core/testing';
import { MessageService } from 'primeng/api';

import { ToastService } from './toast.service';

describe('ToastService', () => {
  let service: ToastService;
  let messageService: MessageService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [MessageService]
    });
    service = TestBed.inject(ToastService);
    messageService = TestBed.inject(MessageService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('showSuccessCustom adds a success message with the given detail', () => {
    spyOn(messageService, 'add');
    service.showSuccessCustom('Produit ajouté', 'Favoris');
    expect(messageService.add).toHaveBeenCalledWith({
      severity: 'success', summary: 'Favoris', detail: 'Produit ajouté'
    });
  });

  it('showWarnCustom adds a warning message with the given detail', () => {
    spyOn(messageService, 'add');
    service.showWarnCustom('Connectez-vous', 'Connexion requise');
    expect(messageService.add).toHaveBeenCalledWith({
      severity: 'warn', summary: 'Connexion requise', detail: 'Connectez-vous'
    });
  });
});
