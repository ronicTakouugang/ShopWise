import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { environment } from '../../../environments/environment';

import { AuthService } from './auth.service';

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()]
    });
    // Le constructeur appelle immédiatement /status pour restaurer une éventuelle
    // session : il faut le laisser en attente (flush plus bas) plutôt que le bloquer.
    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
    httpMock.expectOne(`${environment.apiUrl}/status`).flush({ isAuth: false });
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('signIn rejects an invalid email without making an HTTP call', (done) => {
    service.signIn('not-an-email', 'password123').subscribe({
      error: (err) => {
        expect(err.message).toContain('Email invalide');
        done();
      }
    });
    httpMock.expectNone(`${environment.apiUrl}/login`);
  });

  it('signIn rejects a missing password without making an HTTP call', (done) => {
    service.signIn('user@example.com', '').subscribe({
      error: (err) => {
        expect(err.message).toContain('Mot de passe requis');
        done();
      }
    });
    httpMock.expectNone(`${environment.apiUrl}/login`);
  });

  it('signIn sets isAuth and username on success', () => {
    service.signIn('user@example.com', 'password123').subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/login`);
    req.flush({ idToken: 'abc' });
    expect(service.isAuth).toBeTrue();
    expect(service.username).toBe('user@example.com');
  });

  it('signOut clears isAuth', () => {
    service.isAuth = true;
    service.signOut().subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/logout`);
    req.flush({});
    expect(service.isAuth).toBeFalse();
  });

  it('checkAuthStatus sets isAuth false when the server call fails', () => {
    service.checkAuthStatus().subscribe(isAuth => {
      expect(isAuth).toBeFalse();
    });
    const req = httpMock.expectOne(`${environment.apiUrl}/status`);
    req.flush('error', { status: 500, statusText: 'Server Error' });
    expect(service.isAuth).toBeFalse();
  });
});
