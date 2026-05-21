"""FestivalClock — единый провайдер времени (ADR 0005).

Нигде в домене не зовём datetime.now() напрямую — только через этот провайдер.
Режимы: real / offset / accelerated. Фазы фестиваля выводятся из дат.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable, Optional


class ClockMode(str, Enum):
    REAL = "real"
    OFFSET = "offset"
    ACCELERATED = "accelerated"


class Phase(str, Enum):
    PRE_SALE = "pre_sale"
    ON_SALE = "on_sale"
    FESTIVAL = "festival"
    POST = "post"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ClockState:
    mode: ClockMode = ClockMode.REAL
    anchor_real: Optional[datetime] = None      # реальное время в момент привязки
    anchor_virtual: Optional[datetime] = None   # виртуальное время в момент привязки
    speed: float = 1.0                           # K для accelerated

    def to_json(self) -> str:
        return json.dumps({
            "mode": self.mode.value,
            "anchor_real": self.anchor_real.isoformat() if self.anchor_real else None,
            "anchor_virtual": self.anchor_virtual.isoformat() if self.anchor_virtual else None,
            "speed": self.speed,
        })

    @classmethod
    def from_json(cls, s: str) -> "ClockState":
        d = json.loads(s)
        return cls(
            mode=ClockMode(d["mode"]),
            anchor_real=datetime.fromisoformat(d["anchor_real"]) if d.get("anchor_real") else None,
            anchor_virtual=datetime.fromisoformat(d["anchor_virtual"]) if d.get("anchor_virtual") else None,
            speed=d.get("speed", 1.0),
        )


class FestivalClock:
    def __init__(self, state: Optional[ClockState] = None,
                 real_now: Optional[Callable[[], datetime]] = None):
        self.state = state or ClockState()
        self._real_now = real_now or _utcnow

    @property
    def mode(self) -> ClockMode:
        return self.state.mode

    def now(self) -> datetime:
        s = self.state
        real = self._real_now()
        if s.mode == ClockMode.REAL:
            return real
        elapsed = real - s.anchor_real
        if s.mode == ClockMode.OFFSET:
            return s.anchor_virtual + elapsed
        if s.mode == ClockMode.ACCELERATED:
            return s.anchor_virtual + elapsed * s.speed
        raise ValueError(f"unknown clock mode: {s.mode}")

    # --- управление режимом ---
    def set_real(self) -> None:
        self.state = ClockState(mode=ClockMode.REAL)

    def set_offset(self, virtual_now: datetime) -> None:
        self.state = ClockState(mode=ClockMode.OFFSET,
                                anchor_real=self._real_now(), anchor_virtual=virtual_now)

    def set_accelerated(self, virtual_now: datetime, speed: float) -> None:
        self.state = ClockState(mode=ClockMode.ACCELERATED,
                                anchor_real=self._real_now(), anchor_virtual=virtual_now, speed=speed)

    def jump_to(self, virtual_now: datetime) -> None:
        """Перевести виртуальное время на точку, сохранив текущий ход (offset/accelerated)."""
        mode = self.state.mode if self.state.mode != ClockMode.REAL else ClockMode.OFFSET
        speed = self.state.speed if self.state.mode == ClockMode.ACCELERATED else 1.0
        self.state = ClockState(mode=mode, anchor_real=self._real_now(),
                                anchor_virtual=virtual_now, speed=speed)

    # --- персистентность (переживает рестарт) ---
    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.state.to_json())

    @classmethod
    def load(cls, path: str | Path,
             real_now: Optional[Callable[[], datetime]] = None) -> "FestivalClock":
        return cls(state=ClockState.from_json(Path(path).read_text()), real_now=real_now)


def phase_for(d: date, sales_start: date, festival_start: date, festival_end: date) -> Phase:
    if d < sales_start:
        return Phase.PRE_SALE
    if d < festival_start:
        return Phase.ON_SALE
    if d <= festival_end:
        return Phase.FESTIVAL
    return Phase.POST
