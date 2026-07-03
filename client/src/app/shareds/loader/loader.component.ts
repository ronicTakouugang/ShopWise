import {Component, CUSTOM_ELEMENTS_SCHEMA, OnInit} from '@angular/core';
import {LoaderService} from './services/loader.service';
import {ProgressSpinner} from 'primeng/progressspinner';

@Component({
  selector: 'app-loader',
  imports: [
    ProgressSpinner
  ],
  templateUrl: './loader.component.html',
  standalone: true,
  styleUrl: './loader.component.scss',
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class LoaderComponent implements OnInit{

  isLoading: boolean = false;

  constructor(private loaderService: LoaderService) {
  }

  ngOnInit(): void {
    this.loaderService.loadingSubject.subscribe(
      isLoading => this.isLoading = isLoading
    );
  }

}
