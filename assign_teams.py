#!/usr/bin/env python3
"""Assign fantasy teams to the 12 longest-shot horses from CSV files.

Uses Python's cryptographically secure RNG (`secrets.SystemRandom`).
"""

from __future__ import annotations

import csv
import re
import secrets
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Tuple

ODDS_PATTERN = re.compile(r"^(\d+)-(\d+)$")
SCRATCHED_ODDS = "SCR"
FINISH_COL = "2025 Finish"


def parse_fractional_odds(odds: str) -> tuple[int, int]:
    """Parse odds in the form 'X-Y' and return (X, Y) as ints."""
    match = ODDS_PATTERN.match(odds.strip())
    if not match:
        raise ValueError(f"Invalid odds format: {odds!r}. Expected format like '30-1'.")
    return int(match.group(1)), int(match.group(2))


def is_scratched(odds: str) -> bool:
    return odds.strip().upper() == SCRATCHED_ODDS


def read_horses(input_csv: Path) -> List[Dict[str, str]]:
    with input_csv.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required_cols = {"Post", "Horse", "Odds"}
        if reader.fieldnames is None or not required_cols.issubset(set(reader.fieldnames)):
            raise ValueError("Input CSV must include headers: Post,Horse,Odds")
        rows = list(reader)
    if len(rows) < 12:
        raise ValueError("Input CSV must contain at least 12 horses.")
    return rows


def select_longest_shots(horses: List[Dict[str, str]], count: int = 12) -> List[Dict[str, str]]:
    # Derby field cap: first 20 assignable (non-SCR) horses by post number.
    horses_by_post = sorted(horses, key=lambda row: int(row["Post"]))
    assignable_field: List[Dict[str, str]] = []
    for horse in horses_by_post:
        if is_scratched(horse["Odds"]):
            continue
        assignable_field.append(horse)
        if len(assignable_field) == 20:
            break

    if len(assignable_field) < count:
        raise ValueError(
            f"Need at least {count} assignable horses. Found {len(assignable_field)} non-SCR horses."
        )

    # Higher X in X-1 means longer odds (lower implied chance).
    return sorted(
        assignable_field,
        key=lambda row: parse_fractional_odds(row["Odds"])[0] / parse_fractional_odds(row["Odds"])[1],
        reverse=True,
    )[:count]


def read_teams(input_csv: Path) -> List[Dict[str, str]]:
    with input_csv.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required_cols = {"Team", "Owner", FINISH_COL}
        if reader.fieldnames is None or not required_cols.issubset(set(reader.fieldnames)):
            raise ValueError(f"Teams CSV must include headers: Team,Owner,{FINISH_COL}")
        rows = list(reader)

    if len(rows) != 12:
        raise ValueError("Teams CSV must contain exactly 12 teams.")

    team_names = [row["Team"].strip() for row in rows]
    if any(not name for name in team_names):
        raise ValueError("Team names cannot be blank.")
    if len(set(team_names)) != 12:
        raise ValueError("Team names must be unique.")

    finishes: List[int] = []
    for row in rows:
        finish_raw = row.get(FINISH_COL, "").strip()
        if not finish_raw:
            raise ValueError(f"{FINISH_COL} cannot be blank.")
        if not finish_raw.isdigit():
            raise ValueError(f"{FINISH_COL} must be numeric. Found: {finish_raw!r}")
        finishes.append(int(finish_raw))

    if len(set(finishes)) != 12:
        raise ValueError(f"{FINISH_COL} values must be unique.")

    return sorted(rows, key=lambda row: int(row[FINISH_COL].strip()))


def assign_teams_to_horses(
    teams: List[Dict[str, str]], horses: List[Dict[str, str]]
) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    if len(teams) != 12 or len(horses) != 12:
        raise ValueError("Exactly 12 teams and 12 horses are required.")

    rng = secrets.SystemRandom()
    remaining_horses = horses[:]

    assignments = []
    draw_log = []
    for step, team_row in enumerate(teams, start=1):
        pool_size = len(remaining_horses)
        draw_index = rng.randrange(pool_size)
        horse = remaining_horses.pop(draw_index)

        draw_log.append(
            {
                "Step": str(step),
                "Team": team_row["Team"].strip(),
                "Owner": team_row["Owner"].strip(),
                FINISH_COL: team_row[FINISH_COL].strip(),
                "PoolSize": str(pool_size),
                "Drawn": str(draw_index + 1),
                "AssignedHorse": horse["Horse"],
                "AssignedPost": horse["Post"],
                "AssignedOdds": horse["Odds"],
            }
        )

        assignments.append(
            {
                "Team": team_row["Team"].strip(),
                "Owner": team_row["Owner"].strip(),
                FINISH_COL: team_row[FINISH_COL].strip(),
                "Post": horse["Post"],
                "Horse": horse["Horse"],
                "Odds": horse["Odds"],
            }
        )
    return assignments, draw_log


def write_assignments(output_csv: Path, assignments: List[Dict[str, str]]) -> None:
    fieldnames = [FINISH_COL, "Team", "Owner", "Post", "Horse", "Odds"]
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(assignments)


def print_table(title: str, headers: List[str], rows: List[List[str]]) -> None:
    widths = [len(header) for header in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))

    divider = "+-" + "-+-".join("-" * width for width in widths) + "-+"

    def format_row(values: List[str]) -> str:
        return "| " + " | ".join(values[i].ljust(widths[i]) for i in range(len(values))) + " |"

    print(title)
    print(divider)
    print(format_row(headers))
    print(divider)
    for row in rows:
        print(format_row(row))
    print(divider)
    print()


def print_proof_to_console(
    input_horses_csv: Path,
    input_teams_csv: Path,
    selected_horses: List[Dict[str, str]],
    teams: List[Dict[str, str]],
    draw_log: List[Dict[str, str]],
    assignments: List[Dict[str, str]],
) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    print("Fantasy Football Derby Draw Proof")
    print(f"Generated (UTC): {timestamp}")
    print(f"Horses CSV: {input_horses_csv}")
    print(f"Teams CSV: {input_teams_csv}")
    print()

    horses_rows = [[h["Post"], h["Horse"], h["Odds"]] for h in selected_horses]
    print_table("1) Selected 12 Longest-Odds Horses", ["Post", "Horse", "Odds"], horses_rows)

    teams_rows = [[t[FINISH_COL].strip(), t["Team"].strip(), t["Owner"].strip()] for t in teams]
    print_table("2) Fantasy Teams (Draw Order)", [FINISH_COL, "Team", "Owner"], teams_rows)

    draw_rows = [
        [
            d["Step"],
            d[FINISH_COL],
            d["PoolSize"],
            d["Drawn"],
            d["Team"],
            f"Post {d['AssignedPost']} {d['AssignedHorse']} ({d['AssignedOdds']})",
        ]
        for d in draw_log
    ]
    print_table(
        "3) Random Draw Log (CSPRNG)",
        ["Step", FINISH_COL, "Pool", "Drawn", "Team", "Assigned Horse"],
        draw_rows,
    )

    assignment_rows = [
        [a[FINISH_COL], a["Team"], a["Owner"], a["Post"], a["Horse"], a["Odds"]]
        for a in assignments
    ]
    print_table(
        "4) Final Assignments",
        [FINISH_COL, "Team", "Owner", "Post", "Horse", "Odds"],
        assignment_rows,
    )


def write_proof_report(
    proof_path: Path,
    input_horses_csv: Path,
    input_teams_csv: Path,
    selected_horses: List[Dict[str, str]],
    teams: List[Dict[str, str]],
    draw_log: List[Dict[str, str]],
    assignments: List[Dict[str, str]],
) -> None:
    lines: List[str] = []
    timestamp = datetime.now(timezone.utc).isoformat()
    lines.append("Fantasy Football Derby Draw Proof Report")
    lines.append(f"Generated (UTC): {timestamp}")
    lines.append(f"Horses CSV: {input_horses_csv}")
    lines.append(f"Teams CSV: {input_teams_csv}")
    lines.append("")
    lines.append("1) Selected 12 Longest-Odds Horses")
    for i, horse in enumerate(selected_horses, start=1):
        lines.append(f"{i:>2}. Post {horse['Post']}: {horse['Horse']} ({horse['Odds']})")
    lines.append("")
    lines.append("2) Fantasy Teams (Draw Order)")
    for i, team in enumerate(teams, start=1):
        lines.append(
            f"{i:>2}. {FINISH_COL}={team[FINISH_COL].strip()} "
            f"{team['Team'].strip()} - {team['Owner'].strip()}"
        )
    lines.append("")
    lines.append("3) Random Draw Log (Cryptographically Secure)")
    lines.append("Algorithm: for each team in input order, draw a random index from remaining horses.")
    lines.append("drawn is the 1-based position selected from the remaining horse pool.")
    for row in draw_log:
        lines.append(
            f"Step {row['Step']}: pool_size={row['PoolSize']}, "
            f"{FINISH_COL}={row[FINISH_COL]}, drawn={row['Drawn']} -> "
            f"{row['Team']} assigned to Post {row['AssignedPost']} "
            f"{row['AssignedHorse']} ({row['AssignedOdds']})"
        )
    lines.append("")
    lines.append("4) Final Assignments")
    for i, row in enumerate(assignments, start=1):
        lines.append(
            f"{i:>2}. {FINISH_COL}={row[FINISH_COL]} {row['Team']} - {row['Owner']} -> "
            f"Post {row['Post']} {row['Horse']} ({row['Odds']})"
        )
    lines.append("")

    proof_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assign 12 fantasy football teams to the 12 longest-shot horses."
    )
    parser.add_argument(
        "--input",
        default="input_horses.csv",
        help="Input CSV path (default: input_horses.csv)",
    )
    parser.add_argument(
        "--teams-csv",
        default="input_teams.csv",
        help="Teams CSV path (default: input_teams.csv)",
    )
    parser.add_argument(
        "--output",
        default="team_horse_assignments.csv",
        help="Official output CSV filename (default: team_horse_assignments.csv)",
    )
    parser.add_argument(
        "--proof-output",
        default=None,
        help="Official proof report filename (default: assignment_proof.txt)",
    )
    parser.add_argument(
        "--results-dir",
        default="results",
        help="Directory for official outputs (default: results)",
    )
    parser.add_argument(
        "--official",
        action="store_true",
        help="Write official assignments CSV. Without this flag, no assignments CSV is written.",
    )

    args = parser.parse_args()

    try:
        input_csv = Path(args.input)
        output_csv = Path(args.output)
        proof_output = Path(args.proof_output) if args.proof_output else Path("assignment_proof.txt")
        results_dir = Path(args.results_dir)

        teams = read_teams(Path(args.teams_csv))
        horses = read_horses(input_csv)
        selected_horses = select_longest_shots(horses, 12)
        assignments, draw_log = assign_teams_to_horses(teams, selected_horses)

        print_proof_to_console(
            input_csv,
            Path(args.teams_csv),
            selected_horses,
            teams,
            draw_log,
            assignments,
        )

        if args.official:
            results_dir.mkdir(parents=True, exist_ok=True)
            official_csv = results_dir / output_csv.name
            official_proof = results_dir / proof_output.name

            write_assignments(official_csv, assignments)
            write_proof_report(
                official_proof,
                input_csv,
                Path(args.teams_csv),
                selected_horses,
                teams,
                draw_log,
                assignments,
            )

            print(f"Wrote {len(assignments)} official assignments to {official_csv}")
            print(f"Wrote proof report to {official_proof}")
        else:
            print("Preview mode: no files written. Re-run with --official to write results.")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
