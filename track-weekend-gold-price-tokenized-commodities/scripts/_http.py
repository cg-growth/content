from pathlib import Path
import time
from typing import Optional

import requests

from config import BASE_URL, MAX_RETRIES, REQUEST_TIMEOUT, get_headers


class CoinGeckoClient:
    def __init__(self, timeout: Optional[float] = None, retries: Optional[int] = None) -> None:
        self.base_url = BASE_URL.rstrip("/")
        self.timeout = REQUEST_TIMEOUT if timeout is None else timeout
        self.retries = MAX_RETRIES if retries is None else retries
        self.session = requests.Session()
        self.headers = get_headers()

    def get_json(self, path: str, params: Optional[dict] = None):
        endpoint = f"{self.base_url}/{path.lstrip('/')}"
        last_error = None

        for attempt in range(self.retries + 1):
            try:
                response = self.session.get(endpoint, headers=self.headers, params=params, timeout=self.timeout)
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as exc:
                last_error = exc
                status = exc.response.status_code if exc.response is not None else None
                if status in {429, 500, 502, 503, 504} and attempt < self.retries:
                    time.sleep(2 ** attempt)
                    continue
                body_preview = ""
                if exc.response is not None:
                    body_preview = exc.response.text[:300]
                raise RuntimeError(f"HTTP error on {path}: status={status}, response={body_preview}") from exc
            except requests.RequestException as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(2 ** attempt)
                    continue

        raise RuntimeError(f"Request failed for {path}: {last_error}")


def prepare_output_dirs(out_dir: str = "output"):
    root = Path(out_dir)
    paths = {
        "root": root,
        "json": root / "json",
        "csv": root / "csv",
        "charts": root / "charts",
    }
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)
    return paths
