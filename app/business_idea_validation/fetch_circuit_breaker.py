"""Per-provider circuit breaker for fetch resilience."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum

from app.db.base import utc_now


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class ProviderCircuit:
    failure_threshold: int = 5
    open_seconds: float = 60.0
    state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    opened_at: datetime | None = None

    def allow_request(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN and self.opened_at is not None:
            if utc_now() >= self.opened_at + timedelta(seconds=self.open_seconds):
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        return self.state == CircuitState.HALF_OPEN

    def record_success(self) -> None:
        self.consecutive_failures = 0
        self.state = CircuitState.CLOSED
        self.opened_at = None

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.opened_at = utc_now()


@dataclass
class FetchCircuitRegistry:
    _circuits: dict[str, ProviderCircuit] = field(default_factory=dict)

    def get(self, provider: str) -> ProviderCircuit:
        if provider not in self._circuits:
            self._circuits[provider] = ProviderCircuit()
        return self._circuits[provider]

    def snapshot(self) -> dict[str, str]:
        return {name: circuit.state.value for name, circuit in self._circuits.items()}


_GLOBAL_REGISTRY = FetchCircuitRegistry()


def get_fetch_circuit_registry() -> FetchCircuitRegistry:
    return _GLOBAL_REGISTRY
