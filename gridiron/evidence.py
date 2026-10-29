"""Transparent, *fictional* weekly source evidence for player game attributes.

A synthetic receipt includes raw numerator/denominator, measure-level score,
measure weight and a named source family. A category is computed from those raw
measure scores, and OVR / team OVR are computed from the five categories. Actual
company source mapping and identity data never belong in this repository.
"""
from __future__ import annotations

from .sources import noise

# Stable, documented attribute -> measure hierarchy. Higher is better for
# these validated, eligible-work opportunity ratios. No absence, rework
# detection, reported quality findings, or pay/attendance measures.
METRIC_CATALOG = {
    "quality": {
        "label": "Quality",
        "definition": "Validated quality outcomes on eligible, attributable work.",
        "measures": (
            ("first_pass", "Accepted first-pass jobs", .45, "Synthetic accepted jobs", "Synthetic eligible jobs"),
            ("inspection", "Completed required inspections", .35, "Synthetic completed checks", "Synthetic applicable checks"),
            ("closure", "Verified correct closures", .20, "Synthetic verified closures", "Synthetic reviewed closures"),
        ),
    },
    "efficiency": {
        "label": "Efficiency",
        "definition": "Complexity-adjusted earned effort compared with corrected actual effort, plus validated execution.",
        "measures": (
            ("earned_effort", "Earned versus corrected effort", .55, "Synthetic earned standard minutes", "Synthetic corrected effort minutes"),
            ("work_execution", "Eligible planned work executed", .45, "Synthetic executed opportunities", "Synthetic feasible opportunities"),
        ),
    },
    "flow": {
        "label": "Flow",
        "definition": "Eligible schedule releases and handoffs completed at the validated cutoff.",
        "measures": (
            ("releases", "Feasible releases completed", .60, "Synthetic released tasks", "Synthetic feasible release tasks"),
            ("handoff_flow", "On-time critical handoffs", .40, "Synthetic timely handoffs", "Synthetic eligible critical handoffs"),
        ),
    },
    "teamwork": {
        "label": "Teamwork",
        "definition": "Verified assistance and handoffs, without ranking attendance or willingness to report defects.",
        "measures": (
            ("handoffs", "Verified team handoffs", .55, "Synthetic verified handoffs", "Synthetic accepted handoff opportunities"),
            ("assists", "Qualified support delivered", .45, "Synthetic delivered assists", "Synthetic verified assistance requests"),
        ),
    },
    "records": {
        "label": "Records",
        "definition": "Record completeness and accepted corrections, without penalties for making corrections.",
        "measures": (
            ("complete", "Complete required records", .55, "Synthetic complete records", "Synthetic applicable records"),
            ("corrections", "Verified record corrections closed", .45, "Synthetic accepted corrections", "Synthetic corrections requiring review"),
        ),
    },
}


def synthetic_evidence(player_id: str, week: int, category: str,
                       baseline: int, specialty: str) -> list[dict]:
    """Deterministic fictional events; category score is derived from these."""
    spec = METRIC_CATALOG[category]
    output = []
    specialty_boost = {
        "quality": "quality",
        "efficiency": "execution",
        "flow": "flow",
        "teamwork": "collaboration",
        "records": "precision",
    }
    for measure_id, label, weight, numerator_label, denominator_label in spec["measures"]:
        target = max(55, min(99, baseline + (7 if specialty == specialty_boost[category] else 0)
                             + noise(-8, 8, player_id, week, category, measure_id)))
        if measure_id == "earned_effort":
            numerator = 360 + noise(0, 280, player_id, week, "earned")
            denominator = max(numerator, round(numerator * 100 / target))
            score = round(min(100.0, 100.0 * numerator / denominator), 2)
            unit = "minutes"
        else:
            denominator = 35 + noise(0, 75, player_id, week, category, measure_id, "sample")
            numerator = min(denominator, round(denominator * target / 100))
            score = round(100.0 * numerator / denominator, 2)
            unit = "events"
        output.append({
            "key": measure_id, "label": label,
            "numerator": numerator, "denominator": denominator,
            "numerator_label": numerator_label, "denominator_label": denominator_label,
            "unit": unit, "score": score, "weight": weight,
            "weighted_points": round(score * weight, 4),
            "source_family": "SYNTHETIC_WEEKLY_RECEIPT",
            "normalization": "min(100, 100 × numerator ÷ denominator)",
            "is_synthetic": True,
        })
    return output


def derived_category_score(measures: list[dict]) -> float | None:
    """Never fabricate a category from absent or incomplete measures."""
    if not measures or abs(sum(m.get("weight", 0) for m in measures)-1.0) > 0.00001:
        return None
    if any(m.get("score") is None or m.get("weight") is None for m in measures):
        return None
    return round(sum(float(m["score"]) * float(m["weight"]) for m in measures), 2)
