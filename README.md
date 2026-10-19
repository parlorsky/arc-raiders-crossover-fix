# ARC Raiders — CrossOver 26.3 compatibility fix

**Current status: startup is possible; ARAV1011 remains unresolved.** The error has occurred **in the menu** and immediately after a match was found, before entering it. It also recurred after the old research tracing server was stopped. Playable online sessions are **not confirmed**. The error does not establish which tool was detected. See [Embark's error-code reference](https://id.embark.games/arc-raiders/support/faq/165-system-integrity-violation-and-error-codes).

[Download ZIP](https://github.com/parlorsky/arc-raiders-crossover-fix/archive/refs/heads/main.zip)

Experimental compatibility patches for Apple silicon. The menu/lobby was confirmed by the user on **M5 Pro, 24 GB RAM, macOS 27.0 build 26A428, CrossOver 26.3.0.39832 / Wine 11.0, ARC Raiders Steam build 25879518** (Denuvo Anti-Cheat 7.11). FPS and other Macs remain unverified. Reaching the menu does not establish online match compatibility.

You need your own CrossOver **26.3.0.39832**, a 64-bit CrossOver bottle with Steam and ARC Raiders installed, Rosetta, and Python **3.9 or newer**. Sign in to Steam in CrossOver before installation. Python help is below if it is missing.

1. On this GitHub page, click the green **Code** button, then **Download ZIP** (or use the link above).
2. In Finder, open **Downloads**. Double-click the ZIP if needed, then open the extracted **arc-raiders-crossover-fix-main** folder. It contains **Install.command** beside this README.
3. Close Steam and Windows apps in the source CrossOver bottle using their normal menus.
4. Double-click **Install.command**. It opens Terminal and finds CrossOver and your Steam bottle automatically. The bottle can have **any name**. If several contain Steam, type the number of the one with ARC Raiders and press Return.
5. When installation finishes, Finder shows **Launch ARC Raiders.command** in the new private installation. Double-click it to start Steam and the game; you do not need the downloaded folder for later launches. The online-play limitation above still applies.

No `cd` command or manually typed bottle path is needed for this flow. The installer searches CrossOver's default bottle folder, its configured bottle locations and `CX_BOTTLE_PATH`. Steam must be installed inside the bottle's usual `Program Files (x86)/Steam` or `Program Files/Steam` folder.

The private installation is at `~/Library/Application Support/ARCRaidersCrossOver`. To find it again, press **Shift–Command–G** in Finder and paste that exact path. If it already exists, use its launch shortcut; installation does not overwrite an existing copy. Existing installations retain their copied scripts. To install updated scripts, close Steam and the game in the private copy, run its uninstall shortcut, then run the newly downloaded installer.

First launch may take several minutes. Complete Steam login yourself if requested. D3DMetal is enabled and MSync is off. On the tested Mac, clicking **OK** at the game's minimum GPU hardware warning allowed startup to continue to the menu.

**If macOS blocks the downloaded script:** this community script is not notarized. Review the source before deciding to run it. Where macOS offers it, use the per-download **System Settings → Privacy & Security → Open Anyway** flow described by [Apple](https://support.apple.com/en-us/102445). Do not disable Gatekeeper or other global protections. If macOS reports malware or damaged software, stop and investigate.

**If Finder cannot execute the `.command` file:** after resolving any security warning, open Terminal, type `/bin/sh` followed by a space, drag **Install.command** from Finder into Terminal, then press Return. The script finds its own folder, so no `cd` is needed.

**If Python is missing:** Install.command explains the problem and stops. Install Python 3 using the official [macOS installer from Python.org](https://www.python.org/downloads/macos/), then open Install.command again. Existing compatible Python installations are reused. This project does not automatically install Python, Xcode, Homebrew or another runtime.

**If no Steam bottle is found, or you want to choose one explicitly:** in Terminal, type `python3` and a space, drag **install.py** into Terminal, append ` --bottle `, then drag your actual bottle folder into Terminal and press Return. For CrossOver in a custom location, append ` --crossover ` and drag **CrossOver.app** too. `--list-bottles` lists detected bottles; `--dry-run` validates inputs without copying or starting Wine. A Python script's absolute path works from any Terminal folder.

To uninstall, close the private copy's game and Steam, then double-click **Uninstall ARC Raiders.command** in its installed folder. It stops only that private Wine server and moves the complete private installation to Trash.

The installer checks exact supported binary hashes and patches private engine/bottle copies. Your original CrossOver app, source bottle and game/anti-cheat DLLs are unchanged. The compatibility changes address TLS slot reservation and Rosetta GS handling for private executable memory, with the tested callback ABI and launcher-routing adjustments. No administrator access or global security changes are needed by these scripts.

Only scripts, patch recipes and licenses are distributed. Engine copies, Steam/account data, game files and diagnostics stay local. See [LICENSE](LICENSE), [COPYING.LIB](COPYING.LIB) and [NOTICE.md](NOTICE.md).
