import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { environment } from '../../../environments/environment';

import { NavCmpComponent } from './nav-cmp.component';

describe('NavCmpComponent', () => {
  let component: NavCmpComponent;
  let fixture: ComponentFixture<NavCmpComponent>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NavCmpComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])]
    })
    .compileComponents();

    httpMock = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(NavCmpComponent);
    httpMock.expectOne(`${environment.apiUrl}/status`).flush({ isAuth: false });
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('does not load notifications when the user is not authenticated', () => {
    httpMock.expectNone(`${environment.apiUrl}/notifications`);
    expect(component.notifications).toEqual([]);
  });
});
