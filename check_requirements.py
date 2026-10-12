#!/usr/bin/env python3
"""Check every line of a requirements.txt against PyPI.

Usage: python check_requirements.py [requirements.txt]
"""
import json
import re
import sys
import urllib.error
import urllib.request

# name, optional [extras], optional ==version (anything after is ignored)
LINE_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*(?:==\s*([^\s;,#]+))?")


def fetch_json(url):
    """Return parsed JSON, or None if PyPI answers 404."""
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def parse_line(line):
    """Return (name, version_or_None), or None for blank/comment/option lines."""
    line = line.strip()
    if not line or line.startswith(("#", "-")):
        return None
    m = LINE_RE.match(line)
    if not m:
        return None
    return m.group(1), m.group(2)


def main(path):
    with open(path) as f:
        entries = [p for p in (parse_line(l) for l in f) if p]

    missing_packages, missing_versions = [], []
    oldest = None  # (upload_time, "name==version")

    for name, version in entries:
        pkg = fetch_json(f"https://pypi.org/pypi/{name}/json")
        if pkg is None:
            missing_packages.append(name)
            continue
        if version is None:  # not pinned: nothing more to check
            continue
        rel = fetch_json(f"https://pypi.org/pypi/{name}/{version}/json")
        if rel is None:
            missing_versions.append(f"{name}=={version}")
            continue
        files = rel.get("urls") or []
        if files:
            uploaded = files[0]["upload_time"]  # e.g. 2023-05-01T12:34:56
            if oldest is None or uploaded < oldest[0]:
                oldest = (uploaded, f"{name}=={version}")

    print(f"Dependencies checked: {len(entries)}")
    print(f"Packages not on PyPI: {len(missing_packages)}")
    print(f"Versions not on PyPI: {len(missing_versions)}")
    if oldest:
        print(f"Oldest pinned release: {oldest[1]}({oldest[0][:4]})")
    else:
        print("Oldest pinned release: none")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "requirements.txt")