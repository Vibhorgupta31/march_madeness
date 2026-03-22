import json
import pandas as pd
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

def test_parse_csv_bytes_missing_columns_returns_none():
    # Valid CSV but missing required columns
    df = _parse_csv_bytes(b"not,a,valid,csv\ngarbage")
    assert df is None

def test_parse_csv_bytes_empty_returns_none():
    assert _parse_csv_bytes(b"") is None
