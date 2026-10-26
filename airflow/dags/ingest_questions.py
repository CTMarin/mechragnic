import asyncio
from datetime import UTC, datetime, timedelta

from airflow.sdk import dag, task
from airflow.timetables.interval import CronDataIntervalTimetable


@dag(
    schedule=CronDataIntervalTimetable("@weekly", timezone="UTC"),
    start_date=datetime(2010, 11, 21, tzinfo=UTC),
    catchup=False,
    max_active_runs=1,
    default_args={
        "retries": 3,
        "retry_delay": timedelta(minutes=5),
        "retry_exponential_backoff": True,
    },
    tags=["mechragnic", "ingest"],
)
def ingest_questions():
    @task(pool="ollama")
    def ingest(data_interval_start=None, data_interval_end=None) -> dict:
        from mechragnic.ingest.pipeline import ingest_window
        from mechragnic.models.ingest_questions import IngestSummary

        summary: IngestSummary = asyncio.run(ingest_window(data_interval_start, data_interval_end))
        return summary.model_dump(mode="json")

    ingest()


ingest_questions()
