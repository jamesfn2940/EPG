#!/usr/bin/env python3
"""
EPG Merger - Fetches and merges multiple XMLTV EPG sources into one file.
"""

import xml.etree.ElementTree as ET
import urllib.request
import urllib.error
import gzip
import json
import os
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
CONFIG_FILE = Path("sources.json")
OUTPUT_FILE = Path(os.environ.get("OUTPUT_FILE", "epg_merged.xml"))
TIMEOUT     = int(os.environ.get("FETCH_TIMEOUT", "30"))   # seconds


def load_sources() -> list[dict]:
    """Load EPG source list from sources.json."""
    if not CONFIG_FILE.exists():
        log.error("sources.json not found. Create it from sources.example.json.")
        sys.exit(1)
    with CONFIG_FILE.open() as f:
        data = json.load(f)
    sources = data.get("sources", [])
    enabled = [s for s in sources if s.get("enabled", True)]
    log.info("Loaded %d enabled source(s) out of %d total.", len(enabled), len(sources))
    return enabled


def fetch_epg(url: str) -> bytes | None:
    """Download EPG data; handles gzip and large files."""
    log.info("  Fetching: %s", url)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "EPG-Merger/1.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            chunks = []
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
            raw = b"".join(chunks)
        if raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        return raw
    except urllib.error.HTTPError as e:
        log.warning("  HTTP %s for %s — skipped.", e.code, url)
    except urllib.error.URLError as e:
        log.warning("  URL error for %s: %s — skipped.", url, e.reason)
    except Exception as e:
        log.warning("  Failed to fetch %s: %s — skipped.", url, e)
    return None


def parse_epg(data: bytes, source_name: str) -> ET.Element | None:
    """Parse XMLTV XML; return root element or None."""
    try:
        root = ET.fromstring(data)
        if root.tag != "tv":
            log.warning("  '%s' root tag is <%s>, expected <tv> — skipped.", source_name, root.tag)
            return None
        return root
    except ET.ParseError as e:
        log.warning("  XML parse error in '%s': %s — skipped.", source_name, e)
        return None


def merge_sources(sources: list[dict]) -> ET.Element:
    """Download, parse, and merge all EPG sources into one <tv> root."""
    merged = ET.Element("tv")
    merged.set("generator-info-name", "epg-merger")
    merged.set("generator-info-url", "https://github.com/YOUR_USERNAME/YOUR_REPO")

    seen_channels: set[str] = set()
    total_channels = 0
    total_programmes = 0

    for src in sources:
        name = src.get("name", src["url"])
        log.info("Processing source: %s", name)

        raw = fetch_epg(src["url"])
        if raw is None:
            continue

        root = parse_epg(raw, name)
        if root is None:
            continue

        # Merge <channel> elements (deduplicate by id)
        ch_count = 0
        for channel in root.findall("channel"):
            cid = channel.get("id", "")
            if cid and cid not in seen_channels:
                seen_channels.add(cid)
                merged.append(channel)
                ch_count += 1

        # Merge <programme> elements
        progs = root.findall("programme")
        for prog in progs:
            merged.append(prog)

        log.info(
            "  ✓ Added %d channel(s) (%d dupes skipped) and %d programme(s).",
            ch_count,
            len(root.findall("channel")) - ch_count,
            len(progs),
        )
        total_channels  += ch_count
        total_programmes += len(progs)

    log.info(
        "Merge complete: %d unique channel(s), %d programme(s) total.",
        total_channels,
        total_programmes,
    )
    return merged


def write_output(root: ET.Element, path: Path) -> None:
    """Write merged XML to file with pretty-ish indentation."""
    ET.indent(root, space="  ")
    tree = ET.ElementTree(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(str(path), encoding="utf-8", xml_declaration=True)
    size_kb = path.stat().st_size / 1024
    log.info("Written to %s (%.1f KB).", path, size_kb)


def write_status(success: bool, total_channels: int, total_programmes: int) -> None:
    """Write a small JSON status file for badges / dashboards."""
    status = {
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "success": success,
        "channels": total_channels,
        "programmes": total_programmes,
    }
    with open("epg_status.json", "w") as f:
        json.dump(status, f, indent=2)
    log.info("Status written to epg_status.json.")


# ── Entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    log.info("=== EPG Merger started ===")
    sources = load_sources()

    if not sources:
        log.error("No enabled sources found in sources.json. Nothing to do.")
        sys.exit(1)

    merged = merge_sources(sources)

    # Collect stats from merged tree for status file
    ch_count   = len(merged.findall("channel"))
    prog_count = len(merged.findall("programme"))

    write_output(merged, OUTPUT_FILE)
    write_status(True, ch_count, prog_count)

    log.info("=== Done! ===")


if __name__ == "__main__":
    main()
