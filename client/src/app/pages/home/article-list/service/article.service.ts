import {Injectable} from '@angular/core';
import {Article} from './article';
import {catchError, Subject, tap, throwError, timeout} from 'rxjs';
import {HttpClient, HttpParams} from '@angular/common/http';
import { environment } from '../../../../../environments/environment';
import {HistoryService} from '../../history/services/history.service';

@Injectable({
  providedIn: 'root'
})
export class ArticleService {

  private articles:Article[] = [];
  public articleSubject:Subject<Article[]> = new Subject<Article[]>();
  public errorSubject:Subject<void> = new Subject<void>();
  private apiUrl = environment.apiUrl;

  // true dès qu'une recherche a été lancée (même sans résultat/en erreur) : sert à
  // distinguer "aucun résultat trouvé" d'un "aucune recherche effectuée pour l'instant"
  // (page d'accueil / retour à l'accueil). Ne doit être modifié qu'ici et dans
  // clearArticles(), jamais déduit d'une émission de articleSubject/errorSubject :
  // ArticleListComponent rebroadcaste aussi les articles actuels (vides) à chaque
  // montage via next(), ce qui ne constitue pas une recherche.
  hasSearched: boolean = false;

  constructor(private http:HttpClient, private historyService: HistoryService) { }

  clearArticles() {
    this.articles = [];
    this.hasSearched = false;
    this.next();
  }

  next(){

    this.articleSubject.next(this.articles.slice());
  }

  findProduct(product:string){
    this.hasSearched = true;
    const params = new HttpParams().set('query', product);
    console.log("find2",product);
    return this.http.get<Article[]>(`${this.apiUrl}/search`, { params }).pipe(
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

  /**
   * Déclenche une recherche indépendamment de tout composant (utilisé par l'historique
   * et les suggestions de la page d'accueil, qui n'ont pas de référence à SearchComponent).
   */
  search(term: string): void {
    if (!term || !term.trim()) return;
    this.findProduct(term)
      .pipe(
        tap(() => this.historyService.add(term))
      )
      .subscribe({
        next: () => this.next(),
        error: () => this.errorSubject.next()
      });
  }
}
