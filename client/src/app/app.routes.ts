import { Routes, Router } from '@angular/router';
import { inject } from '@angular/core';
import { map } from 'rxjs';
import { AuthService } from './shareds/AuthModule/auth.service';

const authGuard = () => {
  const authService = inject(AuthService);
  const router = inject(Router);
  return authService.whenAuthChecked().pipe(
    map(isAuth => isAuth ? true : router.parseUrl('/home'))
  );
};

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
    canActivate: [authGuard],
    loadComponent: () => import('./pages/favorites/favorites.component')
      .then(m => m.FavoritesComponent),
  },
  {
    path: "profile",
    canActivate: [authGuard],
    loadComponent: () => import('./pages/profile/profile.component')
      .then(m => m.ProfileComponent),
  },
];
