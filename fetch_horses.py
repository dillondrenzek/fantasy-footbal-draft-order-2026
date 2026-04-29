#!/usr/bin/env python3
"""Fetch Kentucky Derby horses from the official leaderboard page and write CSV."""

from __future__ import annotations

import argparse
import csv
import html
import re
import sys
from pathlib import Path
from typing import Dict, List
from urllib.request import Request, urlopen

ODDS_PATTERN = re.compile(r"^(\d+)-(\d+)$")
SCRATCHED_ODDS = "SCR"
ROW_PATTERN = re.compile(
    r'<li class="leaderboard-show__table__row"[^>]*data-filter-race-series="(?P<series>[^"]+)"[^>]*>'
    r"(?P<body>.*?)"
    r'<div class="leaderboard-show__table__row__content"',
    re.S,
)
COLUMN_PATTERN = re.compile(
    r'<div class="leaderboard-show__table__row__heading__column">\s*<p>(?P<value>.*?)</p>\s*</div>',
    re.S,
)
TAG_PATTERN = re.compile(r"<[^>]+>")


def clean_html_text(raw_html: str) -> str:
    text = TAG_PATTERN.sub("", raw_html)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_horses_from_leaderboard_html(page_html: str, race_series: str) -> List[Dict[str, str]]:
    horses: List[Dict[str, str]] = []
    for row_match in ROW_PATTERN.finditer(page_html):
        if row_match.group("series").strip().lower() != race_series.strip().lower():
            continue

        columns_raw = COLUMN_PATTERN.findall(row_match.group("body"))
        columns = [clean_html_text(col) for col in columns_raw]
        if len(columns) < 5:
            continue

        post = columns[0]
        horse = columns[1]
        odds = re.sub(r"\s*-\s*", "-", columns[4])
        if not post.isdigit():
            continue
        if not horse:
            continue
        if not (ODDS_PATTERN.match(odds) or odds.upper() == SCRATCHED_ODDS):
            continue

        horses.append({"Post": post, "Horse": horse, "Odds": odds})

    if not horses:
        raise ValueError(
            f"No horses found for race series '{race_series}'. The page structure may have changed."
        )
    return horses


def fetch_horses_from_url(url: str, race_series: str) -> List[Dict[str, str]]:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=30) as response:
        page_html = response.read().decode("utf-8", errors="replace")
    return parse_horses_from_leaderboard_html(page_html, race_series)


def write_horses_csv(output_csv: Path, horses: List[Dict[str, str]]) -> None:
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Post", "Horse", "Odds"])
        writer.writeheader()
        writer.writerows(horses)


def print_horses_table(horses: List[Dict[str, str]]) -> None:
    headers = ["Post", "Horse", "Odds"]
    rows = [[horse["Post"], horse["Horse"], horse["Odds"]] for horse in horses]
    widths = []
    for index, header in enumerate(headers):
        max_cell = max((len(row[index]) for row in rows), default=0)
        widths.append(max(len(header), max_cell))

    divider = "+-" + "-+-".join("-" * width for width in widths) + "-+"

    def format_row(values: List[str]) -> str:
        cells = [value.ljust(widths[i]) for i, value in enumerate(values)]
        return "| " + " | ".join(cells) + " |"

    print(divider)
    print(format_row(headers))
    print(divider)
    for row in rows:
        print(format_row(row))
    print(divider)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch Kentucky Derby horses and write Post/Horse/Odds CSV."
    )
    parser.add_argument(
        "--url",
        default="https://www.kentuckyderby.com/derby-horses/",
        help="Leaderboard URL (default: Kentucky Derby horses page)",
    )
    parser.add_argument(
        "--race-series",
        default="American",
        help="Race series tab to parse (default: American)",
    )
    parser.add_argument(
        "--output",
        default="input_horses.csv",
        help="Output CSV path (default: input_horses.csv)",
    )

    args = parser.parse_args()

    try:
        horses = fetch_horses_from_url(args.url, args.race_series)
        write_horses_csv(Path(args.output), horses)
        print_horses_table(horses)
        print(f"Wrote {len(horses)} horses to {args.output}")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
