"""Точка входа FastAPI (server-rendered + HTMX, ADR 0001).
Этап 0 — минимальное приложение со health-check; экраны добавляются с этапа 3+.
"""
from __future__ import annotations

from fastapi import FastAPI

from figaro import __version__

app = FastAPI(title="Figaro v3", version=__version__)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}
