import { ApplicationConfig, provideZoneChangeDetection } from '@angular/core';
import { provideRouter } from '@angular/router';

import { routes } from './app.routes';
import {providePrimeNG} from 'primeng/config';
import {provideAnimationsAsync} from '@angular/platform-browser/animations/async';
import {MyPreset} from '../mytheme1';
import {provideHttpClient, withInterceptors} from '@angular/common/http';
import {loaderInterceptor} from './shareds/loader/services/loader.interceptor';
import {MessageService} from 'primeng/api';
import {ToastInterceptor} from './shareds/toast/services/toast.interceptor';
import {provideAnimations} from '@angular/platform-browser/animations';


export const appConfig: ApplicationConfig = {
  providers: [provideZoneChangeDetection({ eventCoalescing: true }),
    MessageService,
    provideHttpClient(
      withInterceptors([loaderInterceptor,ToastInterceptor])
    ),
    provideAnimations(),
    provideAnimationsAsync(),
    providePrimeNG({
      ripple: true,
      theme: {
        preset: MyPreset,
        options: {
          prefix: 'p',
          darkModeSelector: 'system',
          cssLayer: false
        }
      }
    }),
    provideRouter(routes)]
};
