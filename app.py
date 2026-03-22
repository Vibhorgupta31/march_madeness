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
    pass  # implemented in Task 5
