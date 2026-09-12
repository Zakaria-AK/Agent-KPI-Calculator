from typing import Callable, Optional

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph

from . import nodes as default_nodes
from .router import decide_next
from .state import KPIAgentState

NODE_NAMES = ("planner", "coder", "executor", "advance_step", "finalizer", "failure")


def build_graph(
    overrides: Optional[dict[str, Callable]] = None,
    checkpointer: Optional[BaseCheckpointSaver] = None,
    interrupt_after: Optional[list[str]] = None,
    interrupt_before: Optional[list[str]] = None,
):
    """Compile the KPI agent graph.

    `overrides` lets callers swap in fake node functions (no LLM, no
    subprocess execution) so the retry/advance/finish/fail control flow can
    be tested in isolation — see tests/test_control_flow.py.

    `checkpointer` (e.g. a SqliteSaver) enables LangGraph's built-in
    persistence: invoking with a `config={"configurable": {"thread_id": ...}}`
    saves state after every node, so a run can be resumed later by invoking
    again with the same thread_id and `None` as input — see
    scripts/checkpoint_demo.py. `interrupt_after`/`interrupt_before` pause
    execution at named nodes (requires a checkpointer) to simulate a
    deliberate pause rather than a crash.
    """
    overrides = overrides or {}
    fn = {name: overrides.get(name, getattr(default_nodes, name)) for name in NODE_NAMES}

    graph = StateGraph(KPIAgentState)
    for name in NODE_NAMES:
        graph.add_node(name, fn[name])

    graph.set_entry_point("planner")
    graph.add_edge("planner", "coder")
    graph.add_edge("coder", "executor")
    graph.add_conditional_edges(
        "executor",
        decide_next,
        {
            "retry": "coder",
            "advance": "advance_step",
            "finish": "finalizer",
            "fail": "failure",
        },
    )
    graph.add_edge("advance_step", "coder")
    graph.add_edge("finalizer", END)
    graph.add_edge("failure", END)

    return graph.compile(
        checkpointer=checkpointer,
        interrupt_after=interrupt_after,
        interrupt_before=interrupt_before,
    )
