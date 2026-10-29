"""Team cards computed ONLY from the same participating player ratings as the game.

The hierarchy is: team OVR -> five category means -> weighted underlying
measure means / pooled raw receipts -> eligible player cards -> raw events.
Team OVR uses equal player weights, NOT the sum of work opportunities: one
mechanic with more synthetic exposure does not automatically dominate.
"""
from __future__ import annotations
from collections import defaultdict

from .evidence import METRIC_CATALOG
from .ratings import METRICS, WEIGHTS, lineup_strength


def average(numbers: list[float], places: int = 2) -> float | None:
    return round(sum(numbers) / len(numbers), places) if numbers else None


def team_card(source, team_id: str, week: int, ratings: dict,
              lineup: dict) -> dict:
    """Transparent, reproducible cohort rollup with explicit exclusions."""
    members = [p for p in source.players if p["team_id"] == team_id]
    participating = [p for p in members if p.get("opted_in") and p.get("eligible")
                     and ratings.get(p["id"], {}).get("status") == "READY"]
    people_by_id = {p["id"]: p for p in members}
    valid = [ratings[p["id"]] for p in participating]
    exposure_minutes = sum(r["exposure_minutes"] for r in valid)
    components = {
        category: average([r["components"][category] for r in valid])
        for category in METRICS
    }
    # Use FULL PRECISION per-player scores for the aggregate formula, not
    # the rounded category means displayed in the UI.
    overall = average([r["overall"] for r in valid], 2)
    attribute_groups = {}
    for category, spec in METRIC_CATALOG.items():
        weight = WEIGHTS[category]
        player_rows = []
        for p in participating:
            rating = ratings[p["id"]]
            player_rows.append(dict(
                player_id=p["id"], alias=p["alias"], number=p["number"],
                score=rating["components"][category],
                weighted_points=round(rating["components"][category]*weight, 4),
            ))
        player_rows.sort(key=lambda r: (-r["score"], r["player_id"]))
        measure_rows = []
        for measure_id, label, subweight, numerator_label, denominator_label in spec["measures"]:
            raw = [
                next((row for row in ratings[p["id"]]["attributes"][category]["measures"]
                      if row["key"] == measure_id), None)
                for p in participating
            ]
            complete = [row for row in raw if row is not None]
            total_numerator = sum(row["numerator"] for row in complete)
            total_denominator = sum(row["denominator"] for row in complete)
            scores = [row["score"] for row in complete]
            mean_score = average(scores)
            measure_rows.append(dict(
                key=measure_id, label=label, weight=subweight,
                participant_count=len(complete), mean_score=mean_score,
                weighted_category_points=round(sum(scores) / len(scores) * subweight, 3)
                if scores else None,
                total_numerator=total_numerator if complete else None,
                total_denominator=total_denominator if complete else None,
                numerator_label=numerator_label,
                denominator_label=denominator_label,
                unit="minutes" if measure_id == "earned_effort" else "events",
                pooled_rate=round(min(100.0, 100*total_numerator/total_denominator), 2)
                if total_denominator else None,
                note=("Mean score is the unweighted mean of eligible player scores. "
                      "Pooled rate is calculated from summed raw counts; these "
                      "differ when player denominators differ."),
            ))
        attribute_groups[category] = dict(
            key=category, label=spec["label"], definition=spec["definition"],
            score=components[category], weight=weight,
            weighted_points=round(sum(r["components"][category]*weight for r in valid)
                                  / len(valid), 3) if valid else None,
            participant_count=len(player_rows),
            measures=measure_rows,
            leaders=player_rows[:5],
            player_scores=player_rows,
        )
    offense, defense = lineup["offense"], lineup["defense"]
    two_way = {row["player_id"] for row in offense} & {row["player_id"] for row in defense}
    roles = {}
    for side, entries in (("offense", offense), ("defense", defense)):
        for row in entries:
            bucket = roles.setdefault(f"{side}-{row['position']}",
                                      dict(side=side, position=row["position"], fits=[], athletes=[]))
            bucket["fits"].append(row["fit"])
            bucket["athletes"].append(dict(player_id=row["player_id"], alias=row["alias"],
                                           fit=row["fit"]))
    role_summary = [
        dict(side=rec["side"], position=rec["position"], count=len(rec["fits"]),
             average_fit=average(rec["fits"]), athletes=rec["athletes"])
        for rec in roles.values()
    ]
    player_ranking = sorted([
        dict(player_id=p["id"], alias=p["alias"], number=p["number"],
             overall=ratings[p["id"]]["overall"],
             confidence=ratings[p["id"]]["confidence"],
             components=ratings[p["id"]]["components"])
        for p in participating], key=lambda row: (-row["overall"], row["player_id"]))
    return dict(
        team_id=team_id, week=week, overall=overall,
        methodology="Arithmetic mean of READY, opted-in, eligible teammate overall ratings.",
        formula="TEAM OVR = mean(player OVR); player OVR = Σ(category score × category weight)",
        participating_count=len(participating),
        roster=dict(total=len(members),
                    opted_in=sum(bool(p.get("opted_in")) for p in members),
                    opted_out=sum(not bool(p.get("opted_in")) for p in members),
                    ineligible=sum(not bool(p.get("eligible")) for p in members),
                    rated=len(valid),
                    coverage_pct=round(len(valid)/len(members)*100, 1) if members else 0),
        confidence=average([r["confidence"] for r in valid], 3),
        exposure_minutes=exposure_minutes,
        category_scores=components,
        attributes=attribute_groups,
        offense=dict(average_fit=lineup_strength(lineup, "offense"),
                     starters=len(offense), roles=[r for r in role_summary if r["side"] == "offense"]),
        defense=dict(average_fit=lineup_strength(lineup, "defense"),
                     starters=len(defense), roles=[r for r in role_summary if r["side"] == "defense"]),
        unique_starters=len({row["player_id"] for row in offense + defense}),
        two_way_count=len(two_way), reserve_count=len(lineup["reserves"]),
        player_ranking=player_ranking,
        status=lineup["status"], origin=source.origin,
        notes=[
            "Only consented, eligible and READY-rated teammates are aggregated.",
            "Each eligible person counts once toward team OVR, even when playing on both units.",
            "Underlying receipts are fictional and are not Boeing or FOCUS operational records.",
            "Postseason weeks 11-12 reuse frozen regular-season week 10 ratings.",
        ],
    )
