import { Component } from '@angular/core';
import { KpiAgentComponent } from './kpi-agent/kpi-agent.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [KpiAgentComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css',
})
export class AppComponent {}
