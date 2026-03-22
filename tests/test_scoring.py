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
