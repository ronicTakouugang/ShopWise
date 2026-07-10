import { Injectable } from '@angular/core';

const STORAGE_KEY = 'theme';
const DARK_CLASS = 'app-dark';

@Injectable({
  providedIn: 'root'
})
export class ThemeService {
  isDark: boolean = false;

  constructor() {
    const saved = localStorage.getItem(STORAGE_KEY);
    this.isDark = saved ? saved === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
    this.apply();
  }

  toggle(): void {
    this.isDark = !this.isDark;
    localStorage.setItem(STORAGE_KEY, this.isDark ? 'dark' : 'light');
    this.apply();
  }

  private apply(): void {
    document.documentElement.classList.toggle(DARK_CLASS, this.isDark);
  }
}
