import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { environment } from '../../../../environments/environment';

import { HistoryComponent } from './history.component';
import { HistoryService } from './services/history.service';

describe('HistoryComponent', () => {
  let component: HistoryComponent;
  let fixture: ComponentFixture<HistoryComponent>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HistoryComponent],
      // p-panel (PrimeNG) utilise des animations : sans provider, Angular refuse le
      // listener de transition synthétique @panelContent.done.
      providers: [provideHttpClient(), provideHttpClientTesting(), provideNoopAnimations()]
    })
    .compileComponents();

    httpMock = TestBed.inject(HttpTestingController);

    fixture = TestBed.createComponent(HistoryComponent);
    // Le constructeur d'AuthService (injecté par HistoryComponent) déclenche un appel
    // /status pour restaurer une éventuelle session : on le laisse aboutir ici.
    httpMock.expectOne(`${environment.apiUrl}/status`).flush({ isAuth: false });
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('shows the empty-history placeholder when there is no history', () => {
    TestBed.inject(HistoryService).history = [];
    fixture.detectChanges();
    const empty = fixture.nativeElement.querySelector('.empty-history');
    expect(empty).toBeTruthy();
  });

  it('lists each recent search when history has entries', () => {
    TestBed.inject(HistoryService).history = [{ id: 1, search: 'casque' }];
    fixture.detectChanges();
    const entries = fixture.nativeElement.querySelectorAll('.histor--elem');
    expect(entries.length).toBe(1);
    expect(fixture.nativeElement.querySelector('.empty-history')).toBeFalsy();
  });
});
