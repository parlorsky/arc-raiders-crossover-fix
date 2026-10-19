#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Install the version-pinned ARC compatibility recipe into a private copy."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import uuid

PROJECT = "arc-raiders-crossover-compat"
DEFAULT_DESTINATION = Path.home() / "Library/Application Support/ARCRaidersCrossOver"
HERE = Path(__file__).resolve().parent
NATIVE_REL = Path("lib/wine/x86_64-unix/ntdll.so")
PE_REL = Path("lib/wine/x86_64-windows/ntdll.dll")
SERVER_SHA256 = "f9c4ed146c7d6dfc94334255907d4e0658218585085ca2107a5181b4deb474fc"
SERVER_SIZE = 598160
STEAM_LOCATIONS = (
    Path("drive_c/Program Files (x86)/Steam/steam.exe"),
    Path("drive_c/Program Files/Steam/steam.exe"),
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_manifest(path: Path | str) -> dict:
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or not manifest.get("patches"):
        raise ValueError("Unsupported or empty patch manifest")
    return manifest


def apply_manifest(data: bytes, manifest: dict) -> bytes:
    """Fail closed on file, hunk, bounds, or resulting-file mismatch."""
    if len(data) != manifest["input_size"] or digest(data) != manifest["input_sha256"]:
        raise ValueError(f"Unsupported input for {manifest.get('name', 'patch')}")
    result = bytearray(data)
    previous_end = 0
    for patch in manifest["patches"]:
        offset = patch["offset"]
        before = bytes.fromhex(patch["before_hex"])
        after = bytes.fromhex(patch["after_hex"])
        if (not isinstance(offset, int) or offset < previous_end or offset < 0
                or not before or len(before) != len(after) or offset + len(before) > len(data)):
            raise ValueError("Invalid, overlapping, or out-of-bounds patch")
        if data[offset:offset + len(before)] != before:
            raise ValueError(f"Patch preimage mismatch at {offset:#x}")
        result[offset:offset + len(after)] = after
        previous_end = offset + len(before)
    result = bytes(result)
    if len(result) != manifest["output_size"] or digest(result) != manifest["output_sha256"]:
        raise ValueError("Patch output hash or size mismatch")
    return result


def ensure_owned_target(path: Path | str, root: Path | str) -> Path:
    target, owned = Path(path).resolve(), Path(root).resolve()
    if target == owned or owned not in target.parents:
        raise ValueError("Refusing a target outside the private installation")
    return target


def check_hash(path: Path, expected: str, size: int | None = None) -> None:
    data = path.read_bytes()
    if (size is not None and len(data) != size) or digest(data) != expected:
        raise ValueError(f"Unsupported CrossOver file: {path.name}; this recipe requires build 26.3.0.39832")


def default_crossover() -> Path:
    for path in (Path.home() / "Applications/CrossOver.app", Path("/Applications/CrossOver.app")):
        if path.is_dir():
            return path
    return Path("/Applications/CrossOver.app")


def find_steam(bottle: Path) -> str | None:
    """Find a local Steam install without relying on the bottle's name."""
    for relative in STEAM_LOCATIONS:
        candidate = bottle / relative
        if candidate.is_file() and candidate.resolve().is_relative_to(bottle.resolve()):
            return "C:\\" + str(relative.relative_to("drive_c")).replace("/", "\\")
    return None


def discover_bottles(home: Path | None = None, environ: dict | None = None) -> list[Path]:
    """Read normal CrossOver locations only; never start Wine or scan the disk."""
    home = home or Path.home()
    environ = os.environ if environ is None else environ
    roots = [home / "Library/Application Support/CrossOver/Bottles"]
    roots.extend(Path(p).expanduser() for p in environ.get("CX_BOTTLE_PATH", "").split(os.pathsep) if p)
    preferences = home / "Library/Preferences/com.codeweavers.CrossOver.plist"
    try:
        settings = plistlib.loads(preferences.read_bytes())
        if isinstance(settings, dict):
            configured = settings.get("BottleDir")
            if isinstance(configured, str) and configured:
                roots.append(Path(configured).expanduser())
            managed = settings.get("ManagedBottleDirs", [])
            if isinstance(managed, list):
                roots.extend(Path(p).expanduser() for p in managed if isinstance(p, str) and p)
    except (OSError, ValueError, plistlib.InvalidFileException):
        pass
    found = set()
    for root in roots:
        try:
            candidates = [root] if (root / "cxbottle.conf").is_file() else root.iterdir()
            for candidate in candidates:
                if (candidate / "cxbottle.conf").is_file() and find_steam(candidate):
                    found.add(candidate.resolve())
        except OSError:
            continue
    return sorted(found, key=lambda path: (path.name.casefold(), str(path)))


def choose_bottle(requested: Path | None, *, interactive: bool | None = None,
                  candidates: list[Path] | None = None, input_func=None) -> Path:
    if requested is not None:
        return requested.expanduser().resolve()
    candidates = discover_bottles() if candidates is None else candidates
    if not candidates:
        raise ValueError("No Steam bottle found. Install Steam in CrossOver, or use --bottle with its full folder path.")
    if len(candidates) == 1:
        print(f"Found Steam bottle: {candidates[0].name}")
        return candidates[0]
    print("More than one CrossOver bottle contains Steam:")
    for number, path in enumerate(candidates, 1):
        print(f"  {number}. {path.name}  ({path})")
    interactive = sys.stdin.isatty() if interactive is None else interactive
    if not interactive:
        raise ValueError("Choose a bottle with --bottle '/full/path/to/bottle'; no input was requested in this non-interactive session.")
    read = input_func or input
    while True:
        try:
            answer = read(f"Choose the bottle with ARC Raiders [1-{len(candidates)}], or q to cancel: ").strip()
        except EOFError:
            raise ValueError("No bottle selected. Run again with --bottle '/full/path/to/bottle'.") from None
        if answer.lower() == "q":
            raise ValueError("Installation cancelled.")
        if answer.isdigit() and 1 <= int(answer) <= len(candidates):
            return candidates[int(answer) - 1]
        print("Enter one of the listed numbers, or q.")


def inspect_sources(args: argparse.Namespace) -> dict:
    app, bottle = args.crossover.expanduser().resolve(), args.bottle.expanduser().resolve()
    destination = args.destination.expanduser().absolute()
    if args.destination.is_symlink():
        raise ValueError("Destination must not be a symlink")
    if destination.exists():
        raise ValueError("Destination already exists; nothing was overwritten. Open its 'Launch ARC Raiders.command'. "
                         "For a fresh installation, close its game and Steam and use its 'Uninstall ARC Raiders.command' first.")
    if platform.system() != "Darwin":
        raise ValueError("This installer requires macOS on Apple silicon")
    arm = platform.machine() == "arm64"
    if not arm:
        arm = subprocess.run(
            ["/usr/sbin/sysctl", "-n", "hw.optional.arm64"],
            capture_output=True, text=True, check=False,
        ).stdout.strip() == "1"
    if not arm:
        raise ValueError("This recipe was built for Apple silicon with Rosetta")
    engine = app / "Contents/SharedSupport/CrossOver"
    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    if info.get("CFBundleVersion") != "26.3.0.39832":
        raise ValueError("Only CrossOver build 26.3.0.39832 is accepted")
    for source in (app, bottle):
        if source == destination or source in destination.resolve().parents:
            raise ValueError("Destination must not be inside the original app or bottle")
        if destination.resolve() in source.parents:
            raise ValueError("Destination must not contain the original app or bottle")
    if not (bottle / "cxbottle.conf").is_file():
        raise ValueError("Not a CrossOver bottle directory")
    native = load_manifest(HERE / "patches/ntdll-native.json")
    pe = load_manifest(HERE / "patches/ntdll-pe.json")
    # Validate both full input files and every patch before creating a directory.
    apply_manifest((engine / NATIVE_REL).read_bytes(), native)
    apply_manifest((engine / PE_REL).read_bytes(), pe)
    apply_manifest((bottle / "drive_c/windows/system32/ntdll.dll").read_bytes(), pe)
    check_hash(engine / "bin/wineserver", SERVER_SHA256, SERVER_SIZE)
    steam_exe = find_steam(bottle)
    if not steam_exe:
        raise ValueError("Steam.exe was not found inside this bottle's Program Files or Program Files (x86) folder")
    return {
        "app": app, "engine": engine, "bottle": bottle, "destination": destination,
        "native": native, "pe": pe, "build": info["CFBundleVersion"],
        "version": info.get("CFBundleShortVersionString", "26.3"), "steam_exe": steam_exe,
    }


def copy_tree(source: Path, target: Path) -> None:
    """Prefer APFS clones. Neither command follows directory symlinks."""
    copied = subprocess.run(
        ["/bin/cp", "-cR", str(source), str(target)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    )
    if copied.returncode:
        if target.exists():
            shutil.rmtree(target)  # Only this newly-created staging tree.
        subprocess.run(["/usr/bin/ditto", str(source), str(target)], check=True)


def atomic_bytes(path: Path, data: bytes, mode: int = 0o644) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=".arc-patch-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def set_config_value(text: str, section: str, key: str, value: str) -> str:
    pattern = re.compile(r"(?ms)^\[" + re.escape(section) + r"\][^\n]*\n(.*?)(?=^\[|\Z)")
    match = pattern.search(text)
    line = f'"{key}" = "{value}"'
    if match is None:
        return text.rstrip() + f"\n\n[{section}]\n{line}\n"
    body = match.group(1)
    entry = re.compile(r'(?m)^\s*"' + re.escape(key) + r'"\s*=.*$')
    body = entry.sub(lambda _: line, body) if entry.search(body) else body.rstrip() + "\n" + line + "\n\n"
    return text[:match.start(1)] + body + text[match.end(1):]


def configure_private_bottle(bottle: Path) -> None:
    conf = ensure_owned_target(bottle / "cxbottle.conf", bottle)
    text = conf.read_text(encoding="utf-8")
    # The wrapper applies this section after inheriting the parent environment.
    # Keep user settings, but do not restore injection or child-only routing state.
    sections = re.compile(r"(?ms)^(\[EnvironmentVariables\][^\n]*\n)(.*?)(?=^\[|\Z)")
    inherited = re.compile(
        r'(?m)^[ \t]*"(?:DYLD_[^"\r\n]*|LD_PRELOAD|CX_INITIALIZED|CX_WINELOADER|WINESERVERSOCKET)"'
        r'[ \t]*=.*(?:\n|\Z)'
    )
    text = sections.sub(lambda match: match[1] + inherited.sub("", match[2]), text)
    for key, value in {
        "WINEMSYNC": "0", "CX_GRAPHICS_BACKEND": "d3dmetal",
        "D3DM_ENABLE_METALFX": "0", "DXMT_ENABLE_NVEXT": "0",
    }.items():
        text = set_config_value(text, "EnvironmentVariables", key, value)
    for key in ("MenuMode", "AssocMode"):
        text = set_config_value(text, "Bottle", key, "ignore")
    atomic_bytes(conf, text.encode("utf-8"))
    # Localize personal-folder links in the COPY; never access their contents.
    users = ensure_owned_target(bottle / "drive_c/users", bottle)
    for profile in users.iterdir():
        if not profile.is_dir() or profile.is_symlink():
            continue
        for relative in ("Documents", "Downloads", "Desktop/My Mac Desktop"):
            link = profile / relative
            ensure_owned_target(link.parent, bottle)
            if link.is_symlink():
                link.unlink()
                link.mkdir()


def sign_private(path: Path) -> None:
    subprocess.run(
        ["/usr/bin/codesign", "--force", "--sign", "-", "--options", "0", str(path)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )
    subprocess.run(
        ["/usr/bin/codesign", "--verify", "--strict", str(path)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )


def install_private(inputs: dict, *, baseline: bool = False) -> Path:
    destination = inputs["destination"]
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".arc-install-", dir=destination.parent))
    try:
        engine, bottle = staging / "engine", staging / "bottles/Steam"
        print("Copying the local runtime and Steam bottle (APFS clone when available)...")
        copy_tree(inputs["engine"], engine)
        bottle.parent.mkdir()
        copy_tree(inputs["bottle"], bottle)
        native_path = ensure_owned_target(engine / NATIVE_REL, engine)
        pe_path = ensure_owned_target(engine / PE_REL, engine)
        system32 = ensure_owned_target(bottle / "drive_c/windows/system32", bottle)
        if not baseline:
            atomic_bytes(native_path, apply_manifest(native_path.read_bytes(), inputs["native"]), native_path.stat().st_mode & 0o777)
            atomic_bytes(pe_path, apply_manifest(pe_path.read_bytes(), inputs["pe"]), pe_path.stat().st_mode & 0o777)
            # Replace this FILE, not a symlink that could refer to the source.
            atomic_bytes(system32 / "ntdll.dll", apply_manifest((system32 / "ntdll.dll").read_bytes(), inputs["pe"]))
        configure_private_bottle(bottle)
        if not baseline:
            try:
                from anticheat import describe, ensure_runtime_tweak
                tweak = ensure_runtime_tweak(bottle)
                if tweak:
                    print("Anti-cheat compatibility tweak: " + describe(tweak))
            except (ImportError, OSError, ValueError):
                print("Anti-cheat compatibility tweak will be applied by the launcher.")
        if not baseline:
            sign_private(native_path)
        server = ensure_owned_target(engine / "bin/wineserver", engine)
        check_hash(server, SERVER_SHA256, SERVER_SIZE)
        sign_private(server)
        image_hash = inputs["pe"]["input_sha256" if baseline else "output_sha256"]
        check_hash(pe_path, image_hash)
        check_hash(system32 / "ntdll.dll", image_hash)
        if baseline:
            check_hash(native_path, inputs["native"]["input_sha256"])
        marker = {
            "schema_version": 1, "project": PROJECT, "installation_id": str(uuid.uuid4()),
            "mode": "baseline" if baseline else "patched",
            "crossover_version": inputs["version"], "crossover_build": inputs["build"],
            "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "engine": "engine", "bottle": "bottles/Steam", "bottle_name": "Steam",
            "steam_exe": inputs["steam_exe"],
            "native_pre_sign_sha256": inputs["native"]["input_sha256" if baseline else "output_sha256"],
            "pe_sha256": image_hash,
        }
        (staging / "install.json").write_text(json.dumps(marker, indent=2) + "\n", encoding="utf-8")
        launcher = staging / "launcher"
        launcher.mkdir()
        for filename in ("install.py", "launch.py", "uninstall.py", "anticheat.py"):
            shutil.copy2(HERE / filename, launcher / filename)
        python = shlex.quote(str(Path(sys.executable).resolve()))
        for name, script in (
            ("Launch BEFORE demo.command" if baseline else "Launch ARC Raiders.command", "launch.py"),
            ("Uninstall ARC Raiders.command", "uninstall.py"),
        ):
            command = ("#!/bin/sh\n" + python + " " + shlex.quote(str(destination / "launcher" / script))
                       + " --destination " + shlex.quote(str(destination))
                       + '\nresult=$?\nif [ "$result" -ne 0 ] && [ -t 0 ]; then\n'
                         '  printf "\\nPress Return to close this window..."\n'
                         '  read -r answer\nfi\nexit "$result"\n')
            shortcut = staging / name
            shortcut.write_text(command, encoding="utf-8")
            shortcut.chmod(0o700)
        if destination.exists():
            raise ValueError("Destination appeared during installation; refusing to overwrite it")
        staging.rename(destination)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    return destination


def update_existing(destination: Path) -> Path:
    """Refresh helper scripts and the local tweak in an existing private copy."""
    root = destination.expanduser().resolve(strict=True)
    if not root.is_dir() or root.stat().st_uid != os.getuid():
        raise ValueError("The installation directory is not owned by this user")
    marker = json.loads((root / "install.json").read_text(encoding="utf-8"))
    expected = dict(schema_version=1, project=PROJECT, engine="engine",
                    bottle="bottles/Steam", bottle_name="Steam")
    if not isinstance(marker, dict) or any(marker.get(k) != v for k, v in expected.items()):
        raise ValueError("The existing folder is not an ARC Raiders compatibility installation")
    launcher = root / "launcher"
    if launcher.is_symlink() or not launcher.is_dir():
        raise ValueError("The existing installation has no launcher folder")
    for filename in ("install.py", "launch.py", "uninstall.py", "anticheat.py"):
        shutil.copy2(HERE / filename, launcher / filename)
    # The refreshed launcher must accept the existing images.  If this recipe
    # changed the binary patches, a full reinstall is required instead.
    import launch as launch_module
    launch_module.validate_installation(root)
    from anticheat import describe, ensure_runtime_tweak
    tweak = ensure_runtime_tweak(root / "bottles/Steam")
    if tweak:
        print("Anti-cheat compatibility tweak: " + describe(tweak))
    return root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crossover", type=Path, default=default_crossover())
    parser.add_argument("--bottle", type=Path, help="Source bottle folder; otherwise discover Steam bottles automatically")
    parser.add_argument("--list-bottles", action="store_true", help="List discovered Steam bottles without changing anything")
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    parser.add_argument("--dry-run", action="store_true", help="Only validate the original inputs; write nothing")
    parser.add_argument("--reveal", action="store_true", help="Show the installed launch shortcut in Finder after installation")
    parser.add_argument("--ensure", action="store_true",
                        help="Install fresh, or refresh an existing private copy")
    args = parser.parse_args(argv)
    try:
        if args.list_bottles:
            bottles = discover_bottles()
            for path in bottles:
                print(f"{path.name}: {path}")
            if not bottles:
                print("No Steam bottles found in the normal CrossOver locations.")
            return 0
        if args.ensure and args.destination.expanduser().exists():
            installed = update_existing(args.destination)
            shortcut = installed / "Launch ARC Raiders.command"
            print(f"Updated private copy: {installed}")
            print(f"Double-click: {shortcut}")
            if args.reveal:
                subprocess.run(["/usr/bin/open", "-R", str(shortcut)], check=False,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return 0
        args.bottle = choose_bottle(args.bottle)
        print(f"Source bottle: {args.bottle}")
        inputs = inspect_sources(args)
        print(f"Validated CrossOver {inputs['build']}: native DLL, PE DLL, bottle DLL, wineserver.")
        if args.dry_run:
            print("Dry run passed. No files changed.")
            return 0
        installed = install_private(inputs)
        print(f"Installed private copy: {installed}")
        shortcut = installed / "Launch ARC Raiders.command"
        print(f"Double-click: {shortcut}")
        if args.reveal:
            subprocess.run(["/usr/bin/open", "-R", str(shortcut)], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return 0
    except KeyboardInterrupt:
        print("\nInstallation cancelled.", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        # Do not emit captured child output; it may contain user paths or args.
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
