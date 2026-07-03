import { Injectable } from '@angular/core';
import {Subject} from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class LoaderService {

  private isLoading: boolean = false;
  public loadingSubject: Subject<boolean> = new Subject;

  constructor() { }

  startLoading(){
    this.isLoading = true;
    this.next();
  }
  stopLoading(){
    this.isLoading = false;
    this.next();
  }
  next(){
    this.loadingSubject.next(this.isLoading);
  }
}
