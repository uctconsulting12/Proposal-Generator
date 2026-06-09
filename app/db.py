"""Shared MongoDB connection helpers.

Every piece of durable state — user accounts, company profiles, chat
sessions, uploaded knowledge-base documents and company logos — lives in a
single MongoDB database. Pointing ``COPILOT_MONGODB_URI`` at a cloud cluster
(e.g. MongoDB Atlas) is therefore all it takes to make the whole application
multi-device: a user signs in with the same email + password from anywhere
and sees the same data, because the data never touches local disk.

A ``MongoClient`` maintains its own connection pool and is safe to share
across threads, so we cache one client per (uri) and reuse it everywhere
instead of opening a fresh connection on every call.
"""

from __future__ import annotations

import threading

from gridfs import GridFS
from pymongo import MongoClient
from pymongo.database import Database

from .config import Settings

_lock = threading.Lock()
_clients: dict[str, MongoClient] = {}


def get_client(settings: Settings) -> MongoClient:
    """Return a process-wide cached ``MongoClient`` for the configured URI."""
    uri = settings.mongodb_uri
    client = _clients.get(uri)
    if client is None:
        with _lock:
            client = _clients.get(uri)
            if client is None:
                client = MongoClient(uri, appname="jd-proposal-copilot")
                _clients[uri] = client
    return client


def get_db(settings: Settings) -> Database:
    """Return the application database handle."""
    return get_client(settings)[settings.mongodb_db_name]


def get_gridfs(settings: Settings, bucket: str) -> GridFS:
    """Return a GridFS handle for storing binary blobs (files, logos).

    ``bucket`` namespaces the stored files (e.g. ``"kb_files"`` vs
    ``"logos"``) so different kinds of uploads never collide.
    """
    return GridFS(get_db(settings), collection=bucket)
