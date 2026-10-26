import os

# config/settings.py raises at import time when DATABASE_URL is missing. These tests never
# connect to a database, so a placeholder is enough when no .env is present (as in CI).
os.environ.setdefault("DATABASE_URL", "postgres://unused@localhost/unused")
