import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { MessageService } from 'primeng/api';
import { environment } from '../../../../environments/environment';

import { ArticleListComponent } from './article-list.component';
import { ArticleService } from './service/article.service';
import { Article } from './service/article';

describe('ArticleListComponent', () => {
  let component: ArticleListComponent;
  let fixture: ComponentFixture<ArticleListComponent>;
  let articleService: ArticleService;
  let httpMock: HttpTestingController;

  const sampleArticle: Article = {
    description: 'Casque', price: '19,99 €', rating: '4.5',
    productURL: 'https://x', imageURL: 'img', source: 'Amazon', sourceLogo: 'logo'
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ArticleListComponent],
      // app-article (rendu pour chaque résultat) a besoin de MessageService (ToastService).
      providers: [provideHttpClient(), provideHttpClientTesting(), MessageService]
    })
    .compileComponents();

    httpMock = TestBed.inject(HttpTestingController);
    articleService = TestBed.inject(ArticleService);
    fixture = TestBed.createComponent(ArticleListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  // Régression : le message "Aucun résultat trouvé" ne doit jamais apparaître avant
  // qu'une recherche ait réellement été lancée (ex: sur un premier chargement de /home,
  // où ngOnInit() rebroadcaste un tableau vide juste pour se resynchroniser).
  it('shows no empty-state message before any search has happened', () => {
    expect(articleService.hasSearched).toBeFalse();
    fixture.detectChanges();
    const emptyState = fixture.nativeElement.querySelector('.search-empty-state');
    expect(emptyState).toBeFalsy();
  });

  it('shows the empty-state message once a real search found nothing', () => {
    articleService.search('introuvable');
    httpMock.expectOne(req => req.url === `${environment.apiUrl}/search`).flush([]);
    fixture.detectChanges();
    const emptyState = fixture.nativeElement.querySelector('.search-empty-state');
    expect(emptyState).toBeTruthy();
  });

  it('renders product cards once a real search found results', () => {
    articleService.search('casque');
    httpMock.expectOne(req => req.url === `${environment.apiUrl}/search`).flush([sampleArticle]);
    fixture.detectChanges();
    // app-article (une carte par résultat) injecte AuthService, qui déclenche /status.
    httpMock.expectOne(`${environment.apiUrl}/status`).flush({ isAuth: false });
    expect(fixture.nativeElement.querySelector('.search-empty-state')).toBeFalsy();
    expect(component.paginatedArticles.length).toBe(1);
  });
});
