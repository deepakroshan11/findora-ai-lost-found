from chat_agent.ratelimit import SlidingWindowLimiter


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_allows_up_to_the_limit_then_blocks():
    limiter = SlidingWindowLimiter(max_calls=3, window_seconds=60, clock=Clock())
    assert [limiter.allow("ip") for _ in range(4)] == [True, True, True, False]


def test_window_slides_so_old_calls_expire():
    clock = Clock()
    limiter = SlidingWindowLimiter(max_calls=2, window_seconds=60, clock=clock)
    assert limiter.allow("ip") and limiter.allow("ip")
    assert not limiter.allow("ip")
    clock.now += 61
    assert limiter.allow("ip")


def test_keys_are_independent():
    limiter = SlidingWindowLimiter(max_calls=1, window_seconds=60, clock=Clock())
    assert limiter.allow("a")
    assert limiter.allow("b")
    assert not limiter.allow("a")


def test_blocked_calls_do_not_extend_the_window():
    clock = Clock()
    limiter = SlidingWindowLimiter(max_calls=1, window_seconds=60, clock=clock)
    assert limiter.allow("ip")
    clock.now += 30
    assert not limiter.allow("ip")      # blocked, must not be recorded
    clock.now += 31                     # 61s after the one allowed call
    assert limiter.allow("ip")


def test_idle_keys_are_pruned_to_bound_memory():
    clock = Clock()
    limiter = SlidingWindowLimiter(max_calls=1, window_seconds=10, clock=clock)
    for n in range(5000):
        limiter.allow(f"ip-{n}")
    clock.now += 11
    limiter.allow("fresh")
    assert len(limiter._hits) < 5000
