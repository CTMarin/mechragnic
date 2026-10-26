from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mechragnic.api.controller.ask import ask_router
from mechragnic.api.controller.health import health_router

app = FastAPI(title="Mechragnic LLM API")
app.include_router(ask_router)
app.include_router(health_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
