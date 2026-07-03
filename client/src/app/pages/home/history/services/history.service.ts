import { Injectable } from '@angular/core';
import { Histor } from './histor';
import { HttpClient } from '@angular/common/http';
import { catchError, tap, throwError, timeout } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class HistoryService {

  host = "192.168.1.135:5000";
  localHost = "127.0.0.1:5000";
  history: Histor[] = [];

  constructor(private http: HttpClient) { }

  save(histor: Histor) {
    return this.http.post(`http://${this.host}/subscribe`, null, { withCredentials: true }).pipe(
      timeout(25000),
      tap(data => {
        console.log("Subscribe response:", data);
      }),
      catchError(err => {
        console.error("Erreur lors de l'appel à /subscribe:", err);
        return throwError(() => err);
      })
    );
  }

  add(query: string) {
    this.history.push({ id: this.history.length + 1, search: query, notifications: false });
  }
}
