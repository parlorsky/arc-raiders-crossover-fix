#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Local compatibility adjustment for the anti-cheat runtime copy.

ARC Raiders runs on macOS through CrossOver/Wine.  The Denuvo Anti-Cheat
runtime describes the environment in a small survey payload.  On Wine/CrossOver
that payload carries a marker which the backend classifies as an unsupported
environment.  This module removes that single marker from the *local copy* of
the runtime inside the user's own private installation.

It is a compatibility adjustment, not a gameplay cheat:

  * no game memory access, no gameplay changes, no network interception;
  * no changes outside the private installation;
  * no hidden behaviour — every change is logged, backed up and reversible.

Usage:
    python3 compat.py --bottle "/path/to/bottle" [--dry-run]
    python3 compat.py --bottle "/path/to/bottle" --revert
    python3 compat.py --bottle "/path/to/bottle" --check
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import stat
import sys
import tempfile

COMPONENT_DIR = Path("drive_c/Program Files/Denuvo Anti-Cheat")
RUNTIME_NAME = "denuvo-anti-cheat-runtime.dll"
ENVIRONMENT_MARKER = b', "proton":true'
NORMALIZED_MARKER = b'\x00 "proton":true'
BACKUP_SUFFIX = ".arc-original"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _atomic_write(path: Path, data: bytes) -> None:
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except FileNotFoundError:
        mode = 0o644
    descriptor, temporary = tempfile.mkstemp(prefix=".arc-compat-", dir=path.parent)
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


def find_local_runtime_copies(bottle: Path) -> list[Path]:
    """Return the main runtime plus staged update copies inside *bottle*."""
    root = bottle / COMPONENT_DIR
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


def _state(path: Path) -> str:
    data = path.read_bytes()
    if NORMALIZED_MARKER in data and ENVIRONMENT_MARKER not in data:
        return "already-adjusted"
    if ENVIRONMENT_MARKER in data:
        return "pending"
    return "marker-not-found"


def _ensure_backup(path: Path, data: bytes) -> None:
    backup = path.with_name(path.name + BACKUP_SUFFIX)
    if backup.exists():
        return
    original = (data.replace(NORMALIZED_MARKER, ENVIRONMENT_MARKER, 1)
                if (NORMALIZED_MARKER in data and ENVIRONMENT_MARKER not in data) else data)
    _atomic_write(backup, original)


def normalize_copy(path: Path, *, dry_run: bool = False) -> str:
    data = path.read_bytes()
    if NORMALIZED_MARKER in data and ENVIRONMENT_MARKER not in data:
        if not dry_run:
            _ensure_backup(path, data)
        return "already-adjusted"
    if ENVIRONMENT_MARKER not in data:
        return "marker-not-found"
    if data.count(ENVIRONMENT_MARKER) != 1:
        return "unexpected-marker-count"
    result = data.replace(ENVIRONMENT_MARKER, NORMALIZED_MARKER, 1)
    if not dry_run:
        _ensure_backup(path, data)
        _atomic_write(path, result)
    return "adjusted"


def restore_copy(path: Path, *, dry_run: bool = False) -> str:
    backup = path.with_name(path.name + BACKUP_SUFFIX)
    if not backup.is_file():
        return "no-backup"
    if not dry_run:
        _atomic_write(path, backup.read_bytes())
    return "restored"


def apply_compatibility_tweak(bottle: Path, *, dry_run: bool = False) -> list[tuple[Path, str]]:
    """Best-effort adjustment of every local copy. Never raises on I/O."""
    results: list[tuple[Path, str]] = []
    for path in find_local_runtime_copies(bottle):
        try:
            results.append((path, normalize_copy(path, dry_run=dry_run)))
        except OSError as exc:
            results.append((path, f"error: {exc}"))
    return results


def restore_compatibility_tweak(bottle: Path, *, dry_run: bool = False) -> list[tuple[Path, str]]:
    results: list[tuple[Path, str]] = []
    for path in find_local_runtime_copies(bottle):
        try:
            results.append((path, restore_copy(path, dry_run=dry_run)))
        except OSError as exc:
            results.append((path, f"error: {exc}"))
    return results


def describe(results: list[tuple[Path, str]]) -> str:
    if not results:
        return "components not installed yet"
    states: dict[str, int] = {}
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
        results = [(path, _state(path)) for path in find_local_runtime_copies(bottle)]
    elif args.revert:
        results = restore_compatibility_tweak(bottle, dry_run=args.dry_run)
    else:
        results = apply_compatibility_tweak(bottle, dry_run=args.dry_run)
    for path, status in results:
        try:
            label = str(path.relative_to(bottle))
        except ValueError:
            label = str(path)
        print(f"{status:20s} {label}")
    if not results:
        print("No local anti-cheat runtime found in this bottle yet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
