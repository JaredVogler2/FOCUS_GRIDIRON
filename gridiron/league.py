"""Season builder: round-robin schedule, optimized starters, games and MVPs."""
from __future__ import annotations
from collections import defaultdict
from functools import lru_cache
from .ratings import rate_week, team_lineup
from .sim import game_sim
from .sources import Snapshot, selected_source

PLAYOFF_FIRST_WEEK = 11
PLAYOFF_FINAL_WEEK = 12


def round_robin(team_ids: list[str]) -> list[list[tuple[str, str]]]:
    """Double round robin: every pair meets home & away exactly once."""
    teams = list(team_ids)
    if len(teams) % 2:
        teams.append(None)
    n = len(teams)
    circle = teams[:]
    first = []
    for week in range(n-1):
        pairs = []
        for i in range(n//2):
            a, b = circle[i], circle[n-i-1]
            if a is not None and b is not None:
                pairs.append((a, b) if (week+i) % 2 == 0 else (b, a))
        first.append(pairs)
        circle = [circle[0], circle[-1], *circle[1:-1]]
    second = [[(b, a) for a, b in week] for week in first]
    return first + second


def standings(games: list[dict], teams: list[dict]) -> list[dict]:
    values = {t["id"]: dict(team_id=t["id"], name=t["name"], wins=0, losses=0, ties=0,
                            pf=0, pa=0, played=0, points=0) for t in teams}
    for g in games:
        if g["status"] != "FINAL":
            continue
        h, a = values[g["home"]], values[g["away"]]
        h["played"] += 1
        a["played"] += 1
        h["pf"] += g["home_score"]
        h["pa"] += g["away_score"]
        a["pf"] += g["away_score"]
        a["pa"] += g["home_score"]
        if g["home_score"] > g["away_score"]:
            h["wins"] += 1; a["losses"] += 1
        elif g["away_score"] > g["home_score"]:
            a["wins"] += 1; h["losses"] += 1
        else:
            h["ties"] += 1; a["ties"] += 1
    for v in values.values():
        v["points"] = v["wins"]*2 + v["ties"]
        v["diff"] = v["pf"]-v["pa"]
        v["pct"] = round((v["wins"] + .5*v["ties"])/v["played"], 3) if v["played"] else 0
    return sorted(values.values(), key=lambda v: (-v["points"], -v["diff"], -v["pf"], v["team_id"]))


def brief(g: dict) -> dict:
    return {k: v for k, v in g.items() if k not in ("plays", "player_stats")}


def awards(source: Snapshot, games: list[dict], through_week: int) -> list[dict]:
    """Cross-team MVP race combines performance-derived OVR and game impact."""
    roster = {p["id"]: p for p in source.players}
    avg = defaultdict(list)
    football = defaultdict(float)
    sample = defaultdict(int)
    for week in range(1, min(through_week, 10)+1):
        ratings = rate_week(source, week)
        for pid, r in ratings.items():
            if r["status"] == "READY" and roster[pid]["opted_in"]:
                avg[pid].append(r["overall"])
    for g in games:
        if g["week"] > through_week or g["status"] != "FINAL":
            continue
        for pid, s in g["player_stats"].items():
            # Credit measures are football-only and bounded to reduce position bias.
            football[pid] += (
                s["pass_yards"]*.035 + s["pass_td"]*8 + s["completions"]*.3
                - s["interceptions_thrown"]*5 + s["rush_yards"]*.12
                + s["rush_td"]*9 + s["receiving_yards"]*.12 + s["receiving_td"]*9
                + s["receptions"]*.4 + s["tackles"]*.85 + s["sacks"]*5
                + s["interceptions"]*10 + s["forced_fumbles"]*5
                + s["field_goals"]*6)
            sample[pid] += 1
    ranking = []
    for pid, values in avg.items():
        p = roster[pid]
        base = sum(values)/len(values)
        football_per_week = football[pid] / max(1, min(through_week, 10))
        mvp = round(.72*base + .28*min(100, football_per_week*2.2), 2)
        ranking.append(dict(player_id=pid, alias=p["alias"], team_id=p["team_id"],
                            number=p["number"], overall=round(base, 1),
                            football_impact=round(football[pid], 1),
                            mvp_score=mvp, games_involved=sample[pid]))
    return sorted(ranking, key=lambda r: (-r["mvp_score"], -r["overall"], r["player_id"]))


class League:
    """Build once in process; Vercel and Posit GETs never mutate game results."""
    def __init__(self, source: Snapshot):
        self.source = source
        self.teams = [dict(t) for t in source.teams]
        self.players = [dict(p) for p in source.players]
        self.team_by_id = {t["id"]: t for t in self.teams}
        self.player_by_id = {p["id"]: p for p in self.players}
        self.schedule = round_robin(list(self.team_by_id))
        self.week_ratings = {}
        self.lineups = {}
        self.games = []
        for week, matchups in enumerate(self.schedule, 1):
            ratings = rate_week(source, week)
            self.week_ratings[week] = ratings
            self.lineups[week] = {tid: team_lineup(source, ratings, tid) for tid in self.team_by_id}
            for slot, (h, a) in enumerate(matchups, 1):
                gid = f"wk{week:02d}-m{slot}"
                self.games.append(game_sim(gid, week, self.team_by_id[h],
                                           self.team_by_id[a], self.lineups[week][h],
                                           self.lineups[week][a]))
        regular = standings(self.games, self.teams)
        self.playoff_seed = [t["team_id"] for t in regular[:4]]
        semis = [(self.playoff_seed[0], self.playoff_seed[3]),
                 (self.playoff_seed[1], self.playoff_seed[2])]
        self.lineups[11] = self.lineups[10]
        self.week_ratings[11] = self.week_ratings[10]
        for ix, (h, a) in enumerate(semis, 1):
            self.games.append(self._playoff(f"semi-{ix}", 11, h, a))
        semifinals = self.games[-2:]
        winners = [self._winner(g) for g in semifinals]
        self.lineups[12] = self.lineups[10]
        self.week_ratings[12] = self.week_ratings[10]
        self.games.append(self._playoff("championship", 12, winners[0], winners[1]))
        self.champion = self._winner(self.games[-1])
        self.game_by_id = {g["id"]: g for g in self.games}

    @staticmethod
    def _winner(g):
        if g["home_score"] == g["away_score"]:
            # Deterministic, explicit playoff tiebreak only (not regulation score):
            # home seed advances; show tiebreak in the game result.
            g["tiebreak_winner"] = g["home"]
            return g["home"]
        return g["home"] if g["home_score"] > g["away_score"] else g["away"]

    def _playoff(self, gid, week, home_id, away_id):
        return game_sim(gid, week, self.team_by_id[home_id], self.team_by_id[away_id],
                        self.lineups[week][home_id], self.lineups[week][away_id])

    def overview(self, week: int):
        week = max(1, min(12, week))
        league_games = [g for g in self.games if g["week"] <= min(10, week)]
        view_games = [brief(g) for g in self.games if g["week"] == week]
        return dict(mode=self.source.origin, week=week, weeks=12, regular_season_weeks=10,
                    teams=self.teams, standings=standings(league_games, self.teams),
                    games=view_games, mvp=awards(self.source, league_games, min(week,10))[:12],
                    champion=self.champion if week == 12 else None,
                    playoff_seed=self.playoff_seed if week >= 11 else None,
                    counts=dict(teams=len(self.teams), athletes=len(self.players),
                                games=len(self.games)), version="gridiron-0.1")

    def team(self, team_id: str, week: int):
        t = self.team_by_id.get(team_id)
        if t is None:
            return None
        week = max(1, min(12, week))
        p = [self.player_by_id[x["player_id"]] for x in self.lineups[week][team_id]["offense"]]
        return dict(**t, week=week, lineup=self.lineups[week][team_id],
                    top_players=sorted(
                        [dict(id=x["id"], alias=x["alias"], number=x["number"],
                              **self.week_ratings[week][x["id"]]) for x in self.players if x["team_id"] == team_id
                         and x["opted_in"] and self.week_ratings[week][x["id"]]["status"] == "READY"],
                        key=lambda x: -x["overall"])[:20])

    def player(self, player_id: str, week: int):
        p = self.player_by_id.get(player_id)
        if not p or not p["opted_in"]:
            return None
        week = max(1, min(12, week))
        ratings = self.week_ratings[week].get(player_id)
        if not ratings or ratings["status"] != "READY":
            return None
        return dict(**p, week=week, ratings=ratings,
                    history=[dict(week=w, overall=self.week_ratings[w][player_id]["overall"])
                             for w in range(1, 11)])

    def game(self, game_id: str):
        return self.game_by_id.get(game_id)


@lru_cache(maxsize=1)
def get_league() -> League:
    return League(selected_source().snapshot())
