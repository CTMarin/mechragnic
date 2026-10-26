# Mechragnic

Mechragnic helps diagnose car faults from a plain description of the symptoms. Its
knowledge comes from [Motor Vehicle Maintenance & Repair Stack Exchange](https://mechanics.stackexchange.com),
a forum where people describe a problem with their vehicle and others answer with the
cause and the fix.

How it works:

1. An Apache Airflow DAG downloads the questions of each week and their answers from the
   Stack Exchange API.
2. A local LLM (Ollama) turns each thread into a structured case: symptoms, causes and
   solution. Threads that do not describe a fault (buying advice, procedures, tools) are
   discarded.
3. Each case is embedded and stored in PostgreSQL with pgvector, next to a full-text index.
4. A question is answered with hybrid search: vector similarity and full-text ranking
   combined with reciprocal rank fusion.
5. The search is exposed as MCP tools, used by an agent loop with a local model, a
   FastAPI endpoint and a small React chat in `web/`.

Retrieval is measured on a hand-labelled set of 100 questions
([`eval/cases.json`](src/mechragnic/eval/cases.json)), each with the case ids that answer
it. On the author's local database, with 521 cases ingested, hybrid search gets
**recall@5 = 0.81** and **MRR = 0.614**.

Everything runs locally; no external LLM API is used.

## Requirements

- Docker with Compose (Colima on macOS, with at least 4 GB of memory for Airflow)
- Ollama running on the host, with the models pulled:
  `ollama pull nomic-embed-text && ollama pull qwen2.5:7b-instruct`
- `uv` for local development, and `pnpm` for the web chat

Ollama stays on the host rather than in a container: Docker on macOS cannot use the
GPU, so it would be several times slower. Containers reach it at
`host.docker.internal:11434`.

## Secrets

Copy the example configuration and fill it in:

```bash
cp .env.example .env
```

`docker-compose.yaml` refuses to start without `FERNET_KEY` and
`AIRFLOW__API_AUTH__JWT_SECRET`. Generate them with:

```bash
uv run --with cryptography python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

`airflow/config/airflow.cfg` is not versioned: `airflow-init` generates it on the first
start. The `root`/`root` and `airflow`/`airflow` credentials in `docker-compose.yaml`
are for local development only.

## Starting everything

The first time, create the directories Airflow mounts and initialise it (database
migration and admin user):

```bash
mkdir -p airflow/logs airflow/plugins airflow/config
docker-compose up airflow-init
```

Then start the services and create the pool that limits concurrent use of Ollama:

```bash
docker-compose up -d
docker-compose exec airflow-scheduler airflow pools set ollama 1 "Ollama: one synthesis at a time"
```

This starts:

| Service | Purpose |
|---------|---------|
| `pgvector` | Application database on `localhost:5432` (`root`/`root`, database `mechragnic`) |
| `postgres` | Airflow's own metadata database, not exposed |
| `airflow-apiserver` | Airflow UI on http://localhost:8080 (`airflow`/`airflow`) |
| `airflow-scheduler`, `airflow-dag-processor`, `airflow-triggerer` | Airflow runtime, `LocalExecutor` |

On the first start with an empty volume, Postgres runs every file in
[migrations/](migrations/) to create the schema. Later changes to those files are not
applied automatically. The database starts empty: run the ingestion DAGs (see
[Ingestion](#ingestion)) to fill it.

After changing code under `src/mechragnic`, rebuild the image the Airflow services run:

```bash
docker-compose build && docker-compose up -d
```

DAG files under `airflow/dags` are mounted, so changes to them need no rebuild.

## Configuration

`.env` is read by the application (`config/settings.py`) and by Compose, which
also passes it into the Airflow containers. Inside those containers `DATABASE_URL`
and `OLLAMA_URL` are overridden in `docker-compose.yaml` to point at the `pgvector`
service and at the host.

| Variable | Used for |
|----------|----------|
| `DATABASE_URL` | Application database; required |
| `OLLAMA_URL` | Ollama base URL, default `http://localhost:11434` |
| `EMBEDDING_MODEL` | Default `nomic-embed-text`; must match the `VECTOR(768)` column |
| `CHAT_MODEL` | Default `qwen2.5:7b-instruct`; used for synthesis and the agent |
| `STACK_EXCHANGE_URL` | Stack Exchange API base URL |
| `STACK_EXCHANGE_API_KEY` | Optional; raises the Stack Exchange API quota |
| `AIRFLOW_UID` | User that owns the files Airflow writes to the mounted directories |
| `FERNET_KEY` | Airflow Fernet key; required, see [Secrets](#secrets) |
| `AIRFLOW__API_AUTH__JWT_SECRET` | Secret Airflow signs its API tokens with; required |

## Ingestion

Two DAGs, both limited to the `ollama` pool:

| DAG | Schedule | Does |
|-----|----------|------|
| `ingest_questions` | weekly, Sunday to Sunday | Ingests the questions created in the run's data interval |
| `retry_pending_questions` | daily | Retries pending questions that are worth retrying |

The business logic lives in `mechragnic.ingest.pipeline` and imports nothing from
Airflow; the DAGs only call `ingest_window(start, end)` and `retry_pending(max_attempts)`.

For each question, the pipeline synthesises a diagnostic case with the LLM, keeps it
only if it describes a fault, embeds it and stores it. Every question seen is recorded
in `ingest_questions` as `inserted`, `skipped` (not a fault) or `pending` with a
reason. A retried window skips questions already recorded, so it never repeats a
synthesis.

`retry_pending` always retries `ollama_error` and `db_error`. It retries `no_answer`
and `invalid_case` only when the thread now has more answers than when it was
processed, since synthesis is deterministic and would otherwise give the same result.

The DAG has `catchup=False`: enabling it runs only the latest finished week. History
is loaded with a backfill, from the UI (Trigger → Backfill) or the CLI:

```bash
docker-compose exec airflow-scheduler airflow backfill create \
  --dag-id ingest_questions --from-date 2024-03-03 --to-date 2024-03-03 --dry-run
```

`start_date` is 2010-11-21, the Sunday before the oldest question on the site: one
migrated from another Stack Exchange site that keeps its original creation date.

## Schema

```
ingest_questions (question_id PK, creation_date, status, reason, answer_count,
                  attempt_count, last_checked_at)
        │ 1
        │
        │ 0..1
mechanic_cases   (id PK → ingest_questions.question_id, symptoms, causes, solution,
                  embedding VECTOR(768))
```

`status` and `reason` are Postgres enums, mirrored by the `IngestStatus` and
`IngestPendingReason` enums in Python. A check constraint enforces that `reason` is set
if and only if `status` is `pending`.

## Local development

```bash
uv sync
uv run python -m mechragnic.eval.run          # retrieval: recall@5 and MRR
uv run python -m mechragnic.eval.compare      # retrieval: per-question ranks, two configurations
uv run python -m mechragnic.eval.diagnosis    # synthesis: fault classifier precision and recall
uv run python -m mechragnic.agent.main        # ask the agent a question
uv run mcp dev src/mechragnic/tools/server.py # web inspector for the MCP tools
```

Run modules with `-m` from the repository root, never as loose files, and mark `src`
(not `src/mechragnic`) as the sources root in the IDE.

| Module | Contents |
|--------|----------|
| `config/` | Settings loaded once from `.env` |
| `models/` | Pydantic models and enums |
| `clients/` | Ollama: embeddings, chat, structured chat |
| `database/` | Connection and SQL; functions take a connection and never call Ollama |
| `retrieval/` | Embeds a question and searches the database |
| `embedding/` | Builds the text embedded for a case |
| `ingest/` | Stack Exchange client, synthesis and the ingestion pipeline |
| `tools/` | MCP server exposing the retrieval tools |
| `agent/` | Agent loop over the MCP tools with a local model |
| `api/` | FastAPI app exposing the agent at `POST /ask` |
| `eval/` | Evaluation sets and scripts |
| `scripts/` | One-off maintenance scripts |

`apache-airflow-task-sdk` is installed locally as the default `airflow` dependency
group, only so the IDE can resolve imports in the DAG files.

### MCP tools

| Tool | Purpose |
|------|---------|
| `search_cases(query, top_k)` | Embeds the query and returns the nearest cases with their distances |
| `get_case(case_id)` | Fetches a single case by id |

To use them from Claude Code, register the server with the path to this repository:

```bash
claude mcp add vehicle-diagnostics -- uv --directory /path/to/mechragnic run python -m mechragnic.tools.server
```

### API and web chat

```bash
uv run uvicorn mechragnic.api.app:app        # POST /ask on http://localhost:8000
cd web && pnpm install && pnpm dev           # chat on http://localhost:5173
```

### Tests and linting

```bash
uv run pytest
uv run ruff check
uv run ruff format --check
```

The tests cover pure logic only (retry decision, embedding text, model validation) and
need neither the database nor Ollama. GitHub Actions runs the three commands on every
push and pull request.

## Data and licence

The code is released under the [MIT licence](LICENSE).

The cases are derived from questions and answers on
[Motor Vehicle Maintenance & Repair Stack Exchange](https://mechanics.stackexchange.com),
published under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
Every case id is the id of its source question, reachable at
`https://mechanics.stackexchange.com/q/<id>`. The evaluation files in
[`src/mechragnic/eval/`](src/mechragnic/eval/) contain question titles from the site and
are shared under the same licence. They contain no user names.
