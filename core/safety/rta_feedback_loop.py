"""
Rta Feedback Loop – Core component of the Ṛta‑Feedback Control Loop.

Continuously computes the Ṛta‑Score from:
    Viveka‑Clarity   (from AdaptiveVivekaGate)
    Satya‑Truthfulness (from ContextAwareSatyaLayer)
    Dustara‑Complexity (proxy: normalized reasoning‑step count)
    Ānanda‑Burden    (proxy: normalized inter‑request latency)

and publishes the score to any subscribers via a simple callback‑based
pub/sub mechanism.  Each evaluation tick appends a JSON line to
feedback_ledger.jsonl for long‑term alignment tracking.

The loop runs in its
own daemon thread and can be started/stopped programmatically.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass

# Import the already‑implemented safety layers
from .adaptive_viveka_gate import AdaptiveVivekaGate
from .context_aware_satya_layer import ContextAwareSatyaLayer

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())  # Prevent "No handler found" warnings


# --------------------------------------------------------------------------- #
# Helper estimators (simple placeholders that can be swapped later)
# --------------------------------------------------------------------------- #
@dataclass
class _EstimatorConfig:
    window_size: int = 20          # number of samples to keep (not used directly)
    max_value: float = 1.0         # value at which estimator saturates (-> 1.0)


class _MovingAverageEstimator:
    """
    Simple exponential moving average (EMA) estimator that returns a value
    in the range [0, 1] based on observed samples.
    """

    def __init__(self, alpha: float = 0.1, max_value: float = 1.0):
        self._alpha = alpha
        self._max_value = max_value
        self._value: float = 0.0   # EMA of the raw sample
        self._lock = threading.Lock()

    def update(self, sample: float) -> None:
        """Incorporate a new raw sample into the EMA."""
        with self._lock:
            # Clamp sample to a reasonable range before EMA update
            clamped = max(0.0, min(self._max_value, sample))
            self._value = self._alpha * clamped + (1.0 - self._alpha) * self._value

    def get(self) -> float:
        """Return the current estimate normalized to [0, 1]."""
        with self._lock:
            # Already normalized by construction (value ∈ [0, max_value])
            return min(1.0, self._value / self._max_value) if self._max_value > 0 else 0.0


class DustaraEstimator(_MovingAverageEstimator):
    """
    Proxy for Dustara‑Complexity.
    Uses the average number of reasoning steps / tool calls per interaction.
    Higher complexity → higher estimate (closer to 1.0).
    """

    def __init__(self, max_steps: float = 10.0, alpha: float = 0.1):
        super().__init__(alpha=alpha, max_value=max_steps)
        self._max_steps = max_steps

    def update_steps(self, steps: int) -> None:
        self.update(float(steps))


class AnandaEstimator(_MovingAverageEstimator):
    """
    Proxy for Ānanda‑Burden.
    Uses average inter‑request latency (seconds).
    Higher latency → higher burden.
    """

    def __init__(self, max_latency_sec: float = 30.0, alpha: float = 0.1):
        super().__init__(alpha=alpha, max_value=max_latency_sec)
        self._max_latency = max_latency_sec

    def update_latency(self, latency_sec: float) -> None:
        self.update(latency_sec)


# --------------------------------------------------------------------------- #
# Singleton holders for the already‑implemented layers (lazy init)
# --------------------------------------------------------------------------- #
class _LayerHolder:
    """Lazily‑initialized, thread‑safe singletons for the safety layers."""
    _viveka: Optional[AdaptiveVivekaGate] = None
    _satya: Optional[ContextAwareSatyaLayer] = None
    _lock = threading.Lock()

    @classmethod
    def viveka(cls) -> AdaptiveVivekaGate:
        with cls._lock:
            if cls._viveka is None:
                cls._viveka = AdaptiveVivekaGate()
            return cls._viveka

    @classmethod
    def satya(cls) -> ContextAwareSatyaLayer:
        with cls._lock:
            if cls._satya is None:
                cls._satya = ContextAwareSatyaLayer()
            return cls._satya


# --------------------------------------------------------------------------- #
# Main RtaFeedbackLoop class
# --------------------------------------------------------------------------- #
class RtaFeedbackLoop:
    """
    Computes and publishes the Ṛta‑Score.

    • Pulls Viveka‑Clarity and Satya‑Truthfulness from their respective
      safety‑layer singletons.
    • Uses DustaraEstimator and AnandaEstimator (replaceable) for the other
      two terms.
    • Score formula:  Ṛta = (V * S) / (D + A + ε)
    • Runs an internal evaluation loop (default 1 Hz) in a daemon thread.
    • Provides a simple `subscribe(callback)` API for consumers.
    • Persists each tick to feedback_ledger.jsonl.
    """

    def __init__(
        self,
        eval_interval: float = 1.0,
        dustara_estimator: Optional[DustaraEstimator] = None,
        ananda_estimator: Optional[AnandaEstimator] = None,
        ledger_path: str = "feedback_ledger.jsonl",
        epsilon: float = 1e-8,
    ):
        self._eval_interval = max(0.1, float(eval_interval))
        self._dustara = dustara_estimator or DustaraEstimator()
        self._ananda = ananda_estimator or AnandaEstimator()
        self._ledger_path = os.path.abspath(ledger_path)
        self._epsilon = epsilon

        # Thread‑safe state
        self._lock = threading.RLock()
        self._subscribers: List[Callable[[float, Dict[str, float]], None]] = []
        self._stop_event = threading.Event()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._latest_score: float = 0.0
        self._latest_components: Dict[str, float] = {
            "viveka": 0.0,
            "satya": 0.0,
            "dustara": 0.0,
            "ananda": 0.0,
        }

        # Ensure ledger directory exists
        ledger_dir = os.path.dirname(self._ledger_path)
        if ledger_dir and not os.path.isdir(ledger_dir):
            os.makedirs(ledger_dir, exist_ok=True)

    # --------------------------- Public API ------------------------------- #
    def start(self) -> None:
        """Start the background evaluation thread (if not already running)."""
        with self._lock:
            if self._running:
                logger.warning("RtaFeedbackLoop already started")
                return
            self._stop_event.clear()
            self._running = True
            self._thread = threading.Thread(
                target=self._run_loop, name="RtaFeedbackLoop", daemon=True
            )
            self._thread.start()
            logger.info("RtaFeedbackLoop started (interval=%.2fs)", self._eval_interval)

    def stop(self) -> None:
        """Stop the background evaluation thread."""
        with self._lock:
            if not self._running:
                return
            self._running = False
            self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
            logger.info("RtaFeedbackLoop stopped")

    def subscribe(
        self, callback: Callable[[float, Dict[str, float]], None]
    ) -> Callable[[], None]:
        """
        Register a callback to be invoked on each new Ṛta‑Score.

        Returns an ``unsubscribe`` callable.
        """
        with self._lock:
            self._subscribers.append(callback)

        def unsubscribe() -> None:
            with self._lock:
                if callback in self._subscribers:
                    self._subscribers.remove(callback)

        return unsubscribe

    def set_estimators(
        self,
        dustara: Optional[DustaraEstimator] = None,
        ananda: Optional[AnandaEstimator] = None,
    ) -> None:
        """Replace the estimator objects (mostly for testing)."""
        with self._lock:
            if dustara is not None:
                self._dustara = dustara
            if ananda is not None:
                self._ananda = ananda

    def get_latest(self) -> Tuple[float, Dict[str, float]]:
        """Thread‑safe snapshot of the most recent score and components."""
        with self._lock:
            return self._latest_score, dict(self._latest_components)

    def force_evaluation(self) -> None:
        """Run a single evaluation iteration immediately (useful for tests)."""
        self._evaluate_and_publish()

    # -------------------------- Internal loop ----------------------------- #
    def _run_loop(self) -> None:
        """Main loop: sleep → evaluate → publish."""
        while self._running:
            start = time.time()
            try:
                self._evaluate_and_publish()
            except Exception as exc:  # pragma: no cover – safety net
                logger.exception("Error in RtaFeedbackLoop evaluation: %s", exc)
            finally:
                elapsed = time.time() - start
                sleep_time = max(0.0, self._eval_interval - elapsed)
                # Use stop_event wait to sleep so it breaks immediately on stop()
                if self._stop_event.wait(timeout=sleep_time):
                    break

    def _evaluate_and_publish(self) -> None:
        """Fetch inputs, compute Ṛta, update state, notify subscribers, write ledger."""
        # --- 1. Get Viveka‑Clarity ------------------------------------------------
        try:
            viveka_gate = _LayerHolder.viveka()
            # The gate already tracks a success‑rate; we map it to a clarity score.
            # Using the internal transition success rate as a proxy for clarity.
            viveka = float(viveka_gate._transition_success_rate)  # pylint: disable=protected-access
            # Clamp just in case
            viveka = max(0.0, min(1.0, viveka))
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to read Viveka‑Clarity: %s", exc)
            viveka = self._latest_components["viveka"]  # reuse last good

        # --- 2. Get Satya‑Truthfulness -------------------------------------------
        try:
            satya_layer = _LayerHolder.satya()
            satya = float(satya_layer._truthfulness_metrics.truthfulness_score)  # pylint: disable=protected-access
            satya = max(0.0, min(1.0, satya))
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to read Satya‑Truthfulness: %s", exc)
            satya = self._latest_components["satya"]

        # --- 3. Get Dustara‑Complexity & Ānanda‑Burden ---------------------------
        dustara = self._dustara.get()
        ananda = self._ananda.get()

        # --- 4. Compute Ṛta‑Score -------------------------------------------------
        denominator = dustara + ananda + self._epsilon
        if denominator <= 0:
            # Should never happen because epsilon > 0, but guard anyway
            rta_score = 0.0
        else:
            # Clamp the score to [0.0, 1.0] to prevent mathematical explosion in low complexity states
            rta_score = min(1.0, (viveka * satya) / denominator)

        # --- 5. Update internal state --------------------------------------------
        with self._lock:
            self._latest_score = rta_score
            self._latest_components = {
                "viveka": viveka,
                "satya": satya,
                "dustara": dustara,
                "ananda": ananda,
            }
            subscribers = list(self._subscribers)  # copy to avoid holding lock during callbacks

        # --- 6. Notify subscribers ------------------------------------------------
        for cb in subscribers:
            try:
                cb(rta_score, self._latest_components)
            except Exception as exc:  # pragma: no cover
                logger.error("Subscriber callback raised: %s", exc)

        # --- 7. Persist to ledger -------------------------------------------------
        try:
            record = {
                "timestamp": time.time(),
                "viveka": viveka,
                "satya": satya,
                "dustara": dustara,
                "ananda": ananda,
                "rta": rta_score,
            }
            with open(self._ledger_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as exc:  # pragma: no cover
            logger.error("Unable to write to Rta feedback ledger: %s", exc)

    # --------------------------------------------------------------------------- #
    # Optional: simple introspection / debugging helpers
    # --------------------------------------------------------------------------- #
    def __repr__(self) -> str:  # pragma: no cover
        with self._lock:
            return (
                f"<RtaFeedbackLoop score={self._latest_score:.4f} "
                f"v={self._latest_components['viveka']:.3f} "
                f"s={self._latest_components['satya']:.3f} "
                f"d={self._latest_components['dustara']:.3f} "
                f"a={self._latest_components['ananda']:.3f}>"
            )


# --------------------------------------------------------------------------- #
# Convenience: a module‑level default instance (optional for quick import)
# --------------------------------------------------------------------------- #
_default_loop: Optional[RtaFeedbackLoop] = None
_default_loop_lock = threading.Lock()


def get_default_rta_loop() -> RtaFeedbackLoop:
    """
    Return a process‑wide default RtaFeedbackLoop instance.
    Callers can then ``start()`` it and subscribe to it.
    """
    global _default_loop
    with _default_loop_lock:
        if _default_loop is None:
            _default_loop = RtaFeedbackLoop()
        return _default_loop


# --------------------------------------------------------------------------- #
# If this file is executed directly, run a quick sanity‑check demo.
# --------------------------------------------------------------------------- #
if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    loop = get_default_rta_loop()

    def demo_cb(score: float, comps: Dict[str, float]) -> None:
        print(
            f"[{time.strftime('%H:%M:%S')}] Ṛta={score:.3f} "
            f"(V={comps['viveka']:.2f}, S={comps['satya']:.2f}, "
            f"D={comps['dustara']:.2f}, A={comps['ananda']:.2f})"
        )

    unsub = loop.subscribe(demo_cb)
    loop.start()
    try:
        # Run for ~10 seconds then stop
        time.sleep(10)
    finally:
        loop.stop()
        unsub()