import { ApplicationConfig, ErrorHandler, provideZoneChangeDetection } from '@angular/core';
import { provideRouter } from '@angular/router';
import * as Sentry from '@sentry/angular';

import { routes } from './app.routes';
import {providePrimeNG} from 'primeng/config';
import {provideAnimationsAsync} from '@angular/platform-browser/animations/async';
import {MyPreset} from '../mytheme1';
import {provideHttpClient, withInterceptors} from '@angular/common/http';
import {loaderInterceptor} from './shareds/loader/services/loader.interceptor';
import {MessageService} from 'primeng/api';
import {ToastInterceptor} from './shareds/toast/services/toast.interceptor';


export const appConfig: ApplicationConfig = {
  providers: [provideZoneChangeDetection({ eventCoalescing: true }),
    MessageService,
    provideHttpClient(
      withInterceptors([loaderInterceptor,ToastInterceptor])
    ),
    provideAnimationsAsync(),
    providePrimeNG({
      ripple: true,
      theme: {
        preset: MyPreset,
        options: {
          prefix: 'p',
          darkModeSelector: '.app-dark',
          cssLayer: false
        }
      }
    }),
    provideRouter(routes),
    // Sans effet tant que Sentry.init() n'a pas été appelé (main.ts, conditionné
    // par environment.sentryDsn) : captureException est un no-op silencieux avant
    // init, donc ce provider peut rester actif inconditionnellement.
    { provide: ErrorHandler, useValue: Sentry.createErrorHandler() }]
};
