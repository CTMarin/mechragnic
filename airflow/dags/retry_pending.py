import asyncio
from datetime import UTC, datetime, timedelta

from airflow.sdk import dag, task

MAX_ATTEMPTS = 3


@dag(
    schedule="@daily",
    start_date=datetime(2026, 9, 1, tzinfo=UTC),
    catchup=False,
    max_active_runs=1,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["mechragnic", "ingest"],
)
def retry_pending_questions():
    @task(pool="ollama")
    def retry() -> dict:
        from mechragnic.ingest.pipeline import retry_pending
        from mechragnic.models.ingest_questions import IngestSummary

        summary: IngestSummary = asyncio.run(retry_pending(MAX_ATTEMPTS))
        return summary.model_dump(mode="json")

    retry()


retry_pending_questions()
