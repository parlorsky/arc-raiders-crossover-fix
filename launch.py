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

DEFAULT_DESTINATION = Path.home() / "Library/Application Support/ARCRaidersCrossOver"
PROJECT = "arc-raiders-crossover-compat"
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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    args = parser.parse_args(argv)
    try:
        root, engine, bottle, mode = validate_installation(args.destination)
        if mode == "baseline":
            print("Baseline demo: compatibility patches not applied")
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
    except (OSError, ValueError, KeyError, TypeError):
        print("ARC Raiders could not start. Check or reinstall this compatibility copy.",
              file=sys.stderr)
        return 1
    print("Steam launch requested for ARC Raiders.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
