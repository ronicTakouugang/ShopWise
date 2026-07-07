import {Injectable} from '@angular/core';
import {Article} from './article';
import {catchError, Subject, tap, throwError, timeout} from 'rxjs';
import {HttpClient, HttpParams} from '@angular/common/http';
import { environment } from '../../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ArticleService {

  private articles:Article[] = [];
  public articleSubject:Subject<Article[]> = new Subject<Article[]>();
  private apiUrl = environment.apiUrl;

  constructor(private http:HttpClient) { }

  clearArticles() {
    this.articles = [];
    this.next();
  }

  next(){

    this.articleSubject.next(this.articles.slice());
  }

  findProduct(product:string){
    let params = new HttpParams();
    params.set('query',product);
    console.log("find2",product);
    return this.http.get<Article[]>(`${this.apiUrl}/search?query=${product}`).pipe(
      timeout(25000),
      tap(data =>{
        console.log("find3");
        this.articles=data;
        console.log(data);
      }),
      catchError(err => {
        console.error("err",err)
        return throwError(err);
      })
    );
  }
}
