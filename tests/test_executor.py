import pytest

from src.executor import run_code_in_subprocess


def test_successful_code_returns_result():
    code = "result = 2 + 2"
    result = run_code_in_subprocess(code, csv_paths=[], step_results=[])
    assert result == 4


def test_code_can_see_csv_paths_and_step_results():
    code = "result = (csv_paths, step_results)"
    result = run_code_in_subprocess(code, csv_paths=["a.csv"], step_results=[10, 20])
    assert result == (["a.csv"], [10, 20])


def test_pandas_is_available_as_pd():
    code = "df = pd.DataFrame({'x': [1, 2, 3]})\nresult = int(df['x'].sum())"
    result = run_code_in_subprocess(code, csv_paths=[], step_results=[])
    assert result == 6


def test_raising_code_surfaces_error_message():
    code = "raise ValueError('boom')"
    with pytest.raises(RuntimeError, match="boom"):
        run_code_in_subprocess(code, csv_paths=[], step_results=[])


def test_syntax_error_surfaces_as_runtime_error():
    code = "this is not python"
    with pytest.raises(RuntimeError):
        run_code_in_subprocess(code, csv_paths=[], step_results=[])


def test_infinite_loop_times_out():
    code = "while True:\n    pass"
    with pytest.raises(TimeoutError):
        run_code_in_subprocess(code, csv_paths=[], step_results=[], timeout=1)


def test_unpicklable_result_gives_actionable_error():
    # A function defined via exec() can never be pickled (pickle looks it up
    # by module + qualname, and it isn't really a module attribute). This
    # must fail with a message that tells the coder what's wrong, not a
    # bare AttributeError about __main__.
    code = "def helper():\n    return 1\nresult = {'fn': helper}"
    with pytest.raises(RuntimeError, match="plain data value"):
        run_code_in_subprocess(code, csv_paths=[], step_results=[])


def test_relative_file_writes_land_in_a_throwaway_dir_not_the_caller_cwd(tmp_path, monkeypatch):
    # Regression: earlier the subprocess inherited whatever directory the
    # agent process happened to be launched from, so a step doing
    # `df.to_csv("out.csv")` would scatter files into the repo root instead
    # of somewhere disposable.
    monkeypatch.chdir(tmp_path)
    code = "with open('leftover.csv', 'w') as f:\n    f.write('x')\nresult = 1"
    run_code_in_subprocess(code, csv_paths=[], step_results=[])
    assert not (tmp_path / "leftover.csv").exists()


def test_secrets_are_not_inherited_by_child_process():
    import os

    os.environ["SMOKE_TEST_SECRET"] = "should-not-leak"
    try:
        code = "import os\nresult = os.environ.get('SMOKE_TEST_SECRET')"
        result = run_code_in_subprocess(code, csv_paths=[], step_results=[])
        assert result is None
    finally:
        del os.environ["SMOKE_TEST_SECRET"]
