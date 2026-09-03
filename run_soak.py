"""
================================================================================
NALA — Nexus Autonomous Long-Running Agent
================================================================================
File    : run_soak.py
Purpose : Interactive, colorful CLI runner for the JIRA-007 1-hour soak test.
          Streams pytest output with Rich panels, live progress bars, phase
          banners, heartbeat status sidebar, and a final pass/fail report card.
          Inspired by Claude Code CLI's dense, structured terminal UX.

Usage   : python run_soak.py [--status-dir PATH] [--no-heartbeat]
================================================================================
Jai Bajrang Bali
================================================================================
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Gracefully handle missing Rich (offer install hint)
# ---------------------------------------------------------------------------
try:
    from rich import box
    from rich.columns import Columns
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TaskID,
        TextColumn,
        TimeElapsedColumn,
    )
    from rich.rule import Rule
    from rich.style import Style
    from rich.table import Table
    from rich.text import Text
    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False


_logger = logging.getLogger("nala.soak.runner")

# ===========================================================================
# CONSTANTS
# ===========================================================================

SOAK_DURATION_S   = int(os.environ.get("SOAK_DURATION", 3600))   # default 60 minutes
KILL_WINDOW_START = int(SOAK_DURATION_S * 0.33)
KILL_WINDOW_END   = int(SOAK_DURATION_S * 0.75)
CHAOS_WINDOW_START = int(SOAK_DURATION_S * 0.20)
CHAOS_WINDOW_END   = int(SOAK_DURATION_S * 0.30)

# Log patterns for coloring (compiled once)
_PATTERN_PASS     = re.compile(r"\bPASSED\b|PASSED\.", re.IGNORECASE)
_PATTERN_FAIL     = re.compile(r"\bFAILED\b|FAILED\.|AssertionError|VIOLATION", re.IGNORECASE)
_PATTERN_WARN     = re.compile(r"\bWARNING\b|\bWARN\b|chaos|SIGKILL|stale.lock", re.IGNORECASE)
_PATTERN_INFO     = re.compile(r"\bINFO\b|\[SoakOrchestrator\]|\[SoakSupervisor\]|\[Bootstrap", re.IGNORECASE)
_PATTERN_SPAWN    = re.compile(r"Spawned generation|generation_spawned", re.IGNORECASE)
_PATTERN_CRASH    = re.compile(r"SIGKILL|sigkill_injected|crash_recovery", re.IGNORECASE)
_PATTERN_HANDOFF  = re.compile(r"handoff|PAUSED|spore", re.IGNORECASE)
_PATTERN_COMPACT  = re.compile(r"Dronagiri|compaction|CONTEXT_EXHAUSTED", re.IGNORECASE)
_PATTERN_HEARTBT  = re.compile(r"heartbeat|soak_status", re.IGNORECASE)
_PATTERN_ASSERT   = re.compile(r"assert_\w+\(\) PASSED", re.IGNORECASE)


# ===========================================================================
# PLAIN FALLBACK (no Rich)
# ===========================================================================

def _run_plain(cmd: List[str]) -> int:
    """Simple fallback runner when Rich is not installed."""
    print("\n[NALA Soak Runner] Rich not installed. Running plain pytest...\n")
    print(f"Command: {' '.join(cmd)}\n")
    print("=" * 72)
    proc = subprocess.Popen(cmd, text=True, bufsize=1)
    proc.wait()
    return proc.returncode


# ===========================================================================
# HEARTBEAT READER (background thread)
# ===========================================================================

class HeartbeatReader:
    """
    Polls soak_runs/<latest>/ for soak_status.json every 5 seconds and
    exposes the parsed data thread-safely via ``self.latest``.
    """

    def __init__(self, soak_runs_dir: Path) -> None:
        self.soak_runs_dir = soak_runs_dir
        self.latest: Dict[str, Any] = {}
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._poll, daemon=True, name="heartbeat-reader"
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _poll(self) -> None:
        while not self._stop.is_set():
            try:
                # Find the most recently modified soak_status.json
                candidates = list(self.soak_runs_dir.glob("*/soak_status.json"))
                if candidates:
                    latest_file = max(candidates, key=lambda p: p.stat().st_mtime)
                    raw = latest_file.read_text(encoding="utf-8")
                    self.latest = json.loads(raw)
            except Exception:
                pass
            self._stop.wait(timeout=5.0)


# ===========================================================================
# LOG COLORIZER
# ===========================================================================

def _colorize(line: str) -> Text:
    """Return a Rich Text object with appropriate color for the log line."""
    text = Text(line, end="\n")
    if _PATTERN_FAIL.search(line):
        text.stylize("bold red")
    elif _PATTERN_PASS.search(line) or _PATTERN_ASSERT.search(line):
        text.stylize("bold green")
    elif _PATTERN_CRASH.search(line):
        text.stylize("bold magenta")
    elif _PATTERN_WARN.search(line):
        text.stylize("yellow")
    elif _PATTERN_SPAWN.search(line):
        text.stylize("bold cyan")
    elif _PATTERN_HANDOFF.search(line):
        text.stylize("bold blue")
    elif _PATTERN_COMPACT.search(line):
        text.stylize("bright_yellow")
    elif _PATTERN_HEARTBT.search(line):
        text.stylize("dim cyan")
    elif _PATTERN_INFO.search(line):
        text.stylize("bright_white")
    else:
        text.stylize("white")
    return text


# ===========================================================================
# PHASE DETECTOR
# ===========================================================================

def _get_phase(elapsed_s: float) -> str:
    if elapsed_s < 0:
        return "INIT"
    elif elapsed_s < 600:         # 0–10 min
        return "Phase 1 — Warmup"
    elif elapsed_s < CHAOS_WINDOW_START:  # 10–12 min
        return "Phase 2 — Steady State"
    elif elapsed_s <= CHAOS_WINDOW_END:   # 12–18 min
        return "Phase 2C — CHAOS WINDOW  [disk corruption active]"
    elif elapsed_s < KILL_WINDOW_START:   # 18–20 min
        return "Phase 3 — Pre-Kill Buffer"
    elif elapsed_s <= KILL_WINDOW_END:    # 20–45 min
        return "Phase 3K — SIGKILL WINDOW  [crash injection active]"
    elif elapsed_s < SOAK_DURATION_S:     # 45–60 min
        return "Phase 4 — Recovery Validation"
    else:
        return "Phase 5 — Final Assertions"


def _phase_color(phase: str) -> str:
    if "CHAOS" in phase:    return "bold magenta"
    if "SIGKILL" in phase:  return "bold red"
    if "Warmup" in phase:   return "cyan"
    if "Final" in phase:    return "bold green"
    return "bright_white"


# ===========================================================================
# STATUS PANEL BUILDER
# ===========================================================================

def _build_status_panel(
    hb: Dict[str, Any],
    elapsed_s: float,
    lines_seen: int,
    run_start_wall: float,
) -> Panel:
    """Build the right-hand status panel from the latest heartbeat + elapsed."""
    table = Table.grid(padding=(0, 1))
    table.add_column(style="dim", no_wrap=True)
    table.add_column(no_wrap=True)

    def row(key: str, val: str, style: str = "white") -> None:
        table.add_row(key, Text(val, style=style))

    # Wall clock
    now_str = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    row("🕐 Time",       now_str)
    row("⏱  Elapsed",   f"{elapsed_s/60:.1f} min / 60 min")

    # Progress bar
    pct = min(elapsed_s / SOAK_DURATION_S * 100, 100.0)
    filled = int(pct / 5)   # 20-char bar
    bar = "[" + "#" * filled + "-" * (20 - filled) + "]"
    row("📊 Progress",  f"{bar} {pct:.1f}%", "bold cyan" if pct < 100 else "bold green")

    # Phase
    phase = _get_phase(elapsed_s)
    row("🔄 Phase",     phase, _phase_color(phase))

    table.add_row("", "")  # spacer

    # Heartbeat data
    if hb:
        gen_idx  = hb.get("generation_index", "?")
        session  = str(hb.get("session_id", "?"))[:16] + "…"
        steps_ok = hb.get("steps_completed", "?")
        steps_tt = hb.get("steps_total", "?")
        ctx_st   = hb.get("context_status", "?")
        compacts = hb.get("compactions_this_gen", 0)
        cost     = hb.get("total_cost_usd", 0.0)
        spawn    = hb.get("spawn_reason", "?")
        ts_hb    = hb.get("ts", 0)
        age_s    = time.time() - ts_hb if ts_hb else -1

        ctx_color = (
            "bold green" if ctx_st in ("ok", "OK", "green")
            else "bold yellow" if ctx_st in ("warning", "WARN")
            else "bold red"
        )

        row("🧬 Generation",  f"#{gen_idx}  ({spawn})",         "bright_cyan")
        row("🆔 Session",     session,                           "dim")
        row("✅ Steps",       f"{steps_ok} / {steps_tt}",       "green")
        row("🧠 Context",     str(ctx_st),                       ctx_color)
        row("🗜  Compactions", str(compacts),                    "yellow")
        row("💵 Cost",        f"${cost:.6f}",                    "dim")
        if age_s >= 0:
            stale = "  ⚠ STALE" if age_s > 60 else ""
            row("💓 Heartbeat",  f"{age_s:.0f}s ago{stale}",
                "yellow" if age_s > 60 else "dim green")
    else:
        row("💓 Heartbeat",   "waiting for first write…",        "dim")

    table.add_row("", "")
    row("📝 Log lines",   str(lines_seen),    "dim")

    return Panel(
        table,
        title="[bold bright_white]NALA Soak Monitor[/]",
        subtitle="[dim]Tailscale: soak_status.json[/]",
        border_style="bright_blue",
        padding=(0, 1),
    )


# ===========================================================================
# LOG PANEL BUILDER (rolling last N lines)
# ===========================================================================

class _RollingLog:
    """Thread-safe rolling log buffer."""

    def __init__(self, maxlines: int = 30) -> None:
        self._lines: List[Text] = []
        self._max = maxlines
        self._lock = threading.Lock()

    def append(self, line: str) -> None:
        t = _colorize(line.rstrip())
        with self._lock:
            self._lines.append(t)
            if len(self._lines) > self._max:
                self._lines.pop(0)

    def render(self) -> Text:
        with self._lock:
            out = Text()
            for t in self._lines:
                out.append_text(t)
                out.append("\n")
            return out


# ===========================================================================
# RICH RUNNER
# ===========================================================================

def _run_rich(cmd: List[str], soak_runs_dir: Path) -> int:
    console = Console(highlight=False, markup=True)
    
    # We set max lines to 25 to fit nicely inside the terminal layout box
    run_log = _RollingLog(maxlines=25)
    hb_reader = HeartbeatReader(soak_runs_dir)
    hb_reader.start()

    run_start = time.monotonic()
    wall_start = time.time()
    lines_seen = 0
    returncode = -1

    # ── Subprocess ───────────────────────────────────────────────────────────
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace",
    )

    # Stream reader thread
    _output_done = threading.Event()

    def _stream_reader():
        nonlocal lines_seen
        assert proc.stdout is not None
        for raw_line in proc.stdout:
            line = raw_line.rstrip("\n\r")
            run_log.append(line)
            lines_seen += 1
        _output_done.set()

    reader_thread = threading.Thread(target=_stream_reader, daemon=True)
    reader_thread.start()

    # ── Layout Setup ──────────────────────────────────────────────────────────
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=4),
        Layout(name="body"),
        Layout(name="footer", size=3),
    )
    layout["body"].split_row(
        Layout(name="log", ratio=2),
        Layout(name="status", ratio=1),
    )

    # Header panel content
    header_text = Text.assemble(
        ("🚀 Launching: ", "bold white"),
        (" ".join(cmd), "bright_cyan"),
        ("\n📱 Mobile Live Link: ", "bold white"),
        ("http://100.124.210.9:8000/ ", "bold bright_blue"),
        (" (Refresh on phone to view live soak_status.json updates)", "dim")
    )
    layout["header"].update(Panel(
        header_text,
        title="[bold bright_cyan]NALA · 1-Hour Soak Test · JIRA-007[/]",
        border_style="bright_blue",
        padding=(0, 2),
    ))

    # Inner progress display
    progress_bar = Progress(
        SpinnerColumn(spinner_name="dots12", style="bold bright_cyan"),
        TextColumn("[bold white]{task.description}"),
        BarColumn(bar_width=None, complete_style="bright_cyan", finished_style="bold green"),
        TextColumn("[bright_cyan]{task.percentage:.0f}%"),
        TimeElapsedColumn(),
    )
    soak_task: TaskID = progress_bar.add_task(
        "Soak Run Progress (60 min limit)", total=SOAK_DURATION_S
    )
    layout["footer"].update(Panel(progress_bar, border_style="bright_blue", padding=(0, 1)))

    # ── Live UI Loop ──────────────────────────────────────────────────────────
    try:
        with Live(layout, console=console, refresh_per_second=4, screen=True) as live:
            while proc.poll() is None or not _output_done.is_set():
                elapsed_s = time.monotonic() - run_start
                progress_bar.update(soak_task, completed=min(elapsed_s, SOAK_DURATION_S))

                # Update live log view
                layout["log"].update(Panel(
                    run_log.render(),
                    title=f"[bold bright_white]Live Log Output (last 25 lines) · t+{elapsed_s/60:.1f}m[/]",
                    border_style="dim",
                    padding=(0, 1),
                ))

                # Update live status view
                layout["status"].update(_build_status_panel(
                    hb_reader.latest,
                    elapsed_s,
                    lines_seen,
                    wall_start,
                ))

                time.sleep(0.25)
    except KeyboardInterrupt:
        _logger.warning("[SoakRunner] KeyboardInterrupt detected. Terminating child process...")
        proc.terminate()
        try:
            proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            proc.kill()

    # Wait for child exit
    proc.wait()
    _output_done.wait(timeout=5.0)
    returncode = proc.returncode
    hb_reader.stop()

    # ── Exit Results Screen ──────────────────────────────────────────────────
    elapsed_total = time.monotonic() - run_start
    console.print()
    console.print(Rule("[bold bright_cyan]Test Execution Finished[/]", style="bright_blue"))
    console.print()

    if returncode == 0:
        console.print(Panel(
            Text.assemble(
                ("  ✅  SOAK TEST PASSED\n\n", "bold green"),
                (f"  Duration : {elapsed_total/60:.1f} minutes\n", "white"),
                (f"  Log lines: {lines_seen}\n", "white"),
                (f"  Exit code: {returncode}\n", "white"),
                ("\n  Live Mobile Monitoring Command:\n", "dim"),
                ("  python -m http.server 8000  (in soak_runs/)\n", "bright_cyan"),
            ),
            title="[bold green]JIRA-007 — 1-Hour Soak Test Result[/]",
            border_style="bold green",
            padding=(1, 4),
        ))
    else:
        bundle_files = sorted(
            Path("soak_runs").glob("*/soak_failure_bundle_*.zip"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ) if Path("soak_runs").exists() else []
        bundle_info = (
            f"\n  Bundle   : {bundle_files[0]}\n"
            if bundle_files else
            "\n  Bundle   : not found (written to checkpoint_base_dir)\n"
        )

        console.print(Panel(
            Text.assemble(
                ("  ❌  SOAK TEST FAILED\n\n", "bold red"),
                (f"  Duration : {elapsed_total/60:.1f} minutes\n", "white"),
                (f"  Log lines: {lines_seen}\n", "white"),
                (f"  Exit code: {returncode}\n", "bold red"),
                (bundle_info, "bright_yellow"),
                ("\n  Check soak_runs/<run-id>/soak_failure_report.json\n", "dim"),
            ),
            title="[bold red]JIRA-007 — 1-Hour Soak Test Result[/]",
            border_style="bold red",
            padding=(1, 4),
        ))

    console.print()
    return returncode



# ===========================================================================
# ENTRY POINT
# ===========================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="NALA Soak Test — colorful interactive runner"
    )
    parser.add_argument(
        "--soak-runs-dir",
        default="soak_runs",
        help="Directory where soak run artifacts are written. "
             "Default: soak_runs/ (relative to CWD).",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable Rich colors; fall back to plain output.",
    )
    parser.add_argument(
        "--pytest-args",
        nargs=argparse.REMAINDER,
        default=[],
        help="Extra args forwarded verbatim to pytest after the built-in flags.",
    )
    args = parser.parse_args()

    soak_runs_dir = Path(args.soak_runs_dir).resolve()

    # Show which Python interpreter will be used (important on Windows where
    # multiple Python installs coexist — make sure you run this script with
    # the same interpreter your project uses).
    print(f"\n[NALA Soak Runner] Python: {sys.executable}")
    print(f"[NALA Soak Runner] Soak runs dir: {soak_runs_dir}\n")

    # Base pytest command
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/long_running/test_soak_1hr.py",
        "-m", "long_running",
        "-s",           # no capture — we stream ourselves
        "-v",           # verbose
        "--tb=short",   # short tracebacks (full detail in bundle)
        "--no-header",
    ] + (args.pytest_args or [])

    if args.no_color or not _HAS_RICH:
        if not _HAS_RICH:
            print(
                "\n[NALA] Rich library not found. Install it for the colorful UI:\n"
                "    pip install rich\n"
                "\nFalling back to plain output...\n"
            )
        rc = _run_plain(cmd)
    else:
        rc = _run_rich(cmd, soak_runs_dir)

    sys.exit(rc)


if __name__ == "__main__":
    main()
