#!/usr/bin/env bash
# Run after bumping __version__ in tuxgenie.py
# Updates docs/index.html to match
VER=$(python3 -c "import re; print(re.search(r'__version__ = \"(.+?)\"', open('tuxgenie.py').read()).group(1))")
sed -i "s/v[0-9]\+\.[0-9]\+\.[0-9]\+/v$VER/g" docs/index.html
echo "docs/index.html updated to v$VER"
