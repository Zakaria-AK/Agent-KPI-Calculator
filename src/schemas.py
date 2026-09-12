from pydantic import BaseModel, Field


class Plan(BaseModel):
    steps: list[str] = Field(
        description=(
            "Ordered list of concrete sub-steps needed to answer the KPI "
            "question using pandas over the given CSV(s). Each step should "
            "be small enough to implement in a few lines of code."
        )
    )


class CodeStep(BaseModel):
    code: str = Field(
        description=(
            "Python code implementing only the current step. No markdown "
            "fences, no commentary — just the code."
        )
    )
