"""CLI настройки фестиваля (этапы 1–2 идут через CLI, до появления админ-UI на этапе 3).

Пример:
    python -m figaro.importing.cli --name "Безумные дни 2022" --year 2022 \
        --sales-start 2022-06-01 --start 2022-07-01 --end 2022-07-03 --data-dir data
"""
from __future__ import annotations

import argparse
from datetime import date

from figaro.config import settings
from figaro.db import make_engine, session_scope
from figaro.importing.seed import import_catalog
from figaro.importing.source import from_excel
from figaro.services.festival import create_festival


def main() -> None:  # pragma: no cover - операторский путь
    p = argparse.ArgumentParser(description="Создать фестиваль и импортировать каталог из Excel")
    p.add_argument("--name", required=True)
    p.add_argument("--year", type=int, required=True)
    p.add_argument("--sales-start", type=date.fromisoformat, required=True)
    p.add_argument("--start", type=date.fromisoformat, required=True)
    p.add_argument("--end", type=date.fromisoformat, required=True)
    p.add_argument("--data-dir", default="data")
    args = p.parse_args()

    engine = make_engine(settings.database_url)
    with session_scope(engine) as s:
        fest = create_festival(s, name=args.name, year=args.year, sales_start_on=args.sales_start,
                               starts_on=args.start, ends_on=args.end)
        import_catalog(s, fest.id, from_excel(args.data_dir))
        print(f"festival #{fest.id} '{fest.name}' (draft) — каталог импортирован")


if __name__ == "__main__":
    main()
