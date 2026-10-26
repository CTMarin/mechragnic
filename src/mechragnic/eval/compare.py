import asyncio
import logging

from mechragnic.eval.questions import Case
from mechragnic.eval.run import load_cases
from mechragnic.retrieval.search import search_cases, search_cases_vector

logging.getLogger("httpx").setLevel(logging.WARNING)

TOP_K = 10

BASELINE = ("vector", search_cases_vector)
CANDIDATE = ("hybrid", search_cases)


async def rank_of_expected(case: Case, search) -> int | None:
    results = await search(case.question, TOP_K)
    found = [position for position, result in enumerate(results, start=1) if result["id"] in case.expected_case_ids]
    return found[0] if found else None


def format_rank(rank: int | None) -> str:
    return str(rank) if rank is not None else "-"


def is_better(before: int | None, after: int | None) -> bool:
    if after is None:
        return False
    return before is None or after < before


async def compare():
    cases = load_cases()

    baseline_label, baseline_search = BASELINE
    candidate_label, candidate_search = CANDIDATE

    changed: list[tuple[str, int | None, int | None, str]] = []

    print(f"{'question':<62} {baseline_label:>10} {candidate_label:>10}")
    for case in cases:
        before = await rank_of_expected(case, baseline_search)
        after = await rank_of_expected(case, candidate_search)

        verdict = ""
        if before != after:
            verdict = "better" if is_better(before, after) else "WORSE"
            changed.append((case.question, before, after, verdict))

        print(f"{case.question[:62]:<62} {format_rank(before):>10} {format_rank(after):>10}  {verdict}")

    print(f"\n{len(changed)} of {len(cases)} questions changed rank:")
    for question, before, after, verdict in changed:
        print(f"  {verdict:<6} {format_rank(before)} -> {format_rank(after)}  {question}")


asyncio.run(compare())
