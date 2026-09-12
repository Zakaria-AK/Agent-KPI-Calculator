export type StepStatus = 'pending' | 'running' | 'retrying' | 'succeeded' | 'failed';

export interface StepViewModel {
  index: number;
  description: string;
  codeAttempts: string[];
  status: StepStatus;
  error?: string;
  result?: unknown;
}

export type RunStatus = 'idle' | 'running' | 'done' | 'failed' | 'error';

export interface AgentEvent {
  node: string;
  data: Record<string, unknown>;
}

export interface DataFramePreview {
  __type__: 'dataframe';
  shape: [number, number];
  columns: string[];
  preview: Record<string, unknown>[];
}

export interface SeriesPreview {
  __type__: 'series';
  name: string | null;
  length: number;
  preview: Record<string, unknown>;
}

export function isDataFramePreview(value: unknown): value is DataFramePreview {
  return !!value && typeof value === 'object' && (value as { __type__?: string }).__type__ === 'dataframe';
}

export function isSeriesPreview(value: unknown): value is SeriesPreview {
  return !!value && typeof value === 'object' && (value as { __type__?: string }).__type__ === 'series';
}
