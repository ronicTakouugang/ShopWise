import {HttpErrorResponse, HttpEventType, HttpInterceptorFn} from '@angular/common/http';
import {inject} from '@angular/core';
import {ToastService} from './toast.service';
import {catchError, tap, throwError, timeout} from 'rxjs';

export const ToastInterceptor: HttpInterceptorFn = (req, next) => {
  const toastService = inject(ToastService);

  return next(req).pipe(
    timeout(25000),
    tap( ev =>{
      if(ev.type === HttpEventType.Response){
        console.log("interceptor show toast info");
        toastService.showInfo(ev);
      }
    }),
    catchError(error => {
      console.log("interceptor show toast error");

      let errorMessage = 'Une erreur inconnue est survenue';

      if (error instanceof HttpErrorResponse) {
        if (error.error instanceof ErrorEvent) {
          // Erreur côté client
          errorMessage = `Erreur : ${error.message}`;
        } else {
          // Erreur côté serveur
          errorMessage = `Erreur : ${error.message}`;
        }
      } else if (typeof error === 'string') {
        errorMessage = error;
      } else if (error?.message) {
        errorMessage = error.message;
      }

      console.log("Interceptor show toast error:", errorMessage);
      toastService.showError(errorMessage);
      // toastService.showError(error.toString());
      return throwError(error);
    })
  );
};
