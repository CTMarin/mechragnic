import asyncio
import logging
from collections import defaultdict
from datetime import datetime

from bs4 import BeautifulSoup
from httpx import AsyncClient

from mechragnic.config import settings
from mechragnic.models.stack_exchange import AnswersPage, ApiAnswer, ApiQuestion, QuestionsPage, QuestionWithAnswers

logger = logging.getLogger(__name__)

MAX_PAGES = 50


async def fetch_questions_page(client: AsyncClient, start: datetime, end: datetime, page: int) -> QuestionsPage:
    response = await client.get(
        f"{settings.STACK_EXCHANGE_URL}/questions",
        params={
            **_base_params(),
            "fromdate": int(start.timestamp()),
            "todate": int(end.timestamp()) - 1,
            "sort": "creation",
            "order": "asc",
            "pagesize": 100,
            "page": page,
            "filter": "withbody",
        },
        headers={"User-Agent": "mechragnic/0.1"},
    )
    response.raise_for_status()

    return QuestionsPage.model_validate(response.json())


async def fetch_questions_page_by_ids(client: AsyncClient, question_ids: str) -> QuestionsPage:
    response = await client.get(
        f"{settings.STACK_EXCHANGE_URL}/questions/{question_ids}",
        params={**_base_params(), "sort": "creation", "order": "asc", "pagesize": 100, "filter": "withbody"},
        headers={"User-Agent": "mechragnic/0.1"},
    )
    response.raise_for_status()

    return QuestionsPage.model_validate(response.json())


async def fetch_answers_page(client: AsyncClient, question_ids: str, page: int) -> AnswersPage:
    response = await client.get(
        f"{settings.STACK_EXCHANGE_URL}/questions/{question_ids}/answers",
        params={**_base_params(), "pagesize": 100, "page": page, "filter": "withbody"},
        headers={"User-Agent": "mechragnic/0.1"},
    )
    response.raise_for_status()

    return AnswersPage.model_validate(response.json())


async def fetch_questions(start: datetime, end: datetime) -> list[ApiQuestion]:
    page: int = 1
    has_more: bool = True
    questions: list[ApiQuestion] = []

    async with AsyncClient(timeout=5.0) as client:
        while has_more and page <= MAX_PAGES:
            questions_page: QuestionsPage = await fetch_questions_page(client, start, end, page)
            logger.info(
                "[QUESTIONS] page %s: %s items, has_more=%s, quota_remaining=%s",
                page,
                len(questions_page.items),
                questions_page.has_more,
                questions_page.quota_remaining,
            )
            questions.extend(questions_page.items)

            if questions_page.backoff:
                await asyncio.sleep(questions_page.backoff)

            has_more = questions_page.has_more
            page += 1

    if has_more:
        raise RuntimeError(f"window {start} to {end} has more than {MAX_PAGES} pages")

    return questions


async def fetch_answers(question_ids: list[int]) -> list[ApiAnswer]:
    answers: list[ApiAnswer] = []
    async with AsyncClient(timeout=5.0) as client:
        for index in range(0, len(question_ids), 100):
            page: int = 1
            has_more: bool = True

            chunk: list[int] = question_ids[index : index + 100]
            question_ids_parameter: str = ";".join(str(question_id) for question_id in chunk)

            while has_more and page <= MAX_PAGES:
                answers_page: AnswersPage = await fetch_answers_page(client, question_ids_parameter, page)
                logger.info(
                    "[ANSWERS] page %s: %s items, has_more=%s, quota_remaining=%s",
                    page,
                    len(answers_page.items),
                    answers_page.has_more,
                    answers_page.quota_remaining,
                )
                answers.extend(answers_page.items)

                if answers_page.backoff:
                    await asyncio.sleep(answers_page.backoff)

                has_more = answers_page.has_more
                page += 1

            if has_more:
                raise RuntimeError(f"answers for questions {chunk[0]}...{chunk[-1]} has more than {MAX_PAGES} pages")

    return answers


async def fetch_questions_by_ids(question_ids: list[int]) -> list[ApiQuestion]:
    questions: list[ApiQuestion] = []
    async with AsyncClient(timeout=5.0) as client:
        for index in range(0, len(question_ids), 100):
            chunk = question_ids[index : index + 100]
            ids = ";".join(str(question_id) for question_id in chunk)
            questions_page = await fetch_questions_page_by_ids(client, ids)
            questions.extend(questions_page.items)
            if questions_page.backoff:
                await asyncio.sleep(questions_page.backoff)

    return questions


def clean_html(raw_html: str) -> str:
    return BeautifulSoup(raw_html, "html.parser").get_text(separator="\n", strip=True)


def build_cases(questions: list[ApiQuestion], answers: list[ApiAnswer]) -> list[QuestionWithAnswers]:
    cases: list[QuestionWithAnswers] = []
    answers_by_question: defaultdict[int, list[ApiAnswer]] = defaultdict(list)
    for answer in answers:
        answers_by_question[answer.question_id].append(answer.model_copy(update={"body": clean_html(answer.body)}))

    for question in questions:
        case: QuestionWithAnswers = QuestionWithAnswers(
            question_id=question.question_id,
            creation_date=question.creation_date,
            title=clean_html(question.title),
            body=clean_html(question.body),
            tags=question.tags,
            answers=answers_by_question[question.question_id],
        )
        cases.append(case)

    return cases


def _base_params() -> dict:
    params = {"site": "mechanics"}
    if settings.STACK_EXCHANGE_API_KEY:
        params["key"] = settings.STACK_EXCHANGE_API_KEY
    return params
