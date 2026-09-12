import json

import numpy as np
import pandas as pd

from backend.serialization import to_jsonable


def test_dataframe_with_nan_produces_valid_json_with_null():
    df = pd.DataFrame({"a": [1, 2], "b": [1.5, float("nan")]})
    payload = to_jsonable(df)

    # Must be valid JSON -- json.dumps happily emits the bare `NaN` token,
    # which is what broke the browser's JSON.parse; round-tripping through
    # dumps+loads is exactly the check that would have caught it.
    round_tripped = json.loads(json.dumps(payload))
    assert round_tripped["preview"][1]["b"] is None


def test_series_with_nan_produces_valid_json_with_null():
    s = pd.Series([1.0, float("nan")], name="x")
    payload = to_jsonable(s)

    round_tripped = json.loads(json.dumps(payload))
    assert list(round_tripped["preview"].values())[1] is None


def test_timestamp_becomes_iso_string():
    ts = pd.Timestamp("2025-01-15")
    assert to_jsonable(ts) == "2025-01-15T00:00:00"


def test_numpy_scalars_become_native_python():
    assert to_jsonable(np.int64(5)) == 5
    assert isinstance(to_jsonable(np.int64(5)), int)


def test_nested_dict_and_list_are_recursively_converted():
    payload = to_jsonable({"a": [np.int64(1), pd.Timestamp("2025-01-01")]})
    json.dumps(payload)  # must not raise
    assert payload == {"a": [1, "2025-01-01T00:00:00"]}
