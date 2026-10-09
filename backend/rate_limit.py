from collections import defaultdict, deque

import threading
import time


class RateLimiter:
    """Sliding-window limit of requests per key (user ID).
    Kept in memory, so the limit applies per backend process.
    """
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            requests = self._requests[key]
            while requests and now - requests[0] > self.window_seconds:
                requests.popleft()
            if len(requests) >= self.max_requests:
                return False
            requests.append(now)
            return True

    def retry_after(self, key: str) -> int:
        """Seconds until the oldest request in the window expires."""
        with self._lock:
            requests = self._requests.get(key)
            if not requests:
                return 0
            return max(1, int(self.window_seconds - (time.monotonic() - requests[0])) + 1)
