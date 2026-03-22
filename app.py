import streamlit as st
import pandas as pd
from data import load_teams, fetch_team_data
from scoring import team_stats, score_week

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
    load_errors = []

    for team in teams:
        df = fetch_team_data(team["csv_url"])
        if df is None:
            load_errors.append(f"Could not load data for **{team['name']}** — check the CSV URL.")
            continue
        stats = team_stats(df)
        rows.append({
            "Team": team["name"],
            "Total Score": stats["total_score"],
            "Days Both Attended": stats["days_both"],
            "Days Either Attended": stats["days_either"],
        })

    for msg in load_errors:
        st.warning(msg)

    if not rows:
        st.info("No team data available. Add teams to teams.json and publish their sheets.")
        return

    result_df = pd.DataFrame(rows).sort_values("Total Score", ascending=False).reset_index(drop=True)
    result_df.insert(0, "Rank", result_df.index + 1)
    result_df["Rank"] = result_df["Rank"].apply(
        lambda r: f"{MEDAL[r]} {r}" if r in MEDAL else str(r)
    )
    return result_df


def style_leaderboard(df: pd.DataFrame):
    def row_style(row):
        rank = int(row["Rank"].split()[-1])
        color = ROW_COLORS.get(rank, "")
        return [color] * len(row)
    return df.style.apply(row_style, axis=1)


def build_calendar(df: pd.DataFrame, member_a: str = "Member A", member_b: str = "Member B") -> pd.DataFrame:
    """Build a per-day status DataFrame covering all of March 2026.

    Deduplicates by Date (keeps last row if duplicates exist), then
    reindexes to cover every day in March, filling missing days as 0.
    Returns columns: Date, Member_A, Member_B, status, label, day_num, week.
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
            return "one_a" if a == 1 else "one_b"
        return "none"

    df["status"] = df.apply(day_status, axis=1)
    df["label"] = df["status"].map({
        "both": f"{member_a} & {member_b}",
        "one_a": member_a,
        "one_b": member_b,
        "none": "—",
    })
    df["day_num"] = df.index.day
    df["week"] = df.index.to_series().dt.to_period("W-SUN")
    return df.reset_index().rename(columns={"index": "Date"})


STATUS_COLOR = {
    "both": "#4CAF50",   # green
    "one_a": "#FFC107",  # yellow/amber
    "one_b": "#FFC107",  # yellow/amber
    "none": "#9E9E9E",   # grey
}


def render_calendar(cal_df: pd.DataFrame):
    """Render the calendar grid using st.markdown HTML table."""
    week_order = sorted(cal_df["week"].unique())

    html = "<table style='border-collapse:collapse;width:100%'>"
    html += "<tr><th style='padding:6px'>Week</th>"
    for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
        html += f"<th style='padding:6px;text-align:center'>{day}</th>"
    html += "</tr>"

    for week in week_order:
        week_df = cal_df[cal_df["week"] == week].copy()
        week_df["wd_idx"] = week_df["Date"].dt.dayofweek  # Mon=0..Sun=6
        week_start = week.start_time.date()
        week_end = week.end_time.date()
        mar_start = pd.Timestamp("2026-03-01").date()
        mar_end = pd.Timestamp("2026-03-31").date()
        display_start = max(week_start, mar_start)
        display_end = min(week_end, mar_end)
        if display_start == display_end:
            week_label = display_start.strftime("Mar %-d")
        else:
            week_label = f"{display_start.strftime('Mar %-d')}–{display_end.strftime('%-d')}"
        html += f"<tr><td style='padding:6px;white-space:nowrap'>{week_label}</td>"
        for wd in range(7):  # Mon=0 to Sun=6
            day_row = week_df[week_df["wd_idx"] == wd]
            if day_row.empty:
                html += "<td style='padding:6px'></td>"
            else:
                row = day_row.iloc[0]
                color = STATUS_COLOR[row["status"]]
                label = row["label"]
                day_n = int(row["day_num"])
                html += (
                    f"<td style='padding:6px;text-align:center;"
                    f"background:{color};border-radius:6px;color:#fff'>"
                    f"<b>Mar {day_n}</b><br>{label}</td>"
                )
        html += "</tr>"
    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)


# --- Page routing ---
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
    st.title("Team Detail")

    teams = load_teams()
    team_names = [t["name"] for t in teams]

    if not team_names:
        st.info("No teams configured in teams.json.")
    else:
        selected = st.selectbox("Select a team", team_names)
        team = next(t for t in teams if t["name"] == selected)

        member_a = team.get("member_a", "Member A")
        member_b = team.get("member_b", "Member B")

        df = fetch_team_data(team["csv_url"])
        if df is None:
            st.error(f"Could not load data for {selected}. Check the CSV URL.")
        else:
            st.caption(f"Members: {member_a} & {member_b}")
            stats = team_stats(df)
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Score", stats["total_score"])
            col2.metric(f"Days Both Attended", stats["days_both"])
            col3.metric(f"Days Either Attended", stats["days_either"])

            st.subheader("March Calendar")
            st.caption(f"🟢 Both  🟡 One member  ⚫ Neither")
            cal_df = build_calendar(df, member_a, member_b)
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
                week_score = score_week(week_df.drop(columns=["_week"]))
                bonus = 3 if days_both >= 3 else 0
                week_start = week.start_time.date()
                week_end = week.end_time.date()
                mar_start = pd.Timestamp("2026-03-01").date()
                mar_end = pd.Timestamp("2026-03-31").date()
                display_start = max(week_start, mar_start)
                display_end = min(week_end, mar_end)
                if display_start == display_end:
                    week_label = display_start.strftime("Mar %-d")
                else:
                    week_label = f"{display_start.strftime('Mar %-d')}–{display_end.strftime('%-d')}"
                weekly_rows.append({
                    "Week": week_label,
                    "Days Together": days_both,
                    "Base Score": week_score - bonus,
                    "Bonus": bonus,
                    "Week Total": week_score,
                })
            st.dataframe(pd.DataFrame(weekly_rows), use_container_width=True, hide_index=True)
