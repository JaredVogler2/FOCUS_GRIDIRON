"""Quality-first ratings + optimal positional selection of actual teammates."""
from __future__ import annotations

from functools import lru_cache
from .sources import Snapshot

WEIGHTS = {"quality": .30, "efficiency": .25, "flow": .20,
           "teamwork": .15, "records": .10}
# Demonstration game-position affinities, not official workplace evaluations.
POSITION_WEIGHTS = {
    "QB": {"quality": .20, "efficiency": .05, "flow": .40, "teamwork": .30, "records": .05},
    "RB": {"quality": .22, "efficiency": .50, "flow": .10, "teamwork": .10, "records": .08},
    "WR": {"quality": .45, "efficiency": .40, "flow": .05, "teamwork": .05, "records": .05},
    "TE": {"quality": .25, "efficiency": .20, "flow": .10, "teamwork": .35, "records": .10},
    "OL": {"quality": .30, "efficiency": .05, "flow": .05, "teamwork": .50, "records": .10},
    "DL": {"quality": .40, "efficiency": .30, "flow": .15, "teamwork": .10, "records": .05},
    "LB": {"quality": .45, "efficiency": .05, "flow": .35, "teamwork": .10, "records": .05},
    "DB": {"quality": .45, "efficiency": .25, "flow": .20, "teamwork": .05, "records": .05},
}
OFFENSE = ("QB", "RB", "WR", "WR", "WR", "TE", "OL", "OL", "OL", "OL", "OL")
DEFENSE = ("DL", "DL", "DL", "DL", "LB", "LB", "LB", "DB", "DB", "DB", "DB")
METRICS = tuple(WEIGHTS)


def rate(metric: dict | None) -> dict:
    """A missing measure isn't 0. Invalid / insufficient coverage blocks rating."""
    if not metric or metric.get("evidence_status") not in ("VERIFIED_SYNTHETIC", "VERIFIED_APPROVED"):
        return {"status": "UNKNOWN", "overall": None, "position_scores": {}, "confidence": None}
    if any(metric.get(k) is None or not (0 <= float(metric[k]) <= 100) for k in METRICS):
        return {"status": "UNKNOWN", "overall": None, "position_scores": {}, "confidence": None}
    if (metric.get("exposure_minutes") or 0) < 120:
        return {"status": "PROVISIONAL", "overall": None, "position_scores": {}, "confidence": None}
    values = {k: float(metric[k]) for k in METRICS}
    overall = round(sum(values[k] * v for k, v in WEIGHTS.items()), 1)
    position = {p: round(sum(values[k] * w for k, w in weights.items()), 1)
                for p, weights in POSITION_WEIGHTS.items()}
    return dict(status="READY", overall=overall, position_scores=position,
                confidence=float(metric.get("confidence") or 0),
                components=values, exposure_minutes=int(metric["exposure_minutes"]))


def rate_week(source: Snapshot, week: int) -> dict[str, dict]:
    inputs = {m["player_id"]: m for m in source.metrics if int(m["week"]) == week}
    return {p["id"]: rate(inputs.get(p["id"])) for p in source.players}


def optimal_lineup(players: list[dict], ratings: dict[str, dict], positions: tuple[str, ...]) -> list[dict]:
    """Maximum-weight rectangular assignment using Hungarian algorithm.

    Each position is one slot; each actual person can hold at most one slot
    within this unit. Deterministic tie ordering by player id. Complexity
    O(positions^2 * eligible_people), not greedy overall ranking.
    """
    eligible = sorted(
        [p for p in players if p.get("opted_in") and p.get("eligible") and
         ratings.get(p["id"], {}).get("status") == "READY"], key=lambda p: p["id"])
    n, m = len(positions), len(eligible)
    if m < n:
        return []
    # Hungarian minimization, rows positions, columns people. Zero-based scores
    # negated and scaled to integers; stable input ordering resolves exact ties.
    cost = [[-int(round(ratings[p["id"]]["position_scores"][pos] * 100))
             for p in eligible] for pos in positions]
    u = [0]*(n+1)
    v = [0]*(m+1)
    assigned = [0]*(m+1)
    way = [0]*(m+1)
    for i in range(1, n+1):
        assigned[0] = i
        j0 = 0
        minv = [10**15]*(m+1)
        used = [False]*(m+1)
        while True:
            used[j0] = True
            i0 = assigned[j0]
            delta = 10**15
            j1 = 0
            for j in range(1, m+1):
                if not used[j]:
                    cur = cost[i0-1][j-1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j] = cur
                        way[j] = j0
                    if minv[j] < delta:
                        delta = minv[j]
                        j1 = j
            for j in range(m+1):
                if used[j]:
                    u[assigned[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if assigned[j0] == 0:
                break
        while True:
            j1 = way[j0]
            assigned[j0] = assigned[j1]
            j0 = j1
            if j0 == 0:
                break
    row_person = {}
    for j in range(1, m+1):
        if assigned[j]:
            row_person[assigned[j]-1] = eligible[j-1]
    return [dict(position=pos, slot=index+1, player_id=row_person[index]["id"],
                 alias=row_person[index]["alias"], number=row_person[index]["number"],
                 overall=ratings[row_person[index]["id"]]["overall"],
                 fit=ratings[row_person[index]["id"]]["position_scores"][pos])
            for index, pos in enumerate(positions)]


def team_lineup(source: Snapshot, ratings: dict[str, dict], team_id: str) -> dict:
    members = [p for p in source.players if p["team_id"] == team_id]
    offense = optimal_lineup(members, ratings, OFFENSE)
    defense = optimal_lineup(members, ratings, DEFENSE)
    starter_ids = {p["player_id"] for p in offense + defense}
    reserve = sorted((p for p in members if p["id"] not in starter_ids and
                      p.get("opted_in") and p.get("eligible") and
                      ratings.get(p["id"], {}).get("status") == "READY"),
                     key=lambda p: -ratings[p["id"]]["overall"])
    return dict(team_id=team_id,
                status="READY" if len(offense) == 11 and len(defense) == 11 else "ROSTER_INCOMPLETE",
                eligible_count=sum(1 for p in members if p.get("opted_in") and p.get("eligible") and
                                   ratings.get(p["id"], {}).get("status") == "READY"),
                offense=offense, defense=defense,
                reserves=[dict(player_id=p["id"], alias=p["alias"], number=p["number"],
                               overall=ratings[p["id"]]["overall"]) for p in reserve])


def lineup_strength(lineup: dict, side: str) -> float:
    values = [p["fit"] for p in lineup[side]]
    return round(sum(values)/len(values), 2) if values else 0.0
