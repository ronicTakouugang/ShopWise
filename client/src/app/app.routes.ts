import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path:"",
    redirectTo: "home",
    pathMatch: "full"
  },
  {
    path: "home",
    loadComponent: () => import('./pages/home/home.component')
      .then(m => m.HomeComponent),
  },
  {
    path: "favorites",
    loadComponent: () => import('./pages/favorites/favorites.component')
      .then(m => m.FavoritesComponent),
  },
  {
    path: "profile",
    loadComponent: () => import('./pages/profile/profile.component')
      .then(m => m.ProfileComponent),
  },
];
