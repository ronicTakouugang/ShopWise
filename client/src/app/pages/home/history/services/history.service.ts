import { Injectable } from '@angular/core';
import { Histor } from './histor';

@Injectable({
  providedIn: 'root'
})
export class HistoryService {

  history: Histor[] = [];

  constructor() {
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

  add(query: string) {
    // Éviter les doublons consécutifs ou identiques
    if (this.history.find(h => h.search === query)) {
      return;
    }
    this.history.unshift({ id: Date.now(), search: query });
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

  remove(id: number) {
    this.history = this.history.filter(h => h.id !== id);
    this.saveToLocal();
  }
}
