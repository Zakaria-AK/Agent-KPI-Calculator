"""The conditional-edge decision logic that follows the executor node.

Deliberately a plain, pure function of state -> label. Nothing here calls an
LLM, which is the point: the retry/advance/finish/fail decision is explicit
and unit-testable, unlike the decision buried inside an agent's own reasoning
loop.
"""

from typing import Literal

from .state import KPIAgentState

MAX_RETRIES = 3

RouteDecision = Literal["retry", "advance", "finish", "fail"]


def decide_next(state: KPIAgentState) -> RouteDecision:
    if state.get("error") is not None:
        if state.get("retry_count", 0) < MAX_RETRIES:
            return "retry"
        return "fail"

    if state["current_step"] + 1 < len(state["plan"]):
        return "advance"

    return "finish"
