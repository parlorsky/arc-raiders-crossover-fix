# ARC Raiders — CrossOver 26.3 compatibility fix

**Status: the anti-cheat error `ARAV1011` is resolved on the tested setup.** The private launcher applies a local compatibility tweak before every start, so the fix is re-applied automatically after a relaunch and after normal anti-cheat updates. The menu was confirmed, and an online session ran without account restrictions during testing. Other Macs, FPS and long sessions remain unverified.

> **Use at your own risk.** This is an unofficial community experiment, not endorsed by Embark, Steam or CodeWeavers. It changes local copies of compatibility and anti-cheat components inside a private installation. That may conflict with the game's terms of service and could lead to account restrictions. No bans were observed in testing, but no guarantee is given. Use it only with your own licensed copies.

## What this is — and what it is not

This is a compatibility project for running your own game on macOS. It does **not** read or modify game memory, does **not** change gameplay, and does **not** interact with other players. It only adjusts local copies of the compatibility runtime and the anti-cheat runtime inside the private installation, keeps a backup of every changed file, and can restore it at any time.

[Download ZIP](https://github.com/parlorsky/arc-raiders-crossover-fix/archive/refs/heads/main.zip)

## One-button install

1. Download the ZIP and unzip it (Finder does this automatically).
2. Open the extracted **arc-raiders-crossover-fix-main** folder and double-click **ARC Raiders.command**.
   - **First run:** creates the private copy, applies the compatibility fix and launches the game. No administrator password is needed.
   - **Later runs:** just launches the game and re-applies the local tweak.
3. If Steam asks you to sign in, do it in the game window. The first launch can take several minutes.

That is the whole flow — no Terminal commands and no manually typed paths.

**If macOS blocks the downloaded script:** this community script is not notarized. Review the source before deciding to run it. Where macOS offers it, use the per-download **System Settings → Privacy & Security → Open Anyway** flow described by [Apple](https://support.apple.com/en-us/102445). Do not disable Gatekeeper or other global protections. If macOS reports malware or damaged software, stop and investigate.

**If Finder cannot execute the `.command` file:** after resolving any security warning, open Terminal, type `/bin/sh` followed by a space, drag **ARC Raiders.command** from Finder into Terminal, then press Return. The script finds its own folder, so no `cd` is needed.

## What you need

Your own CrossOver **26.3.0.39832**, a 64-bit CrossOver bottle with Steam and ARC Raiders installed, Rosetta, and Python **3.9 or newer**. Sign in to Steam in CrossOver at least once before installation. The bottle can have **any name**; the installer finds Steam automatically. Python help is below if it is missing.

If several bottles contain Steam, the installer lists them and asks for a number. Steam must be installed inside the bottle's usual `Program Files (x86)/Steam` or `Program Files/Steam` folder.

The private installation is stored at `~/Library/Application Support/ARCRaidersCrossOver`. To find it later, press **Shift–Command–G** in Finder and paste that path. The folder contains **Launch ARC Raiders.command** (same as the one-button entry) and **Uninstall ARC Raiders.command**.

## After installation

- First launch may take several minutes. Complete Steam login yourself if requested. D3DMetal is enabled and MSync is off.
- On the tested Mac, clicking **OK** at the game's minimum GPU hardware warning allowed startup to continue to the menu.
- **If `ARAV1011` appears on the very first launch:** quit the game completely, then launch it again from the private shortcut. Anti-cheat components are installed during the first start, and the launcher applies the local tweak before every later start.
- **If `ARAV1011` returns after a game or anti-cheat update:** close the game and launch it again. The launcher re-applies the local tweak before starting Steam; no reinstall is needed.

## Troubleshooting

**If Python is missing:** the script explains the problem and stops. Install Python 3 using the official [macOS installer from Python.org](https://www.python.org/downloads/macos/), then open **ARC Raiders.command** again. Existing compatible Python installations are reused. This project does not automatically install Python, Xcode, Homebrew or another runtime.

**If no Steam bottle is found, or you want to choose one explicitly:** in Terminal, type `python3` and a space, drag **install.py** into Terminal, append ` --bottle `, then drag your actual bottle folder into Terminal and press Return. For CrossOver in a custom location, append ` --crossover ` and drag **CrossOver.app** too. `--list-bottles` lists detected bottles; `--dry-run` validates inputs without copying or starting Wine. A Python script's absolute path works from any Terminal folder.

**To update an existing private copy:** double-click **ARC Raiders.command** from the newly downloaded folder. It refreshes the helper scripts and the local tweak, then launches the game. If the binary recipe itself changed, it asks for a clean reinstall instead.

## Uninstall

Close the private copy's game and Steam, then double-click **Uninstall ARC Raiders.command** in its installed folder. It stops only that private Wine server and moves the complete private installation to Trash. Your original CrossOver app and source bottle are untouched.

## What the installer changes

The installer checks exact supported binary hashes and patches private engine and bottle copies. Your original CrossOver app, source bottle and game files are unchanged. The launcher applies local compatibility tweaks only inside its own private copy. No administrator access or global security changes are needed by these scripts.

Only scripts, patch recipes and licenses are distributed. Engine copies, Steam/account data, game files and diagnostics stay local. See [LICENSE](LICENSE), [COPYING.LIB](COPYING.LIB) and [NOTICE.md](NOTICE.md).
