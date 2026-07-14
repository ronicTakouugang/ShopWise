import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { MessageService } from 'primeng/api';
import { environment } from '../../../environments/environment';

import { HomeComponent } from './home.component';
import { ArticleService } from './article-list/service/article.service';
import { AuthService } from '../../shareds/AuthModule/auth.service';

describe('HomeComponent', () => {
  let component: HomeComponent;
  let fixture: ComponentFixture<HomeComponent>;
  let articleService: ArticleService;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HomeComponent],
      // app-history (rendu quand authService.isAuth passe à true) contient un p-panel
      // PrimeNG, qui a besoin d'un provider d'animations pour ne pas planter.
      // MessageService : app-compare-bar (via ArticleListComponent) utilise
      // CompareService -> ToastService -> MessageService.
      providers: [provideHttpClient(), provideHttpClientTesting(), provideNoopAnimations(), MessageService]
    })
    .compileComponents();

    httpMock = TestBed.inject(HttpTestingController);
    articleService = TestBed.inject(ArticleService);
    fixture = TestBed.createComponent(HomeComponent);
    // AuthService (injecté par HomeComponent) déclenche un appel /status au démarrage.
    httpMock.expectOne(`${environment.apiUrl}/status`).flush({ isAuth: false });
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    // app-search (rendu deux fois dans le template : hero + résultats) recharge les
    // recherches populaires pour l'autocomplétion à chaque (re)création de l'instance,
    // donc à chaque bascule hero/résultats. Purge les requêtes en attente avant verify().
    httpMock.match(`${environment.apiUrl}/analytics/summary`).forEach(req => req.flush({ top_searches: [] }));
    httpMock.verify();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  // Régression : la page d'accueil restait cachée dès l'arrivée sur /home, sans
  // recherche réelle, pour un visiteur non connecté / sans historique.
  it('shows the hero section on a fresh load, before any search', () => {
    expect(component.articleService.hasSearched).toBeFalse();
    const hero = fixture.nativeElement.querySelector('.hero-section');
    expect(hero).toBeTruthy();
  });

  it('hides the hero and shows the results header after a real search', () => {
    articleService.findProduct('casque').subscribe();
    httpMock.expectOne(req => req.url === `${environment.apiUrl}/search`).flush([]);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.hero-section')).toBeFalsy();
    expect(fixture.nativeElement.querySelector('.results-header')).toBeTruthy();
  });

  it('clearSearch() restores the hero section', () => {
    articleService.findProduct('casque').subscribe();
    httpMock.expectOne(req => req.url === `${environment.apiUrl}/search`).flush([]);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.hero-section')).toBeFalsy();

    component.clearSearch();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.hero-section')).toBeTruthy();
  });

  it('only shows the recent-searches sidebar when authenticated', () => {
    expect(fixture.nativeElement.querySelector('.wrapper--history')).toBeFalsy();

    TestBed.inject(AuthService).isAuth = true;
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.wrapper--history')).toBeTruthy();
  });
});
