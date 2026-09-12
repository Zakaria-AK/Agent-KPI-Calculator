"""Build-order step 2: confirm the graph's control flow (retry / advance /
finish / fail) with hardcoded fake node behavior, before any real LLM or
subprocess execution is wired in.
"""

from src.graph import build_graph
from src.state import initial_state


def fake_planner(state):
    return {"plan": ["load and clean data", "compute the metric"], "current_step": 0}


def fake_coder(state):
    attempts = state.get("code_attempts", []) + [
        f"code for step {state['current_step']}, attempt {len(state.get('code_attempts', [])) + 1}"
    ]
    return {"code_attempts": attempts}


def fake_finalizer(state):
    return {"final_report": f"done: {state['step_results']}"}


def scripted_executor(outcomes):
    """Returns a fake executor node that succeeds/fails in the given order."""
    it = iter(outcomes)

    def executor(state):
        ok = next(it)
        if ok:
            results = state.get("step_results", []) + [f"result-{state['current_step']}"]
            return {"step_results": results, "error": None, "retry_count": 0}
        return {"error": "simulated failure", "retry_count": state.get("retry_count", 0) + 1}

    return executor


def _run(outcomes, plan_len=2):
    graph = build_graph(
        overrides={
            "planner": fake_planner,
            "coder": fake_coder,
            "executor": scripted_executor(outcomes),
            "finalizer": fake_finalizer,
        }
    )
    state = initial_state(csv_paths=["fake.csv"], question="fake question")
    return graph.invoke(state)


def test_retry_then_advance_then_finish():
    # step 0 fails twice then succeeds (exercises "retry"); step 1 succeeds
    # immediately (exercises "advance" then "finish").
    result = _run(outcomes=[False, False, True, True])

    assert result["error"] is None
    assert result["step_results"] == ["result-0", "result-1"]
    assert result["current_step"] == 1
    assert result["final_report"] == "done: ['result-0', 'result-1']"


def test_single_step_success_goes_straight_to_finish():
    graph = build_graph(
        overrides={
            "planner": lambda state: {"plan": ["only step"], "current_step": 0},
            "coder": fake_coder,
            "executor": scripted_executor([True]),
            "finalizer": fake_finalizer,
        }
    )
    state = initial_state(csv_paths=["fake.csv"], question="fake question")
    result = graph.invoke(state)

    assert result["final_report"] == "done: ['result-0']"


def test_exceeding_max_retries_routes_to_failure():
    # MAX_RETRIES is 3: three straight failures on a single-step plan should
    # exhaust retries and land in the failure node, never reaching finalizer.
    graph = build_graph(
        overrides={
            "planner": lambda state: {"plan": ["only step"], "current_step": 0},
            "coder": fake_coder,
            "executor": scripted_executor([False, False, False]),
            "finalizer": fake_finalizer,
        }
    )
    state = initial_state(csv_paths=["fake.csv"], question="fake question")
    result = graph.invoke(state)

    assert result["error"] == "simulated failure"
    assert result["retry_count"] == 3
    assert "step 0" in result["final_report"] and "after 3 attempts" in result["final_report"]
