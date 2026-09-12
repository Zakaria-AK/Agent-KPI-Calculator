"""Turns arbitrary node-output values (pandas DataFrames/Series/Timestamps,
numpy scalars, plain Python data) into something json.dumps can handle, for
sending over the SSE stream to the Angular UI.
"""

import json

import numpy as np
import pandas as pd

PREVIEW_ROWS = 10


def to_jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, pd.DataFrame):
        # Route through pandas' own JSON encoder (not astype(str)/to_dict):
        # it correctly turns NaN/NaT into JSON null and numpy dtypes into
        # native types. astype(str) leaves stray float('nan') cells behind
        # on some pandas versions, which json.dumps then emits as the bare
        # token `NaN` -- invalid JSON that breaks the browser's JSON.parse.
        preview_json = value.head(PREVIEW_ROWS).to_json(orient="records", date_format="iso")
        return {
            "__type__": "dataframe",
            "shape": list(value.shape),
            "columns": [str(c) for c in value.columns],
            "preview": json.loads(preview_json),
        }

    if isinstance(value, pd.Series):
        preview_json = value.head(PREVIEW_ROWS).to_json(date_format="iso")
        return {
            "__type__": "series",
            "name": value.name,
            "length": len(value),
            "preview": json.loads(preview_json),
        }

    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()

    if isinstance(value, np.generic):
        return value.item()

    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]

    # Fallback for anything else the LLM-generated code might produce
    # (DatetimeIndex, custom objects, etc.) -- never crash the stream over it.
    return str(value)
