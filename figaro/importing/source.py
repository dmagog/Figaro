"""Источник каталога для импорта.

Абстракция, чтобы тесты/BDD кормили маленькие детерминированные наборы,
а CLI — реальные Excel-выгрузки. Импорт (`seed.py`) работает с этими структурами,
не зная про Excel.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class HallRow:
    name: str
    address: Optional[str] = None
    seats: int = 0
    lat: Optional[float] = None
    lon: Optional[float] = None


@dataclass
class TransitionRow:
    from_name: str
    to_name: str
    minutes: int


@dataclass
class ConcertRow:
    show_num: int
    crm_show_id: Optional[int]
    title: str
    hall_name: str
    starts_at: datetime
    duration_min: int
    genre: Optional[str] = None
    price_kopecks: int = 0
    is_family_friendly: bool = False
    capacity: Optional[int] = None  # None → дефолт = вместимость зала
    link: Optional[str] = None


@dataclass
class ArtistRow:
    show_num: int
    name: str
    is_special: bool = False


@dataclass
class CompositionRow:
    show_num: int
    author: str
    title: str


@dataclass
class PurchaseRow:
    external_op_id: int
    customer_external_id: str
    crm_show_id: int
    purchased_at_raw: object  # сырое значение даты (datetime/str/excel-serial)
    price_kopecks: int = 0


@dataclass
class OffProgramRow:
    external_num: int
    title: str
    hall_name: Optional[str] = None
    starts_at: object = None        # datetime/str/excel-serial
    duration_min: Optional[int] = None
    description: Optional[str] = None
    fmt: Optional[str] = None
    recommend: bool = False
    link: Optional[str] = None


@dataclass
class CatalogSource:
    halls: List[HallRow] = field(default_factory=list)
    transitions: List[TransitionRow] = field(default_factory=list)
    concerts: List[ConcertRow] = field(default_factory=list)
    artists: List[ArtistRow] = field(default_factory=list)
    compositions: List[CompositionRow] = field(default_factory=list)
    purchases: List[PurchaseRow] = field(default_factory=list)
    off_program: List[OffProgramRow] = field(default_factory=list)


def _long_to_min(v) -> Optional[int]:
    if v is None or str(v).strip() == "" or str(v) == "nan":
        return None
    parts = str(v).split(":")
    h = int(parts[0])
    m = int(parts[1]) if len(parts) > 1 else 0
    return h * 60 + m


def offprogram_from_excel(data_dir: str) -> List[OffProgramRow]:
    """Парсинг файла офф-программы (Offprogram-good.xlsx) → строки. Для CLI и проверки данных."""
    import pandas as pd
    from pathlib import Path

    df = pd.read_excel(Path(data_dir) / "Offprogram-good.xlsx")
    rows = []
    for _, r in df.iterrows():
        rows.append(OffProgramRow(
            external_num=int(r["EventNum"]), title=str(r["EventName"]),
            hall_name=(None if str(r.get("HallName")) == "nan" else r.get("HallName")),
            starts_at=r.get("EventDate"), duration_min=_long_to_min(r.get("EventLong")),
            description=(None if str(r.get("Description")) == "nan" else r.get("Description")),
            fmt=(None if str(r.get("Format")) == "nan" else r.get("Format")),
            recommend=bool(r.get("Recommend")),
            link=(None if str(r.get("link")) == "nan" else r.get("link"))))
    return rows


def from_excel(data_dir: str) -> CatalogSource:  # pragma: no cover - путь CLI, не покрывается BDD
    """Адаптер реальных выгрузок (Excel/CSV) → CatalogSource.

    Намеренно вне автотестов: реальные данные (особенно даты покупок `OpDate`)
    требуют чистки по аудиту (docs/05). Используется в CLI-настройке фестиваля.
    """
    import pandas as pd
    from pathlib import Path

    d = Path(data_dir)

    def long_to_min(v) -> int:
        # "00:45:00" → 45
        parts = str(v).split(":")
        h, m = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
        return h * 60 + m

    halls = [HallRow(name=r["HallName"], address=r.get("Adress"), seats=int(r.get("Seats") or 0),
                     lat=r.get("latitude"), lon=r.get("longitude"))
             for _, r in pd.read_excel(d / "HallList-good.xlsx").iterrows()]

    tm = pd.read_excel(d / "HallsTime-good.xlsx")
    origin_col = tm.columns[0]
    transitions = []
    for _, row in tm.iterrows():
        frm = row[origin_col]
        for to in tm.columns[1:]:
            transitions.append(TransitionRow(from_name=frm, to_name=to, minutes=int(row[to])))

    concerts = [ConcertRow(show_num=int(r["ShowNum"]), crm_show_id=int(r["ShowId"]),
                           title=r["ShowName"], hall_name=r["HallName"],
                           starts_at=r["ShowDate"], duration_min=long_to_min(r["ShowLong"]),
                           genre=r.get("Genre"), price_kopecks=int(r.get("Price") or 0) * 100,
                           is_family_friendly=bool(r.get("Family")) )
                for _, r in pd.read_excel(d / "ConcertList-good.xlsx").iterrows()]

    artists = [ArtistRow(show_num=int(r["ShowNum"]), name=r["Artists"], is_special=bool(r.get("Spetial")))
               for _, r in pd.read_excel(d / "ArtistDetails-good.xlsx").iterrows()]

    compositions = [CompositionRow(show_num=int(r["ShowNum"]), author=r["Author"], title=str(r["Programm"]).strip())
                    for _, r in pd.read_excel(d / "show_details.xlsx").iterrows()]

    purchases = [PurchaseRow(external_op_id=int(r["OpId"]), customer_external_id=str(r["ClientId"]),
                             crm_show_id=int(r["ShowId"]), purchased_at_raw=r["OpDate"],
                             price_kopecks=int(r.get("Price") or 0) * 100)
                 for _, r in pd.read_excel(d / "GoodOperations.xlsx").iterrows()]

    off_program = offprogram_from_excel(data_dir)

    return CatalogSource(halls=halls, transitions=transitions, concerts=concerts,
                         artists=artists, compositions=compositions, purchases=purchases,
                         off_program=off_program)
