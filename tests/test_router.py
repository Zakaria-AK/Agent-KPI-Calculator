from src.router import MAX_RETRIES, decide_next


def _state(**overrides):
    base = {
        "plan": ["a", "b"],
        "current_step": 0,
        "error": None,
        "retry_count": 0,
    }
    base.update(overrides)
    return base


def test_retry_when_error_and_under_max_retries():
    state = _state(error="boom", retry_count=MAX_RETRIES - 1)
    assert decide_next(state) == "retry"


def test_fail_when_error_and_max_retries_reached():
    state = _state(error="boom", retry_count=MAX_RETRIES)
    assert decide_next(state) == "fail"


def test_advance_when_success_and_steps_remain():
    state = _state(error=None, current_step=0, plan=["a", "b", "c"])
    assert decide_next(state) == "advance"


def test_finish_when_success_and_last_step():
    state = _state(error=None, current_step=1, plan=["a", "b"])
    assert decide_next(state) == "finish"
