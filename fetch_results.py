#!/usr/bin/env python3
"""Fetch (stub) race results and compute final fantasy draft order.

Current fetch behavior is intentionally stubbed: results are read from a local CSV
(`input_race_results.csv`) until a live source is chosen.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, List, Tuple

SCRATCHED_ODDS = "SCR"
RESULTS_HEADERS = ["Post"]
ENRICHED_HEADERS = ["Finished", "Horse", "Post", "Owner", "Team"]
DRAFT_HEADERS = ["Pick", "Owner", "Horse", "Finished"]


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header row: {path}")
        return list(reader)


def write_csv_rows(path: Path, headers: List[str], rows: List[Dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def load_assignments(assignments_csv: Path) -> List[Dict[str, str]]:
    rows = read_csv_rows(assignments_csv)
    required = {"Team", "Owner", "Horse", "Post"}
    if not rows:
        raise ValueError(f"Assignments CSV is empty: {assignments_csv}")
    if not required.issubset(rows[0].keys()):
        raise ValueError(
            f"Assignments CSV must include columns: {', '.join(sorted(required))}"
        )
    return rows


def load_horses_by_post(horses_csv: Path) -> Dict[str, str]:
    rows = read_csv_rows(horses_csv)
    required = {"Post", "Horse"}
    if not rows:
        raise ValueError(f"Horses CSV is empty: {horses_csv}")
    if not required.issubset(rows[0].keys()):
        raise ValueError("Horses CSV must include columns: Post,Horse")

    return {row["Post"].strip(): row["Horse"].strip() for row in rows}


def build_stub_race_results(horses_csv: Path, output_csv: Path, field_size: int = 20) -> List[Dict[str, str]]:
    horses = read_csv_rows(horses_csv)
    required = {"Post", "Horse", "Odds"}
    if not horses:
        raise ValueError(f"Horses CSV is empty: {horses_csv}")
    if not required.issubset(horses[0].keys()):
        raise ValueError("Horses CSV must include columns: Post,Horse,Odds")

    horses_by_post = sorted(horses, key=lambda row: int(row["Post"]))
    starters: List[Dict[str, str]] = []
    for horse in horses_by_post:
        if horse["Odds"].strip().upper() == SCRATCHED_ODDS:
            continue
        starters.append(horse)
        if len(starters) == field_size:
            break

    rows: List[Dict[str, str]] = []
    for horse in starters:
        rows.append({
            "Post": horse["Post"].strip(),
        })

    write_csv_rows(output_csv, RESULTS_HEADERS, rows)
    return rows


def fetch_results_stub(results_csv: Path, horses_csv: Path) -> Tuple[List[Dict[str, str]], bool]:
    """Stub fetch: read `results_csv`; if missing, generate a starter template."""
    if results_csv.exists():
        rows = read_csv_rows(results_csv)
        if not rows:
            raise ValueError(f"Results CSV is empty: {results_csv}")
        if not set(RESULTS_HEADERS).issubset(rows[0].keys()):
            raise ValueError("Results CSV must include column: Post")
        return rows, False

    rows = build_stub_race_results(horses_csv, results_csv)
    return rows, True


def enrich_results_with_assignments(
    race_results: List[Dict[str, str]],
    assignments: List[Dict[str, str]],
    horses_by_post: Dict[str, str],
) -> List[Dict[str, str]]:
    by_post = {row["Post"].strip(): row for row in assignments}

    normalized: List[Dict[str, str]] = []
    seen_posts = set()
    for idx, row in enumerate(race_results, start=1):
        finished = str(idx)
        post = row["Post"].strip()
        horse = horses_by_post.get(post, "")

        if not post:
            raise ValueError(f"Post cannot be blank at results row {idx}.")
        if post in seen_posts:
            raise ValueError(f"Duplicate post in race results: {post}")
        seen_posts.add(post)
        if not horse:
            raise ValueError(f"Post {post!r} in race results was not found in horses CSV.")

        team_row = by_post.get(post)
        owner = team_row["Owner"].strip() if team_row else ""
        team = team_row["Team"].strip() if team_row else ""

        normalized.append(
            {
                "Finished": finished,
                "Horse": horse,
                "Post": post,
                "Owner": owner,
                "Team": team,
            }
        )

    return normalized


def build_final_draft_order(enriched_results: List[Dict[str, str]]) -> List[Dict[str, str]]:
    assigned_finishers = [row for row in enriched_results if row["Owner"] and row["Team"]]

    draft_rows: List[Dict[str, str]] = []
    for pick, row in enumerate(assigned_finishers, start=1):
        draft_rows.append(
            {
                "Pick": str(pick),
                "Owner": row["Owner"],
                "Horse": row["Horse"],
                "Finished": row["Finished"],
            }
        )
    return draft_rows


def print_table(title: str, headers: List[str], rows: List[List[str]]) -> None:
    widths = [len(h) for h in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))

    divider = "+-" + "-+-".join("-" * w for w in widths) + "-+"

    def fmt(values: List[str]) -> str:
        return "| " + " | ".join(values[i].ljust(widths[i]) for i in range(len(values))) + " |"

    print(title)
    print(divider)
    print(fmt(headers))
    print(divider)
    for row in rows:
        print(fmt(row))
    print(divider)
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch race results (stub) and determine final fantasy draft order."
    )
    parser.add_argument(
        "--results-input",
        default="input_race_results.csv",
        help="Stub race results CSV source (default: input_race_results.csv)",
    )
    parser.add_argument(
        "--horses-input",
        default="input_horses.csv",
        help="Horses CSV used to create a stub results template if missing.",
    )
    parser.add_argument(
        "--assignments-input",
        default="results/team_horse_assignments.csv",
        help="Official assignments CSV (default: results/team_horse_assignments.csv)",
    )
    parser.add_argument(
        "--results-output",
        default="race_results.csv",
        help="Official output filename for enriched race results (default: race_results.csv)",
    )
    parser.add_argument(
        "--draft-output",
        default="final_draft_order.csv",
        help="Official output filename for final draft order (default: final_draft_order.csv)",
    )
    parser.add_argument(
        "--results-dir",
        default="results",
        help="Directory for official outputs (default: results)",
    )
    parser.add_argument(
        "--official",
        action="store_true",
        help="Write official race results and final draft order CSVs to results dir.",
    )

    args = parser.parse_args()

    try:
        results_input = Path(args.results_input)
        horses_input = Path(args.horses_input)
        assignments_input = Path(args.assignments_input)
        results_dir = Path(args.results_dir)

        if not assignments_input.exists():
            raise ValueError(
                f"Assignments file not found: {assignments_input}. "
                "Run `python3 assign_teams.py --official` first."
            )

        race_results, created_stub = fetch_results_stub(results_input, horses_input)
        horses_by_post = load_horses_by_post(horses_input)
        assignments = load_assignments(assignments_input)
        enriched_results = enrich_results_with_assignments(race_results, assignments, horses_by_post)
        draft_order = build_final_draft_order(enriched_results)

        if created_stub:
            print(f"Created stub results file at {results_input} (edit as needed, then rerun).")
            print()

        print_table(
            "Fetched Race Results (with Team Mapping)",
            ENRICHED_HEADERS,
            [[r[h] for h in ENRICHED_HEADERS] for r in enriched_results],
        )
        print_table(
            "Final Draft Order",
            DRAFT_HEADERS,
            [[r[h] for h in DRAFT_HEADERS] for r in draft_order],
        )

        if args.official:
            results_dir.mkdir(parents=True, exist_ok=True)
            race_results_out = results_dir / Path(args.results_output).name
            draft_order_out = results_dir / Path(args.draft_output).name

            write_csv_rows(race_results_out, ENRICHED_HEADERS, enriched_results)
            write_csv_rows(draft_order_out, DRAFT_HEADERS, draft_order)

            print(f"Wrote official race results to {race_results_out}")
            print(f"Wrote official final draft order to {draft_order_out}")
        else:
            print("Preview mode: no files written. Re-run with --official to write results.")

        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
