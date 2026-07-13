import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { MessageService } from 'primeng/api';
import { environment } from '../../../../../environments/environment';

import { ArticleComponent } from './article.component';
import { Article } from '../service/article';

describe('ArticleComponent', () => {
  let component: ArticleComponent;
  let fixture: ComponentFixture<ArticleComponent>;
  let httpMock: HttpTestingController;

  const sampleArticle: Article = {
    description: 'Casque', price: '19,99 €', rating: '4.5',
    productURL: 'https://x', imageURL: 'img', source: 'Amazon', sourceLogo: 'logo'
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ArticleComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), MessageService]
    })
    .compileComponents();

    httpMock = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(ArticleComponent);
    httpMock.expectOne(`${environment.apiUrl}/status`).flush({ isAuth: false });
    component = fixture.componentInstance;
    component.article = sampleArticle;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('initializes isFavorite/isSubscribed from the article input', () => {
    expect(component.isFavorite).toBeFalse();
    expect(component.isSubscribed).toBeFalse();
  });

  it('toggleSubscription does nothing (and warns) when not authenticated', () => {
    const event = new Event('click');
    component.toggleSubscription(event);
    httpMock.expectNone(`${environment.apiUrl}/subscribe`);
    expect(component.isSubscribed).toBeFalse();
  });
});
