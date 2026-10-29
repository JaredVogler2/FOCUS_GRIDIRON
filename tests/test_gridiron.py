"""Core deterministic, integrity and same-production-team roster acceptance suite."""
from __future__ import annotations

import colorsys
import hashlib
import itertools
import json
import re
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


def test_football_team_colors_are_distinct_from_green_turf():
    """Every franchise gets a vivid hue; match the approved orange/blue UI."""
    teams = SyntheticSource().snapshot().teams
    colors = {team["id"]: team["color"] for team in teams}
    assert colors["riveters"] == "#FF6900"
    assert colors["flight"] == "#0652FF"
    assert len(set(colors.values())) == 6
    hue_angles = []
    for color in colors.values():
        assert re.fullmatch(r"#[0-9a-fA-F]{6}", color)
        rgb = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        hue, saturation, _ = colorsys.rgb_to_hsv(*rgb)
        hue *= 360
        assert saturation > 0.70  # clear colors, not near-turf gray/teal
        assert not 80 <= hue <= 170  # no green-field/camouflage jerseys
        hue_angles.append(hue)
        # Each franchise receives black or white numeral ink by comparing
        # the relative luminance of its jersey color.
        def linear(v):
            return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
        luminance = sum(linear(c) * w for c, w in zip(rgb, (.2126, .7152, .0722)))
        ink_luminance = 0.0 if luminance > 0.179 else 1.0
        contrast = (max(luminance, ink_luminance) + .05) / (min(luminance, ink_luminance) + .05)
        assert contrast >= 4.5
    # Not merely unique hexes: distinct hue families on an actual field.
    for a, b in itertools.combinations(hue_angles, 2):
        assert min(abs(a - b), 360 - abs(a - b)) >= 25



def test_synthetic_receipts_reconstruct_every_attribute():
    from gridiron.evidence import METRIC_CATALOG, derived_category_score
    source = SyntheticSource().snapshot()
    assert len(METRIC_CATALOG) == 5
    for m in source.metrics[::37]:
        assert set(m["evidence"]) == set(METRIC_CATALOG)
        for category, measures in m["evidence"].items():
            assert len(measures) == len(METRIC_CATALOG[category]["measures"])
            assert derived_category_score(measures) == m[category]
            assert sum(row["weight"] for row in measures) == pytest.approx(1.0)
            for row in measures:
                assert row["is_synthetic"]
                assert row["numerator"] <= row["denominator"]
                assert row["score"] == pytest.approx(
                    round(100 * row["numerator"]/row["denominator"], 2))
    from gridiron.ratings import rate
    r = rate(source.metrics[0])
    assert r["status"] == "READY"
    assert sum(a["weighted_points"] for a in r["attributes"].values()) == pytest.approx(
        r["overall"], abs=0.055)
    assert set(r["position_details"]) == {"QB","RB","WR","TE","OL","DL","LB","DB"}


def test_tampered_evidence_fails_closed():
    from gridiron.ratings import rate
    import copy
    original = SyntheticSource().snapshot().metrics[0]
    m = copy.deepcopy(original)
    m["evidence"]["quality"][0]["score"] = 0
    assert rate(m)["status"] == "UNKNOWN"
    assert rate(m)["overall"] is None


def test_team_card_rolls_up_all_five_metrics_and_every_eligible_teammate():
    l = get_league()
    for week in (1, 6, 10, 12):
        card = l.team_card("riveters", week)
        assert card["team_id"] == "riveters"
        assert card["rank"] in range(1, 7)
        assert card["roster"]["total"] == 30
        assert card["roster"]["opted_out"] == 2
        assert card["roster"]["rated"] == 28
        assert card["offense"]["starters"] == 11
        assert card["defense"]["starters"] == 11
        assert card["participating_count"] == len(card["player_ranking"]) == 28
        assert card["overall"] == pytest.approx(
            sum(p["overall"] for p in card["player_ranking"])/28, abs=0.005)
        assert set(card["attributes"]) == {"quality","efficiency","flow","teamwork","records"}
        assert sum(a["weighted_points"] for a in card["attributes"].values()) == pytest.approx(
            card["overall"], abs=0.055)
        for attr in card["attributes"].values():
            assert attr["participant_count"] == 28
            assert len(attr["player_scores"]) == 28
            for m in attr["measures"]:
                assert m["participant_count"] == 28
                assert m["total_denominator"] > 0
                assert m["total_numerator"] <= m["total_denominator"]
                assert m["mean_score"] is not None
                assert m["pooled_rate"] is not None
        if week == 12:
            assert card["overall"] == l.team_card("riveters", 10)["overall"]
            assert card["history"][-1]["week"] == 10


def test_team_rankings_and_new_evidence_endpoints():
    client=app.test_client()
    overview=client.get("/api/league?week=7").json
    team_cards=overview["team_cards"]
    assert len(team_cards) == 6
    assert [card["rank"] for card in team_cards] == list(range(1, 7))
    assert all(team_cards[i]["overall"] >= team_cards[i+1]["overall"] for i in range(5))
    detail=client.get("/api/teams/riveters?week=7").json
    assert detail["card"]["team_id"] == "riveters"
    new=client.get("/api/teams/riveters/card?week=7")
    assert new.status_code == 200
    assert new.json["overall"] == detail["card"]["overall"]
    assert client.get("/api/teams/fake/card").status_code == 404
    catalog=client.get("/api/attributes")
    assert catalog.status_code == 200
    assert catalog.json["attributes"]["quality"]["weight"] == .30
    assert len(catalog.json["attributes"]["quality"]["measures"]) == 3
    player=client.get("/api/players/riveters-p01?week=2").json
    assert player["ratings"]["attributes"]["efficiency"]["measures"]
    assert player["ratings"]["source_receipt"] == "demo-02"
    assert client.get("/static/cards.js").status_code == 200
    assert client.get("/static/cards.css").status_code == 200
    html=client.get("/").get_data(as_text=True)
    assert "cards.js" in html and "cards.css" in html


def test_original_player_card_bars_expand_into_true_source_receipts():
    """The classic five-bar player card remains the default visible layout."""
    from pathlib import Path
    script = (Path(__file__).resolve().parents[1] / "static" / "cards.js").read_text()
    sheet = (Path(__file__).resolve().parents[1] / "static" / "cards.css").read_text()
    assert 'const keys = ["quality","efficiency","flow","teamwork","records"]' in script
    assert 'class="original-metric-item"' in script
    assert 'class="original-metric-line"' in script
    assert 'class="original-metric-track"' in script
    assert 'TAP ANY SCORE TO SEE ITS EVIDENCE' in script
    assert "a.measures.map(measure)" in script
    assert "a.receipt||r.source_receipt" in script
    assert 'class="original-evidence-detail"' in script
    assert 'class="original-metric-item" open' not in script
    assert ".original-metric-item[open]" in sheet
