"""Deterministic 2D-replay-friendly American football game simulation.

Synthetic-only entertainment, never an authoritative workplace performance grade.
Game outcomes depend on position-fit lineup strength but retain seeded variance.
"""
from __future__ import annotations
import hashlib
import json
import random
from .ratings import lineup_strength
from .sources import seeded_int


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def game_sim(game_id: str, week: int, home: dict, away: dict,
             home_lineup: dict, away_lineup: dict, *, seed: int | None = None) -> dict:
    """Simulate four 15-min quarters, drives, first downs and standard scoring."""
    if home_lineup["status"] != "READY" or away_lineup["status"] != "READY":
        return dict(id=game_id, week=week, home=home["id"], away=away["id"],
                    home_score=None, away_score=None, plays=[], player_stats={},
                    status="ROSTER_INCOMPLETE", seed=None)
    if seed is None:
        seed = seeded_int("gridiron-v1", game_id, week)
    rng = random.Random(seed)
    lineups = {home["id"]: home_lineup, away["id"]: away_lineup}
    team_names = {home["id"]: home["name"], away["id"]: away["name"]}
    ids = (home["id"], away["id"])
    score = {home["id"]: 0, away["id"]: 0}
    offense = rng.choice(ids)
    defense = ids[0] if offense == ids[1] else ids[1]
    yard, down, distance, elapsed = 25, 1, 10, 0
    plays, stats = [], {}
    drives = 0

    def stat(pid, key, amount=1):
        if pid is None:
            return
        rec = stats.setdefault(pid, {"pass_yards": 0, "pass_td": 0, "pass_att": 0,
                                    "completions": 0, "interceptions_thrown": 0,
                                    "rush_yards": 0, "rush_att": 0, "rush_td": 0,
                                    "receiving_yards": 0, "receptions": 0,
                                    "receiving_td": 0, "tackles": 0, "sacks": 0,
                                    "interceptions": 0, "forced_fumbles": 0,
                                    "field_goals": 0, "field_goal_att": 0})
        rec[key] += amount

    def choose(team, side, position):
        group = [p for p in lineups[team][side] if p["position"] == position]
        return rng.choice(group) if group else rng.choice(lineups[team][side])

    def append(kind, description, old_yard, advance, actor=None, target=None, points=0, down_before=None):
        q = min(4, elapsed // 900 + 1)
        remaining = 900 - (elapsed % 900)
        plays.append(dict(number=len(plays)+1, quarter=q, clock=remaining,
                          offense=offense, defense=defense,
                          down=(down_before if down_before is not None else down),
                          distance=distance, yard_line=old_yard,
                          end_yard=clamp(old_yard+advance, 0, 100),
                          yards=advance, kind=kind, description=description,
                          actor=actor["player_id"] if actor else None,
                          target=target["player_id"] if target else None,
                          points=points, score=dict(score)))

    def change_possession(new_yard):
        nonlocal offense, defense, yard, down, distance, drives
        offense, defense = defense, offense
        yard = clamp(new_yard, 1, 99)
        down, distance = 1, min(10, 100-yard)
        drives += 1

    for _ in range(230):
        if elapsed >= 3600:
            break
        old = yard
        before = down
        o_rating = lineup_strength(lineups[offense], "offense")
        d_rating = lineup_strength(lineups[defense], "defense")
        advantage = o_rating - d_rating
        # Restrict probabilities so underdogs are always competitive.
        tick = rng.randint(22, 38)
        if elapsed + tick >= 3600:
            tick = 3600 - elapsed
        elapsed += tick

        # Fourth down decisions, including field goal and punts.
        if down == 4 and distance > 1 and (yard >= 63 or yard < 70):
            if yard >= 63:
                kicker = choose(offense, "offense", "QB")
                stat(kicker["player_id"], "field_goal_att")
                chance = clamp(.68 + .010*(yard-72) + .005*advantage, .20, .94)
                made = rng.random() < chance
                if made:
                    score[offense] += 3
                    stat(kicker["player_id"], "field_goals")
                append("FIELD_GOAL" if made else "MISSED_FG",
                       f"{team_names[offense]} {'convert' if made else 'miss'} a {117-yard}-yard field goal.",
                       old, 0, kicker, points=3 if made else 0, down_before=before)
                change_possession(25 if made else 100-yard)
                continue
            distance_punt = rng.randint(33, 53)
            receiving_yard = clamp(100-(yard+distance_punt), 20, 90)
            append("PUNT", f"{team_names[offense]} punt it away. Ball changes hands.", old, 0,
                   choose(offense, "offense", "QB"), down_before=before)
            change_possession(receiving_yard)
            continue

        is_pass = rng.random() < (.58 if distance >= 5 else .43)
        if is_pass:
            qb = choose(offense, "offense", "QB")
            wr = choose(offense, "offense", rng.choice(("WR", "WR", "TE")))
            db = choose(defense, "defense", rng.choice(("DB", "DB", "LB")))
            stat(qb["player_id"], "pass_att")
            sack_prob = clamp(.062 - .0025*advantage, .025, .15)
            int_prob = clamp(.028 - .0010*advantage, .010, .065)
            roll = rng.random()
            if roll < sack_prob:
                loss = rng.randint(2, 9)
                stat(db["player_id"], "sacks")
                stat(db["player_id"], "tackles")
                yard -= loss
                down += 1
                append("SACK", f"{db['alias']} sacks {qb['alias']} for a {loss}-yard loss.", old, -loss, db, qb, down_before=before)
            elif roll < sack_prob + int_prob:
                stat(qb["player_id"], "interceptions_thrown")
                stat(db["player_id"], "interceptions")
                return_yds = rng.randint(0, 22)
                append("INTERCEPTION", f"INTERCEPTED! {db['alias']} jumps the passing lane.", old, 0, db, qb, down_before=before)
                change_possession(100-yard+return_yds)
                continue
            elif rng.random() < clamp(.61+.008*advantage, .38, .82):
                yards = rng.randint(1, 13) + (rng.randint(6, 24) if rng.random() < .14 else 0)
                stat(qb["player_id"], "completions")
                stat(qb["player_id"], "pass_yards", yards)
                stat(wr["player_id"], "receptions")
                stat(wr["player_id"], "receiving_yards", yards)
                yard += yards
                down += 1
                append("PASS", f"{qb['alias']} connects with {wr['alias']} for {yards} yards.", old, yards, qb, wr, down_before=before)
            else:
                down += 1
                append("INCOMPLETE", f"{qb['alias']}'s pass falls incomplete.", old, 0, qb, wr, down_before=before)
        else:
            rb = choose(offense, "offense", "RB")
            lb = choose(defense, "defense", "LB")
            y = clamp(round(rng.gauss(4.5+advantage*.12, 4.1)), -5, 21)
            stat(rb["player_id"], "rush_att")
            stat(rb["player_id"], "rush_yards", y)
            stat(lb["player_id"], "tackles")
            yard += y
            down += 1
            append("RUN", f"{rb['alias']} rushes for {y} yards.", old, y, rb, lb, down_before=before)
            if rng.random() < .008:
                stat(lb["player_id"], "forced_fumbles")
                append("FUMBLE", f"FUMBLE! {lb['alias']} recovers for {team_names[defense]}.", yard, 0, lb, rb, down_before=down)
                change_possession(100-yard)
                continue

        if yard >= 100:
            scorer = plays[-1]["target"] if plays[-1]["kind"] == "PASS" else plays[-1]["actor"]
            touchdown_type = "receiving_td" if plays[-1]["kind"] == "PASS" else "rush_td"
            stat(scorer, touchdown_type)
            if plays[-1]["kind"] == "PASS":
                stat(qb["player_id"], "pass_td")
            score[offense] += 6
            # Fixed extra point probability for a simple honest game model.
            pat = rng.random() < .94
            score[offense] += int(pat)
            append("TOUCHDOWN", f"TOUCHDOWN {team_names[offense]}! {'Extra point good.' if pat else 'Extra point missed.'}",
                   old, 100-old, target={"player_id":scorer} if scorer else None, points=6+int(pat), down_before=before)
            change_possession(25)
            continue
        if yard <= 0:
            score[defense] += 2
            append("SAFETY", f"SAFETY! {team_names[defense]} force the offense into its end zone.", old, -old, points=2, down_before=before)
            change_possession(25)
            continue
        if yard >= 100-distance and (down > 1):  # meaningful progress, handled by accumulated chain below
            pass

        # Use the previous line of scrimmage and earned yards to calculate
        # distance remaining; negative gain increases the distance.
        gain = yard - old
        distance -= gain
        if distance <= 0:
            append("FIRST_DOWN", f"First down {team_names[offense]}!", yard, 0, down_before=before)
            down, distance = 1, min(10, 100-yard)
        if down > 4:
            append("DOWNS", f"{team_names[offense]} turn it over on downs.", yard, 0, down_before=4)
            change_possession(100-yard)

    # Four quarters only; ties are allowed in regular season.
    return dict(id=game_id, week=week, home=home["id"], away=away["id"],
                home_score=score[home["id"]], away_score=score[away["id"]],
                status="FINAL", seed=seed, engine="gridiron-sim-1",
                plays=plays, player_stats=stats, drives=drives,
                replay_hash=hashlib.sha256(json.dumps(plays, sort_keys=True).encode()).hexdigest())
