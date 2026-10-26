from os import getenv
from pathlib import Path

from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(ENV_PATH)

DATABASE_URL = getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(f"DATABASE_URL is not set; expected it in {ENV_PATH}")

OLLAMA_URL = getenv("OLLAMA_URL", "http://localhost:11434")
EMBEDDING_MODEL = getenv("EMBEDDING_MODEL", "nomic-embed-text")
CHAT_MODEL = getenv("CHAT_MODEL", "qwen2.5:7b-instruct")
STACK_EXCHANGE_URL = getenv("STACK_EXCHANGE_URL")
STACK_EXCHANGE_API_KEY = getenv("STACK_EXCHANGE_API_KEY")
