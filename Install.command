#!/bin/sh
# SPDX-License-Identifier: MIT
# Finder opens this script in Terminal. No working-directory setup is needed.
set -u
arc_directory=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
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
arc_result=1
if [ -z "$arc_python" ]; then
    printf '%s\n' 'Python 3.9 or newer is required.' \
        'Install the macOS Python 3 installer from https://www.python.org/downloads/macos/,' \
        'then open Install.command again. This script does not install Python or Xcode.'
else
    printf '%s\n' 'ARC Raiders CrossOver compatibility installer' \
        'Close Steam and Windows apps in the source CrossOver bottle before continuing.'
    "$arc_python" "$arc_directory/install.py" --reveal "$@"
    arc_result=$?
fi
if [ -t 0 ]; then
    printf '\nPress Return to close this window...'
    read -r arc_answer || :
fi
exit "$arc_result"
