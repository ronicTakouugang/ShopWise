import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { environment } from '../../../../../environments/environment';

import { ArticleService } from './article.service';
import { Article } from './article';

describe('ArticleService', () => {
  let service: ArticleService;
  let httpMock: HttpTestingController;

  const sampleArticle: Article = {
    description: 'Casque', price: '19,99 €', rating: '4.5',
    productURL: 'https://x', imageURL: 'img', source: 'Amazon', sourceLogo: 'logo'
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()]
    });
    service = TestBed.inject(ArticleService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  // Régression : ArticleListComponent rebroadcaste les articles courants (vides) à
  // chaque montage via next(), ce qui ne doit jamais être confondu avec une vraie
  // recherche - sinon la page d'accueil se cache derrière un faux "aucun résultat".
  it('next() alone (resync on mount) does not set hasSearched', () => {
    expect(service.hasSearched).toBeFalse();
    service.next();
    expect(service.hasSearched).toBeFalse();
  });

  it('findProduct() marks hasSearched true immediately, before the response arrives', () => {
    expect(service.hasSearched).toBeFalse();
    service.findProduct('casque').subscribe();
    expect(service.hasSearched).toBeTrue();
    httpMock.expectOne(req => req.url === `${environment.apiUrl}/search`).flush([sampleArticle]);
  });

  it('findProduct() sets hasSearched true even when the search errors out', () => {
    service.findProduct('casque').subscribe({ error: () => {} });
    expect(service.hasSearched).toBeTrue();
    httpMock.expectOne(req => req.url === `${environment.apiUrl}/search`)
      .flush('error', { status: 500, statusText: 'Server Error' });
  });

  it('clearArticles() resets hasSearched to false and broadcasts an empty list', () => {
    service.findProduct('casque').subscribe();
    httpMock.expectOne(req => req.url === `${environment.apiUrl}/search`).flush([sampleArticle]);
    expect(service.hasSearched).toBeTrue();

    let broadcast: Article[] | undefined;
    service.articleSubject.subscribe(articles => broadcast = articles);
    service.clearArticles();

    expect(service.hasSearched).toBeFalse();
    expect(broadcast).toEqual([]);
  });

  it('search() ignores a blank term without making an HTTP call', () => {
    service.search('   ');
    httpMock.expectNone(`${environment.apiUrl}/search?query=%20%20%20`);
    expect(service.hasSearched).toBeFalse();
  });

  it('search() sets hasSearched and broadcasts results on success', () => {
    let broadcast: Article[] | undefined;
    service.articleSubject.subscribe(articles => broadcast = articles);

    service.search('casque');
    expect(service.hasSearched).toBeTrue();

    httpMock.expectOne(req => req.url === `${environment.apiUrl}/search`).flush([sampleArticle]);
    expect(broadcast).toEqual([sampleArticle]);
  });
});
