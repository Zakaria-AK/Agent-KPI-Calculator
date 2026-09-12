import { Injectable } from '@angular/core';
import { AgentEvent } from './models';

const API_BASE = 'http://localhost:8000/api';

@Injectable({ providedIn: 'root' })
export class KpiAgentService {
  async startRun(question: string, useSample: boolean, files: File[]): Promise<string> {
    const form = new FormData();
    form.set('question', question);
    form.set('use_sample', String(useSample));
    for (const file of files) {
      form.append('files', file, file.name);
    }

    const response = await fetch(`${API_BASE}/runs`, { method: 'POST', body: form });
    if (!response.ok) {
      const body = await response.text();
      throw new Error(`Failed to start run (${response.status}): ${body}`);
    }
    const body = (await response.json()) as { run_id: string };
    return body.run_id;
  }

  /** Opens the SSE stream for a run. Returns a function that closes it early. */
  streamRun(
    runId: string,
    onEvent: (event: AgentEvent) => void,
    onDone: () => void,
    onError: () => void
  ): () => void {
    const source = new EventSource(`${API_BASE}/runs/${runId}/stream`);

    source.onmessage = (message) => {
      onEvent(JSON.parse(message.data) as AgentEvent);
    };
    source.addEventListener('done', () => {
      source.close();
      onDone();
    });
    source.onerror = () => {
      source.close();
      onError();
    };

    return () => source.close();
  }
}
