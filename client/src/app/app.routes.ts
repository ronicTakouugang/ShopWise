import { Routes, Router } from '@angular/router';
import { inject } from '@angular/core';
import { map } from 'rxjs';
import { AuthService } from './shareds/AuthModule/auth.service';
import { ToastService } from './shareds/toast/services/toast.service';

const authGuard = () => {
  const authService = inject(AuthService);
  const router = inject(Router);
  const toastService = inject(ToastService);
  return authService.whenAuthChecked().pipe(
    map(isAuth => {
      if (isAuth) return true;
      toastService.showWarnCustom('Connectez-vous pour accéder à cette page.', 'Connexion requise');
      return router.parseUrl('/home');
    })
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
  {
    path: "dashboard",
    canActivate: [authGuard],
    loadComponent: () => import('./pages/dashboard/dashboard.component')
      .then(m => m.DashboardComponent),
  },
  {
    path: "**",
    redirectTo: "home"
  },
];
