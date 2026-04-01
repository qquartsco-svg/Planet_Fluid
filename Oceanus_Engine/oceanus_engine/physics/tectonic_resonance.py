"""L4.5 — Tectonic Resonance Scan (FrequencyCore bridge + plate event emit)."""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

from oceanus_engine.physics.plate_hooks import PlateEvent, PlateHookRegistry


def _dominant_freq_fallback(signal: Iterable[float], sample_rate_hz: float) -> float:
    values = list(float(x) for x in signal)
    n = len(values)
    if n < 3 or sample_rate_hz <= 0.0:
        return 0.0
    best_k = 1
    best_amp = 0.0
    for k in range(1, n // 2):
        re = 0.0
        im = 0.0
        for t, x in enumerate(values):
            ang = 2.0 * math.pi * k * t / n
            re += x * math.cos(ang)
            im -= x * math.sin(ang)
        amp = (re * re + im * im) ** 0.5
        if amp > best_amp:
            best_amp = amp
            best_k = k
    return best_k * sample_rate_hz / n


def _ensure_frequency_core_on_path() -> None:
    here = Path(__file__).resolve()
    # .../_staging/Oceanus_Engine/oceanus_engine/physics/tectonic_resonance.py
    staging_root = here.parents[3]
    candidate = staging_root / "FrequencyCore_Engine"
    if candidate.exists():
        p = str(candidate)
        if p not in sys.path:
            sys.path.insert(0, p)


def _scan_with_frequency_core(
    signal: Iterable[float],
    sample_rate_hz: float,
    natural_freq_hz: float,
) -> Tuple[float, str, float, float]:
    _ensure_frequency_core_on_path()
    from frequency_core import observe_frequency, analyze_resonance  # type: ignore

    values = [float(x) for x in signal]
    obs = observe_frequency(values, sample_rate_hz=sample_rate_hz)
    ex = float(getattr(obs, "dominant_freq_hz", 0.0))
    rep = analyze_resonance(values, natural_freq_hz=natural_freq_hz, excitation_freq_hz=ex)
    raw_state = getattr(rep, "resonance_state", "UNKNOWN")
    state = str(getattr(raw_state, "value", raw_state)).upper()
    if state == "NEAR":
        state = "NEAR_RESONANCE"
    eff = float(getattr(rep, "coupling_efficiency", 0.0))
    omega = float(getattr(rep, "omega_freq", 0.0))
    return ex, state, eff, omega


def _scan_fallback(
    signal: Iterable[float],
    sample_rate_hz: float,
    natural_freq_hz: float,
) -> Tuple[float, str, float, float]:
    ex = _dominant_freq_fallback(signal, sample_rate_hz)
    if natural_freq_hz <= 1e-9:
        return ex, "UNKNOWN", 0.0, 0.0
    r = ex / natural_freq_hz
    d = abs(r - 1.0)
    if d < 0.05:
        state = "TUNED"
    elif d < 0.15:
        state = "NEAR_RESONANCE"
    else:
        state = "DETUNED"
    eff = max(0.0, min(1.0, 1.0 - min(1.0, d)))
    omega = eff
    return ex, state, eff, omega


def scan_tectonic_resonance_and_emit(
    signal: Iterable[float],
    *,
    sample_rate_hz: float,
    natural_freq_hz: float,
    boundary_id: str,
    t_s: float,
    registry: PlateHookRegistry | None = None,
    magnitude_scale: float = 7.0,
    emit_threshold_state: Tuple[str, ...] = ("TUNED", "NEAR_RESONANCE"),
) -> Dict[str, Any]:
    """
    FrequencyCore 기반(가능 시) 지각 공명 스캔 후, 임계 도달 시 PlateEvent emit.
    """
    try:
        ex, state, eff, omega = _scan_with_frequency_core(
            signal, sample_rate_hz, natural_freq_hz
        )
        source = "frequency_core"
    except Exception:
        ex, state, eff, omega = _scan_fallback(
            signal, sample_rate_hz, natural_freq_hz
        )
        source = "fallback_dft"

    emitted = False
    magnitude = max(0.0, min(10.0, eff * magnitude_scale))
    emit_states = tuple(str(s).upper() for s in emit_threshold_state)
    if registry is not None and state in emit_states:
        event = PlateEvent(
            kind="earthquake",
            t_s=float(t_s),
            magnitude=float(magnitude),
            d_eta_m=float(0.05 * eff),
            heat_flux_wm2=float(10.0 * eff),
            meta=(
                ("boundary_id", boundary_id),
                ("resonance_state", state),
                ("excitation_freq_hz", float(ex)),
                ("natural_freq_hz", float(natural_freq_hz)),
                ("omega_freq", float(omega)),
                ("source", source),
            ),
        )
        registry.emit(event)
        emitted = True

    return {
        "boundary_id": boundary_id,
        "source": source,
        "excitation_freq_hz": float(ex),
        "natural_freq_hz": float(natural_freq_hz),
        "resonance_state": state,
        "coupling_efficiency": float(eff),
        "omega_freq": float(omega),
        "event_emitted": emitted,
        "event_kind": "earthquake" if emitted else None,
        "event_magnitude": float(magnitude) if emitted else 0.0,
    }

