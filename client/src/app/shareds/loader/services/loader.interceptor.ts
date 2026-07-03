import {HttpEventType, HttpInterceptorFn} from '@angular/common/http';
import {catchError, tap, throwError} from 'rxjs';
import {LoaderService} from './loader.service';
import {inject} from '@angular/core';

export const loaderInterceptor: HttpInterceptorFn = (req, next) => {
  const loaderService = inject(LoaderService); // Injection correcte
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
