#!/usr/bin/env python3
"""Launch ARC Raiders through this owned CrossOver compatibility installation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

try:
    from compat import apply_compatibility_tweak, describe
except ImportError:  # Older installations may not ship the module yet.
    apply_compatibility_tweak = describe = None

DEFAULT_DESTINATION = Path.home() / "Library/Application Support/ARCRaidersCrossOver"
# User-editable overrides, kept at the repository root for easy editing.
OVERRIDES_FILE = Path(__file__).resolve().parent.parent / "bottle-env.conf"
PROJECT = "arc-raiders-crossover-compat"
# After a game update, the anti-cheat update service downloads a fresh runtime
# copy in the middle of a running session — after the launch-time adjustment.
# The watcher re-scans for such copies for a bounded window and adjusts them
# within seconds, before the game sends its first match survey.
WATCH_SECONDS = 1800
WATCH_INTERVAL = 10
WATCH_LOG_NAME = "compat-watch.log"
PE_SHA256 = "97110d7731ca6f6aa5e6cc7bd9c538682877cc390cdfb489bf0057e4fd64f6ed"
BASELINE_PE_SHA256 = "6dff64c00793ce92124f1316985c63783f539f26b392975c70f57637458d2387"
STEAM_EXE = r"C:\Program Files (x86)\Steam\steam.exe"
STEAM_EXES = (STEAM_EXE, r"C:\Program Files\Steam\steam.exe")


def contained(root, relative):
    path = (root / relative).resolve(strict=True)
    if not path.is_relative_to(root):
        raise ValueError("A launch target is outside the owned installation")
    return path


def validate_installation(destination):
    root = destination.expanduser().resolve(strict=True)
    if not root.is_dir() or root.stat().st_uid != os.getuid():
        raise ValueError("The installation directory is not owned by this user")
    marker = json.loads(contained(root, "install.json").read_text())
    if not isinstance(marker, dict):
        raise ValueError("The installation marker is invalid")
    mode = marker.get("mode", "patched")
    if mode not in ("patched", "baseline"):
        raise ValueError("The installation mode is invalid")
    expected_pe = BASELINE_PE_SHA256 if mode == "baseline" else PE_SHA256
    expected = dict(schema_version=1, project=PROJECT, crossover_version="26.3",
                    crossover_build="26.3.0.39832", engine="engine",
                    bottle="bottles/Steam", bottle_name="Steam", pe_sha256=expected_pe)
    if any(marker.get(k) != v for k, v in expected.items()):
        raise ValueError("The installation marker does not match this launcher")
    if marker.get("steam_exe") not in STEAM_EXES:
        raise ValueError("The Steam executable in the installation marker is invalid")
    if not isinstance(marker.get("installation_id"), str):
        raise ValueError("The installation UUID is missing")
    uuid.UUID(marker["installation_id"])
    engine = contained(root, "engine")
    bottle = contained(root, "bottles/Steam")
    if not engine.is_dir() or not bottle.is_dir():
        raise ValueError("The engine or bottle is missing")
    contained(bottle, "drive_c/" + marker["steam_exe"][3:].replace("\\", "/"))
    for image in (contained(engine, "lib/wine/x86_64-windows/ntdll.dll"),
                  contained(bottle, "drive_c/windows/system32/ntdll.dll")):
        if hashlib.sha256(image.read_bytes()).hexdigest() != expected_pe:
            raise ValueError("The installed TLS compatibility image does not match")
    return root, engine, bottle, mode


def launch_environment(root, engine, bottle):
    remove = {"WINEPREFIX", "WINESERVER", "WINELOADER", "CX_ROOT", "OLDPWD",
              "CX_INITIALIZED", "CX_WINELOADER", "WINESERVERSOCKET", "LD_PRELOAD",
              "CX_ALT_LOADER_SOCKET", "CX_WINEWRAPPER_ALT_LOADER_SOCKET"}
    # This is a standalone launch, not a child of an already initialized bottle.
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("DYLD_") and k not in remove}
    # Inject user overrides from app/bottle-env.conf when present.
    # Format: one "KEY = value" per line. Lines starting with # are comments,
    # so an option is toggled by adding or removing a single #.
    injector = OVERRIDES_FILE
    if injector.is_file():
        try:
            overrides = {}
            for raw in injector.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                line = line.split("#", 1)[0].strip()  # inline comment after a value is allowed
                if not line:
                    continue
                if "=" not in line:
                    raise ValueError(f"invalid line: {raw!r}")
                key, value = line.split("=", 1)
                key, value = key.strip(), value.strip()
                if not key or not key.isupper():
                    raise ValueError(f"invalid line: {raw!r}")
                overrides[key] = value
            env.update(overrides)
            if overrides:
                print(f"Bottle environment overrides: {', '.join(sorted(overrides))}")
        except (OSError, ValueError) as exc:
            print(f"Overrides from {injector.name} ignored: {exc}", file=sys.stderr)
    env.update(WINEPREFIX=str(bottle), CX_BOTTLE_PATH=str(root / "bottles"),
               CX_ROOT=str(engine), PWD=str(root), WINEMSYNC="0",
               CX_GRAPHICS_BACKEND="d3dmetal", CX_LOG="/dev/null",
               CX_DEBUGMSG="-all", WINEDEBUG="-all")
    return env


def start_server(root, engine, bottle, env):
    identity = bottle.stat()
    socket = (Path("/private/tmp") / (".wine-%d" % os.getuid()) /
              ("server-%x-%x" % (identity.st_dev, identity.st_ino)) / "socket")
    if socket.is_socket():
        return
    server = contained(engine, "bin/wineserver")
    subprocess.Popen([str(server), "-f", "-p"], cwd=root, env=env,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.monotonic() + 4.0
    while time.monotonic() < deadline:
        if socket.is_socket():
            return
        time.sleep(0.05)
    raise TimeoutError("The owned wineserver did not become ready")


def run_adjustment_watcher(root, bottle, duration=WATCH_SECONDS, interval=WATCH_INTERVAL):
    """Re-apply the adjustment for a bounded window while the game is running.

    Closes the race where the anti-cheat update service downloads a fresh
    runtime copy after this launcher already adjusted the previous ones.
    Returns a list of (level, message) events worth reporting.
    """
    events = []
    deadline = time.monotonic() + duration
    seen = {}
    while time.monotonic() < deadline:
        if apply_compatibility_tweak is None:
            return events
        try:
            results = apply_compatibility_tweak(bottle)
        except (OSError, ValueError) as exc:
            events.append(("warn", f"watcher adjustment error: {exc}"))
            return events
        for path, status in results:
            known = seen.get(path)
            if status == "adjusted" or (known is not None and known != status):
                events.append(("info", f"{path.name} in {path.parent.name}: {known} -> {status}"))
            seen[path] = status
        if "marker-not-found" in {status for _, status in results}:
            events.append(("warn", "a new copy lacks the known marker; "
                                   "the anti-cheat layout may have changed"))
            return events
        time.sleep(interval)
    return events


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    parser.add_argument("--watch", action="store_true",
                        help="run the mid-session adjustment watcher and exit when done")
    args = parser.parse_args(argv)
    try:
        root, engine, bottle, mode = validate_installation(args.destination)
        if args.watch:
            run_adjustment_watcher(root, bottle)
            return 0
        if mode == "baseline":
            print("Baseline demo: compatibility patches not applied")
        elif apply_compatibility_tweak is not None:
            try:
                tweak = apply_compatibility_tweak(bottle)
                print("Compatibility adjustment: " + describe(tweak))
                if not tweak:
                    print("Anti-cheat components are not installed yet; "
                          "if ARAV1011 appears on this first launch, quit the game "
                          "and launch it again.")
            except (OSError, ValueError) as exc:
                print("Compatibility adjustment skipped: " + str(exc), file=sys.stderr)
        wine = contained(engine, "bin/wine")
        env = launch_environment(root, engine, bottle)
        start_server(root, engine, bottle, env)
        steam_exe = json.loads(contained(root, "install.json").read_text())["steam_exe"]
        subprocess.Popen([str(wine), "--bottle", "Steam", "--no-update",
                          "--env", "WINEMSYNC=0", "--enable-alt-loader", "macdrv",
                          "--cx-log=/dev/null", "--debugmsg=-all", "--cx-app",
                          steam_exe, "-applaunch", "1808500"], cwd=root, env=env,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
        # Detached watcher: closes the update-during-session race so a fresh
        # copy downloaded after the launch-time adjustment is still adjusted.
        if apply_compatibility_tweak is not None and mode != "baseline":
            watch_log = (root / WATCH_LOG_NAME).open("a")
            subprocess.Popen([sys.executable, str(Path(__file__).resolve()),
                              "--watch", "--destination", str(root)],
                             stdout=watch_log, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, start_new_session=True)
            print(f"Watching for mid-session anti-cheat updates for {WATCH_SECONDS // 60} minutes.")
    except (OSError, ValueError, KeyError, TypeError):
        print("ARC Raiders could not start. Check or reinstall this compatibility copy.",
              file=sys.stderr)
        return 1
    print("Steam launch requested for ARC Raiders.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
