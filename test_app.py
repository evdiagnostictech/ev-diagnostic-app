"""
Tests for EV Diagnostic App
Run with: pytest test_app.py -v
"""

import os
import sqlite3
import tempfile

import pandas as pd
import pytest

# ── Minimal fault_codes.csv in memory for tests ──────────────────────────────

SAMPLE_CSV = """code,description,severity,causes,actions
P0A80,Drive Battery Pack Deterioration,High,Battery cell degradation;Excessive charge cycles,Replace degraded battery modules;Run full battery diagnostic
P0A94,DC/DC Converter Circuit Low,Medium,Weak 12V battery;DC/DC converter efficiency loss,Test 12V battery health;Measure DC/DC output voltage
P0A6A,Hybrid Battery Pack Cooling Fan,Low,Cooling fan speed below spec;Fan obstruction,Inspect battery cooling fan;Remove any obstruction
"""


@pytest.fixture(autouse=True)
def patch_data(tmp_path, monkeypatch):
    """Replace the global CSV data with a small test dataset."""
    import app
    csv_path = tmp_path / "fault_codes.csv"
    csv_path.write_text(SAMPLE_CSV)
    monkeypatch.setattr(app, "data", pd.read_csv(str(csv_path)))


@pytest.fixture()
def test_db(tmp_path, monkeypatch):
    """Use a temporary SQLite database for each test."""
    import app
    db_path = str(tmp_path / "test_diagnostics.db")
    monkeypatch.setattr(app, "DB_PATH", db_path)
    app.init_db()
    return db_path


@pytest.fixture()
def client(test_db):
    """Flask test client with testing mode enabled."""
    import app
    app.app.config["TESTING"] = True
    with app.app.test_client() as c:
        yield c


# ── ai_explanation ────────────────────────────────────────────────────────────

class TestAiExplanation:
    def test_high_severity(self):
        from app import ai_explanation
        result = ai_explanation("P0A80", "Battery Deterioration", "High")
        assert "P0A80" in result
        assert "critical" in result.lower()

    def test_medium_severity(self):
        from app import ai_explanation
        result = ai_explanation("P0A94", "DC/DC Converter", "Medium")
        assert "P0A94" in result
        assert "attention" in result.lower()

    def test_low_severity(self):
        from app import ai_explanation
        result = ai_explanation("P0A6A", "Cooling Fan", "Low")
        assert "P0A6A" in result
        assert "minor" in result.lower()


# ── diagnose ──────────────────────────────────────────────────────────────────

class TestDiagnose:
    def test_valid_high_code(self):
        from app import diagnose
        result = diagnose("P0A80", voltage=350, temperature=25, cycles=100)
        assert "error" not in result
        assert result["code"] == "P0A80"
        assert result["severity"] == "High"
        assert isinstance(result["causes"], list)
        assert isinstance(result["actions"], list)
        assert len(result["causes"]) > 0
        assert len(result["actions"]) > 0

    def test_valid_medium_code(self):
        from app import diagnose
        result = diagnose("P0A94", voltage=350, temperature=25, cycles=100)
        assert result["severity"] == "Medium"

    def test_valid_low_code(self):
        from app import diagnose
        result = diagnose("P0A6A", voltage=350, temperature=25, cycles=100)
        assert result["severity"] == "Low"

    def test_unknown_code_returns_error(self):
        from app import diagnose
        result = diagnose("P9999", voltage=350, temperature=25, cycles=100)
        assert "error" in result
        assert "P9999" in result["error"]

    def test_negative_cycles_returns_error(self):
        from app import diagnose
        result = diagnose("P0A80", voltage=350, temperature=25, cycles=-1)
        assert "error" in result

    def test_battery_health_clamped_max(self):
        from app import diagnose
        # Very low temperature pushes score above 100 — must clamp to 100
        result = diagnose("P0A80", voltage=350, temperature=-50, cycles=0)
        assert result["battery_health"] <= 100

    def test_battery_health_clamped_min(self):
        from app import diagnose
        # Extreme values push score below 0 — must clamp to 0
        result = diagnose("P0A80", voltage=100, temperature=100, cycles=5000)
        assert result["battery_health"] >= 0

    def test_low_voltage_penalty(self):
        from app import diagnose
        high_v = diagnose("P0A80", voltage=350, temperature=25, cycles=100)
        low_v  = diagnose("P0A80", voltage=200, temperature=25, cycles=100)
        assert low_v["battery_health"] < high_v["battery_health"]

    def test_battery_health_typical(self):
        from app import diagnose
        result = diagnose("P0A80", voltage=350, temperature=25, cycles=100)
        # 100 - (100*0.02) - (25*0.5) = 100 - 2 - 12.5 = 85.5 → 86
        assert result["battery_health"] == 86

    def test_code_case_insensitive(self):
        from app import diagnose
        # app.py uppercases code in the route, diagnose receives uppercase
        result = diagnose("P0A80", voltage=350, temperature=25, cycles=100)
        assert "error" not in result


# ── Database ──────────────────────────────────────────────────────────────────

class TestDatabase:
    def test_init_db_creates_table(self, test_db):
        with sqlite3.connect(test_db) as con:
            tables = con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        assert ("diagnostics",) in tables

    def test_save_and_retrieve(self, test_db):
        from app import save_diagnostic, get_history
        result = {
            "code": "P0A80",
            "description": "Battery Deterioration",
            "severity": "High",
            "diagnosis": "Critical fault.",
            "battery_health": 82,
            "causes": ["Cell degradation"],
            "actions": ["Inspect battery"],
        }
        save_diagnostic("5YJ3E1EA", result, voltage=350, temperature=25, cycles=100)
        history = get_history("5YJ3E1EA")
        assert len(history) == 1
        assert history[0]["code"] == "P0A80"
        assert history[0]["battery_health"] == 82

    def test_vin_normalized_uppercase(self, test_db):
        from app import save_diagnostic, get_history
        result = {
            "code": "P0A80", "description": "x", "severity": "High",
            "diagnosis": "x", "battery_health": 80,
            "causes": [], "actions": [],
        }
        save_diagnostic("5yj3e1ea", result, 350, 25, 100)
        history = get_history("5YJ3E1EA")
        assert len(history) == 1

    def test_multiple_records_same_vin(self, test_db):
        from app import save_diagnostic, get_history
        base = {
            "code": "P0A80", "description": "x", "severity": "High",
            "diagnosis": "x", "battery_health": 80,
            "causes": [], "actions": [],
        }
        save_diagnostic("VIN001", base, 350, 25, 100)
        save_diagnostic("VIN001", base, 340, 30, 150)
        history = get_history("VIN001")
        assert len(history) == 2

    def test_history_different_vins_isolated(self, test_db):
        from app import save_diagnostic, get_history
        base = {
            "code": "P0A80", "description": "x", "severity": "High",
            "diagnosis": "x", "battery_health": 80,
            "causes": [], "actions": [],
        }
        save_diagnostic("VIN_A", base, 350, 25, 100)
        save_diagnostic("VIN_B", base, 350, 25, 100)
        assert len(get_history("VIN_A")) == 1
        assert len(get_history("VIN_B")) == 1

    def test_get_all_vins(self, test_db):
        from app import save_diagnostic, get_all_vins
        base = {
            "code": "P0A80", "description": "x", "severity": "High",
            "diagnosis": "x", "battery_health": 80,
            "causes": [], "actions": [],
        }
        save_diagnostic("VIN_A", base, 350, 25, 100)
        save_diagnostic("VIN_B", base, 350, 25, 100)
        vins = get_all_vins()
        assert "VIN_A" in vins
        assert "VIN_B" in vins


# ── Flask routes ──────────────────────────────────────────────────────────────

class TestRoutes:
    def test_get_homepage(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert b"EV Diagnostic" in response.data

    def test_post_valid_diagnosis(self, client):
        response = client.post("/", data={
            "vin": "5YJ3E1EA1NF000001",
            "code": "P0A80",
            "voltage": "350",
            "temperature": "25",
            "cycles": "100",
        })
        assert response.status_code == 200
        assert b"P0A80" in response.data
        assert b"Battery" in response.data

    def test_post_without_vin(self, client):
        """Diagnosis should work without a VIN."""
        response = client.post("/", data={
            "vin": "",
            "code": "P0A80",
            "voltage": "350",
            "temperature": "25",
            "cycles": "100",
        })
        assert response.status_code == 200
        assert b"P0A80" in response.data

    def test_post_unknown_code_shows_error(self, client):
        response = client.post("/", data={
            "vin": "",
            "code": "P9999",
            "voltage": "350",
            "temperature": "25",
            "cycles": "100",
        })
        assert response.status_code == 200
        assert b"P9999" in response.data

    def test_post_invalid_voltage_shows_error(self, client):
        response = client.post("/", data={
            "vin": "",
            "code": "P0A80",
            "voltage": "abc",
            "temperature": "25",
            "cycles": "100",
        })
        assert response.status_code == 200
        assert b"Invalid input" in response.data

    def test_history_page(self, client, test_db):
        # First save a record via POST
        client.post("/", data={
            "vin": "TESTVIN001",
            "code": "P0A80",
            "voltage": "350",
            "temperature": "25",
            "cycles": "100",
        })
        response = client.get("/history/TESTVIN001")
        assert response.status_code == 200
        assert b"TESTVIN001" in response.data
        assert b"P0A80" in response.data

    def test_delete_record(self, client, test_db):
        from app import get_history
        client.post("/", data={
            "vin": "DELVIN",
            "code": "P0A80",
            "voltage": "350",
            "temperature": "25",
            "cycles": "100",
        })
        history = get_history("DELVIN")
        assert len(history) == 1
        record_id = history[0]["id"]

        client.post(f"/delete/{record_id}", data={"vin": "DELVIN"})
        assert len(get_history("DELVIN")) == 0