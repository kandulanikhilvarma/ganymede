#!/usr/bin/env bash
# Usage: bash .enhance/shoot.sh <before|after>. Needs the site on :4173.
out="$(cygpath -w "$PWD/.enhance/screens/$1")"; mkdir -p ".enhance/screens/$1"
chrome="/c/Program Files/Google/Chrome/Application/chrome.exe"
profile="$(cygpath -w "$TEMP/chr-shot")"
shot() { timeout 90 "$chrome" --headless=new --disable-gpu --hide-scrollbars \
  --user-data-dir="$profile" --virtual-time-budget=3000 --window-size="$2" \
  "--screenshot=$out/$1.png" "$3" 2>&1 | grep -c written; }
for p in index system evidence queue desk case glossary about design 404; do
  url="http://localhost:4173/$p.html"; [ "$p" = index ] && url="http://localhost:4173/"
  shot "$p-desktop" 1440,2400 "$url"
  shot "$p-mobile" 390,2400 "$url"
done
ls ".enhance/screens/$1" | wc -l
