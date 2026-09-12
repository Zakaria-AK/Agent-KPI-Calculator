"""Node implementations.

planner/coder/finalizer call a real LLM (build order step 3). executor stays
a stub until sandboxed execution is added (build order step 4).
"""

from langchain_core.messages import HumanMessage, SystemMessage

from .executor import run_code_in_subprocess
from .llm import get_llm
from .schemas import CodeStep, Plan
from .state import KPIAgentState

PLANNER_SYSTEM_PROMPT = """You are a data-analysis planner. Given a natural-language KPI question and \
a preview of the available CSV schema(s), break the question into an ordered list of small, concrete \
sub-steps that, executed in order with pandas, compute the answer. Each step should be independently \
codeable in a few lines and should build on the results of prior steps."""

CODER_SYSTEM_PROMPT = """You are a Python data-analysis coder. Write code for exactly ONE step of a \
larger plan, using pandas. Assume:
- pandas is already imported as `pd`.
- CSV file paths are available in a list called `csv_paths`.
- Results from already-completed steps are available in a list called `step_results`, in order \
(step_results[0] is the result of step 1, etc).
- Your code must set a variable named `result` to whatever this step should hand off to later steps \
(a DataFrame, Series, scalar, or dict/list of such -- whatever makes sense).
- `result` crosses a process boundary via pickle, so it must be a plain data value. NEVER put a \
function, lambda, open file handle, or other non-data object in `result` -- if a step needs a \
helper function, define and use it inline within that same step instead of trying to pass it forward.
Do not re-implement earlier steps; use step_results. Do not wrap the code in markdown fences."""

FINALIZER_SYSTEM_PROMPT = """You are a data analyst. Given the original KPI question and the results \
of each step used to answer it, write a clear, concise final report/answer for a business stakeholder. \
Cite concrete numbers from the step results."""


def planner(state: KPIAgentState) -> dict:
    llm = get_llm().with_structured_output(Plan)
    result: Plan = llm.invoke(
        [
            SystemMessage(PLANNER_SYSTEM_PROMPT),
            HumanMessage(
                f"Question: {state['question']}\n\n"
                f"CSV schema preview:\n{state['csv_schema_preview']}"
            ),
        ]
    )
    return {"plan": result.steps, "current_step": 0}


def coder(state: KPIAgentState) -> dict:
    llm = get_llm().with_structured_output(CodeStep)

    step_description = state["plan"][state["current_step"]]
    prior_steps = "\n".join(
        f"- step {i}: {s} -> step_results[{i}]"
        for i, s in enumerate(state["plan"][: state["current_step"]])
    )

    prompt_parts = [
        f"Current step ({state['current_step']}): {step_description}",
        f"csv_paths: {state['csv_paths']}",
        f"Completed steps so far:\n{prior_steps or '(none)'}",
    ]

    if state.get("error"):
        previous_code = state["code_attempts"][-1] if state["code_attempts"] else "(none)"
        prompt_parts.append(
            "The previous attempt at this step failed. Fix it.\n"
            f"Previous code:\n{previous_code}\n\n"
            f"Error it raised:\n{state['error']}"
        )

    result: CodeStep = llm.invoke(
        [SystemMessage(CODER_SYSTEM_PROMPT), HumanMessage("\n\n".join(prompt_parts))]
    )

    return {"code_attempts": state["code_attempts"] + [result.code]}


def executor(state: KPIAgentState) -> dict:
    code = state["code_attempts"][-1]
    try:
        result = run_code_in_subprocess(code, state["csv_paths"], state["step_results"])
    except (RuntimeError, TimeoutError) as exc:
        return {"error": str(exc), "retry_count": state["retry_count"] + 1}

    return {
        "step_results": state["step_results"] + [result],
        "error": None,
        "retry_count": 0,
    }


def advance_step(state: KPIAgentState) -> dict:
    """Not an LLM node: moves current_step forward after a successful step.

    Kept separate from the router (router.decide_next) so the router stays a
    pure decision function while this node owns the one piece of state
    mutation that "advance" implies.
    """
    return {"current_step": state["current_step"] + 1}


def finalizer(state: KPIAgentState) -> dict:
    llm = get_llm()
    steps_and_results = "\n".join(
        f"- step {i} ({desc}): {result!r}"
        for i, (desc, result) in enumerate(zip(state["plan"], state["step_results"]))
    )
    response = llm.invoke(
        [
            SystemMessage(FINALIZER_SYSTEM_PROMPT),
            HumanMessage(f"Question: {state['question']}\n\nStep results:\n{steps_and_results}"),
        ]
    )
    return {"final_report": response.content}


def failure(state: KPIAgentState) -> dict:
    print(
        f"[failure] stub: step {state['current_step']} failed after "
        f"{state['retry_count']} retries"
    )
    return {
        "final_report": (
            f"Could not complete step {state['current_step']} "
            f"after {state['retry_count']} attempts."
        )
    }
