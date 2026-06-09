"""Service container and FastAPI dependency providers.

A single ``Services`` instance is built during application startup and stored on
``app.state``. Route handlers receive the pieces they need via the dependency
functions below, which keeps handlers free of global state and easy to test.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from .config import Settings
from .llm import LlmClient
from .rag import RagService
from .storage import MongoSessionStore


@dataclass
class Services:
    settings: Settings
    store: MongoSessionStore
    llm: LlmClient
    rag: RagService


def _services(request: Request) -> Services:
    return request.app.state.services


def get_settings_dep(request: Request) -> Settings:
    return _services(request).settings


def get_store(request: Request) -> MongoSessionStore:
    return _services(request).store


def get_llm(request: Request) -> LlmClient:
    return _services(request).llm


def get_rag(request: Request) -> RagService:
    return _services(request).rag
