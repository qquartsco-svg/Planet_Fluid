"""L4 — 판 경계 이벤트 훅 (지진·열수·융기 등 연속 PDE 대신 이산 레이어)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Tuple, Any


@dataclass
class PlateEvent:
    kind: str  # "earthquake" | "uplift" | "volcanic_flux" | ...
    t_s: float
    magnitude: float = 0.0
    d_eta_m: float = 0.0
    heat_flux_wm2: float = 0.0
    meta: Tuple[Tuple[str, Any], ...] = ()


PlateHandler = Callable[[PlateEvent], None]


@dataclass
class PlateHookRegistry:
    handlers: List[PlateHandler] = field(default_factory=list)

    def register(self, fn: PlateHandler) -> None:
        self.handlers.append(fn)

    def emit(self, event: PlateEvent) -> None:
        for h in self.handlers:
            h(event)
