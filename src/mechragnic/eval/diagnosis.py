import asyncio
import logging
from datetime import datetime
from json import load
from pathlib import Path

from pydantic import ValidationError

from mechragnic.ingest.stackexchange import build_cases, fetch_answers, fetch_questions
from mechragnic.ingest.synthesis import synthesize
from mechragnic.models.stack_exchange import QuestionWithAnswers

logging.getLogger("httpx").setLevel(logging.WARNING)

LABELS_FILE = Path(__file__).resolve().parent / "diagnosis_labels.json"


def load_labels() -> tuple[datetime, datetime, dict[int, bool]]:
    with open(LABELS_FILE) as file:
        data = load(file)

    start = datetime.fromisoformat(data["window"]["start"])
    end = datetime.fromisoformat(data["window"]["end"])
    labels = {label["question_id"]: label["is_fault_diagnosis"] for label in data["labels"]}
    return start, end, labels


async def predict(case: QuestionWithAnswers) -> str:
    try:
        synthesized = await synthesize(case)
    except ValidationError:
        return "invalid"
    return "fault" if synthesized.is_fault_diagnosis else "other"


def ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


async def evaluate():
    start, end, labels = load_labels()

    questions = await fetch_questions(start, end)
    answers = await fetch_answers([question.question_id for question in questions])
    cases = [case for case in build_cases(questions, answers) if case.question_id in labels]

    missing = set(labels) - {case.question_id for case in cases}
    if missing:
        print(f"WARNING: {len(missing)} labelled questions not returned by the API: {sorted(missing)}")

    missed_faults: list[QuestionWithAnswers] = []
    admitted_non_faults: list[QuestionWithAnswers] = []
    invalid: list[QuestionWithAnswers] = []
    true_positives = false_positives = true_negatives = 0

    for index, case in enumerate(cases, start=1):
        prediction = await predict(case)
        expected = labels[case.question_id]
        print(f"{index}/{len(cases)} {case.question_id} expected={'fault' if expected else 'other'} got={prediction}")

        if prediction == "invalid":
            invalid.append(case)
            continue

        predicted = prediction == "fault"
        if predicted and expected:
            true_positives += 1
        elif predicted and not expected:
            false_positives += 1
            admitted_non_faults.append(case)
        elif not predicted and expected:
            missed_faults.append(case)
        else:
            true_negatives += 1

    expected_faults = sum(labels[case.question_id] for case in cases)
    print()
    print(f"precision: {ratio(true_positives, true_positives + false_positives):.2f}")
    print(
        f"recall:    {ratio(true_positives, expected_faults):.2f} ({true_positives}/{expected_faults} faults admitted)"
    )
    print(f"accuracy:  {ratio(true_positives + true_negatives, len(cases)):.2f}")

    for heading, group in (
        ("Faults skipped (lost for good)", missed_faults),
        ("Non-faults admitted (noise in the database)", admitted_non_faults),
        ("Said diagnosis but failed validation (would go to pending)", invalid),
    ):
        if group:
            print(f"\n{heading}:")
            for case in group:
                print(f"  {case.question_id} {case.title}")


if __name__ == "__main__":
    asyncio.run(evaluate())
