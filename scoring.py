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
