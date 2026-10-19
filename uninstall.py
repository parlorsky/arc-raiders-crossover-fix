#!/usr/bin/env python3
"""Stop this installation's server, then move its complete directory to Trash."""
import argparse
import datetime
import errno
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import uuid

from install import DEFAULT_DESTINATION


def owned_paths(destination):
    raw = Path(os.path.abspath(Path(destination).expanduser()))
    if raw.is_symlink() or not stat.S_ISDIR(raw.lstat().st_mode):
        raise ValueError("The installation root must be a real directory, not a symlink.")
    root, home = raw.resolve(strict=True), Path.home().resolve()
    if root.stat().st_uid != os.getuid():
        raise ValueError("The installation root must be owned by the current user.")
    protected = {Path(p) for p in ("/", "/Applications", "/System", "/Library", "/Users",
                                  "/usr", "/bin", "/sbin", "/opt", "/private", "/tmp", "/var", "/etc", "/Volumes")}
    protected.update({home, home.parent, home / ".Trash"})
    protected.update(home / p for p in ("Applications", "Library", "Documents", "Desktop", "Downloads",
                                       "Library/Application Support"))
    if os.path.ismount(root) or str(root).casefold() in {str(p.resolve()).casefold() for p in protected}:
        raise ValueError("Refusing a protected directory.")
    marker = root / "install.json"
    if marker.is_symlink() or not stat.S_ISREG(marker.lstat().st_mode) or marker.stat().st_size > 16384:
        raise ValueError("A regular installation ownership marker is required.")
    data = json.loads(marker.read_text(encoding="utf-8"))
    expected = {"schema_version": 1, "project": "arc-raiders-crossover-compat", "engine": "engine",
                "bottle": "bottles/Steam", "bottle_name": "Steam"}
    if (not isinstance(data, dict) or type(data.get("schema_version")) is not int
            or any(data.get(k) != v for k, v in expected.items())):
        raise ValueError("The marker does not identify an owned ARC Raiders installation.")
    identity = data.get("installation_id")
    if not isinstance(identity, str) or str(uuid.UUID(identity)) != identity:
        raise ValueError("The installation marker must contain a canonical UUID.")
    engine, bottle = root / "engine", root / "bottles/Steam"
    server = engine / "bin/wineserver"
    for path in (engine, bottle, server):
        resolved = path.resolve(strict=True)
        if root not in resolved.parents:
            raise ValueError("An installation path escapes its owned root.")
    if not engine.is_dir() or not bottle.is_dir() or not server.is_file():
        raise ValueError("The private engine, bottle and wineserver must exist.")
    return root, bottle, server.resolve(strict=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    args = parser.parse_args(argv)
    try:
        root, bottle, server = owned_paths(args.destination)
        original = root.stat()
        trash = Path.home().resolve() / ".Trash"
        if trash.is_symlink():
            raise ValueError("Refusing a symlink as the Trash directory.")
        trash.mkdir(mode=0o700, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        moved = trash / ("ARCRaidersCrossOver-" + stamp + "-" + uuid.uuid4().hex[:8])
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("DYLD_", "CX_ALT_")) and k not in
               {"WINEPREFIX", "WINESERVER", "WINESERVERSOCKET", "WINELOADER", "WINEDLLPATH",
                "CX_INITIALIZED", "CX_WINELOADER", "LD_PRELOAD",
                "CX_WINEWRAPPER_ALT_LOADER_SOCKET", "CX_ROOT", "CX_BOTTLE_PATH", "CX_LOG"}}
        env.update(WINEPREFIX=str(bottle), PWD=str(root))
        result = subprocess.run([str(server), "-k"], cwd=str(root), env=env,
                                timeout=10, capture_output=True, check=False)
        if result.returncode not in (0, 1):
            raise ValueError("Private wineserver shutdown failed; installation files were preserved.")
        current = root.lstat()
        if stat.S_ISLNK(current.st_mode) or (current.st_dev, current.st_ino) != (original.st_dev, original.st_ino):
            raise ValueError("Installation root changed; refusing to move it.")
        try:
            os.rename(root, moved)
        except OSError as exc:
            if exc.errno == errno.EXDEV:
                raise ValueError("Installation preserved: Trash is on another filesystem; no files were copied or deleted.") from exc
            raise
        print("Moved installation to " + str(moved))
        print("The complete bottle is preserved locally in Trash.")
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print("Uninstall stopped: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
