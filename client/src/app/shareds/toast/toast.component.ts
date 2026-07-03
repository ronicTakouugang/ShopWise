import {Component, CUSTOM_ELEMENTS_SCHEMA} from '@angular/core';
import {ToastService} from './services/toast.service';
import {MessageService} from 'primeng/api';

@Component({
  selector: 'app-toast',
  imports: [],
  templateUrl: './toast.component.html',
  standalone: true,
  styleUrl: './toast.component.scss',
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class ToastComponent {


}
