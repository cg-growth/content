from __future__ import annotations

import time


class SimpleRateLimiter:
    def __init__(self, seconds_between_calls: float) -> None:
        self.seconds_between_calls = max(0.0, seconds_between_calls)
        self._last_call = 0.0

    def wait(self) -> None:
        elapsed = time.time() - self._last_call
        delay = self.seconds_between_calls - elapsed
        if delay > 0:
            time.sleep(delay)
        self._last_call = time.time()
