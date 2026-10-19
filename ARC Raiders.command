#!/bin/sh
# SPDX-License-Identifier: MIT
# One button: install on the first run, refresh an existing copy, then launch.
set -u
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
destination="$HOME/Library/Application Support/ARCRaidersCrossOver"
arc_python=""
arc_path_python=$(command -v python3 2>/dev/null || :)
for arc_candidate in "$arc_path_python" /opt/homebrew/bin/python3 /usr/local/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/Current/bin/python3 /usr/bin/python3; do
    [ -n "$arc_candidate" ] && [ -x "$arc_candidate" ] || continue
    # Apple's stub may offer to install developer tools. Do not invoke it unless
    # those tools are already present; no runtime is installed automatically.
    if [ "$arc_candidate" = /usr/bin/python3 ] && ! /usr/bin/xcode-select -p >/dev/null 2>&1; then
        continue
    fi
    if "$arc_candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 9))' >/dev/null 2>&1; then
        arc_python=$arc_candidate
        break
    fi
done

if [ -z "$arc_python" ]; then
    printf '%s\n' 'Python 3.9 or newer is required.' \
        'Install the macOS Python 3 installer from https://www.python.org/downloads/macos/,' \
        'then open "ARC Raiders.command" again. This script does not install Python or Xcode.'
    exit 1
fi

printf '%s\n' 'ARC Raiders — CrossOver compatibility' \
    'First run installs a private copy; later runs just launch the game.'

"$arc_python" "$here/install.py" --ensure || exit $?
"$arc_python" "$destination/launcher/launch.py" --destination "$destination"
arc_result=$?
if [ "$arc_result" -ne 0 ] && [ -t 0 ]; then
    printf '\nPress Return to close this window...'
    read -r arc_answer || :
fi
exit "$arc_result"
