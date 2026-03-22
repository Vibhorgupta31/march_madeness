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
