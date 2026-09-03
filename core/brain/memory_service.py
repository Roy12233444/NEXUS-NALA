"""
================================================================================
NALA — Nexus Autonomous Long-Running Agent
================================================================================
File    : core/brain/memory_service.py
Purpose : Flat-file memory service — adapted from qm-main's memory-service.ts
          Stores facts as bullet points in memory/MEMORY.md.
          This is the interim implementation before Anjaneya Memory Protocol (AMP).

Format  : memory/MEMORY.md
          # Memory
          - (2026-08-05) User's name is Sourav Ray, founder of Nexus LAB AI.
          - (2026-08-05) User prefers dark mode UI with glassmorphic design.

AMP Note: When AMP is ready, replace the read/write methods here with AMP API calls.
          The MemoryService interface will remain identical — no UI changes needed.
================================================================================
"""

import hashlib
import os
import re
from datetime import datetime, timezone
from typing import Optional

MEMORY_FILE = "memory/MEMORY.md"
MEMORY_HEADER = "# Memory\n\n"
MAX_FACTS = 300


def _revision_token(content: str) -> str:
    """SHA-256 hash of content — used to detect concurrent edits (qm pattern)."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _date_str(ts: Optional[float] = None) -> str:
    """Returns ISO date string like '2026-08-05'."""
    dt = datetime.fromtimestamp(ts, tz=timezone.utc) if ts else datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%d")


def _is_bullet(line: str) -> bool:
    """True if a line is a markdown bullet point starting with - or *."""
    return bool(re.match(r"^\s*[-*]\s+", line))


def _normalize(text: str) -> str:
    """Lowercase + strip for deduplication (qm pattern)."""
    return re.sub(r"\s+", " ", text.lower().strip())


class MemoryService:
    """
    NALA's flat-file memory service.
    Adapted directly from qm-main's memory-service.ts logic.
    """

    def __init__(self, memory_dir: str = "."):
        self.memory_path = os.path.join(memory_dir, MEMORY_FILE)
        os.makedirs(os.path.dirname(self.memory_path), exist_ok=True)

    # ──────────────────────────────────────────────────────────────────────────
    # Low-level read / write
    # ──────────────────────────────────────────────────────────────────────────

    def _read_raw(self) -> str:
        """Read raw content of MEMORY.md. Returns empty string if not found."""
        if not os.path.exists(self.memory_path):
            return ""
        with open(self.memory_path, "r", encoding="utf-8") as f:
            return f.read()

    def _write_raw(self, content: str) -> None:
        """Write raw content back to MEMORY.md atomically."""
        tmp_path = self.memory_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, self.memory_path)

    # ──────────────────────────────────────────────────────────────────────────
    # Public API (mirrors qm-main MemoryService interface)
    # ──────────────────────────────────────────────────────────────────────────

    def read(self) -> str:
        """Return full raw content of the memory notebook."""
        return self._read_raw()

    def read_head(self) -> dict:
        """Return content + revision token (for optimistic concurrency, qm pattern)."""
        content = self._read_raw()
        return {"content": content, "revision": _revision_token(content)}

    def parse_facts(self) -> list[dict]:
        """
        Parse bullet points from the memory file.
        Returns list of {line, text, date?} dicts — same as qm's facts() function.
        """
        content = self._read_raw()
        facts = []
        for i, row in enumerate(content.split("\n")):
            match = re.match(
                r"^\s*[-*]\s+(?:\((\d{4}-\d{2}-\d{2})\)\s*)?(.*\S)\s*$", row
            )
            if match:
                entry: dict = {"line": i, "text": match.group(2)}
                if match.group(1):
                    entry["date"] = match.group(1)
                facts.append(entry)
        return facts

    def capture(self, facts_text: list[str], author: str = "user") -> int:
        """
        Add new facts. Deduplicates, date-stamps, appends to MEMORY.md.
        Adapted from qm-main's foldCapture() function.
        Returns number of facts actually added.
        """
        existing = self._read_raw()
        lines = existing.split("\n")
        seen = set(
            _normalize(re.sub(r"^\s*[-*]\s+(?:\(\d{4}-\d{2}-\d{2}\)\s*)?", "", l))
            for l in lines if _is_bullet(l)
        )

        date = _date_str()
        to_add = []
        for f in facts_text:
            clean = re.sub(r"\s+", " ", f.strip())
            clean = re.sub(r"^[-*]\s+", "", clean)
            if not clean:
                continue
            key = _normalize(clean)
            if not key or key in seen:
                continue
            seen.add(key)
            to_add.append(f"- ({date}) {clean}")

        if not to_add:
            return 0

        if existing.strip():
            body = existing.rstrip() + "\n" + "\n".join(to_add) + "\n"
        else:
            body = MEMORY_HEADER + "\n".join(to_add) + "\n"

        # Enforce MAX_FACTS sliding window (qm pattern)
        all_lines = body.split("\n")
        bullet_idxs = [i for i, l in enumerate(all_lines) if _is_bullet(l)]
        overflow = len(bullet_idxs) - MAX_FACTS
        if overflow > 0:
            drop = set(bullet_idxs[:overflow])
            body = "\n".join(l for i, l in enumerate(all_lines) if i not in drop)

        self._write_raw(body)
        return len(to_add)

    def delete_fact(self, line_index: int) -> bool:
        """Remove the bullet at the given line number (0-indexed)."""
        content = self._read_raw()
        lines = content.split("\n")
        if 0 <= line_index < len(lines):
            lines.pop(line_index)
            self._write_raw("\n".join(lines))
            return True
        return False

    def replace(self, content: str) -> None:
        """Replace entire memory notebook (used by raw editor save, qm pattern)."""
        normalized = content.rstrip() + "\n" if content.strip() else ""
        if normalized:
            self._write_raw(normalized)
        elif os.path.exists(self.memory_path):
            os.remove(self.memory_path)

    def replace_if_revision(self, content: str, revision: str) -> bool:
        """
        Optimistic concurrency save — only replaces if revision matches.
        Returns False if memory was changed concurrently (qm pattern).
        """
        current = self._read_raw()
        if _revision_token(current) != revision:
            return False
        self.replace(content)
        return True

    def query(self, q: str, limit: int = 20) -> list[str]:
        """
        Search memory facts containing all query terms.
        Adapted from qm-main's queryBullets() function.
        """
        terms = q.lower().split()
        if not terms:
            return []
        content = self._read_raw()
        results = []
        for line in content.split("\n"):
            if _is_bullet(line):
                if all(t in line.lower() for t in terms):
                    results.append(line.strip())
                    if len(results) >= limit:
                        break
        return results

    def recall(self, max_chars: int = 8000) -> str:
        """
        Return a trimmed view of memory for injection into the AI prompt.
        Adapted from qm-main's recall() + recallBody() functions.
        """
        content = self._read_raw().strip()
        if not content:
            return ""
        return content[:max_chars] if len(content) > max_chars else content


# Singleton instance for use in nala_server.py
_memory_service: Optional[MemoryService] = None


def get_memory_service() -> MemoryService:
    global _memory_service
    if _memory_service is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        _memory_service = MemoryService(memory_dir=base_dir)
    return _memory_service
