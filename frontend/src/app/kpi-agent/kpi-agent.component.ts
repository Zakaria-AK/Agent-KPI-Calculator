import { Component, OnDestroy, computed, signal } from '@angular/core';
import { JsonPipe, NgTemplateOutlet } from '@angular/common';

import { KpiAgentService } from '../kpi-agent.service';
import {
  AgentEvent,
  DataFramePreview,
  RunStatus,
  SeriesPreview,
  StepStatus,
  StepViewModel,
  isDataFramePreview,
  isSeriesPreview,
} from '../models';

const DEFAULT_QUESTION = "What's the monthly churn rate by region for the last 12 months?";

const STATUS_LABELS: Record<StepStatus, string> = {
  pending: 'Pending',
  running: 'Running',
  retrying: 'Retrying',
  succeeded: 'Done',
  failed: 'Failed',
};

@Component({
  selector: 'app-kpi-agent',
  standalone: true,
  imports: [JsonPipe, NgTemplateOutlet],
  templateUrl: './kpi-agent.component.html',
  styleUrl: './kpi-agent.component.css',
})
export class KpiAgentComponent implements OnDestroy {
  readonly question = signal(DEFAULT_QUESTION);
  readonly useSample = signal(true);
  readonly selectedFiles = signal<File[]>([]);

  readonly runStatus = signal<RunStatus>('idle');
  readonly steps = signal<StepViewModel[]>([]);
  readonly finalReport = signal<string | null>(null);
  readonly errorMessage = signal<string | null>(null);

  readonly isRunning = computed(() => this.runStatus() === 'running');
  readonly canSubmit = computed(
    () =>
      !this.isRunning() &&
      this.question().trim().length > 0 &&
      (this.useSample() || this.selectedFiles().length > 0)
  );

  private currentStepIndex = 0;
  private closeStream: (() => void) | null = null;

  constructor(private readonly agent: KpiAgentService) {}

  ngOnDestroy(): void {
    this.closeStream?.();
  }

  onFilesSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.selectedFiles.set(input.files ? Array.from(input.files) : []);
  }

  onQuestionInput(event: Event): void {
    this.question.set((event.target as HTMLTextAreaElement).value);
  }

  statusLabel(status: StepStatus): string {
    return STATUS_LABELS[status];
  }

  asDataFrame(value: unknown): DataFramePreview | null {
    return isDataFramePreview(value) ? value : null;
  }

  asSeries(value: unknown): SeriesPreview | null {
    return isSeriesPreview(value) ? value : null;
  }

  isArray(value: unknown): value is unknown[] {
    return Array.isArray(value);
  }

  async submit(): Promise<void> {
    this.closeStream?.();
    this.steps.set([]);
    this.finalReport.set(null);
    this.errorMessage.set(null);
    this.currentStepIndex = 0;
    this.runStatus.set('running');

    let runId: string;
    try {
      runId = await this.agent.startRun(this.question().trim(), this.useSample(), this.selectedFiles());
    } catch (err) {
      this.errorMessage.set(err instanceof Error ? err.message : 'Failed to start the run.');
      this.runStatus.set('error');
      return;
    }

    this.closeStream = this.agent.streamRun(
      runId,
      (event) => this.handleEvent(event),
      () => this.handleDone(),
      () => this.handleStreamError()
    );
  }

  private handleEvent(event: AgentEvent): void {
    switch (event.node) {
      case 'planner': {
        const plan = event.data['plan'] as string[];
        this.currentStepIndex = 0;
        this.steps.set(
          plan.map((description, index) => ({
            index,
            description,
            codeAttempts: [],
            status: index === 0 ? 'running' : 'pending',
          }))
        );
        break;
      }
      case 'coder': {
        const codeAttempts = event.data['code_attempts'] as string[];
        this.patchStep(this.currentStepIndex, { codeAttempts, status: 'running' });
        break;
      }
      case 'executor': {
        const error = event.data['error'] as string | null;
        if (error) {
          this.patchStep(this.currentStepIndex, { status: 'retrying', error });
        } else {
          const stepResults = event.data['step_results'] as unknown[];
          const result = stepResults[stepResults.length - 1];
          this.patchStep(this.currentStepIndex, { status: 'succeeded', error: undefined, result });
        }
        break;
      }
      case 'advance_step': {
        const newIndex = event.data['current_step'] as number;
        this.currentStepIndex = newIndex;
        this.patchStep(newIndex, { status: 'running' });
        break;
      }
      case 'finalizer': {
        this.finalReport.set(event.data['final_report'] as string);
        this.runStatus.set('done');
        break;
      }
      case 'failure': {
        this.finalReport.set(event.data['final_report'] as string);
        this.patchStep(this.currentStepIndex, { status: 'failed' });
        this.runStatus.set('failed');
        break;
      }
    }
  }

  private patchStep(index: number, patch: Partial<StepViewModel>): void {
    this.steps.update((steps) => steps.map((step, i) => (i === index ? { ...step, ...patch } : step)));
  }

  private handleDone(): void {
    if (this.runStatus() === 'running') {
      this.runStatus.set('done');
    }
  }

  private handleStreamError(): void {
    if (this.runStatus() === 'running') {
      this.errorMessage.set('Connection to the agent was lost.');
      this.runStatus.set('error');
    }
  }
}
