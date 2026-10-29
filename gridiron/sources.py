"""Replaceable *read-only* league input providers.

Input contract (fixture and approved SQL adapter):
teams: id, name, short, color, accent, motto
players: id, team_id, alias, opted_in, eligible, and each week's position-neutral metadata
metrics: player_id, week, quality, efficiency, flow, teamwork, records, confidence,
         exposure_minutes (all component scores 0..100 or NULL)
Absent values are unknown, not 0. No attendance, pay, medical, native badge or
source query details are carried into the sports domain.

Approved work-side ETL can replace the named SQL reference views with approved
mapped sources, *within work-only infrastructure*. Never send actual internal
schema or records to this public repository.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Protocol

HERE = Path(__file__).resolve().parent.parent
WEEKS = 10


def seeded_int(*items: object) -> int:
    """Stable cross-process random integer without Python's salted hash()."""
    data = "|".join(map(str, items)).encode("utf-8")
    return int.from_bytes(hashlib.sha256(data).digest()[:8], "big")


def noise(lo: int, hi: int, *items: object) -> int:
    return lo + seeded_int(*items) % (hi - lo + 1)


@dataclass(frozen=True)
class Snapshot:
    teams: tuple[dict, ...]
    players: tuple[dict, ...]
    metrics: tuple[dict, ...]
    origin: str
    weeks: int = WEEKS


class LeagueSource(Protocol):
    def snapshot(self) -> Snapshot: ...


FIRST = ("Avery", "Jordan", "Quinn", "Riley", "Taylor", "Parker", "Morgan", "Casey",
         "Cameron", "Drew", "Skyler", "Blake", "Alex", "Reese", "Micah", "Rowan",
         "Jamie", "Emerson", "Hayden", "Logan", "Sawyer", "Finley", "Devin", "Ellis")
LAST = ("Vale", "Bennett", "Sato", "Reed", "Hart", "Stone", "Hayes", "Arden",
        "Mercer", "Keller", "Moss", "Park", "Brooks", "Keene", "Lane", "Wells",
        "Nolan", "Gray", "Bishop", "Rhodes", "Cruz", "West", "Bell", "Ellis")
SPECIALTIES = ("precision", "quality", "execution", "flow", "collaboration", "versatility")


class SyntheticSource:
    """Fully invented people, work records and scores. No SQL access."""

    @lru_cache(maxsize=1)
    def snapshot(self) -> Snapshot:
        teams = json.loads((HERE / "data" / "teams.json").read_text(encoding="utf-8"))
        players, metrics = [], []
        for t, team in enumerate(teams):
            for n in range(30):
                pid = f"{team['id']}-p{n+1:02d}"
                alias = f"{FIRST[(n + t*5) % len(FIRST)]} {LAST[(n*7+t*3) % len(LAST)]}"
                specialty = SPECIALTIES[(n + 2*t) % len(SPECIALTIES)]
                # All people and metrics in this dataset are fictional.
                # A few opted-out players show that consent is meaningful.
                opted_in = n not in (27, 29)
                players.append(dict(id=pid, team_id=team["id"], alias=alias,
                                    number=10 + n, opted_in=opted_in, eligible=True,
                                    specialty=specialty, is_synthetic=True))
                for week in range(1, WEEKS + 1):
                    # The five published scores are computed FROM underlying
                    # fictional opportunity counts and validated-effort ratios.
                    # This makes the demo card fully auditable rather than
                    # inventing post-hoc evidence for a preassigned rating.
                    from .evidence import METRIC_CATALOG, synthetic_evidence, derived_category_score
                    base = 68 + noise(0, 20, "talent", pid)
                    drift = noise(-7, 7, "week", pid, week)
                    evidence = {
                        category: synthetic_evidence(pid, week, category, base + drift, specialty)
                        for category in METRIC_CATALOG
                    }
                    scores = {category: derived_category_score(measures)
                              for category, measures in evidence.items()}
                    metrics.append(dict(player_id=pid, week=week,
                        **scores, evidence=evidence,
                        confidence=round(0.82 + noise(0, 17, pid, week, "confidence") / 100, 2),
                        exposure_minutes=480 + noise(0, 900, pid, week, "exposure"),
                        evidence_status="VERIFIED_SYNTHETIC",
                        source_receipt=f"demo-{week:02d}"))
        return Snapshot(tuple(teams), tuple(players), tuple(metrics), "SYNTHETIC")


class SqlServerSource:
    """Optional internal-only read of approved projections.

    The SQL views below are PUBLIC CONTRACT PLACEHOLDERS, not known corporate
    tables. Deployers create governed views matching docs/DATA_CONTRACT.md.
    A private work adapter may replace this implementation entirely.
    """
    def snapshot(self) -> Snapshot:
        if os.environ.get("FOCUS_DEPLOYMENT_CLASS") != "internal" or os.environ.get("VERCEL"):
            raise RuntimeError("Private SQL source is disabled outside approved internal deployments.")
        if os.environ.get("FOCUS_SQL_APPROVED") != "true":
            raise RuntimeError("SQL secondary-use authorization has not been acknowledged.")
        conn_str = os.environ.get("FOCUS_SQLSERVER_CONNECTION")
        if not conn_str:
            raise RuntimeError("Missing approved SQL Server connection configuration.")
        try:
            import pyodbc  # installed separately in approved internal environment
        except ImportError as exc:
            raise RuntimeError("Install company-approved pyodbc driver for internal SQL mode.") from exc

        # The work-side account MUST have SELECT on these four governed
        # projections only; no user-controlled identifiers or dynamic SQL.
        with pyodbc.connect(conn_str, timeout=15, autocommit=True) as connection:
            def read(sql: str):
                cursor = connection.cursor()
                cursor.execute(sql)
                columns = [d[0].lower() for d in cursor.description]
                rows = tuple(dict(zip(columns, row)) for row in cursor.fetchall())
                cursor.close()
                return rows
            teams = read("SELECT id, name, short, color, accent, motto FROM gridiron.vw_Teams")
            players = read("SELECT id, team_id, alias, number, opted_in, eligible, specialty, is_synthetic FROM gridiron.vw_Players")
            metrics = read("SELECT player_id, week, quality, efficiency, flow, teamwork, records, confidence, exposure_minutes, evidence_status, source_receipt FROM gridiron.vw_WeeklyMetrics")
            receipts = read("SELECT player_id, week, category, measure_key, numerator, denominator, score, weight, source_family FROM gridiron.vw_WeeklyEvidence")

        if not teams or not players or not metrics or not receipts:
            raise RuntimeError("Approved source lacks team, player, metric or evidence coverage; no fixture fallback.")
        from .evidence import METRIC_CATALOG, derived_category_score
        index = {}
        for m in metrics:
            key = (m["player_id"], int(m["week"]))
            if key in index:
                raise RuntimeError("Duplicate weekly metric receipt.")
            index[key] = dict(m, evidence={})
        seen = set()
        for raw in receipts:
            key = (raw["player_id"], int(raw["week"]))
            category, metric_key = raw["category"], raw["measure_key"]
            if key not in index or category not in METRIC_CATALOG:
                raise RuntimeError("Orphan or unknown evidence category.")
            expected = next((item for item in METRIC_CATALOG[category]["measures"]
                             if item[0] == metric_key), None)
            unique = (*key, category, metric_key)
            if expected is None or unique in seen:
                raise RuntimeError("Unexpected or duplicate source measure.")
            seen.add(unique)
            n, d = float(raw["numerator"]), float(raw["denominator"])
            if n < 0 or d <= 0 or n > d:
                raise RuntimeError("Invalid raw source fraction.")
            score, weight = float(raw["score"]), float(raw["weight"])
            if abs(score - round(100*n/d, 2)) > .015 or abs(weight-expected[2]) > .00001:
                raise RuntimeError("Measure score or weight does not reconcile to source counts.")
            index[key]["evidence"].setdefault(category, []).append(dict(
                key=metric_key, label=expected[1], numerator=n, denominator=d,
                numerator_label=expected[3], denominator_label=expected[4],
                unit="minutes" if metric_key == "earned_effort" else "events",
                score=score, weight=weight,
                weighted_points=round(score*weight, 4),
                source_family=str(raw["source_family"]),
                normalization="min(100, 100 × numerator ÷ denominator)",
                is_synthetic=False,
            ))
        for metric in index.values():
            for category, spec in METRIC_CATALOG.items():
                values = metric["evidence"].get(category, [])
                if len(values) != len(spec["measures"]):
                    raise RuntimeError("Missing governed evidence records.")
                calculated = derived_category_score(values)
                if calculated is None or abs(calculated - float(metric[category])) > .015:
                    raise RuntimeError("Metric does not reconcile to its governed source receipts.")
        return Snapshot(tuple(teams), tuple(players), tuple(index.values()), "SQLSERVER")


def selected_source() -> LeagueSource:
    mode = os.environ.get("FOCUS_DATA_SOURCE", "synthetic").lower()
    if mode == "synthetic":
        return SyntheticSource()
    if mode == "sqlserver":
        return SqlServerSource()
    raise RuntimeError("Unknown FOCUS_DATA_SOURCE; no fallback allowed.")
