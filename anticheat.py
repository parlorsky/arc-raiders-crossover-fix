#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Apply the local anti-cheat compatibility tweak to a private bottle copy.

The Denuvo Anti-Cheat runtime describes the environment in a survey payload.
On Wine/CrossOver that payload contains a marker which makes the backend treat
the environment as unsupported.  This module removes that single JSON field
from the *local copy* of the runtime, leaving the runtime itself and all of its
checks intact.

The edit is marker-based (not version- or hash-based), so it keeps working
across minor anti-cheat updates.  Every patched file keeps a one-time backup.

Usage:
    python3 anticheat.py --bottle "/path/to/bottle" [--dry-run]
    python3 anticheat.py --bottle "/path/to/bottle" --revert
    python3 anticheat.py --bottle "/path/to/bottle" --check
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import stat
import sys
import tempfile

DAC_DIR = Path("drive_c/Program Files/Denuvo Anti-Cheat")
RUNTIME_NAME = "denuvo-anti-cheat-runtime.dll"
MARKER = b', "proton":true'
MUTED = b'\x00 "proton":true'
BACKUP_SUFFIX = ".arc-original"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _atomic_write(path: Path, data: bytes) -> None:
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except FileNotFoundError:
        mode = 0o644
    descriptor, temporary = tempfile.mkstemp(prefix=".arc-ac-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _inside(path: Path, root: Path) -> bool:
    try:
        return path.resolve().is_relative_to(root.resolve())
    except OSError:
        return False


def find_runtime_copies(bottle: Path) -> list[Path]:
    """Return the main runtime plus its staged update copies."""
    root = bottle / DAC_DIR
    if not root.is_dir():
        return []
    copies: list[Path] = []
    main = root / RUNTIME_NAME
    if main.is_file() and not main.is_symlink():
        copies.append(main)
    try:
        children = sorted(root.iterdir(), key=lambda item: item.name)
    except OSError:
        return copies
    for child in children:
        if not child.is_dir() or child.is_symlink():
            continue
        candidate = child / RUNTIME_NAME
        if candidate.is_file() and not candidate.is_symlink():
            copies.append(candidate)
    return [path for path in copies if _inside(path, bottle)]


def _status(path: Path) -> str:
    data = path.read_bytes()
    if MUTED in data and MARKER not in data:
        return "already-applied"
    if MARKER in data:
        return "pending"
    return "marker-not-found"


def _ensure_backup(path: Path, data: bytes) -> None:
    backup = path.with_name(path.name + BACKUP_SUFFIX)
    if backup.exists():
        return
    original = data.replace(MUTED, MARKER, 1) if (MUTED in data and MARKER not in data) else data
    _atomic_write(backup, original)


def apply_copy(path: Path, *, dry_run: bool = False) -> str:
    data = path.read_bytes()
    if MUTED in data and MARKER not in data:
        if not dry_run:
            _ensure_backup(path, data)
        return "already-applied"
    if MARKER not in data:
        return "marker-not-found"
    if data.count(MARKER) != 1:
        return "unexpected-marker-count"
    result = data.replace(MARKER, MUTED, 1)
    if not dry_run:
        _ensure_backup(path, data)
        _atomic_write(path, result)
    return "applied"


def revert_copy(path: Path, *, dry_run: bool = False) -> str:
    backup = path.with_name(path.name + BACKUP_SUFFIX)
    if not backup.is_file():
        return "no-backup"
    if not dry_run:
        _atomic_write(path, backup.read_bytes())
    return "reverted"


def ensure_runtime_tweak(bottle: Path, *, dry_run: bool = False) -> list[tuple[Path, str]]:
    """Best-effort patch of every copy inside *bottle*. Never raises on I/O."""
    results: list[tuple[Path, str]] = []
    for path in find_runtime_copies(bottle):
        try:
            results.append((path, apply_copy(path, dry_run=dry_run)))
        except OSError as exc:
            results.append((path, f"error: {exc}"))
    return results


def revert_runtime_tweak(bottle: Path, *, dry_run: bool = False) -> list[tuple[Path, str]]:
    results: list[tuple[Path, str]] = []
    for path in find_runtime_copies(bottle):
        try:
            results.append((path, revert_copy(path, dry_run=dry_run)))
        except OSError as exc:
            results.append((path, f"error: {exc}"))
    return results


def describe(results: list[tuple[Path, str]]) -> str:
    if not results:
        return "anti-cheat components not installed yet"
    states = {}
    for _path, status in results:
        states[status] = states.get(status, 0) + 1
    return ", ".join(f"{status} x{count}" for status, count in sorted(states.items()))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bottle", type=Path, required=True,
                        help="CrossOver bottle folder (contains drive_c)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change")
    parser.add_argument("--revert", action="store_true", help="Restore the one-time backups")
    parser.add_argument("--check", action="store_true", help="Only report the current state")
    args = parser.parse_args(argv)
    bottle = args.bottle.expanduser().resolve()
    if not (bottle / "drive_c").is_dir():
        print(f"Not a CrossOver bottle: {bottle}", file=sys.stderr)
        return 2
    if args.check:
        results = [(path, _status(path)) for path in find_runtime_copies(bottle)]
    elif args.revert:
        results = revert_runtime_tweak(bottle, dry_run=args.dry_run)
    else:
        results = ensure_runtime_tweak(bottle, dry_run=args.dry_run)
    for path, status in results:
        try:
            label = str(path.relative_to(bottle))
        except ValueError:
            label = str(path)
        print(f"{status:20s} {label}")
    if not results:
        print("No Denuvo Anti-Cheat runtime found in this bottle yet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
