# March Madness Krav Class Tracker — Design Spec

**Date:** 2026-03-21
**Status:** Approved

---

## Overview

A Streamlit app that tracks and displays scores for a team-based March Madness competition at a Krav Maga gym. Teams of 2 compete by attending classes throughout March 2026. The app reads attendance data from Google Sheets (published as public CSV), calculates scores using a defined ruleset, and displays a ranked leaderboard.

---

## Competition Rules

- **Duration:** March 1–31, 2026
- **Team size:** 2 members per team
- **Number of teams:** Variable (managed via config file)

### Scoring (per day, capped — multiple classes in a day do not stack)

| Scenario | Points |
|---|---|
| Only Member A attends | +1 pt |
| Only Member B attends | +1 pt |
| Both attend the same class | +4 pts (1 + 1 + 2 together bonus) |

### Weekly Bonus

- If both members attended together on **3 or more days** in a week: **+3 pts** (applied once per week)
- Maximum per week: 7 days × 4 pts + 3 bonus = **31 pts**

### Leaderboard

- Cumulative totals across all of March (not week-by-week)

---

## Data Schema

### Google Sheet (one per team)

Each team maintains their own Google Sheet with one row per day:

| Column | Type | Description |
|---|---|---|
| Date | YYYY-MM-DD | The date of the class |
| Member_A | 0 or 1 | 1 = attended, 0 = did not attend |
| Member_B | 0 or 1 | 1 = attended, 0 = did not attend |

The sheet is published as a public CSV via Google Sheets "Publish to web" feature.

### teams.json

Located at the project root. Lists all teams and their CSV URLs:

```json
[
  {"name": "Team Alpha", "csv_url": "https://docs.google.com/spreadsheets/d/.../export?format=csv"},
  {"name": "Team Beta",  "csv_url": "https://docs.google.com/spreadsheets/d/.../export?format=csv"}
]
```

To add a new team, append an entry to this file.

---

## Architecture

```
march_madness_app/
├── app.py              # Streamlit entry point (multipage)
├── teams.json          # Team registry (name + CSV URL)
├── scoring.py          # Pure scoring logic
├── data.py             # CSV fetching and parsing
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-03-21-march-madness-design.md
```

### Components

**`data.py`**
- `fetch_team_data(csv_url) -> pd.DataFrame` — fetches and parses a team's Google Sheet CSV
- `load_teams() -> list[dict]` — reads `teams.json`

**`scoring.py`**
- `score_day(member_a: int, member_b: int) -> int` — returns daily points
- `score_week(week_df: pd.DataFrame) -> int` — returns weekly points including bonus
- `score_team(df: pd.DataFrame) -> int` — returns total March score for a team

**`app.py`**
- Page 1: Leaderboard — loads all teams, calculates scores, renders ranked table
- Page 2: Team Detail — dropdown to select a team, calendar view + running total

---

## UI

### Page 1 — Leaderboard

- Ranked table: **Rank | Team Name | Total Score | Days Both Attended | Days Either Attended**
- 1st/2nd/3rd place highlighted with gold/silver/bronze styling
- "Refresh" button to re-fetch all CSVs

### Page 2 — Team Detail

- Team selector dropdown
- March calendar grid, each day color-coded:
  - **Green** — both attended
  - **Yellow** — one attended
  - **Grey** — neither attended
- Summary stats: total score, weekly breakdown table

---

## Error Handling

- If a team's CSV URL is unreachable, skip that team and show a warning in the UI
- If a row has missing/invalid data, treat that day as 0 attendance for the affected member

---

## Out of Scope

- Authentication / admin UI (teams managed via `teams.json` directly)
- Week-by-week leaderboard view
- Historical data beyond March 2026
