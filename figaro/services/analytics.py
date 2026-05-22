"""Аналитика для роли «исследователь» (дашборды).

Только агрегаты и псевдонимы покупателей — без ПДн (docs/08). Источники: каталог,
история снимков наличия (`AvailabilitySnapshot`) и покупки (псевдоним `customer_external_id`).
Веб-слой лишь показывает эти агрегаты.
"""
from __future__ import annotations

from typing import Dict, List

from sqlmodel import Session, select

from figaro.domain.models import (Archetype, AvailabilitySnapshot, Concert,
                                  DayRoute, Hall, Purchase)
from figaro.services import availability


def festival_overview(session: Session, festival_id: int) -> Dict[str, int]:
    concerts = session.exec(select(Concert).where(Concert.festival_id == festival_id)).all()
    halls = session.exec(select(Hall).where(Hall.festival_id == festival_id)).all()
    routes = session.exec(select(DayRoute).where(DayRoute.festival_id == festival_id)).all()
    arches = session.exec(select(Archetype).where(Archetype.festival_id == festival_id)).all()
    on_sale = sum(1 for c in concerts if availability.is_on_sale(session, c.id))
    available_routes = sum(1 for dr in routes if availability.route_available(session, dr.id))
    return {"concerts": len(concerts), "halls": len(halls), "day_routes": len(routes),
            "available_routes": available_routes, "archetypes": len(arches),
            "on_sale": on_sale, "sold_out": len(concerts) - on_sale}


def enumerated_route_total(session: Session, festival_id: int) -> int:
    """Сколько путей перечисляется до Парето-отсева (dev-метрика «сжатия»; с потолком перечисления)."""
    from figaro.batch.precompute import _concert_lite, build_resolver
    from figaro.domain.models import FestivalDay
    from figaro.domain.routing.dayroutes import build_day_routes

    resolver = build_resolver(session, festival_id)
    total = 0
    for day in session.exec(select(FestivalDay).where(
            FestivalDay.festival_id == festival_id)).all():
        concerts = session.exec(select(Concert).where(
            Concert.festival_id == festival_id, Concert.festival_day_id == day.id)).all()
        if concerts:
            total += len(build_day_routes([_concert_lite(session, c) for c in concerts], resolver))
    return total


def archetype_supply(session: Session, festival_id: int) -> List[dict]:
    """Сколько предрассчитанных маршрутов на архетип + средние comfort/diversity."""
    titles = {a.id: (a.key, a.title) for a in session.exec(
        select(Archetype).where(Archetype.festival_id == festival_id)).all()}
    groups: Dict[int, list] = {}
    for dr in session.exec(select(DayRoute).where(DayRoute.festival_id == festival_id)).all():
        groups.setdefault(dr.archetype_id, []).append(dr)
    out = []
    for aid, drs in groups.items():
        key, title = titles.get(aid, ("other", "Прочее"))
        n = len(drs)
        out.append({"key": key, "title": title, "routes": n,
                    "avg_comfort": round(sum(d.comfort_score for d in drs) / n, 2),
                    "avg_diversity": round(sum(d.diversity_score for d in drs) / n, 2)})
    out.sort(key=lambda x: x["routes"], reverse=True)
    return out


def availability_timeline(session: Session, festival_id: int) -> List[dict]:
    """Кривая продаж по снимкам: на каждый момент — суммарный остаток и сколько распродано."""
    cids = {c.id for c in session.exec(
        select(Concert).where(Concert.festival_id == festival_id)).all()}
    by_time: Dict = {}
    for sn in session.exec(select(AvailabilitySnapshot)).all():
        if sn.concert_id not in cids:
            continue
        b = by_time.setdefault(sn.at, {"at": sn.at, "tickets_left": 0,
                                       "sold_out": 0, "on_sale": 0})
        b["tickets_left"] += sn.tickets_left or 0
        if sn.is_on_sale:
            b["on_sale"] += 1
        else:
            b["sold_out"] += 1
    return [by_time[k] for k in sorted(by_time)]


def customer_purchase_counts(session: Session, festival_id: int, top: int = 20) -> dict:
    """Псевдонимизированная сводка покупок: всего покупателей/покупок + топ по числу покупок."""
    counts: Dict[str, int] = {}
    for p in session.exec(select(Purchase).where(Purchase.festival_id == festival_id)).all():
        counts[p.customer_external_id] = counts.get(p.customer_external_id, 0) + 1
    top_list = sorted(({"customer": c, "purchases": n} for c, n in counts.items()),
                      key=lambda x: x["purchases"], reverse=True)[:top]
    return {"customers": len(counts), "purchases": sum(counts.values()), "top": top_list}
