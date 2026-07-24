import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { ChartModule } from 'primeng/chart';
import { environment } from '../../../environments/environment';

interface CrossRetailerDeal {
  canonical_title: string;
  cheapest_source: string;
  cheapest_price: number;
  priciest_source: string;
  priciest_price: number;
  savings: number;
}

interface AnalyticsSummary {
  top_searches: { query: string; count: number }[];
  source_stats: { source: string; product_count: number; avg_price: number; min_price: number; max_price: number }[];
  recent_price_drops: number;
  tracked_subscriptions: number;
  tracked_favorites: number;
  cross_retailer_deals: CrossRetailerDeal[];
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink, ChartModule],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss'
})
export class DashboardComponent implements OnInit {
  apiUrl = environment.apiUrl;
  loading = true;
  loadError = false;
  summary: AnalyticsSummary | null = null;

  topSearchesChart: any = null;
  sourceStatsChart: any = null;
  chartOptions: any = {
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: '#6b7280' } },
      y: { ticks: { color: '#6b7280' }, beginAtZero: true }
    }
  };

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.loadSummary();
  }

  loadSummary() {
    this.loading = true;
    this.loadError = false;
    this.http.get<AnalyticsSummary>(`${this.apiUrl}/analytics/summary`)
      .subscribe({
        next: (data) => {
          this.summary = data;
          this.buildCharts(data);
          this.loading = false;
        },
        error: (err) => {
          console.error('Erreur lors du chargement des statistiques', err);
          this.loading = false;
          this.loadError = true;
        }
      });
  }

  private buildCharts(data: AnalyticsSummary) {
    this.topSearchesChart = {
      labels: data.top_searches.map(s => s.query),
      datasets: [{
        label: 'Recherches',
        data: data.top_searches.map(s => s.count),
        backgroundColor: '#4632e2'
      }]
    };

    this.sourceStatsChart = {
      labels: data.source_stats.map(s => s.source),
      datasets: [{
        label: 'Prix moyen (€)',
        data: data.source_stats.map(s => Math.round((s.avg_price || 0) * 100) / 100),
        backgroundColor: '#22c55e'
      }]
    };
  }
}
