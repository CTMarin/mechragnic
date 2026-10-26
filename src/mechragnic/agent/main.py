import logging
from asyncio import run

from mechragnic.agent import client
from mechragnic.agent.prompts import SYSTEM_PROMPT

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

if __name__ == "__main__":
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "my battery is flat every morning even though I don't leave anything on"},
    ]
    response, trace = run(client.ask(messages))
    print(response)
    print(trace)
