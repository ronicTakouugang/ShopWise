import { Injectable } from '@angular/core';
import {Subject} from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class LoaderService {

  private activeRequests: number = 0;
  public loadingSubject: Subject<boolean> = new Subject;

  constructor() { }

  startLoading(){
    this.activeRequests++;
    this.next();
  }
  stopLoading(){
    this.activeRequests = Math.max(0, this.activeRequests - 1);
    this.next();
  }
  next(){
    this.loadingSubject.next(this.activeRequests > 0);
  }
}
