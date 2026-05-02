# Fantasy Football Draft Order 2026

A small Python utility for assigning 12 fantasy football teams to the 12 longest-shot Kentucky Derby horses.

## Files

- `fetch_horses.py`: Pulls horse data from the Kentucky Derby website and writes `input_horses.csv`.
- `assign_teams.py`: Randomly assigns teams to horses using a cryptographically secure RNG.
- `fetch_results.py`: Fetches race results (stubbed via local CSV for now), maps them to fantasy teams, and builds final draft order.
- `input_teams.csv`: Your team list (`Team,Owner,2025 Finish`) with exactly 12 teams.
- `input_horses.csv`: Horse list (`Post,Horse,Odds`).
- `input_race_results.csv`: Stub race results input (`Finished,Post`) used by `fetch_results.py` until a live source is added.
- `results/team_horse_assignments.csv`: Official output assignments (written with `--official`).
- `results/assignment_proof.txt`: Official proof report (written with `--official`).
- `results/race_results.csv`: Official enriched race results with team mapping (written with `fetch_results.py --official`).
- `results/final_draft_order.csv`: Official final draft order (written with `fetch_results.py --official`).

## Requirements

- Python 3

## How to Run

1. Update horse data from the website:

```bash
python3 fetch_horses.py
```

2. Run a preview draw (prints proof tables to console, does not write CSV):

```bash
python3 assign_teams.py
```

3. Run the official draw (writes both CSV + proof report to `results/`):

```bash
python3 assign_teams.py --official
```

4. Build draft order from race results (preview mode, console tables only):

```bash
python3 fetch_results.py
```

5. Write official race results + final draft order CSVs:

```bash
python3 fetch_results.py --official
```

## Notes

- `input_teams.csv` must contain exactly 12 unique team names.
- `2025 Finish` determines draw order and must be numeric and unique.
- Odds are expected in fractional format like `30-1`.
- `fetch_horses.py` includes scratched horses with `Odds=SCR` in `input_horses.csv`.
- Scratched horses (`SCR`) are never assignable.
- The assignment field is built from the first 20 assignable (non-`SCR`) horses by post number, then the script selects the 12 longest odds from that field.
- Proof output is always shown in console as neat tables.
- `fetch_results.py` is currently stubbed to use `input_race_results.csv`; if the file does not exist, a starter template is generated automatically.
- `input_race_results.csv` is manual-entry friendly and only requires `Finished` and `Post`; `Horse` is auto-filled from `input_horses.csv`.
- In the race results table, horses that were not assigned to fantasy teams will show blank `Owner` and `Team`.
- Draft order is determined by finish position: best finish gets pick 1, worst assigned finish gets pick 12.
- In preview mode (no `--official`), no files are written.
