import { ComponentFixture, TestBed } from '@angular/core/testing';

import { KpiAgentComponent } from './kpi-agent.component';
import { DataFramePreview, StepViewModel } from '../models';

describe('KpiAgentComponent', () => {
  let fixture: ComponentFixture<KpiAgentComponent>;
  let component: KpiAgentComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [KpiAgentComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(KpiAgentComponent);
    component = fixture.componentInstance;
  });

  it('creates', () => {
    expect(component).toBeTruthy();
  });

  it('renders a single DataFrame result as a table', () => {
    const df: DataFramePreview = {
      __type__: 'dataframe',
      shape: [2, 2],
      columns: ['a', 'b'],
      preview: [
        { a: '1', b: '2' },
        { a: '3', b: '4' },
      ],
    };
    const steps: StepViewModel[] = [
      { index: 0, description: 'step', codeAttempts: [], status: 'succeeded', result: df },
    ];
    component.steps.set(steps);
    fixture.detectChanges();

    const tables = fixture.nativeElement.querySelectorAll('table');
    expect(tables.length).toBe(1);
  });

  it('renders a list of DataFrames as multiple tables, not a raw JSON dump', () => {
    // Regression test: a step's `result` can legitimately be a *list* of
    // DataFrames (e.g. one per month). The renderer used to only special-case
    // a single DataFrame/Series at the top level and fell back to dumping
    // the whole array as unreadable pretty-printed JSON.
    const df1: DataFramePreview = { __type__: 'dataframe', shape: [1, 1], columns: ['x'], preview: [{ x: '1' }] };
    const df2: DataFramePreview = { __type__: 'dataframe', shape: [1, 1], columns: ['y'], preview: [{ y: '2' }] };
    const steps: StepViewModel[] = [
      { index: 0, description: 'step', codeAttempts: [], status: 'succeeded', result: [df1, df2] },
    ];
    component.steps.set(steps);
    fixture.detectChanges();

    const tables = fixture.nativeElement.querySelectorAll('table');
    expect(tables.length).toBe(2);
    expect((fixture.nativeElement.textContent as string)).not.toContain('__type__');
  });

  it('falls back to JSON for a plain, non-DataFrame result', () => {
    const steps: StepViewModel[] = [
      { index: 0, description: 'step', codeAttempts: [], status: 'succeeded', result: { total: 42 } },
    ];
    component.steps.set(steps);
    fixture.detectChanges();

    const pre = fixture.nativeElement.querySelector('.step-result pre');
    expect(pre?.textContent).toContain('42');
  });
});
