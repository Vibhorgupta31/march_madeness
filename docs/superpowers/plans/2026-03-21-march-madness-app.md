# March Madness Krav Tracker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a two-page Streamlit app that reads team attendance from public Google Sheet CSVs, calculates March Madness scores, and displays a ranked leaderboard with a per-team calendar detail view.

**Architecture:** Pure scoring logic lives in `scoring.py`, data fetching/parsing in `data.py`, and the Streamlit UI in `app.py`. Teams are configured via `teams.json` at the project root. No database — all state is fetched from Google Sheets on demand, cached for 5 minutes via `@st.cache_data`.

**Tech Stack:** Python 3.11+, Streamlit, pandas, requests, pytest

---

## File Map

| File | Role |
|---|---|
| `requirements.txt` | Python dependencies |
| `teams.json` | Team registry (name + CSV URL) |
| `scoring.py` | Pure scoring logic — no I/O, no Streamlit |
| `data.py` | CSV fetching, parsing, caching |
| `app.py` | Streamlit UI — leaderboard + team detail pages |
| `tests/test_scoring.py` | Unit tests for scoring logic |
| `tests/test_data.py` | Unit tests for data parsing |

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `teams.json`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
streamlit>=1.32.0
pandas>=2.0.0
requests>=2.31.0
pytest>=8.0.0
```

- [ ] **Step 2: Create teams.json with one placeholder team**

Use an empty string for the URL so the app fails fast with a parse error rather than waiting 10 seconds on a network timeout:

```json
[
  {
    "name": "Team Alpha",
    "csv_url": ""
  }
]
```

- [ ] **Step 3: Create tests directory**

```bash
mkdir tests && touch tests/__init__.py
```

- [ ] **Step 4: Install dependencies**

```bash
pip install -r requirements.txt
```

- [ ] **Step 5: Commit**

```bash
git add requirements.txt teams.json tests/__init__.py
git commit -m "feat: project setup — deps, team config, test scaffold"
```

---

## Task 2: Scoring Engine

**Files:**
- Create: `scoring.py`
- Create: `tests/test_scoring.py`

### What the scoring rules are (read before writing tests)

- `score_day(a, b)`: both=4, one=1, neither=0
- `score_week(week_df)`: sum of daily scores + 3 bonus if days where both attended >= 3
- `score_team(df)`: filter to March 1–31 2026, partition into Monday–Sunday weeks (using `pd.Period('W-SUN')`), sum `score_week` results
- `team_stats(df)`: filter to March, return `{"total_score": int, "days_both": int, "days_either": int}`

Weeks in March 2026 (Monday–Sunday, weeks ending Sunday):
- Week 1: Mar 1 only (Sunday)
- Week 2: Mar 2–8
- Week 3: Mar 9–15
- Week 4: Mar 16–22
- Week 5: Mar 23–29
- Week 6: Mar 30–31

- [ ] **Step 1: Write failing tests**

Create `tests/test_scoring.py`:

```python
import pandas as pd
import pytest
from scoring import score_day, score_week, score_team, team_stats


# --- score_day ---

def test_score_day_both_attend():
    assert score_day(1, 1) == 4

def test_score_day_only_a():
    assert score_day(1, 0) == 1

def test_score_day_only_b():
    assert score_day(0, 1) == 1

def test_score_day_neither():
    assert score_day(0, 0) == 0


# --- score_week ---

def _make_week(rows):
    """rows: list of (date_str, member_a, member_b)"""
    df = pd.DataFrame(rows, columns=["Date", "Member_A", "Member_B"])
    df["Date"] = pd.to_datetime(df["Date"])
    return df

def test_score_week_no_bonus():
    # Both attend 2 days, A solo 1 day → 2*4 + 1 = 9, no bonus
    df = _make_week([
        ("2026-03-02", 1, 1),
        ("2026-03-03", 1, 1),
        ("2026-03-04", 1, 0),
    ])
    assert score_week(df) == 9

def test_score_week_with_bonus():
    # Both attend 3 days → 3*4 + 3 bonus = 15
    df = _make_week([
        ("2026-03-02", 1, 1),
        ("2026-03-03", 1, 1),
        ("2026-03-04", 1, 1),
    ])
    assert score_week(df) == 15

def test_score_week_max():
    # Both attend all 7 days → 7*4 + 3 = 31
    days = [(f"2026-03-{d:02d}", 1, 1) for d in range(2, 9)]
    df = _make_week(days)
    assert score_week(df) == 31

def test_score_week_empty():
    df = _make_week([])
    assert score_week(df) == 0


# --- score_team ---

def _make_team_df(rows):
    df = pd.DataFrame(rows, columns=["Date", "Member_A", "Member_B"])
    df["Date"] = pd.to_datetime(df["Date"])
    return df

def test_score_team_ignores_out_of_range():
    # Feb row should be ignored
    df = _make_team_df([
        ("2026-02-28", 1, 1),  # ignored
        ("2026-03-01", 1, 1),  # 4 pts, week of Mar 1 (Sun only)
    ])
    assert score_team(df) == 4

def test_score_team_accumulates_weeks():
    # Week 1: Mar 1 only, both attend → 4 pts, no bonus (only 1 day together)
    # Week 2: Mar 2-4, both attend → 3*4 + 3 = 15 pts
    df = _make_team_df([
        ("2026-03-01", 1, 1),
        ("2026-03-02", 1, 1),
        ("2026-03-03", 1, 1),
        ("2026-03-04", 1, 1),
    ])
    assert score_team(df) == 4 + 15

def test_score_team_empty():
    df = _make_team_df([])
    assert score_team(df) == 0


# --- team_stats ---

def test_team_stats_structure():
    df = _make_team_df([
        ("2026-03-02", 1, 1),
        ("2026-03-03", 1, 0),
        ("2026-03-04", 0, 0),
    ])
    stats = team_stats(df)
    assert set(stats.keys()) == {"total_score", "days_both", "days_either"}

def test_team_stats_values():
    df = _make_team_df([
        ("2026-03-02", 1, 1),  # both
        ("2026-03-03", 1, 0),  # either
        ("2026-03-04", 0, 0),  # neither
    ])
    stats = team_stats(df)
    assert stats["days_both"] == 1
    assert stats["days_either"] == 2
    assert stats["total_score"] == 4 + 1  # 4 for both day, 1 for solo day
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_scoring.py -v
```

Expected: `ModuleNotFoundError: No module named 'scoring'`

- [ ] **Step 3: Implement scoring.py**

```python
import pandas as pd


MARCH_START = pd.Timestamp("2026-03-01")
MARCH_END = pd.Timestamp("2026-03-31")


def score_day(member_a: int, member_b: int) -> int:
    """Return points for a single day. Both=4, one=1, neither=0."""
    if member_a == 1 and member_b == 1:
        return 4
    return int(member_a) + int(member_b)


def score_week(week_df: pd.DataFrame) -> int:
    """Return total points for a pre-sliced week DataFrame.

    Caller is responsible for passing only rows belonging to that week.
    Adds a 3-point bonus if both members attended on 3+ days.
    """
    if week_df.empty:
        return 0
    daily = week_df.apply(
        lambda row: score_day(row["Member_A"], row["Member_B"]), axis=1
    ).sum()
    days_both = int(((week_df["Member_A"] == 1) & (week_df["Member_B"] == 1)).sum())
    bonus = 3 if days_both >= 3 else 0
    return int(daily) + bonus


def score_team(df: pd.DataFrame) -> int:
    """Return total March score for a team.

    Filters to March 1–31 2026, partitions into Monday–Sunday weeks
    (pd.Period freq='W-SUN' = week ending Sunday), and sums weekly scores.
    """
    df = df[(df["Date"] >= MARCH_START) & (df["Date"] <= MARCH_END)].copy()
    if df.empty:
        return 0
    df["_week"] = df["Date"].dt.to_period("W-SUN")
    total = 0
    for _, week_df in df.groupby("_week"):
        total += score_week(week_df.drop(columns=["_week"]))
    return total


def team_stats(df: pd.DataFrame) -> dict:
    """Return scoring summary dict for the leaderboard table.

    Returns: {"total_score": int, "days_both": int, "days_either": int}
    """
    df = df[(df["Date"] >= MARCH_START) & (df["Date"] <= MARCH_END)].copy()
    total_score = score_team(df)
    days_both = int(((df["Member_A"] == 1) & (df["Member_B"] == 1)).sum())
    days_either = int(((df["Member_A"] == 1) | (df["Member_B"] == 1)).sum())
    return {
        "total_score": total_score,
        "days_both": days_both,
        "days_either": days_either,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_scoring.py -v
```

Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add scoring.py tests/test_scoring.py
git commit -m "feat: scoring engine with full test coverage"
```

---

## Task 3: Data Layer

**Files:**
- Create: `data.py`
- Create: `tests/test_data.py`

The `fetch_team_data` function uses `@st.cache_data(ttl=300)`. To make it testable without Streamlit running, the actual HTTP fetch is extracted into a helper that tests can mock.

- [ ] **Step 1: Write failing tests**

Create `tests/test_data.py`:

```python
import json
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
from data import load_teams, _parse_csv_bytes


# --- load_teams ---

def test_load_teams(tmp_path, monkeypatch):
    config = [{"name": "Team Alpha", "csv_url": "http://example.com/alpha.csv"}]
    teams_file = tmp_path / "teams.json"
    teams_file.write_text(json.dumps(config))
    monkeypatch.chdir(tmp_path)
    result = load_teams()
    assert result == config

def test_load_teams_empty(tmp_path, monkeypatch):
    (tmp_path / "teams.json").write_text("[]")
    monkeypatch.chdir(tmp_path)
    assert load_teams() == []


# --- _parse_csv_bytes ---

def test_parse_csv_bytes_valid():
    csv = b"Date,Member_A,Member_B\n2026-03-01,1,1\n2026-03-02,0,1\n"
    df = _parse_csv_bytes(csv)
    assert len(df) == 2
    assert list(df.columns) == ["Date", "Member_A", "Member_B"]
    assert df["Date"].dtype == "datetime64[ns]"
    assert df["Member_A"].tolist() == [1, 0]
    assert df["Member_B"].tolist() == [1, 1]

def test_parse_csv_bytes_fills_missing_as_zero():
    # Missing value in Member_B should become 0
    csv = b"Date,Member_A,Member_B\n2026-03-01,1,\n"
    df = _parse_csv_bytes(csv)
    assert df["Member_B"].tolist() == [0]

def test_parse_csv_bytes_invalid_returns_none():
    df = _parse_csv_bytes(b"not,a,valid,csv\ngarbage")
    assert df is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_data.py -v
```

Expected: `ModuleNotFoundError: No module named 'data'`

- [ ] **Step 3: Implement data.py**

```python
import json
import io
import pandas as pd
import requests
import streamlit as st


TEAMS_FILE = "teams.json"


def load_teams() -> list[dict]:
    """Read team registry from teams.json. Returns list of {name, csv_url} dicts."""
    with open(TEAMS_FILE, "r") as f:
        return json.load(f)


def _parse_csv_bytes(raw: bytes) -> pd.DataFrame | None:
    """Parse raw CSV bytes into a DataFrame.

    Expects columns: Date, Member_A, Member_B.
    Missing attendance values are filled with 0.
    Returns None if parsing fails or required columns are missing.
    """
    try:
        df = pd.read_csv(io.BytesIO(raw))
        required = {"Date", "Member_A", "Member_B"}
        if not required.issubset(df.columns):
            return None
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Member_A"] = pd.to_numeric(df["Member_A"], errors="coerce").fillna(0).astype(int)
        df["Member_B"] = pd.to_numeric(df["Member_B"], errors="coerce").fillna(0).astype(int)
        df = df.dropna(subset=["Date"])
        return df
    except Exception:
        return None


@st.cache_data(ttl=300)
def fetch_team_data(csv_url: str) -> pd.DataFrame | None:
    """Fetch and parse a team's Google Sheet CSV.

    Returns a DataFrame with columns [Date, Member_A, Member_B],
    or None if the URL is unreachable or the data is malformed.
    Cached for 5 minutes. Call st.cache_data.clear() to force refresh.
    """
    try:
        response = requests.get(csv_url, timeout=10)
        response.raise_for_status()
        return _parse_csv_bytes(response.content)
    except Exception:
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_data.py -v
```

Expected: all tests PASS

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -v
```

Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add data.py tests/test_data.py
git commit -m "feat: data layer — CSV fetching, parsing, caching"
```

---

## Task 4: Leaderboard Page

**Files:**
- Create: `app.py`

This task builds the full app with the leaderboard as the default page. Team Detail is added in Task 5.

- [ ] **Step 1: Create app.py with leaderboard**

```python
import streamlit as st
import pandas as pd
from data import load_teams, fetch_team_data
from scoring import team_stats

st.set_page_config(page_title="March Madness Krav Tracker", layout="wide")

MEDAL = {1: "🥇", 2: "🥈", 3: "🥉"}
ROW_COLORS = {
    1: "background-color: #FFD700; color: #000",  # gold
    2: "background-color: #C0C0C0; color: #000",  # silver
    3: "background-color: #CD7F32; color: #000",  # bronze
}

def build_leaderboard():
    teams = load_teams()
    rows = []
    warnings = []

    for team in teams:
        df = fetch_team_data(team["csv_url"])
        if df is None:
            warnings.append(f"Could not load data for **{team['name']}** — check the CSV URL.")
            continue
        stats = team_stats(df)
        rows.append({
            "Team": team["name"],
            "Total Score": stats["total_score"],
            "Days Both Attended": stats["days_both"],
            "Days Either Attended": stats["days_either"],
        })

    for msg in warnings:
        st.warning(msg)

    if not rows:
        st.info("No team data available. Add teams to teams.json and publish their sheets.")
        return

    result_df = pd.DataFrame(rows).sort_values("Total Score", ascending=False).reset_index(drop=True)
    result_df.insert(0, "Rank", result_df.index + 1)
    result_df["Rank"] = result_df["Rank"].apply(lambda r: f"{MEDAL.get(r, '')} {r}")
    return result_df


def style_leaderboard(df: pd.DataFrame):
    def row_style(row):
        rank = int(row["Rank"].split()[-1])
        color = ROW_COLORS.get(rank, "")
        return [color] * len(row)
    return df.style.apply(row_style, axis=1)


# --- Page: Leaderboard ---
page = st.sidebar.radio("Navigate", ["Leaderboard", "Team Detail"])

if page == "Leaderboard":
    st.title("March Madness 2026 — Leaderboard")
    st.caption("March 1–31, 2026 | Krav Maga Class Competition")

    if st.button("Refresh Data"):
        fetch_team_data.clear()
        st.rerun()

    with st.spinner("Loading team scores..."):
        leaderboard_df = build_leaderboard()

    if leaderboard_df is not None:
        st.dataframe(
            style_leaderboard(leaderboard_df),
            use_container_width=True,
            hide_index=True,
        )

elif page == "Team Detail":
    pass  # implemented in Task 5
```

- [ ] **Step 2: Run the app and verify leaderboard loads**

```bash
streamlit run app.py
```

Open http://localhost:8501. Expected: leaderboard page loads, shows a warning for the placeholder team URL.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: leaderboard page with gold/silver/bronze styling and refresh"
```

---

## Task 5: Team Detail Page

**Files:**
- Modify: `app.py`

Add the Team Detail page as a second nav option. This page shows a per-day calendar grid for the selected team.

- [ ] **Step 1: Add calendar builder and team detail page to app.py**

In `app.py`:
- Change the import line `from scoring import team_stats` to `from scoring import team_stats, score_week`
- Replace `elif page == "Team Detail": pass` with the full implementation below
- Add the helper functions above that `elif` block (before it, inside the module scope)

```python
# ---- Add these functions before the elif page == "Team Detail" block ----

def build_calendar(df: pd.DataFrame) -> pd.DataFrame:
    """Build a per-day status DataFrame covering all of March 2026.

    Deduplicates by Date (keeps last row if duplicates exist), then
    reindexes to cover every day in March, filling missing days as 0.
    Returns columns: Date, Member_A, Member_B, status, day_num, week.
    """
    # Deduplicate: if sheet has two rows for same date, keep last
    df = df.drop_duplicates(subset=["Date"], keep="last")

    march_days = pd.date_range("2026-03-01", "2026-03-31")
    df = df.set_index("Date").reindex(march_days)
    df["Member_A"] = df["Member_A"].fillna(0).astype(int)
    df["Member_B"] = df["Member_B"].fillna(0).astype(int)

    def day_status(row):
        a, b = row["Member_A"], row["Member_B"]
        if a == 1 and b == 1:
            return "both"
        if a == 1 or b == 1:
            return "one"
        return "none"

    df["status"] = df.apply(day_status, axis=1)
    df["day_num"] = df.index.day
    df["weekday"] = df.index.strftime("%a")
    df["week"] = df.index.to_series().dt.to_period("W-SUN")
    return df.reset_index().rename(columns={"index": "Date"})


STATUS_COLOR = {
    "both": "#4CAF50",   # green
    "one": "#FFC107",    # yellow/amber
    "none": "#9E9E9E",   # grey
}

STATUS_LABEL = {
    "both": "Both",
    "one": "One",
    "none": "—",
}


def render_calendar(cal_df: pd.DataFrame):
    """Render the calendar grid using st.markdown HTML table."""
    weeks = cal_df.groupby("week")
    week_order = sorted(cal_df["week"].unique())

    html = "<table style='border-collapse:collapse;width:100%'>"
    html += "<tr><th style='padding:6px'>Week</th>"
    for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
        html += f"<th style='padding:6px;text-align:center'>{day}</th>"
    html += "</tr>"

    for week in week_order:
        week_df = cal_df[cal_df["week"] == week].copy()
        week_df["wd_idx"] = pd.to_datetime(week_df["Date"]).dt.dayofweek  # Mon=0..Sun=6
        html += f"<tr><td style='padding:6px;white-space:nowrap'>{str(week)}</td>"
        for wd in range(7):  # Mon=0 to Sun=6
            day_row = week_df[week_df["wd_idx"] == wd]
            if day_row.empty:
                html += "<td style='padding:6px'></td>"
            else:
                row = day_row.iloc[0]
                color = STATUS_COLOR[row["status"]]
                label = STATUS_LABEL[row["status"]]
                day_n = int(row["day_num"])
                html += (
                    f"<td style='padding:6px;text-align:center;"
                    f"background:{color};border-radius:6px;color:#fff'>"
                    f"<b>Mar {day_n}</b><br>{label}</td>"
                )
        html += "</tr>"
    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)
```

Replace the placeholder `elif page == "Team Detail": pass` with:

```python
elif page == "Team Detail":
    st.title("Team Detail")

    teams = load_teams()
    team_names = [t["name"] for t in teams]

    if not team_names:
        st.info("No teams configured in teams.json.")
    else:
        selected = st.selectbox("Select a team", team_names)
        team = next(t for t in teams if t["name"] == selected)

        df = fetch_team_data(team["csv_url"])
        if df is None:
            st.error(f"Could not load data for {selected}. Check the CSV URL.")
        else:
            stats = team_stats(df)
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Score", stats["total_score"])
            col2.metric("Days Both Attended", stats["days_both"])
            col3.metric("Days Either Attended", stats["days_either"])

            st.subheader("March Calendar")
            st.caption("🟢 Both attended  🟡 One attended  ⚫ Neither")
            cal_df = build_calendar(df)
            render_calendar(cal_df)

            # Weekly breakdown table
            st.subheader("Weekly Breakdown")
            march_df = df[
                (df["Date"] >= pd.Timestamp("2026-03-01")) &
                (df["Date"] <= pd.Timestamp("2026-03-31"))
            ].copy()
            march_df["_week"] = march_df["Date"].dt.to_period("W-SUN")
            weekly_rows = []
            for week, week_df in march_df.groupby("_week"):
                days_both = int(((week_df["Member_A"] == 1) & (week_df["Member_B"] == 1)).sum())
                week_score = score_week(week_df)
                bonus = 3 if days_both >= 3 else 0
                weekly_rows.append({
                    "Week": str(week),
                    "Days Together": days_both,
                    "Base Score": week_score - bonus,
                    "Bonus": bonus,
                    "Week Total": week_score,
                })
            st.dataframe(pd.DataFrame(weekly_rows), use_container_width=True, hide_index=True)
```

- [ ] **Step 2: Run the app and verify both pages work**

```bash
streamlit run app.py
```

- Navigate to "Leaderboard" — should show ranked table
- Navigate to "Team Detail" — should show dropdown, metrics, and calendar grid
- Click Refresh — should clear cache and reload

- [ ] **Step 3: Run full test suite one last time**

```bash
pytest tests/ -v
```

Expected: all tests PASS

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: team detail page with calendar grid and score metrics"
```

---

## Done

The app is complete. To add a new team:
1. Create their Google Sheet with columns `Date, Member_A, Member_B`
2. Publish it: File → Share → Publish to web → CSV
3. Copy the CSV URL and add it to `teams.json`
4. Hit Refresh in the app
