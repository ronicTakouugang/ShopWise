import {HttpErrorResponse, HttpEventType, HttpInterceptorFn} from '@angular/common/http';
import {inject} from '@angular/core';
import {ToastService} from './toast.service';
import {catchError, tap, throwError, timeout} from 'rxjs';

export const ToastInterceptor: HttpInterceptorFn = (req, next) => {
  const toastService = inject(ToastService);

  return next(req).pipe(
    timeout(25000),
    tap( ev =>{
      // On ne montre plus de toast info systématique sur chaque réponse pour ne pas polluer l'UI
      // if(ev.type === HttpEventType.Response){
      //   console.log("interceptor show toast info");
      //   toastService.showInfo(ev);
      // }
    }),
    catchError(error => {
      console.log("interceptor show toast error");

      let errorMessage = 'Une erreur inattendue est survenue';
      let summary = 'Erreur';

      if (error instanceof HttpErrorResponse) {
        summary = `Erreur ${error.status}`;
        switch (error.status) {
          case 0:
            errorMessage = 'Impossible de contacter le serveur. Vérifiez votre connexion.';
            break;
          case 401:
            errorMessage = 'Identifiants incorrects. Veuillez réessayer.';
            summary = 'Authentification';
            break;
          case 403:
            errorMessage = 'Vous n\'avez pas la permission d\'accéder à cette ressource.';
            break;
          case 404:
            errorMessage = 'La ressource demandée est introuvable.';
            break;
          case 429:
            errorMessage = 'Trop de requêtes. Veuillez patienter un instant.';
            break;
          case 500:
            errorMessage = 'Erreur interne du serveur. Nos techniciens sont sur le coup.';
            break;
          case 503:
            errorMessage = 'Le service est temporairement indisponible.';
            break;
          default:
            errorMessage = error.error?.error || error.message || errorMessage;
        }
      } else if (typeof error === 'string') {
        errorMessage = error;
      } else if (error?.message) {
        errorMessage = error.message;
      }

      console.log("Interceptor show toast error:", errorMessage);
      toastService.showError(errorMessage, summary);
      return throwError(() => error);
    })
  );
};
