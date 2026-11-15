"""Rate limits kept in memory: at most N attempts per time window per key.

In memory is enough because the API runs as one process with one worker on one
server; a restart resets the counters. With more workers or servers this would have
to move to a shared store.

`acquire()` checks and counts in one step, with no `await` in between, so parallel
requests cannot all slip past the check.
"""

import math
import time
from collections import deque
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import timedelta

from app.core.errors import TooManyRequestsError

_all_limiters: list[RateLimiter] = []


class RateLimiter:
    def __init__(
        self,
        *,
        limit: int,
        window: timedelta,
        clock: Callable[[], float] = time.monotonic,
        sweep_above_keys: int = 10_000,
    ) -> None:
        self._limit = limit
        self._window = window.total_seconds()
        self._clock = clock
        self._sweep_above_keys = sweep_above_keys
        """Forget keys with no recent attempt once this many are tracked, at most once
        per window, so memory stays bounded without scanning on every request."""
        self._last_sweep = clock()
        self._attempts: dict[str, deque[float]] = {}
        _all_limiters.append(self)

    def acquire(self, key: str) -> float:
        """Count one attempt for `key` and return it, or raise `TooManyRequestsError`."""
        now = self._clock()
        attempts = self._recent_attempts(key, now)
        if len(attempts) >= self._limit:
            raise TooManyRequestsError(math.ceil(attempts[0] + self._window - now))
        attempts.append(now)
        self._sweep_if_due(now)
        return now

    def release(self, key: str, attempt: float) -> None:
        """Take back one attempt returned by `acquire()`, e.g. a login that succeeded."""
        attempts = self._attempts.get(key)
        if attempts and attempt in attempts:
            attempts.remove(attempt)

    @contextmanager
    def counting_only(self, key: str, failure: type[Exception]) -> Iterator[None]:
        """Count the attempt only if the block raises `failure`.

        Used for wrong passwords: a correct one, or any other error, is taken back.
        """
        attempt = self.acquire(key)
        try:
            yield
        except failure:
            raise
        except BaseException:
            self.release(key, attempt)
            raise
        self.release(key, attempt)

    def tracked_keys(self) -> int:
        return len(self._attempts)

    def reset(self) -> None:
        self._attempts.clear()

    def _recent_attempts(self, key: str, now: float) -> deque[float]:
        attempts = self._attempts.setdefault(key, deque())
        while attempts and attempts[0] <= now - self._window:
            attempts.popleft()
        return attempts

    def _sweep_if_due(self, now: float) -> None:
        if len(self._attempts) <= self._sweep_above_keys:
            return
        if now - self._last_sweep < self._window:
            return
        self._last_sweep = now
        for key in list(self._attempts):
            if not self._recent_attempts(key, now):
                del self._attempts[key]


def reset_all_limiters() -> None:
    """For tests: every test starts with fresh counters."""
    for limiter in _all_limiters:
        limiter.reset()
