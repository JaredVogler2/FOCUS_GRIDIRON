"""Core deterministic, integrity and same-production-team roster acceptance suite."""
from __future__ import annotations

import hashlib
import itertools
import json
import pytest
from app import app
from gridiron.league import get_league, round_robin, standings
from gridiron.ratings import OFFENSE, DEFENSE, rate, rate_week, team_lineup, optimal_lineup
from gridiron.sim import game_sim
from gridiron.sources import SyntheticSource


def test_fixture_contract_and_consent():
    source = SyntheticSource().snapshot()
    assert source.origin == "SYNTHETIC"
    assert len(source.teams) == 6
    assert len(source.players) == 180
    assert len(source.metrics) == 1800
    assert len({p["id"] for p in source.players}) == 180
    assert all(p["is_synthetic"] for p in source.players)
    assert all(m["evidence_status"] == "VERIFIED_SYNTHETIC" for m in source.metrics)


def test_roster_matches_actual_production_team():
    source = SyntheticSource().snapshot()
    for week in (1, 5, 10):
        rated = rate_week(source, week)
        for team in source.teams:
            roster = team_lineup(source, rated, team["id"])
            assert roster["status"] == "READY"
            for side, positions in (("offense", OFFENSE), ("defense", DEFENSE)):
                assert len(roster[side]) == 11
                assert sorted(p["position"] for p in roster[side]) == sorted(positions)
                assert len({p["player_id"] for p in roster[side]}) == 11
                for p in roster[side]:
                    original = next(x for x in source.players if x["id"] == p["player_id"])
                    assert original["team_id"] == team["id"]
                    assert original["opted_in"] and original["eligible"]


def test_incomplete_roster_never_fabricated():
    src = SyntheticSource().snapshot()
    team = src.teams[0]["id"]
    members = [p for p in src.players if p["team_id"] == team][:10]
    rated = rate_week(src, 1)
    assert optimal_lineup(members, rated, OFFENSE) == []
    assert optimal_lineup(members, rated, DEFENSE) == []


def test_position_matching_maximizes_not_greedy_overall():
    positions = ("QB", "RB")
    people = [{"id":p, "alias":p, "number":n, "eligible":True, "opted_in":True}
              for n,p in enumerate(["a","b","c"],1)]
    rated = {
        "a":{"status":"READY","overall":98,"position_scores":{"QB":100,"RB":99}},
        "b":{"status":"READY","overall":95,"position_scores":{"QB":98,"RB":1}},
        "c":{"status":"READY","overall":90,"position_scores":{"QB":1,"RB":70}},
    }
    lineup = optimal_lineup(people, rated, positions)
    score = sum(p["fit"] for p in lineup)
    exhaustive = max(rated[x]["position_scores"]["QB"]+rated[y]["position_scores"]["RB"]
                     for x,y in itertools.permutations(["a","b","c"],2))
    assert score == exhaustive == 197
    assert lineup[0]["player_id"] == "b"
    assert lineup[1]["player_id"] == "a"


def test_missing_metrics_are_unknown_not_zero():
    assert rate(None)["overall"] is None
    assert rate({"evidence_status":"NOT_PROBED"})["status"] == "UNKNOWN"
    src = SyntheticSource().snapshot()
    m = dict(src.metrics[0])
    m["quality"] = None
    assert rate(m)["overall"] is None


def test_round_robin_every_pair_twice_home_and_away():
    teams = list("ABCDEF")
    weeks = round_robin(teams)
    assert len(weeks) == 10
    assert all(len(w) == 3 for w in weeks)
    matchups = list(itertools.chain.from_iterable(weeks))
    for a,b in itertools.combinations(teams,2):
        assert matchups.count((a,b)) == 1
        assert matchups.count((b,a)) == 1


def test_game_is_reproducible_and_scores_nonnegative():
    src = SyntheticSource().snapshot()
    ratings = rate_week(src, 1)
    a, b = src.teams[:2]
    a_roster = team_lineup(src, ratings, a["id"])
    b_roster = team_lineup(src, ratings, b["id"])
    x = game_sim("test", 1, a, b, a_roster, b_roster, seed=321)
    y = game_sim("test", 1, a, b, a_roster, b_roster, seed=321)
    assert x == y
    assert x["status"] == "FINAL"
    assert x["home_score"] >= 0 and x["away_score"] >= 0
    assert 0 < len(x["plays"]) <= 230
    assert [p["number"] for p in x["plays"]] == list(range(1,len(x["plays"])+1))
    assert all(0 <= p["end_yard"] <= 100 for p in x["plays"])
    assert hashlib.sha256(json.dumps(x["plays"],sort_keys=True).encode()).hexdigest() == x["replay_hash"]


def test_season_schedule_playoffs_and_mvp():
    l=get_league()
    assert len(l.games) == 33  # 30 league + 2 semis + final
    assert len(l.playoff_seed) == 4
    assert l.champion in l.playoff_seed
    final=l.overview(12)
    assert len(final["standings"]) == 6
    assert final["champion"] == l.champion
    assert final["mvp"]
    assert final["mvp"][0]["mvp_score"] >= final["mvp"][1]["mvp_score"]


def test_flask_api_and_nonparticipants_are_private():
    client = app.test_client()
    assert client.get("/").status_code == 200
    assert client.get("/health").json["status"] == "ok"
    overview=client.get("/api/league?week=3")
    assert overview.status_code == 200
    assert overview.json["week"] == 3
    assert len(overview.json["games"]) == 3
    team=client.get("/api/teams/riveters?week=1")
    assert team.status_code == 200
    assert len(team.json["lineup"]["offense"]) == 11
    game=client.get("/api/games/wk01-m1")
    assert game.status_code == 200
    assert game.json["rosters"]
    assert game.json["plays"]
    assert client.get("/api/players/riveters-p30").status_code == 404
    assert client.get("/api/games/not-real").status_code == 404
    assert client.get("/api/teams/not-real").status_code == 404
