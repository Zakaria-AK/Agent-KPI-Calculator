"""FastAPI backend for the KPI agent UI.

POST /api/runs        -- register a run (question + CSV source), returns a run_id
GET  /api/runs/{id}/stream -- SSE stream of the graph's node-by-node progress

Single-process, in-memory run registry: fine for a local/demo deployment,
not for multi-worker production use.
"""

import json
import sys
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from starlette.concurrency import iterate_in_threadpool

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.graph import build_graph
from src.schema_preview import build_schema_preview
from src.state import initial_state

from backend.serialization import to_jsonable

SAMPLE_CSV_PATH = ROOT / "data" / "superstore.csv"
UPLOADS_DIR = ROOT / "backend" / "uploads"

app = FastAPI(title="KPI Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# run_id -> {"state": KPIAgentState, "started": bool}
RUNS: dict[str, dict] = {}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/runs")
async def create_run(
    question: str = Form(...),
    use_sample: bool = Form(False),
    files: Optional[list[UploadFile]] = None,
):
    question = question.strip()
    if not question:
        raise HTTPException(400, "question is required")

    if use_sample:
        csv_paths = [str(SAMPLE_CSV_PATH)]
    elif files:
        run_upload_dir = UPLOADS_DIR / str(uuid.uuid4())
        run_upload_dir.mkdir(parents=True, exist_ok=True)
        csv_paths = []
        for f in files:
            dest = run_upload_dir / f.filename
            dest.write_bytes(await f.read())
            csv_paths.append(str(dest))
    else:
        raise HTTPException(400, "provide at least one CSV file, or set use_sample=true")

    state = initial_state(csv_paths=csv_paths, question=question)
    state["csv_schema_preview"] = build_schema_preview(csv_paths)

    run_id = str(uuid.uuid4())
    RUNS[run_id] = {"state": state, "started": False}
    return {"run_id": run_id}


def _run_events(state):
    graph = build_graph()
    for update in graph.stream(state, config={"recursion_limit": 100}, stream_mode="updates"):
        for node_name, node_output in update.items():
            payload = {"node": node_name, "data": to_jsonable(node_output)}
            yield f"data: {json.dumps(payload)}\n\n"
    yield "event: done\ndata: {}\n\n"


@app.get("/api/runs/{run_id}/stream")
async def stream_run(run_id: str):
    run = RUNS.get(run_id)
    if run is None:
        raise HTTPException(404, "unknown run_id")
    if run["started"]:
        raise HTTPException(409, "run already started (reconnection is not supported)")
    run["started"] = True

    return StreamingResponse(
        iterate_in_threadpool(_run_events(run["state"])),
        media_type="text/event-stream",
    )
