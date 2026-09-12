from typing import Any, TypedDict


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


def initial_state(csv_paths: list[str], question: str) -> KPIAgentState:
    return KPIAgentState(
        csv_paths=csv_paths,
        question=question,
        csv_schema_preview="",
        plan=[],
        current_step=0,
        code_attempts=[],
        step_results=[],
        error=None,
        retry_count=0,
        final_report=None,
    )
