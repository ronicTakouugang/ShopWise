import { Injectable } from '@angular/core';
import {HttpClient} from '@angular/common/http';
import {catchError, map, Observable, of, shareReplay, tap, throwError, timeout} from 'rxjs';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class AuthService {

  apiUrl = environment.apiUrl;
  username="";
  isAuth:boolean=false;
  private authCheck$: Observable<boolean>;

  constructor(private http:HttpClient) {
    this.authCheck$ = this.checkAuthStatus();
    this.authCheck$.subscribe();
  }

  checkAuthStatus(): Observable<boolean> {
    return this.http.get<{isAuth: boolean, email?: string}>(`${this.apiUrl}/status`, { withCredentials: true })
      .pipe(
        map(res => {
          if (res.isAuth && res.email) {
            this.isAuth = true;
            this.username = res.email;
            console.log("Session restaurée pour :", res.email);
          } else {
            this.isAuth = false;
          }
          return this.isAuth;
        }),
        catchError(() => {
          console.log("Pas de session active.");
          this.isAuth = false;
          return of(false);
        }),
        shareReplay(1)
      );
  }

  /** Émet une seule fois que le statut d'authentification initial a été déterminé. */
  whenAuthChecked(): Observable<boolean> {
    return this.authCheck$;
  }

  signIn(email:string, password:string){
    const cleanEmail = email.trim();
    if (!cleanEmail || !cleanEmail.includes('@')) {
       return throwError(() => new Error("Email invalide."));
    }
    if (!password) {
       return throwError(() => new Error("Mot de passe requis."));
    }
    let body = {email: cleanEmail, password};
    console.log("Tentative de connexion pour :", cleanEmail);
    return this.http.post(`${this.apiUrl}/login`, body, { withCredentials: true }).pipe(
      timeout(25000),
      tap(data =>{
        console.log("Login réussi: ", data);
        this.isAuth=true;
        this.username=cleanEmail;
      }),
      catchError((err: any) => {
        console.error("Erreur login :", err)
        return throwError(() => err);
      })
    );
  }

  signOn(email:string, password:string){
    const cleanEmail = email.trim();
    if (!cleanEmail || !cleanEmail.includes('@')) {
       return throwError(() => new Error("Veuillez entrer un email valide."));
    }
    if (!password || password.length < 6) {
       return throwError(() => new Error("Le mot de passe doit contenir au moins 6 caractères."));
    }
    let body = {email: cleanEmail, password};
    console.log("Tentative d'inscription pour :", cleanEmail);
    return this.http.post(`${this.apiUrl}/register`, body, { withCredentials: true }).pipe(
      timeout(25000),
      tap(data =>{
        console.log("Inscription réussie: ", data);
        this.isAuth=true;
        this.username=cleanEmail;
      }),
      catchError((err: any) => {
        console.error("Erreur inscription :", err)
        return throwError(() => err);
      })
    );
  }

  signOut() {
    return this.http.post(`${this.apiUrl}/logout`, null, { withCredentials: true }).pipe(
      timeout(25000),
      tap(data =>{
        console.log("Logout réussi: ", data);
        this.isAuth=false;
      }),
      catchError((err: any) => {
        console.error("Erreur logout :", err)
        return throwError(() => err);
      })
    );
  }
}
