from datetime import timedelta

import pytest

from app.core.errors import TooManyRequestsError
from app.core.rate_limit import RateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def _limiter(clock: FakeClock, limit: int = 3) -> RateLimiter:
    return RateLimiter(limit=limit, window=timedelta(minutes=10), clock=clock)


def test_attempts_beyond_the_limit_are_refused_with_the_wait_time() -> None:
    clock = FakeClock()
    limiter = _limiter(clock)
    for _ in range(3):
        limiter.acquire("1.2.3.4")
    clock.now += 60

    with pytest.raises(TooManyRequestsError) as refused:
        limiter.acquire("1.2.3.4")

    assert refused.value.headers["Retry-After"] == "540"


def test_attempts_leave_the_window_after_it_passes() -> None:
    clock = FakeClock()
    limiter = _limiter(clock)
    for _ in range(3):
        limiter.acquire("1.2.3.4")

    clock.now += 600
    limiter.acquire("1.2.3.4")


def test_keys_are_counted_separately() -> None:
    limiter = _limiter(FakeClock(), limit=1)
    limiter.acquire("1.2.3.4")

    limiter.acquire("5.6.7.8")


def test_released_attempt_does_not_count() -> None:
    limiter = _limiter(FakeClock(), limit=1)
    attempt = limiter.acquire("1.2.3.4")
    limiter.release("1.2.3.4", attempt)

    limiter.acquire("1.2.3.4")


def test_release_takes_back_its_own_attempt_not_the_newest() -> None:
    clock = FakeClock()
    limiter = _limiter(clock, limit=2)
    first = limiter.acquire("1.2.3.4")
    clock.now += 100
    limiter.acquire("1.2.3.4")
    limiter.release("1.2.3.4", first)
    limiter.acquire("1.2.3.4")

    with pytest.raises(TooManyRequestsError) as refused:
        limiter.acquire("1.2.3.4")

    # The oldest remaining attempt is the one at +100 s, not the released one.
    assert refused.value.headers["Retry-After"] == "600"


class WrongGuess(Exception):
    pass


def test_counting_only_keeps_failures_and_takes_back_everything_else() -> None:
    limiter = _limiter(FakeClock(), limit=1)
    with limiter.counting_only("a", failure=WrongGuess):
        pass
    with pytest.raises(ValueError), limiter.counting_only("a", failure=WrongGuess):
        raise ValueError
    with pytest.raises(WrongGuess), limiter.counting_only("a", failure=WrongGuess):
        raise WrongGuess

    with pytest.raises(TooManyRequestsError):
        limiter.acquire("a")


def test_idle_keys_are_forgotten_at_most_once_per_window() -> None:
    clock = FakeClock()
    limiter = RateLimiter(limit=5, window=timedelta(minutes=10), clock=clock, sweep_above_keys=2)
    for key in ("a", "b", "c"):
        limiter.acquire(key)
    assert limiter.tracked_keys() == 3

    clock.now += 600
    limiter.acquire("d")
    assert limiter.tracked_keys() == 1

    for key in ("e", "f", "g"):
        limiter.acquire(key)
    assert limiter.tracked_keys() == 4, "no second sweep inside the same window"
