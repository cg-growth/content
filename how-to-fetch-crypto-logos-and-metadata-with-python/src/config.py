from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_local_env_file() -> None:
    """Load .env from repo root if present, without overriding existing env vars."""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True)
class ApiConfig:
    mode: str
    api_key: str | None
    timeout_seconds: int
    retry_max: int
    backoff_seconds: float
    debug: bool
    save_raw: bool

    @property
    def base_url(self) -> str:
        if self.mode == "pro":
            return "https://pro-api.coingecko.com/api/v3"
        return "https://api.coingecko.com/api/v3"

    @property
    def auth_header_name(self) -> str:
        return "x-cg-pro-api-key" if self.mode == "pro" else "x-cg-demo-api-key"


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    return normalized in {"1", "true", "yes", "on"}


def load_api_config() -> ApiConfig:
    _load_local_env_file()
    mode = os.getenv("CG_API_MODE", "demo").strip().lower()
    if mode not in {"demo", "pro"}:
        raise ValueError("CG_API_MODE must be 'demo' or 'pro'.")

    api_key = os.getenv("COINGECKO_PRO_API_KEY") if mode == "pro" else os.getenv("COINGECKO_DEMO_API_KEY")

    return ApiConfig(
        mode=mode,
        api_key=api_key,
        timeout_seconds=int(os.getenv("CG_TIMEOUT_SECONDS", "20")),
        retry_max=int(os.getenv("CG_RETRY_MAX", "3")),
        backoff_seconds=float(os.getenv("CG_BACKOFF_SECONDS", "1.2")),
        debug=_parse_bool(os.getenv("CG_DEBUG"), True),
        save_raw=_parse_bool(os.getenv("CG_SAVE_RAW"), True),
    )
