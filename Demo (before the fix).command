#!/bin/sh
# SPDX-License-Identifier: MIT
# One button for the baseline demo copy: install on the first run, then launch.
# Shows how the game behaves without the compatibility patches.
set -u
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
destination="$HOME/Library/Application Support/ARCRaidersCrossOverDemoBefore"
arc_python=""
arc_path_python=$(command -v python3 2>/dev/null || :)
for arc_candidate in "$arc_path_python" /opt/homebrew/bin/python3 /usr/local/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/Current/bin/python3 /usr/bin/python3; do
    [ -n "$arc_candidate" ] && [ -x "$arc_candidate" ] || continue
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
        'then open this script again. This script does not install Python or Xcode.'
    exit 1
fi

printf '%s\n' 'ARC Raiders — baseline demo (before the fix)' \
    'First run installs the demo copy; later runs just launch it.'

"$arc_python" "$here/app/install.py" --mode baseline --ensure --destination "$destination" || exit $?
"$arc_python" "$destination/launcher/launch.py" --destination "$destination"
arc_result=$?
if [ "$arc_result" -ne 0 ] && [ -t 0 ]; then
    printf '\nPress Return to close this window...'
    read -r arc_answer || :
fi
exit "$arc_result"
