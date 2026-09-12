import pandas as pd


def build_schema_preview(csv_paths: list[str], sample_rows: int = 5) -> str:
    """Column names/dtypes/sample rows for each CSV, built once at start."""
    sections = []
    for path in csv_paths:
        df = pd.read_csv(path)
        sections.append(
            f"File: {path}\n"
            f"Columns and dtypes:\n{df.dtypes.to_string()}\n"
            f"Sample rows:\n{df.head(sample_rows).to_string(index=False)}"
        )
    return "\n\n".join(sections)
