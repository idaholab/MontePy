#!/usr/bin/env python
"""Developer tool: validate and look up references into the MCNP manuals.

Sphinx's linkcheck can't validate ``#section.5.2`` or ``#page=55`` fragments of
the manual PDFs, so this script does it from local copies of the PDFs.

It needs ``mutool`` (MuPDF) and ``pdftotext``/``pdfinfo`` (poppler) on the PATH.
The manuals are defined in ``doc/source/conf.py`` (``MCNP_MANUAL_PDFS``).

Commands (run from anywhere)::

    python doc/check_manual_refs.py download          # fetch the PDFs once
    python doc/check_manual_refs.py check             # validate every reference
    python doc/check_manual_refs.py check -v          # also show what each resolves to
    python doc/check_manual_refs.py search "Cell Cards"   # find a heading in each manual
    python doc/check_manual_refs.py map topics.json   # resolve headings in every manual

``check`` scans ``montepy/**/*.py`` for ``.. mcnp-manuals::`` fields and for
``:manual<ver>:`` roles. It also checks that ``doc/source/index.rst`` links each manual
PDF exactly once, with "<name> User Manual" as the link text. It exits non-zero if any reference doesn't exist, or if
a ``#page=`` value is outside the PDF. For ``#page=`` links the value must be the
*physical* page index (what a PDF viewer loads), not the printed page number.

The PDFs are cached in ``$MONTEPY_MANUAL_DIR`` or ``~/.cache/montepy/mcnp_manuals``.
"""

from __future__ import annotations

import argparse
import functools
import os
import re
import runpy
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONF = ROOT / "doc" / "source" / "conf.py"
DEFAULT_CACHE = Path.home() / ".cache" / "montepy" / "mcnp_manuals"

_conf = runpy.run_path(str(CONF))
PDFS: dict[str, str] = _conf["MCNP_MANUAL_PDFS"]
NAMES: dict[str, str] = _conf["_MCNP_VERSION_NAMES"]
ANCHORED: tuple[str, ...] = _conf["_MCNP_ANCHOR_VERSIONS"]
BASE_URL: str = _conf["_MCNP_PDF_URL"]
KINDS: dict[str, tuple[str, str]] = _conf["_MCNP_ANCHOR_KINDS"]

KEY_RE = re.compile(
    "^(%s)(%s)?$"
    % (
        "|".join(sorted(map(re.escape, PDFS), key=len, reverse=True)),
        "|".join(k for k in KINDS if k),
    )
)
FIELD_RE = re.compile(r"^(\s+):(\w+):\s*(\S+)\s*$")
ROLE_RE = re.compile(r":manual(\w+?):`([^`]+)`")


def cache_dir() -> Path:
    return Path(os.environ.get("MONTEPY_MANUAL_DIR", DEFAULT_CACHE))


def pdf_path(version: str) -> Path:
    return cache_dir() / f"{version}.pdf"


def _run(cmd: list[str]) -> str:
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True, check=True, errors="replace"
        ).stdout
    except FileNotFoundError:
        sys.exit(f"Required tool not found: {cmd[0]} (see the module docstring).")
    except subprocess.CalledProcessError as e:
        sys.exit(f"{' '.join(cmd)} failed: {e.stderr.strip()}")


def require_pdf(version: str) -> Path:
    path = pdf_path(version)
    if not path.exists():
        sys.exit(f"{path} is missing. Run: python doc/check_manual_refs.py download")
    return path


@functools.lru_cache(maxsize=None)
def page_count(version: str) -> int:
    out = _run(["pdfinfo", str(require_pdf(version))])
    return int(re.search(r"^Pages:\s+(\d+)", out, re.M).group(1))


@functools.lru_cache(maxsize=None)
def all_pages(version: str) -> list[str]:
    """Text of every physical page (index 0 is page 1)."""
    out = _run(["pdftotext", "-layout", str(require_pdf(version)), "-"])
    pages = out.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    return pages


@functools.lru_cache(maxsize=None)
def outline(version: str) -> list[tuple[str, str]]:
    """``(title, destination)`` for each outline entry."""
    out = _run(["mutool", "show", str(require_pdf(version)), "outline"])
    entries = []
    for line in out.splitlines():
        m = re.match(r'^\|\s*"(.*)"\s+#(\S+)', line)
        if m:
            entries.append((m.group(1).strip(), m.group(2)))
    return entries


@functools.lru_cache(maxsize=None)
def named_destinations(version: str) -> frozenset[str]:
    out = _run(["mutool", "show", str(require_pdf(version)), "grep"])
    return frozenset(
        re.findall(
            r"\(((?:chapter|part|section|subsection|subsubsection)\.[^)\s]+)\)", out
        )
    )


_NUMBERED = re.compile(r"^(\d+(\.\d+)+|[A-Z]\.)\s+\S")


def page_summary(version: str, page: int) -> str:
    """What a page link lands on: the headings on the page, else its first lines."""
    lines = [l.strip() for l in all_pages(version)[page - 1].splitlines() if l.strip()]
    heads = [
        l
        for l in lines
        if _NUMBERED.match(l) and not _LEADERS.search(l) and not l[-1].isdigit()
    ]
    return (" | ".join(heads) if heads else " | ".join(lines[:3]))[:160]


def check_ref(version: str, suffix: str, value: str) -> tuple[bool, str]:
    """Return ``(ok, description of what the reference resolves to)``."""
    if version in ANCHORED:
        dest = f"{KINDS[suffix][0]}.{value}"
        if dest not in named_destinations(version):
            return False, f"no named destination '{dest}' in {NAMES[version]}"
        titles = [t for t, d in outline(version) if d == f"nameddest={dest}"]
        return True, titles[0] if titles else "(exists; not in the PDF outline)"
    if suffix:
        return False, f"{NAMES[version]} only supports page links, not '{suffix}'"
    if not value.isdigit():
        return False, f"page must be a number, got '{value}'"
    page = int(value)
    if not 1 <= page <= page_count(version):
        return False, f"page {page} outside 1..{page_count(version)}"
    return True, page_summary(version, page)


def find_refs(paths: list[Path]):
    """Yield ``(file, line number, key, value)`` for every manual reference."""
    for path in paths:
        in_block = False
        for n, line in enumerate(path.read_text().splitlines(), 1):
            if ".. mcnp-manuals::" in line:
                in_block = True
                continue
            m = FIELD_RE.match(line)
            if in_block and m:
                yield path, n, m.group(2), m.group(3)
                continue
            if in_block and line.strip():
                in_block = False
            for m in ROLE_RE.finditer(line):
                yield path, n, m.group(1), m.group(2)


_LEADERS = re.compile(r"\.{3,}|(?:\.\s){3,}")
_HEADING = re.compile(
    r"^(?P<num>(?:[A-Z]\.(?:\d+\.?)*|\d+(?:\.\d+)*\.?))?\s*(?P<title>\S.*?)\s*$"
)


def find_headings(version: str, title_re: str) -> list[tuple[int, str, str]]:
    """Find heading lines matching ``title_re``.

    Returns ``(physical page, section number or '', full line)`` in page order.
    Table of contents lines (dot leaders, trailing page numbers) are skipped.
    """
    rx = re.compile(title_re, re.I)
    found = []
    for number, text in enumerate(all_pages(version), 1):
        for line in text.splitlines():
            s = line.strip()
            if not s or len(s) > 90 or _LEADERS.search(s) or s[-1].isdigit():
                continue
            m = _HEADING.match(s)
            if m and rx.search(m.group("title")) and len(m.group("title")) < 80:
                found.append((number, (m.group("num") or "").rstrip("."), s))
    return found


def anchor_key(num: str) -> tuple[str, str] | None:
    """The ``(role suffix, value)`` for a section number in an anchored manual."""
    depth = num.count(".")
    if not num or not num[0].isdigit() or depth not in (1, 2, 3):
        return None
    return {1: "sec", 2: "", 3: "sub"}[depth], num


def cmd_map(args):
    """Resolve topics (heading regexes) to references in every manual."""
    import json

    topics = json.loads(Path(args.topics).read_text())
    for topic, spec in topics.items():
        print(f"## {topic}")
        for version in args.versions or PDFS:
            if not pdf_path(version).exists():
                continue
            title_re = spec.get(version, spec["title"])
            if title_re is None:
                continue
            hits = find_headings(version, title_re)
            shown = []
            for page, num, line in hits:
                if version in ANCHORED:
                    k = anchor_key(num)
                    if (
                        k is None
                        or f"{KINDS[k[0]][0]}.{k[1]}" not in named_destinations(version)
                    ):
                        continue
                    shown.append(f"{version}{k[0]}:{k[1]} (p{page}) {line!r}")
                else:
                    shown.append(f"{version}:{page} {line!r}")
            for item in shown[: args.limit]:
                print(f"  {item}")
            if not shown:
                print(f"  {version}: -- none --")
            elif len(shown) > args.limit:
                print(f"  {version}: ... +{len(shown) - args.limit} more")


INDEX = ROOT / "doc" / "source" / "index.rst"
_INDEX_LINK = re.compile(r"`([^`<]+?)\s*<(" + re.escape(BASE_URL) + r"[^>\s]+)>`_")


def check_index(index: Path = INDEX) -> list[str]:
    """Check that the index lists each manual PDF exactly once, as "<name> User Manual".

    Sphinx doesn't complain about a repeated list item, and linkcheck only
    requests each URL once, so duplicates would otherwise go unnoticed.
    """
    links: dict[str, list[str]] = {}
    for text, url in _INDEX_LINK.findall(index.read_text()):
        links.setdefault(url, []).append(text.strip())
    problems = []
    for version, pdf in PDFS.items():
        texts = links.pop(BASE_URL + pdf, [])
        if not texts:
            problems.append(f"{NAMES[version]}: not linked in {index.name}")
        elif len(texts) > 1:
            problems.append(
                f"{NAMES[version]}: linked {len(texts)} times in {index.name}"
            )
        elif texts[0] != f"{NAMES[version]} User Manual":
            problems.append(f"{NAMES[version]}: link text is '{texts[0]}'")
    for url in links:
        problems.append(f"{index.name} links {url}, which is not in MCNP_MANUAL_PDFS")
    return problems


def cmd_download(args):
    cache_dir().mkdir(parents=True, exist_ok=True)
    first = True
    for version, name in PDFS.items():
        dest = pdf_path(version)
        if dest.exists():
            continue
        if not first:
            time.sleep(2)  # be gentle with mcnp.lanl.gov
        first = False
        print(f"Downloading {NAMES[version]} -> {dest}")
        urllib.request.urlretrieve(BASE_URL + name, dest)


def cmd_check(args):
    paths = [Path(p) for p in args.paths] or sorted((ROOT / "montepy").rglob("*.py"))
    bad = total = 0
    if not args.paths:  # the index only matters for a full check
        for problem in check_index():
            bad += 1
            print(f"FAIL {INDEX.relative_to(ROOT)}: {problem}")
    for path, line, key, value in find_refs(paths):
        total += 1
        m = KEY_RE.match(key)
        rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        if m is None:
            bad += 1
            print(f"FAIL {rel}:{line}: unknown manual key '{key}'")
            continue
        ok, info = check_ref(m.group(1), m.group(2) or "", value)
        bad += not ok
        if not ok or args.verbose:
            print(f"{'ok  ' if ok else 'FAIL'} {rel}:{line}: {key} {value} -> {info}")
    print(f"{total} references checked, {bad} failed.")
    if total == 0:
        sys.exit("No references found: check the paths.")
    sys.exit(1 if bad else 0)


def cmd_search(args):
    pattern = re.compile(args.pattern, re.I)
    for version in args.versions or PDFS:
        if not pdf_path(version).exists():
            print(f"== {NAMES[version]}: PDF not downloaded")
            continue
        print(f"== {NAMES[version]}")
        hits = 0
        if version in ANCHORED:
            for title, dest in outline(version):
                if pattern.search(title):
                    print(f"   outline: {title!r}  #{dest}")
                    hits += 1
        for number, text in enumerate(all_pages(version), 1):
            for line in text.splitlines():
                s = line.strip()
                # Heading-like lines only: short, so body text doesn't swamp the output.
                if len(s) < args.max_line and pattern.search(s):
                    print(f"   page {number}: {s}")
                    hits += 1
                    break
            if hits >= args.limit:
                print("   ... (limit reached)")
                break


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("download", help="download missing PDFs").set_defaults(
        f=cmd_download
    )
    c = sub.add_parser("check", help="validate references")
    c.add_argument("paths", nargs="*", help="files to scan (default montepy/**/*.py)")
    c.add_argument("-v", "--verbose", action="store_true")
    c.set_defaults(f=cmd_check)
    s = sub.add_parser("search", help="find headings matching a regex")
    s.add_argument("pattern")
    s.add_argument("--versions", nargs="*", choices=list(PDFS))
    s.add_argument("--limit", type=int, default=12)
    s.add_argument("--max-line", type=int, default=70)
    s.set_defaults(f=cmd_search)
    mp = sub.add_parser("map", help="resolve topics from a JSON file in every manual")
    mp.add_argument(
        "topics", help='JSON: {"topic": {"title": regex, "<ver>": regex|null}}'
    )
    mp.add_argument("--limit", type=int, default=3)
    mp.add_argument("--versions", nargs="*", choices=list(PDFS))
    mp.set_defaults(f=cmd_map)
    args = p.parse_args()
    args.f(args)


if __name__ == "__main__":
    main()
