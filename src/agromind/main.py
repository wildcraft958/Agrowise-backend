"""AgroMind FastAPI application entry point."""
from __future__ import annotations

from fastapi import FastAPI

from agromind.api import chat, diagnosis, health

app = FastAPI(title="AgroMind", version="0.1.0")

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(diagnosis.router)
