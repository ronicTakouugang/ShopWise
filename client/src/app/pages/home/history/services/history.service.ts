import { Injectable } from '@angular/core';
import { Histor } from './histor';
import { HttpClient } from '@angular/common/http';
import { catchError, tap, throwError, timeout } from 'rxjs';

import { environment } from '../../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class HistoryService {

  apiUrl = environment.apiUrl;
  history: Histor[] = [];

  constructor(private http: HttpClient) {
    this.loadHistory();
  }

  loadHistory() {
    const saved = localStorage.getItem('search_history');
    if (saved) {
      try {
        this.history = JSON.parse(saved);
      } catch (e) {
        console.error("Erreur lors du chargement de l'historique", e);
        this.history = [];
      }
    }
  }

  saveToLocal() {
    localStorage.setItem('search_history', JSON.stringify(this.history));
  }

  save(histor: Histor) {
    return this.http.post(`${this.apiUrl}/subscribe`, null, { withCredentials: true }).pipe(
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
    // Éviter les doublons consécutifs ou identiques
    if (this.history.find(h => h.search === query)) {
      return;
    }
    this.history.unshift({ id: Date.now(), search: query, notifications: false });
    // Limiter à 15 éléments
    if (this.history.length > 15) {
      this.history.pop();
    }
    this.saveToLocal();
  }

  clearHistory() {
    this.history = [];
    localStorage.removeItem('search_history');
  }
}
