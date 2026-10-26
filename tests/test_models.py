import pytest
from pydantic import ValidationError

from mechragnic.models.ingest_questions import IngestPendingReason, PendingQuestion
from mechragnic.models.mechanic_case import SynthesizedCase


def test_placeholders_are_dropped_and_values_stripped():
    case = SynthesizedCase(
        is_fault_diagnosis=True,
        symptoms=[" engine stalls ", "N/A", ""],
        causes=["None specified", "bad idle valve"],
        solution=[" unknown "],
    )

    assert case.symptoms == ["engine stalls"]
    assert case.causes == ["bad idle valve"]
    assert case.solution == []


def test_fault_without_symptoms_is_rejected():
    with pytest.raises(ValidationError):
        SynthesizedCase(is_fault_diagnosis=True, symptoms=["none"], causes=["belt"], solution=["replace"])


def test_fault_without_cause_or_solution_is_rejected():
    with pytest.raises(ValidationError):
        SynthesizedCase(is_fault_diagnosis=True, symptoms=["noise"], causes=[], solution=["n/a"])


@pytest.mark.parametrize(("causes", "solution"), [(["belt"], []), ([], ["replace belt"])])
def test_fault_needs_only_one_of_cause_or_solution(causes, solution):
    case = SynthesizedCase(is_fault_diagnosis=True, symptoms=["noise"], causes=causes, solution=solution)

    assert case.is_fault_diagnosis


def test_non_fault_can_be_empty():
    case = SynthesizedCase(is_fault_diagnosis=False, symptoms=[], causes=[], solution=[])

    assert case.symptoms == case.causes == case.solution == []


def test_pending_question_rejects_unknown_reason():
    with pytest.raises(ValidationError):
        PendingQuestion(question_id=1, reason="timeout", answer_count=0)


def test_pending_question_parses_reason_from_database_value():
    question = PendingQuestion(question_id=1, reason="ollama_error", answer_count=0)

    assert question.reason is IngestPendingReason.OLLAMA_ERROR
