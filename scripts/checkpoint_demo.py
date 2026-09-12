"""Demonstrates LangGraph's built-in persistence: pause a run, then resume
it later (a fresh script invocation, same process or not) from exactly
where it left off -- the direct parallel to the RLM's persistent=True
session behavior.

Run it once:  it starts a fresh run and pauses right after the first
`coder` step (simulating a crash/interrupt right before that code executes).

Run it again (same thread_id): it resumes from the saved checkpoint and
runs to completion, with no interrupt this time.

    .venv/Scripts/python scripts/checkpoint_demo.py
    .venv/Scripts/python scripts/checkpoint_demo.py   # run again to resume
"""

import sqlite3
import sys
from contextlib import closing
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite import SqliteSaver

from src.graph import build_graph
from src.schema_preview import build_schema_preview
from src.state import initial_state

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = str(ROOT / "data" / "checkpoints.sqlite")
CSV_PATH = str(ROOT / "data" / "sample_churn.csv")
THREAD_ID = "kpi-demo-run"
QUESTION = "What's the monthly churn rate by region for the last 12 months?"

config = {"configurable": {"thread_id": THREAD_ID}}

# step_results holds pandas DataFrames, which the default msgpack/JSON
# checkpoint encoding can't serialize -- pickle_fallback=True falls back to
# pickle for anything it doesn't natively support.
serde = JsonPlusSerializer(pickle_fallback=True)

with closing(sqlite3.connect(DB_PATH, check_same_thread=False)) as conn:
    checkpointer = SqliteSaver(conn, serde=serde)
    existing = checkpointer.get(config)

    if existing is None:
        print(
            f"No checkpoint for thread '{THREAD_ID}' -- starting a fresh run, "
            "pausing right after the first `coder` step.\n"
        )
        graph = build_graph(checkpointer=checkpointer, interrupt_after=["coder"])
        state = initial_state(csv_paths=[CSV_PATH], question=QUESTION)
        state["csv_schema_preview"] = build_schema_preview(state["csv_paths"])
        result = graph.invoke(state, config=config)

        print("=== paused ===")
        print(f"current_step: {result['current_step']}")
        print(f"code_attempts so far: {len(result['code_attempts'])}")
        print(f"step_results so far: {len(result['step_results'])}")
        print(f"\nRun this script again to resume thread '{THREAD_ID}'.")
    else:
        print(f"Found a checkpoint for thread '{THREAD_ID}' -- resuming to completion.\n")
        graph = build_graph(checkpointer=checkpointer)
        result = graph.invoke(None, config=config)

        print("=== final_report ===")
        print(result["final_report"])
        print(f"\nDelete {DB_PATH} to start a fresh demo run.")
