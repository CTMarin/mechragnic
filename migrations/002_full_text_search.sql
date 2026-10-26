CREATE OR REPLACE FUNCTION join_text(text[]) RETURNS text
    LANGUAGE sql IMMUTABLE PARALLEL SAFE
    AS $$ SELECT array_to_string($1, ' ') $$;

ALTER TABLE mechanic_cases
    ADD COLUMN search_text tsvector GENERATED ALWAYS AS (
        to_tsvector('english', join_text(symptoms) || ' ' || join_text(causes))
    ) STORED;

CREATE INDEX mechanic_cases_search_text_idx ON mechanic_cases USING gin(search_text);