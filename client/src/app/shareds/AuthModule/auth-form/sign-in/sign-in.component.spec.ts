import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { MessageService } from 'primeng/api';

import { SignInComponent } from './sign-in.component';

describe('SignInComponent', () => {
  let component: SignInComponent;
  let fixture: ComponentFixture<SignInComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SignInComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), MessageService]
    })
    .compileComponents();

    fixture = TestBed.createComponent(SignInComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('rejects an invalid email', () => {
    component.email = 'not-an-email';
    expect(component.isValidEmail()).toBeFalse();
  });

  it('accepts a well-formed email', () => {
    component.email = 'user@example.com';
    expect(component.isValidEmail()).toBeTrue();
  });

  it('requires a password of at least 6 characters', () => {
    component.password = '12345';
    expect(component.isValidPassword()).toBeFalse();
    component.password = '123456';
    expect(component.isValidPassword()).toBeTrue();
  });
});
