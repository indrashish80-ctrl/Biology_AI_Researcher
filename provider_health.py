"""
provider_health.py
------------------
High-resilience health and cooldown tracker for multi-provider AI routing.

Cooldown policy:
    - RATE LIMIT (429 / TPM / RPM): Short breather (3-5 seconds). Rate limits
      are transient traffic spikes, NOT dead API keys.
    - HARD ERROR (401 / 403 / billing / invalid key): Long cooldown (5+ minutes).
      Retrying immediately is futile.
    - SOFT ERROR (500 / 502 / 503 / 504 / timeout): Escalates to cooldown only
      after consecutive threshold failures (default: 3).
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

DEFAULT_SOFT_FAILURE_THRESHOLD = 3
DEFAULT_BASE_COOLDOWN_SECONDS = 20
DEFAULT_RATE_LIMIT_COOLDOWN_SECONDS = 3.5
DEFAULT_MAX_COOLDOWN_SECONDS = 5 * 60

# Unrecoverable account/credential errors -> immediate full cooldown
HARD_ERROR_PATTERNS = [
    r"\b401\b", r"\b403\b", r"unauthorized", r"invalid api key",
    r"insufficient_quota", r"billing", r"account.*(suspended|disabled)",
]

# Transient capacity / rate spikes -> short breather (3.5s)
RATE_LIMIT_PATTERNS = [
    r"\b429\b", r"rate limit", r"rate_limit", r"tpm", r"rpm", r"too many requests",
    r"tokens per minute", r"requests per minute",
]

# Server-side hiccups -> retryable or soft threshold
SOFT_ERROR_PATTERNS = [
    r"\b500\b", r"\b502\b", r"\b503\b", r"\b504\b",
    r"timeout", r"timed out", r"connection", r"unavailable", r"reset by peer",
    r"overloaded", r"service temporarily overloaded",
]


def classify_error(error_text: str) -> str:
    text = (error_text or "").lower()
    for pattern in HARD_ERROR_PATTERNS:
        if re.search(pattern, text):
            return "hard"
    for pattern in RATE_LIMIT_PATTERNS:
        if re.search(pattern, text):
            return "rate_limit"
    for pattern in SOFT_ERROR_PATTERNS:
        if re.search(pattern, text):
            return "soft"
    return "unknown"


@dataclass
class ProviderStats:
    provider: str
    consecutive_failures: int = 0
    total_calls: int = 0
    total_failures: int = 0
    latencies_ms: List[float] = field(default_factory=list)
    last_error: Optional[str] = None
    last_error_class: Optional[str] = None
    cooldown_until: float = 0.0
    cooldown_strikes: int = 0
    status_override: Optional[str] = None

    def avg_latency_ms(self) -> Optional[float]:
        if not self.latencies_ms:
            return None
        recent = self.latencies_ms[-20:]
        return sum(recent) / len(recent)

    def status(self) -> str:
        if self.status_override:
            return self.status_override
        if time.time() < self.cooldown_until:
            return "COOLDOWN"
        if 1 <= self.consecutive_failures < DEFAULT_SOFT_FAILURE_THRESHOLD:
            return "DEGRADED"
        return "HEALTHY"

    def to_dict(self) -> Dict[str, Any]:
        remaining = max(0.0, self.cooldown_until - time.time())
        return {
            "provider": self.provider,
            "status": self.status(),
            "consecutive_failures": self.consecutive_failures,
            "total_calls": self.total_calls,
            "total_failures": self.total_failures,
            "avg_latency_ms": round(self.avg_latency_ms(), 1) if self.avg_latency_ms() else None,
            "last_error": self.last_error,
            "last_error_class": self.last_error_class,
            "cooldown_seconds_remaining": round(remaining, 1),
            "cooldown_strikes": self.cooldown_strikes,
        }


class ProviderHealthTracker:
    """
    In-process provider health and cooldown manager.
    Coordinates failover routing and prevents thundering-herd retry storms.
    """

    def __init__(
        self,
        db: Optional[Any] = None,
        soft_failure_threshold: int = DEFAULT_SOFT_FAILURE_THRESHOLD,
        base_cooldown_seconds: int = DEFAULT_BASE_COOLDOWN_SECONDS,
        rate_limit_cooldown_seconds: float = DEFAULT_RATE_LIMIT_COOLDOWN_SECONDS,
        max_cooldown_seconds: int = DEFAULT_MAX_COOLDOWN_SECONDS,
    ):
        self.db = db
        self.soft_failure_threshold = soft_failure_threshold
        self.base_cooldown_seconds = base_cooldown_seconds
        self.rate_limit_cooldown_seconds = rate_limit_cooldown_seconds
        self.max_cooldown_seconds = max_cooldown_seconds
        self._stats: Dict[str, ProviderStats] = {}

    def _get(self, provider: str) -> ProviderStats:
        if provider not in self._stats:
            self._stats[provider] = ProviderStats(provider=provider)
        return self._stats[provider]

    # -------------------------------------------------------------------------
    # Availability Queries
    # -------------------------------------------------------------------------

    def is_available(self, provider: str) -> bool:
        stats = self._get(provider)
        return stats.status() != "COOLDOWN"

    def status(self, provider: str) -> str:
        return self._get(provider).status()

    def all_status(self) -> Dict[str, Dict[str, Any]]:
        return {name: stats.to_dict() for name, stats in self._stats.items()}

    def rank_providers(self, providers: List[str]) -> List[str]:
        tier_rank = {"HEALTHY": 0, "DEGRADED": 1, "COOLDOWN": 2}

        def key(name: str):
            stats = self._get(name)
            latency = stats.avg_latency_ms()
            return (
                tier_rank.get(stats.status(), 3),
                latency if latency is not None else float("inf"),
            )

        return sorted(providers, key=key)

    def disable(self, provider: str) -> None:
        self._get(provider).status_override = "COOLDOWN"

    def enable(self, provider: str) -> None:
        stats = self._get(provider)
        stats.status_override = None
        stats.cooldown_until = 0.0
        stats.consecutive_failures = 0

    # -------------------------------------------------------------------------
    # Recording Outcomes
    # -------------------------------------------------------------------------

    def record_success(self, provider: str, latency_ms: float) -> None:
        stats = self._get(provider)
        stats.total_calls += 1
        stats.consecutive_failures = 0
        stats.latencies_ms.append(latency_ms)
        was_cooldown = stats.cooldown_until > time.time()
        stats.cooldown_until = 0.0

        if self.db is not None and hasattr(self.db, "log_provider_event"):
            try:
                self.db.log_provider_event(provider, "success", latency_ms=latency_ms)
                if was_cooldown:
                    self.db.log_provider_event(provider, "cooldown_cleared")
            except Exception:
                pass

    def record_failure(self, provider: str, error_text: str, latency_ms: Optional[float] = None) -> str:
        stats = self._get(provider)
        stats.total_calls += 1
        stats.total_failures += 1
        stats.consecutive_failures += 1
        stats.last_error = error_text
        error_class = classify_error(error_text)
        stats.last_error_class = error_class
        if latency_ms is not None:
            stats.latencies_ms.append(latency_ms)

        # 1. Rate limits (429 / TPM) -> short 3.5s pause
        if error_class == "rate_limit":
            stats.cooldown_until = time.time() + self.rate_limit_cooldown_seconds
            if self.db is not None and hasattr(self.db, "log_provider_event"):
                try:
                    self.db.log_provider_event(provider, "rate_limited", latency_ms=latency_ms, error_text=error_text)
                except Exception:
                    pass
            return "COOLDOWN"

        # 2. Hard errors (invalid key, billing dead) -> long cooldown
        if error_class == "hard":
            stats.cooldown_strikes += 1
            stats.cooldown_until = time.time() + self.max_cooldown_seconds
            if self.db is not None and hasattr(self.db, "log_provider_event"):
                try:
                    self.db.log_provider_event(provider, "hard_error", latency_ms=latency_ms, error_text=error_text)
                except Exception:
                    pass
            return "COOLDOWN"

        # 3. Soft errors (500s, 503s, timeouts) -> threshold escalation
        if stats.consecutive_failures >= self.soft_failure_threshold:
            stats.cooldown_strikes += 1
            duration = min(
                self.base_cooldown_seconds * (2 ** (stats.cooldown_strikes - 1)),
                self.max_cooldown_seconds,
            )
            stats.cooldown_until = time.time() + duration
            if self.db is not None and hasattr(self.db, "log_provider_event"):
                try:
                    self.db.log_provider_event(provider, "cooldown_entered", latency_ms=latency_ms, error_text=error_text)
                except Exception:
                    pass
            return "COOLDOWN"

        if self.db is not None and hasattr(self.db, "log_provider_event"):
            try:
                self.db.log_provider_event(provider, "error", latency_ms=latency_ms, error_text=error_text)
            except Exception:
                pass

        return "DEGRADED"