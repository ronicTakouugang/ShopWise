import { bootstrapApplication } from '@angular/platform-browser';
import * as Sentry from '@sentry/angular';
import { appConfig } from './app/app.config';
import { AppComponent } from './app/app.component';
import { environment } from './environments/environment';

// Optionnel : désactivé tant que environment.sentryDsn est vide (dev local, ou
// avant qu'un projet Sentry ait été créé pour la prod).
if (environment.sentryDsn) {
  Sentry.init({
    dsn: environment.sentryDsn,
    integrations: [Sentry.browserTracingIntegration()],
    tracesSampleRate: 0.1,
  });
}

bootstrapApplication(AppComponent, appConfig)
  .catch((err) => console.error(err));
