#!/usr/bin/env python3
"""Work out the next semantic version from Conventional Commits.

    feat                    -> minor bump
    fix, perf               -> patch bump
    any type with ! or a
    "BREAKING CHANGE:" footer -> major bump
    everything else         -> no release

Usage (run inside the git repository):
    next_version.py            print the next version (no "v"), or nothing if
                               there is nothing to release
    next_version.py --notes    print release notes (markdown) for those commits

The baseline is the latest reachable tag matching v<major>.<minor>.<patch>.
With no tag yet, the first release is 0.1.0.
"""

import re
import subprocess
import sys

HEADER = re.compile(r"^(?P<type>[A-Za-z]+)(?:\((?P<scope>[^)]*)\))?(?P<bang>!)?: (?P<desc>.+)$")
BREAKING_FOOTER = re.compile(r"^BREAKING[ -]CHANGE: ", re.MULTILINE)
TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")

SECTIONS = [("breaking", "Breaking changes"), ("feat", "Features"), ("fix", "Bug fixes"),
            ("perf", "Performance"), ("other", "Other changes")]


def parse(message: str):
    """Return (type, scope, description, breaking) or None if not conventional."""
    header = message.strip().split("\n", 1)[0]
    m = HEADER.match(header)
    if not m:
        return None
    breaking = bool(m["bang"]) or bool(BREAKING_FOOTER.search(message))
    return m["type"].lower(), m["scope"], m["desc"], breaking


def bump(current, messages):
    """Next (major, minor, patch) given the current one (or None), or None."""
    level = 0  # 1 patch, 2 minor, 3 major
    for message in messages:
        parsed = parse(message)
        if not parsed:
            continue
        kind, _scope, _desc, breaking = parsed
        if breaking:
            level = 3
        elif kind == "feat":
            level = max(level, 2)
        elif kind in ("fix", "perf"):
            level = max(level, 1)
    if level == 0:
        return None
    if current is None:
        return (0, 1, 0)
    major, minor, patch = current
    if level == 3:
        return (major + 1, 0, 0)
    if level == 2:
        return (major, minor + 1, 0)
    return (major, minor, patch + 1)


def notes(messages) -> str:
    groups = {key: [] for key, _ in SECTIONS}
    for message in messages:
        parsed = parse(message)
        if parsed:
            kind, scope, desc, breaking = parsed
            key = "breaking" if breaking else kind if kind in ("feat", "fix", "perf") else "other"
            line = f"**{scope}:** {desc}" if scope else desc
        else:
            key, line = "other", message.strip().split("\n", 1)[0]
        if line:
            groups[key].append(line)
    out = []
    for key, title in SECTIONS:
        if groups[key]:
            out.append(f"### {title}\n" + "\n".join(f"- {line}" for line in groups[key]))
    return "\n\n".join(out) + "\n"


def _git(*args) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def last_version():
    try:
        tag = _git("describe", "--tags", "--abbrev=0", "--match", "v[0-9]*").strip()
    except subprocess.CalledProcessError:
        return None, None
    m = TAG.match(tag)
    return (tag, tuple(int(x) for x in m.groups())) if m else (None, None)


def commit_messages(since_tag):
    rng = f"{since_tag}..HEAD" if since_tag else "HEAD"
    raw = _git("log", "--format=%B%x1e", rng)
    return [m.strip() for m in raw.split("\x1e") if m.strip()]


def main(argv) -> int:
    tag, current = last_version()
    messages = commit_messages(tag)
    if "--notes" in argv:
        print(notes(messages), end="")
        return 0
    nxt = bump(current, messages)
    if nxt:
        print(".".join(map(str, nxt)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
