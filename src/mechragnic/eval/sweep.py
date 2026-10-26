import asyncio
import logging
from functools import partial

from mechragnic.eval.run import TOP_K, evaluate, load_cases
from mechragnic.retrieval.search import search_cases

logging.getLogger("httpx").setLevel(logging.WARNING)

ALPHAS = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]


async def sweep():
    cases = load_cases()
    for alpha in ALPHAS:
        recall, mrr, _ = await evaluate(cases, partial(search_cases, alpha=alpha))
        print(f"alpha {alpha:.1f}   recall@{TOP_K} {recall:.3f}   MRR {mrr:.3f}")


if __name__ == "__main__":
    asyncio.run(sweep())
