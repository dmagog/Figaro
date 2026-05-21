"""Планировщик: один на инстанс (отдельный процесс/лидер через advisory-lock).
Тики наличия и диспетчер outbox двигаются от FestivalClock. Без брокера (ADR 0002).

Скелет этапа 0 — реализация тиков появляется на этапах 5–6 (см. docs/figaro-v3/06-mvp-roadmap.md).
"""
from __future__ import annotations


def run() -> None:  # pragma: no cover - точка входа сервиса scheduler
    raise NotImplementedError("Тики наличия/уведомлений реализуются на этапах 5–6")


if __name__ == "__main__":  # pragma: no cover
    run()
