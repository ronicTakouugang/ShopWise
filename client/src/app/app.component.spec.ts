import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { MessageService } from 'primeng/api';
import { environment } from '../environments/environment';

import { AppComponent } from './app.component';

describe('AppComponent', () => {
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([]), MessageService],
    }).compileComponents();

    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    // AppComponent contient app-nav-cmp, qui déclenche un /status au démarrage.
    httpMock.expectOne(`${environment.apiUrl}/status`).flush({ isAuth: false });
    expect(app).toBeTruthy();
  });

  it(`should have the 'ShopWise' title`, () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    httpMock.expectOne(`${environment.apiUrl}/status`).flush({ isAuth: false });
    expect(app.title).toEqual('ShopWise');
  });

  it('renders the navigation bar', () => {
    const fixture = TestBed.createComponent(AppComponent);
    httpMock.expectOne(`${environment.apiUrl}/status`).flush({ isAuth: false });
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('app-nav-cmp')).toBeTruthy();
  });
});
