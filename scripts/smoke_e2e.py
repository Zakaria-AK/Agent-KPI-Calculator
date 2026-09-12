"""End-to-end smoke test: real planner/coder/finalizer LLM calls + real
sandboxed execution, run through the actual compiled graph.

    .venv/Scripts/python scripts/smoke_e2e.py
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.graph import build_graph
from src.schema_preview import build_schema_preview
from src.state import initial_state

CSV_PATH = str(Path(__file__).resolve().parent.parent / "data" / "sample_churn.csv")
QUESTION = "What's the monthly churn rate by region for the last 12 months?"

state = initial_state(csv_paths=[CSV_PATH], question=QUESTION)
state["csv_schema_preview"] = build_schema_preview(state["csv_paths"])

graph = build_graph()
result = graph.invoke(state, config={"recursion_limit": 100})

print("\n=== plan ===")
for i, step in enumerate(result["plan"]):
    print(f"{i}: {step}")

print("\n=== step_results ===")
for i, r in enumerate(result["step_results"]):
    print(f"--- step {i} ---")
    print(r)

print("\n=== final_report ===")
print(result["final_report"])

if result["error"] is not None:
    print("\n=== last error ===")
    print(result["error"])
    print("\n=== code attempts for failed step ===")
    for i, attempt in enumerate(result["code_attempts"]):
        print(f"--- attempt {i} ---")
        print(attempt)
