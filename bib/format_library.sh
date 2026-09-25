#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$script_dir"

if ! command -v bibtool >/dev/null 2>&1; then
  echo "bibtool is required." >&2
  echo "macOS: brew install bib-tool" >&2
  echo "Debian: apt-get install bibtool" >&2
  exit 1
fi

output_file="$(mktemp ./all.bib.tmp.XXXXXX)"
trap 'rm -f -- "$output_file"' EXIT

bibtool -r ./options.rsc -o "$output_file" ./all.bib
chmod 0644 "$output_file"
mv -f "$output_file" ./all.bib
./check_library.py
