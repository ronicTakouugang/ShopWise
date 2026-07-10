import {HttpContextToken, HttpEventType, HttpInterceptorFn} from '@angular/common/http';
import {catchError, tap, throwError} from 'rxjs';
import {LoaderService} from './loader.service';
import {inject} from '@angular/core';

// Permet à un appel HTTP ponctuel/en arrière-plan (ex: historique de prix d'une carte)
// de ne pas déclencher le loader global de la liste de produits, qui recrée sinon
// toutes les cartes (et perd leur état local, ex: l'historique de prix ouvert).
export const SKIP_LOADER = new HttpContextToken<boolean>(() => false);

export const loaderInterceptor: HttpInterceptorFn = (req, next) => {
  const loaderService = inject(LoaderService); // Injection correcte
  if (req.context.get(SKIP_LOADER)) {
    return next(req);
  }
  return next(req).pipe(
    tap(event => {
      if(event.type === HttpEventType.Sent){
        console.log('Request started');
        loaderService.startLoading();
      }
      if (event.type === HttpEventType.Response){
        console.log('Request completed');
        loaderService.stopLoading();
      }
    }),
    catchError(error => {
      loaderService.stopLoading();
      return throwError(error);
    })
  );
};
