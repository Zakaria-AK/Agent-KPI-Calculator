"""Manual smoke test for the real Azure-backed planner/coder nodes.

Not part of the automated test suite (it costs real API calls and needs a
filled-in .env). Run it after setting AZURE_OPENAI_* in .env:

    .venv/Scripts/python scripts/smoke_llm.py
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.nodes import coder, planner
from src.schema_preview import build_schema_preview
from src.state import initial_state

CSV_PATH = str(Path(__file__).resolve().parent.parent / "data" / "superstore.csv")
QUESTION = "What are the total monthly sales and profit by region for the most recent 12 months in the data?"

state = initial_state(csv_paths=[CSV_PATH], question=QUESTION)
state["csv_schema_preview"] = build_schema_preview(state["csv_paths"])

print("=== schema preview ===")
print(state["csv_schema_preview"])

print("\n=== planner ===")
plan_update = planner(state)
state.update(plan_update)
for i, step in enumerate(state["plan"]):
    print(f"{i}: {step}")

print("\n=== coder (step 0) ===")
code_update = coder(state)
state.update(code_update)
print(state["code_attempts"][-1])
