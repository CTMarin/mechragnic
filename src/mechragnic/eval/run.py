import asyncio
from json import load
from pathlib import Path

from mechragnic.eval.questions import Case
from mechragnic.retrieval.search import search_cases

JSON_FILE = Path(__file__).resolve().parent / "cases.json"
TOP_K = 5


def load_cases() -> list[Case]:
    with open(JSON_FILE) as file:
        return [Case.model_validate(case) for case in load(file)]


async def evaluate(cases: list[Case], search) -> tuple[float, float, list[tuple[Case, list]]]:
    hits = 0
    ranks: list[int] = []
    errors: list[tuple[Case, list]] = []

    for case in cases:
        results = await search(case.question, TOP_K)
        found = [i for i, result in enumerate(results, start=1) if result["id"] in case.expected_case_ids]

        if found:
            hits += 1
            ranks.append(found[0])
        else:
            errors.append((case, results))

    recall = hits / len(cases)
    mrr = sum(1 / rank for rank in ranks) / len(cases)
    return recall, mrr, errors


async def run():
    cases = load_cases()
    recall, mrr, errors = await evaluate(cases, search_cases)

    print(f"MRR: {mrr}")
    print(f"recall@{TOP_K}: {recall}")
    for case, results in errors:
        print(f"MISS: {case.question}")
        print(f"  expected: {case.expected_case_ids}")
        print(f"  got: {[(result['id'], round(result['distance'], 4)) for result in results]}")


if __name__ == "__main__":
    asyncio.run(run())
