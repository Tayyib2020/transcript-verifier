"""Compute the exact digest expected by TranscriptVerifier."""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python scripts/hash_transcript.py <utf8-transcript-file>")

    transcript = Path(sys.argv[1]).read_text(encoding="utf-8")
    digest = hashlib.sha256(transcript.encode("utf-8")).hexdigest()
    print(f"0x{digest}")


if __name__ == "__main__":
    main()
