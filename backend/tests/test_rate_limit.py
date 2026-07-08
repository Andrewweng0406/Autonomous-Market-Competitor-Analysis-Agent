from app.core.rate_limit import RateLimiter


def test_allows_up_to_the_limit_then_blocks():
    limiter = RateLimiter(max_requests=2, window_seconds=60)
    assert limiter.allow("client-a") is True
    assert limiter.allow("client-a") is True
    assert limiter.allow("client-a") is False


def test_limits_are_tracked_independently_per_key():
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    assert limiter.allow("client-a") is True
    assert limiter.allow("client-b") is True  # separate bucket, unaffected
    assert limiter.allow("client-a") is False


def test_window_resets_after_it_elapses(monkeypatch):
    limiter = RateLimiter(max_requests=1, window_seconds=10)
    fake_now = [1_000.0]
    monkeypatch.setattr("app.core.rate_limit.time.monotonic", lambda: fake_now[0])

    assert limiter.allow("client-a") is True
    assert limiter.allow("client-a") is False

    fake_now[0] += 11  # advance past the 10s window
    assert limiter.allow("client-a") is True


def test_retry_after_seconds_is_positive_once_limited():
    limiter = RateLimiter(max_requests=1, window_seconds=30)
    limiter.allow("client-a")
    assert limiter.retry_after_seconds("client-a") > 0


def test_retry_after_seconds_defaults_to_full_window_for_unseen_key():
    limiter = RateLimiter(max_requests=1, window_seconds=15)
    assert limiter.retry_after_seconds("never-seen") == 15
