"""Уведомления через outbox (этап 6, docs/05#уведомления-outbox).

Доменный код знает только enqueue (ставит событие в outbox с idempotency_key).
Диспетчер (в планировщике, тикает от FestivalClock) шлёт через подменяемый транспорт —
без брокера (ADR 0002). Идемпотентность: повторная постановка с тем же ключом не плодит дублей.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, List, Optional

from sqlmodel import Session, select

from figaro.domain.models import (Concert, OutboxMessage, RouteSheet,
                                  RouteSheetItem)
from figaro.services import availability

MAX_ATTEMPTS = 3


def _strip(dt: datetime) -> datetime:
    return dt.replace(tzinfo=None) if dt and dt.tzinfo else dt


def _noop_sender(message: OutboxMessage) -> None:
    """Транспорт по умолчанию (email-скелет). Реальная отправка — провайдер/SMTP."""
    return None


def enqueue(session: Session, *, type: str, user_id: Optional[int], scheduled_for: datetime,
            idempotency_key: str, payload: Optional[dict] = None) -> OutboxMessage:
    existing = session.exec(select(OutboxMessage).where(
        OutboxMessage.idempotency_key == idempotency_key)).first()
    if existing is not None:
        return existing  # идемпотентность: дубль не создаём
    m = OutboxMessage(type=type, user_id=user_id, scheduled_for=_strip(scheduled_for),
                      idempotency_key=idempotency_key, payload=payload or {}, status="pending")
    session.add(m)
    session.flush()
    return m


def dispatch(session: Session, now: datetime,
             sender: Optional[Callable[[OutboxMessage], None]] = None) -> List[OutboxMessage]:
    sender = sender or _noop_sender
    now = _strip(now)
    sent = []
    for m in session.exec(select(OutboxMessage).where(OutboxMessage.status == "pending")).all():
        if _strip(m.scheduled_for) > now:
            continue
        if m.next_attempt_at and _strip(m.next_attempt_at) > now:
            continue
        try:
            sender(m)
            m.status = "sent"
            m.sent_at = now
            sent.append(m)
        except Exception:
            m.attempts += 1
            if m.attempts >= MAX_ATTEMPTS:
                m.status = "failed"
            else:
                m.next_attempt_at = now + timedelta(minutes=m.attempts)  # возрастающий backoff
        session.add(m)
    session.flush()
    return sent


def schedule_reminders(session: Session, sheet: RouteSheet, minutes_before: int) -> None:
    for it in session.exec(select(RouteSheetItem).where(
            RouteSheetItem.route_sheet_id == sheet.id)).all():
        c = session.get(Concert, it.concert_id)
        enqueue(session, type="concert_reminder", user_id=sheet.user_id,
                scheduled_for=c.starts_at - timedelta(minutes=minutes_before),
                idempotency_key=f"reminder:{sheet.user_id}:{c.id}",
                payload={"concert_id": c.id})


def alert_soldout(session: Session, festival_id: int, concert_id: int, now: datetime) -> None:
    """Концерт из листа распродан → алерт с альтернативой (для каждого затронутого листа)."""
    concert = session.get(Concert, concert_id)
    items = session.exec(select(RouteSheetItem).where(
        RouteSheetItem.concert_id == concert_id)).all()
    for it in items:
        sheet = session.get(RouteSheet, it.route_sheet_id)
        alt = availability.find_alternative(session, festival_id, concert)
        enqueue(session, type="availability_alert", user_id=sheet.user_id, scheduled_for=now,
                idempotency_key=f"alert:{sheet.id}:{concert_id}:soldout",
                payload={"concert_id": concert_id,
                         "alternative_id": (alt.id if alt else None)})
