"""
Rta Governor – Enforces Ṛta‑Bounds for the NALA Transcendent Dual‑Mode System.

Subscribes to the Ṛta‑Score published by `rta_feedback_loop.py` and:
    • When Ṛta < low_bound (default 0.4): requests a gentle shift toward
      PRATYAKSHA (more interactive/human‑in‑the‑loop) to recover coherence.
    • When Ṛta > high_bound (default 0.95): triggers a "sacred pause"
      forces the system into ATHAPRAPTI (meditative, zero‑I/O) for a fixed
      duration (default 60 seconds) to prevent overconfident runaway behavior.
    • Logs all bound violations and actions to the feedback ledger (or a
      separate governor log) for long‑term audit.

The governor does NOT change modes directly; it emits ModeRequest objects
via a dispatcher callback that the fleet coordinator (or other mode‑handling
subsystem) should consume and act upon.

Design highlights:
    • Thread‑safe – safe to use from the feedback loop’s daemon thread.
    • Configurable bounds, pause duration, and estimator injection.
    • Clear separation of concerns: score computation (feedback loop) vs.
      correction (governor).
    • Pluggable mode‑dispatcher – by default logs requests; inject a real
      dispatcher to talk to fleet.coordinator, model_router, etc.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

# Import the feedback loop to subscribe to its updates
from .rta_feedback_loop import RtaFeedbackLoop

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())  # Prevent "No handler found" warnings


# --------------------------------------------------------------------------- #
# Mode request definitions
# --------------------------------------------------------------------------- #
class ModeRequestType(enum.Enum):
    """Types of mode‑adjustment requests the governor can emit."""
    SHIFT_PRATYAKSHA = "shift_pratyaksha"  # Bias toward interactive/collaborative
    SACRED_PAUSE = "sacred_pause"          # Force ATHAPRAPTI cooldown


@dataclass(frozen=True)
class ModeRequest:
    """
    Immutable request sent to the mode‑handling subsystem (e.g., fleet coordinator).

    Attributes:
        request_type: The kind of request (shift or pause).
        intensity: For SHIFT_PRATYAKSHA, a value in [0,1] indicating how strongly
                   to bias toward PRATYAKSHA (0 = no bias, 1 = maximum bias).
                   Ignored for SACRED_PAUSE.
        duration_s: For SACRED_PAUSE, the pause length in seconds.
                    Ignored for SHIFT_PRATYAKSHA.
        timestamp: When the request was generated.
    """
    request_type: ModeRequestType
    intensity: float = 0.0
    duration_s: float = 0.0
    timestamp: float = 0.0


# --------------------------------------------------------------------------- #
# Governor implementation
# --------------------------------------------------------------------------- #
class RtaGovernor:
    """
    Watches the Ṛta‑Score and enforces the Ṛta‑Bounds.

    Example usage:
        loop = RtaFeedbackLoop()
        def handle_request(req: ModeRequest) -> None:
            # TODO: integrate with fleet.coordinator or model_router
            print(f"Governor request: {req}")

        gov = RtaGovernor(
            rta_feedback_loop=loop,
            low_bound=0.4,
            high_bound=0.95,
            sacred_pause_duration=60.0,
            mode_dispatcher=handle_request,
        )
        loop.start()
        # ... later ...
        loop.stop()
    """

    def __init__(
        self,
        *,
        rta_feedback_loop: RtaFeedbackLoop,
        low_bound: float = 0.4,
        high_bound: float = 0.95,
        sacred_pause_duration: float = 60.0,
        mode_dispatcher: Optional[Callable[[ModeRequest], None]] = None,
    ) -> None:
        if not (0.0 <= low_bound < high_bound):
            raise ValueError("Require 0.0 <= low_bound < high_bound")
        if sacred_pause_duration <= 0:
            raise ValueError("sacred_pause_duration must be positive")

        self._loop = rta_feedback_loop
        self._low_bound = float(low_bound)
        self._high_bound = float(high_bound)
        self._sacred_pause_duration = float(sacred_pause_duration)
        self._mode_dispatcher = mode_dispatcher or self._default_dispatcher

        # Thread‑safe state
        self._lock = threading.RLock()
        self._unsubscribable: Optional[Callable[[], None]] = None
        self._in_sacred_pause: bool = False
        self._pause_end_time: float = 0.0

        # Subscribe to the feedback loop
        self._unsubscribable = self._loop.subscribe(self._on_rta_update)

        logger.info(
            "RtaGovernor initialized (low=%.2f, high=%.2f, pause=%.0fs)",
            self._low_bound,
            self._high_bound,
            self._sacred_pause_duration,
        )

    # --------------------------- Public API ------------------------------- #
    def stop(self) -> None:
        """Stop listening to the feedback loop and clean up."""
        with self._lock:
            if self._unsubscribable is not None:
                try:
                    self._unsubscribable()
                except Exception:  # pragma: no cover – defensive
                    logger.exception("Error while unsubscribing from RtaFeedbackLoop")
                self._unsubscribable = None
            # Reset pause state (not strictly required but tidy)
            self._in_sacred_pause = False
            self._pause_end_time = 0.0
        logger.info("RtaGovernor stopped")

    # -------------------------- Internal callbacks ------------------------ #
    def _on_rta_update(self, score: float, components: dict) -> None:
        """
        Called by RtaFeedbackLoop on each new Ṛta‑Score.
        Evaluates bounds and emits mode requests as needed.
        """
        now = time.time()
        with self._lock:
            # If we are currently in a sacred pause, ignore further updates
            # until the pause elapses.
            if self._in_sacred_pause:
                if now < self._pause_end_time:
                    # Still in pause – do nothing (could log debug)
                    return
                # Pause has ended
                self._in_sacred_pause = False
                self._pause_end_time = 0.0

            # Now we are not in a pause – check bounds
            if score < self._low_bound:
                # Request gentle shift toward PRATYAKSHA
                intensity = (self._low_bound - score) / self._low_bound
                # Clamp to [0,1] for safety (should already be in range)
                if intensity < 0.0:
                    intensity = 0.0
                elif intensity > 1.0:
                    intensity = 1.0
                self._dispatch_mode_request(
                    ModeRequestType.SHIFT_PRATYAKSHA,
                    intensity=intensity,
                )
                logger.info(
                    "Ṛta=%.3f < low_bound=%.2f → SHIFT_PRATYAKSHA (intensity=%.2f)",
                    score,
                    self._low_bound,
                    intensity,
                )
            elif score > self._high_bound:
                # Trigger sacred pause
                self._in_sacred_pause = True
                self._pause_end_time = now + self._sacred_pause_duration
                self._dispatch_mode_request(
                    ModeRequestType.SACRED_PAUSE,
                    duration_s=self._sacred_pause_duration,
                )
                logger.info(
                    "Ṛta=%.3f > high_bound=%.2f → SACRED_PAUSE (duration=%.0fs)",
                    score,
                    self._high_bound,
                    self._sacred_pause_duration,
                )
            else:
                # Score within bounds – normal operation, log at debug
                logger.debug(
                    "Ṛta=%.3f within bounds [%.2f, %.2f] – no action",
                    score,
                    self._low_bound,
                    self._high_bound,
                )

    def _dispatch_mode_request(
        self,
        request_type: ModeRequestType,
        *,
        intensity: float = 0.0,
        duration_s: float = 0.0,
    ) -> None:
        """Build a ModeRequest and send it via the configured dispatcher."""
        req = ModeRequest(
            request_type=request_type,
            intensity=intensity,
            duration_s=duration_s,
            timestamp=time.time(),
        )
        try:
            self._mode_dispatcher(req)
        except Exception as exc:  # pragma: no cover – safety net
            logger.error("Mode dispatcher raised: %s", exc)

    @staticmethod
    def _default_dispatcher(req: ModeRequest) -> None:
        """Fallback dispatcher: logs the request (useful for testing/demos)."""
        if req.request_type == ModeRequestType.SHIFT_PRATYAKSHA:
            logger.info(
                "Governor request: SHIFT_PRATYAKSHA (intensity=%.2f)",
                req.intensity,
            )
        elif req.request_type == ModeRequestType.SACRED_PAUSE:
            logger.info(
                "Governor request: SACRED_PAUSE (duration=%.0fs)",
                req.duration_s,
            )

    # --------------------------------------------------------------------------- #
    # Optional introspection / debugging
    # --------------------------------------------------------------------------- #
    def get_state(self) -> dict:
        """Return a snapshot of the governor’s internal state (thread‑safe)."""
        with self._lock:
            return {
                "low_bound": self._low_bound,
                "high_bound": self._high_bound,
                "sacred_pause_duration": self._sacred_pause_duration,
                "in_sacred_pause": self._in_sacred_pause,
                "pause_end_time": self._pause_end_time,
                "time_remaining": (
                    max(0.0, self._pause_end_time - time.time())
                    if self._in_sacred_pause
                    else 0.0
                ),
            }

    def __repr__(self) -> str:  # pragma: no cover
        with self._lock:
            state = self.get_state()
            return (
                f"<RtaGovernor low={state['low_bound']:.2f} "
                f"high={state['high_bound']:.2f} "
                f"in_pause={state['in_sacred_pause']} "
                f"remaining={state['time_remaining']:.1f}s>"
            )


# --------------------------------------------------------------------------- #
# Convenience: a module‑level default governor (optional for quick import)
# --------------------------------------------------------------------------- #
_default_governor: Optional[RtaGovernor] = None
_default_governor_lock = threading.Lock()


def get_default_rta_governor() -> RtaGovernor:
    """
    Return a process‑wide default RtaGovernor instance (uses the default
    RtaFeedbackLoop). Callers can then ``start()`` the loop and the governor
    will automatically begin listening.
    """
    global _default_governor
    with _default_governor_lock:
        if _default_governor is None:
            _default_governor = RtaGovernor(
                rta_feedback_loop=RtaFeedbackLoop()
            )
        return _default_governor


# --------------------------------------------------------------------------- #
# If this file is executed directly, run a quick sanity‑check demo.
# --------------------------------------------------------------------------- #
if __name__ == "__main__":  # pragma: no cover
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    loop = RtaFeedbackLoop()

    def handle_request(req: ModeRequest) -> None:
        if req.request_type == ModeRequestType.SHIFT_PRATYAKSHA:
            print(
                f"[{time.strftime('%H:%M:%S')}] Governor → SHIFT_PRATYAKSHA "
                f"(intensity={req.intensity:.2f})"
            )
        elif req.request_type == ModeRequestType.SACRED_PAUSE:
            print(
                f"[{time.strftime('%H:%M:%S')}] Governor → SACRED_PAUSE "
                f"(duration={req.duration_s:.0f}s)"
            )

    gov = RtaGovernor(
        rta_feedback_loop=loop,
        low_bound=0.4,
        high_bound=0.95,
        sacred_pause_duration=10.0,  # shorter for demo
        mode_dispatcher=handle_request,
    )
    loop.start()
    try:
        # Run for 30 seconds then stop
        time.sleep(30)
    finally:
        loop.stop()
        gov.stop()