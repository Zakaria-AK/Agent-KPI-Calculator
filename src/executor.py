"""Sandboxed execution of LLM-generated code.

Isolation model: subprocess + timeout + a stripped environment.
- Each code attempt runs in its own `python` process (not in-process
  `exec()`), so a crash or infinite loop can't take down the agent process
  and can be killed on a timeout.
- The child's environment is reduced to PATH/SYSTEMROOT only, so it doesn't
  inherit AZURE_API_KEY or anything else from the parent's .env.
- Inputs (csv_paths, step_results) and the output (`result`) cross the
  process boundary via pickle files in a throwaway temp directory, which is
  also the child's cwd -- so a relative-path `to_csv(...)` the LLM writes
  lands there and gets deleted with it, not scattered into the repo.

What this does NOT provide: filesystem or network jailing. The generated
code can still read/write any file the OS user can via an absolute path, or
make network calls. Closing that gap is what a container (Docker + no
network + read-only mounts) buys over this, at the cost of needing Docker
available and added latency per step -- the trade-off called out in the spec.
"""

import os
import pickle
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any

DEFAULT_TIMEOUT_SECONDS = 15

_RUNNER_TEMPLATE = """
import pickle
import sys

with open(r"{input_path}", "rb") as f:
    payload = pickle.load(f)

import pandas as pd

exec_globals = {{
    "pd": pd,
    "csv_paths": payload["csv_paths"],
    "step_results": payload["step_results"],
}}

exec(payload["code"], exec_globals)

result = exec_globals.get("result")

try:
    with open(r"{output_path}", "wb") as f:
        pickle.dump({{"result": result}}, f)
except (pickle.PicklingError, TypeError, AttributeError) as exc:
    print(
        "`result` is not a plain data value and cannot cross the sandbox "
        "process boundary (it likely contains a function, open file, or "
        "other non-data object). Store only DataFrames/Series/scalars/"
        "lists/dicts of such in `result`.\\n"
        f"Underlying error: {{exc}}",
        file=sys.stderr,
    )
    sys.exit(1)
"""


def _tail(text: str, n_lines: int = 20) -> str:
    lines = text.strip().splitlines()
    return "\n".join(lines[-n_lines:])


def run_code_in_subprocess(
    code: str,
    csv_paths: list[str],
    step_results: list[Any],
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> Any:
    """Runs `code` in an isolated subprocess and returns its `result` variable.

    Raises RuntimeError (with the tail of the child's traceback) on a
    non-zero exit, or TimeoutError if it runs past `timeout` seconds.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        input_path = tmp_dir_path / "input.pkl"
        output_path = tmp_dir_path / "output.pkl"
        runner_path = tmp_dir_path / "runner.py"

        with open(input_path, "wb") as f:
            pickle.dump({"code": code, "csv_paths": csv_paths, "step_results": step_results}, f)

        runner_path.write_text(
            textwrap.dedent(_RUNNER_TEMPLATE).format(input_path=input_path, output_path=output_path)
        )

        env = {
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
        }

        try:
            proc = subprocess.run(
                [sys.executable, str(runner_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                cwd=str(tmp_dir_path),
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(f"code exceeded {timeout}s timeout") from exc

        if proc.returncode != 0:
            raise RuntimeError(_tail(proc.stderr) or f"subprocess exited with code {proc.returncode}")

        with open(output_path, "rb") as f:
            output = pickle.load(f)

        return output["result"]
