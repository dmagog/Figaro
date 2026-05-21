"""Единый конфиг (pydantic-settings). Всё, что в v2 было хардкодом, — здесь."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Приложение ---
    app_name: str = "Figaro"
    debug: bool = False
    festival_timezone: str = "Europe/Moscow"

    # --- БД / кэш ---
    database_url: str = "postgresql+psycopg2://figaro:figaro@db:5432/figaro"
    redis_url: str = "redis://redis:6379/0"

    # --- Часы (FestivalClock) ---
    clock_default_mode: str = "real"  # real | offset | accelerated
    clock_state_path: str = "instance/clock_state.json"
    tick_seconds: int = 30  # период реального тика планировщика

    # --- Пороги конфликтов переходов (мин) ---
    buffer_tight_minutes: int = 10
    buffer_overlap_slack: int = 3
    default_concert_minutes: int = 90
    walk_speed_m_per_min: float = 83.3

    # --- Наличие ---
    availability_mode: str = "sim_curve"  # sim_curve | sim_replay | crm_import
    availability_seed: int = 42

    # --- Почта (outbox) ---
    smtp_url: str = ""


settings = Settings()
