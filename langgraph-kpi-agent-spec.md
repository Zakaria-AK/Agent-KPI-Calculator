# Project Spec: Recursive Code-Writing KPI Agent (LangGraph)

## Purpose
A LangGraph learning project, designed to be built and referenced for the Btechnologie interview (LangChain/LangGraph — no prior professional use, but strong conceptual understanding via the analogous RLM Excel/Word agent already shipped at Renault).

The goal is not just a working demo — it's to be able to explain, in an interview, *why* each part of the graph is shaped the way it is, and how it maps onto (and improves on) the "shared mutable context + manual loop" pattern already used in production.

## Problem statement
Given one or more CSV files and a natural-language KPI question (e.g. "what's the monthly churn rate by region for the last 12 months"), the system should:
1. Break the question into an ordered plan of sub-steps.
2. Write Python code to execute each step, using results from prior steps as needed.
3. Execute that code, recover from errors by rewriting the code (recursive retry), and move to the next step once a step succeeds.
4. Once all steps succeed, synthesize a final answer/report.

## Architecture: LangGraph `StateGraph`

### Shared state
```python
class KPIAgentState(TypedDict):
    csv_paths: list[str]
    question: str
    csv_schema_preview: str        # column names/dtypes/sample rows, built once at start
    plan: list[str]                # ordered sub-steps from the planner
    current_step: int
    code_attempts: list[str]       # code written for the current step (grows on retry)
    step_results: list[Any]        # captured output of each *completed* step, available to later steps
    error: str | None              # last execution error, cleared on success
    retry_count: int               # retries for the *current* step, reset when step advances
    final_report: str | None
```

### Nodes

1. **`planner`**
   - Input: `question`, `csv_schema_preview`.
   - One LLM call. Output: ordered `plan` (list of natural-language sub-steps, e.g. `["load and clean churn CSV", "compute monthly churn rate", "group by region", "identify top 3 regions by churn"]`).
   - Runs once, at the start.

2. **`coder`**
   - Input: `plan[current_step]`, `step_results` so far (as available variables/context), `error` (if this is a retry).
   - One LLM call producing a Python code block for the current step only.
   - If `error` is set, the prompt must include the previous code attempt + the error message, and explicitly ask the model to fix it — this is the "recursive" part, directly analogous to the RLM's REPL feedback loop.
   - Appends the new code to `code_attempts`.

3. **`executor`**
   - Executes the most recent code from `code_attempts`.
   - **Sandboxing decision to make explicitly (this is a known gap from the Excel/Word RLM project — worth doing properly here):** run in a subprocess with a resource/time limit, or a Docker container, rather than in-process `exec()`. Since this is a fresh project, this is the chance to build the "hardened" version referenced in the interview prep notes for Project 2.
   - On success: store result in `step_results`, clear `error`, reset `retry_count`.
   - On failure: capture the exception message into `error`, increment `retry_count`.

4. **Conditional edge (router function) after `executor`**
   - Not an LLM call — a plain Python function reading state, returning the next node name. This is the piece that's implicit in a plain `AgentExecutor` loop but explicit and testable here.
   - Logic:
     - `error is not None` and `retry_count < MAX_RETRIES` → back to `coder` (retry same step).
     - `error is not None` and `retry_count >= MAX_RETRIES` → route to a `failure` node (don't loop forever).
     - `error is None` and `current_step + 1 < len(plan)` → increment `current_step`, back to `coder` (next step).
     - `error is None` and `current_step + 1 == len(plan)` → route to `finalizer`.

5. **`finalizer`**
   - Input: `step_results` (all of them).
   - One LLM call synthesizing the final KPI answer/report from the accumulated results.
   - Sets `final_report`, ends the graph.

6. **`failure`** (small addition beyond the original flow — worth having for a complete answer)
   - Reached only if a step exceeds `MAX_RETRIES`.
   - Returns a clear "couldn't complete step N after M attempts" message rather than silently failing or looping forever.

### Graph wiring (conceptual)
```
planner -> coder -> executor -> [conditional router]
                                   -> coder      (retry same step)
                                   -> coder      (next step, current_step += 1)
                                   -> finalizer  (all steps done)
                                   -> failure    (max retries exceeded)
finalizer -> END
failure -> END
```

## Why this design (talking points for the interview)

- **State object vs. shared mutable context (Project 1 comparison):** `KPIAgentState` is the formalized version of the ad hoc shared context object from the IT triage platform — same idea (shared state multiple steps read/write), but each node has an explicit, typed contract instead of an implicit shared object anyone can mutate. Should be able to point at exactly which fields each node reads vs. writes.
- **Conditional edges vs. an agent's internal loop:** the retry/advance/finish decision is a plain, testable Python function — not buried inside a model's own reasoning loop the way a `ToolCallingAgent`'s internal loop is (Project 1) or an `AgentExecutor`'s loop is. This is the concrete answer to "what does LangGraph give you that a plain agent loop doesn't."
- **Recursive retry loop vs. the RLM REPL loop:** the `coder → executor → (error) → coder` cycle is functionally the same pattern as the RLM's "write code, see the real result, write more code" loop from the Excel/Word agent — just expressed as explicit graph edges instead of a bespoke `while` loop with a custom `environment.execute_code`.
- **Sandboxing done properly this time:** unlike the Excel/Word agent (where the Docker-sandboxed path existed but wasn't the one shipped to production), this project is a chance to actually build and use a subprocess/Docker execution boundary from the start, given the model is again writing arbitrary code.

## Suggested build order
1. Scaffold the state schema and stub nodes that just print/pass.
2. Wire the graph with the conditional router, test with hardcoded fake LLM responses (no real model calls yet) to confirm the control flow (retry/advance/finish/failure) works.
3. Plug in a real LLM for `planner`, `coder`, `finalizer`.
4. Add real (sandboxed) execution in `executor`.
5. Test end-to-end on a couple of real CSVs with a genuine KPI question.
6. (Optional, strengthens the interview story further) Add LangGraph's built-in persistence/checkpointing so a run can be paused/resumed — directly parallels the RLM's `persistent=True` session behavior from Project 2.

## What to bring back for the next prep session
- The actual sandboxing mechanism you used (subprocess vs. Docker) and why.
- Any real failure/retry case you hit while building it — a genuine "the coder wrote bad code, here's what the retry did" story is much stronger in an interview than a hypothetical one.
- Whether you added the optional checkpointing/persistence piece.
- Any deviation from this spec and why — interviewers often ask "why did you build it this way" for exactly the parts that changed from the original plan.
