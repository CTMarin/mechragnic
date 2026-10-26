from pydantic import BaseModel, field_validator, model_validator

PLACEHOLDERS = {"", "none", "none specified", "n/a", "unknown"}


class MechanicCase(BaseModel):
    id: int
    symptoms: list[str]
    causes: list[str]
    solution: list[str]


class SynthesizedCase(BaseModel):
    is_fault_diagnosis: bool
    symptoms: list[str]
    causes: list[str]
    solution: list[str]

    @field_validator("symptoms", "causes", "solution", mode="before")
    @classmethod
    def drop_placeholders(cls, values: list[str]) -> list[str]:
        return [value.strip() for value in values if value.strip().lower() not in PLACEHOLDERS]

    @model_validator(mode="after")
    def diagnosis_needs_symptoms_and_solution(self) -> "SynthesizedCase":
        if self.is_fault_diagnosis and (not self.symptoms or not (self.causes or self.solution)):
            raise ValueError("a fault diagnosis needs symptoms and at least a cause or a solution")
        return self
