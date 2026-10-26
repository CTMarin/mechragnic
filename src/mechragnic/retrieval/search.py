from collections import defaultdict

from mechragnic.clients.ollama import create_embedding
from mechragnic.database.cases import get_cases_by_ids_ordered, search_by_embedding, search_by_keywords

CANDIDATES = 20


async def search_cases_vector(query: str, top_k: int) -> list[dict]:
    embedding = await create_embedding(query)
    return await search_by_embedding(embedding, top_k)


async def search_cases(query: str, top_k: int, alpha: float = 0.7) -> list[dict]:
    embedding = await create_embedding(query)
    embedding_result_ids: list[int] = [case["id"] for case in await search_by_embedding(embedding, CANDIDATES)]
    keyword_result_ids: list[int] = await search_by_keywords(query, CANDIDATES)

    result_ids: list[int] = reciprocal_rank_fusion([embedding_result_ids, keyword_result_ids], [alpha, 1 - alpha])[
        :top_k
    ]
    results: list[dict] = await get_cases_by_ids_ordered(result_ids, embedding)

    return results


def reciprocal_rank_fusion(rankings: list[list[int]], weights: list[float], k: int = 60) -> list[int]:
    scores: defaultdict[int, float] = defaultdict(float)

    for ranking, weight in zip(rankings, weights):
        for position, case_id in enumerate(ranking, start=1):
            scores[case_id] += weight / (k + position)

    return sorted(scores, key=scores.get, reverse=True)
