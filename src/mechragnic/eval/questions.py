from pydantic import BaseModel


class Case(BaseModel):
    question: str
    expected_case_ids: list[int]
    note: str
