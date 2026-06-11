"""Rate limiting por token bucket, em memoria, thread-safe.

Adequado ao deploy single-container deste projeto. Escopos com limites
distintos (login, registro, mutacoes, global), chaveados por IP.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

MAX_KEYS = 50_000  # protecao de memoria


@dataclass
class _Scope:
    capacity: float
    refill_per_second: float


class RateLimiter:
    def __init__(self) -> None:
        self._scopes: Dict[str, _Scope] = {}
        self._buckets: Dict[Tuple[str, str], Tuple[float, float]] = {}
        self._lock = threading.Lock()

    def configure(self, scope: str, capacity: int, per_seconds: float) -> None:
        if capacity <= 0 or per_seconds <= 0:
            raise ValueError("limites devem ser positivos")
        self._scopes[scope] = _Scope(
            capacity=float(capacity), refill_per_second=capacity / per_seconds
        )

    def allow(self, scope: str, key: str, now: Optional[float] = None) -> Tuple[bool, float]:
        """Retorna (permitido, retry_after_seconds)."""
        cfg = self._scopes[scope]  # escopo desconhecido = bug: deixa lancar
        ts = time.monotonic() if now is None else now
        bucket_key = (scope, key)
        with self._lock:
            tokens, last = self._buckets.get(bucket_key, (cfg.capacity, ts))
            tokens = min(cfg.capacity, tokens + (ts - last) * cfg.refill_per_second)
            if tokens >= 1.0:
                self._buckets[bucket_key] = (tokens - 1.0, ts)
                return True, 0.0
            self._buckets[bucket_key] = (tokens, ts)
            retry_after = (1.0 - tokens) / cfg.refill_per_second
            if len(self._buckets) > MAX_KEYS:
                self._prune(ts)
            return False, retry_after

    def reset(self, scope: str) -> None:
        """Limpa os buckets de um escopo (uso em testes/admin)."""
        with self._lock:
            for key in [k for k in self._buckets if k[0] == scope]:
                del self._buckets[key]

    def _prune(self, now: float) -> None:
        stale = [k for k, (_, last) in self._buckets.items() if now - last > 3600]
        for k in stale:
            del self._buckets[k]


def default_limiter() -> RateLimiter:
    rl = RateLimiter()
    rl.configure("login", 5, 60)
    rl.configure("register", 3, 3600)
    rl.configure("refresh", 30, 60)
    rl.configure("mutate", 120, 60)  # 72 apostas de grupos numa sentada cabem (R2-F3)
    rl.configure("global", 240, 60)
    rl.configure("oauth", 10, 60)
    return rl
