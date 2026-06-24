from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import requests

from src.config import ApiConfig
from src.io_utils import ensure_dir, write_json


class NonRetryableRequestError(RuntimeError):
    pass


class CoinGeckoClient:
    def __init__(self, config: ApiConfig, raw_output_dir: Path | None = None) -> None:
        self.config = config
        self.raw_output_dir = raw_output_dir

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"accept": "application/json"}
        if self.config.api_key:
            headers[self.config.auth_header_name] = self.config.api_key
        return headers

    def _save_raw_snapshot(self, name: str, payload: Any) -> None:
        if not self.config.save_raw or self.raw_output_dir is None:
            return
        ensure_dir(self.raw_output_dir)
        path = self.raw_output_dir / f"{name}.json"
        write_json(path, payload)

    def request(self, endpoint: str, params: dict[str, Any] | None = None, snapshot_name: str | None = None) -> Any:
        url = f"{self.config.base_url}{endpoint}"
        params = params or {}
        last_error: Exception | None = None

        for attempt in range(1, self.config.retry_max + 1):
            try:
                response = requests.get(
                    url,
                    headers=self._headers(),
                    params=params,
                    timeout=self.config.timeout_seconds,
                )
                if self.config.debug:
                    print(f"[debug] GET {response.url} -> {response.status_code}")

                if response.status_code == 429:
                    retry_after_header = response.headers.get("Retry-After")
                    if retry_after_header and retry_after_header.strip().isdigit():
                        sleep_for = float(retry_after_header.strip())
                        if sleep_for <= 0:
                            sleep_for = max(10.0, self.config.backoff_seconds * attempt * 4)
                    else:
                        sleep_for = max(10.0, self.config.backoff_seconds * attempt * 4)
                    if self.config.debug:
                        print(
                            f"[debug] 429 rate limit for {endpoint}. Waiting {sleep_for:.1f}s before retry "
                            f"(attempt {attempt}/{self.config.retry_max})"
                        )
                    if attempt == self.config.retry_max:
                        response.raise_for_status()
                    time.sleep(sleep_for)
                    continue

                if response.status_code >= 500:
                    response.raise_for_status()

                if response.status_code >= 400:
                    preview = response.text[:300]
                    raise NonRetryableRequestError(
                        f"HTTP {response.status_code} for {endpoint}. Preview: {preview}"
                    )

                payload = response.json()
                if snapshot_name:
                    self._save_raw_snapshot(snapshot_name, payload)
                return payload
            except NonRetryableRequestError:
                raise
            except Exception as exc:
                last_error = exc
                if attempt == self.config.retry_max:
                    break
                sleep_for = self.config.backoff_seconds * attempt
                if self.config.debug:
                    print(f"[debug] attempt {attempt} failed: {exc}. Retrying in {sleep_for:.1f}s")
                time.sleep(sleep_for)

        raise RuntimeError(f"Request failed after {self.config.retry_max} attempts for endpoint={endpoint}") from last_error
