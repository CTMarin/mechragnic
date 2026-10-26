CREATE EXTENSION IF NOT EXISTS vector;

CREATE TYPE ingest_status AS ENUM ('inserted', 'skipped', 'pending');
CREATE TYPE ingest_pending_reason AS ENUM ('no_answer', 'invalid_case', 'ollama_error', 'db_error');

CREATE TABLE ingest_questions(
    question_id BIGINT PRIMARY KEY,
    creation_date BIGINT NOT NULL,
    status ingest_status NOT NULL,
    reason ingest_pending_reason,
    answer_count INTEGER NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 1,
    last_checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT if_pending_reason_not_null CHECK ((status = 'pending') = (reason IS NOT NULL))
);

CREATE TABLE mechanic_cases(
    id BIGINT PRIMARY KEY REFERENCES ingest_questions (question_id),
    symptoms TEXT[] NOT NULL,
    causes TEXT[] NOT NULL,
    solution TEXT[] NOT NULL,
    embedding VECTOR(768) NOT NULL
);