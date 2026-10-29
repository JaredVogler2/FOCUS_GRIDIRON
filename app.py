"""FOCUS GRIDIRON — standalone WSGI app (Vercel and Posit Connect: app:app)."""
from __future__ import annotations

import os
from flask import Flask, jsonify, render_template, request
from gridiron.league import get_league

app = Flask(__name__)
app.json.sort_keys = False


@app.before_request
def private_data_gate():
    # This standalone public/fixture UI deliberately has no employee SSO or
    # caller-owned team scoping. Never expose live employee data through it.
    # Corporate work-side agents must replace this gate with approved identity,
    # row-level authorization and team-scope-before-fetch, then review APIs.
    if os.environ.get("FOCUS_DATA_SOURCE", "synthetic").lower() != "synthetic":
        return jsonify(error="Private data mode requires company SSO, scope and approved adapter integration; disabled in standalone demo."), 503



def week_arg():
    try:
        return max(1, min(12, int(request.args.get("week", "1"))))
    except (ValueError, TypeError):
        return 1


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/health")
def health():
    # No network or SQL read on health; sources can be initialized on /api.
    return jsonify(status="ok", service="focus-gridiron", data_source=os.getenv("FOCUS_DATA_SOURCE", "synthetic"))


@app.get("/api/league")
def league():
    return jsonify(get_league().overview(week_arg()))


@app.get("/api/schedule")
def schedule():
    l = get_league()
    return jsonify(weeks=12, games=[
        {k:v for k,v in game.items() if k not in ("plays", "player_stats")}
        for game in l.games
    ], teams=l.teams)


@app.get("/api/teams")
def teams():
    return jsonify(get_league().teams)


@app.get("/api/teams/<team_id>")
def team(team_id):
    data = get_league().team(team_id, week_arg())
    if data is None:
        return jsonify(error="Unknown team"), 404
    return jsonify(data)


@app.get("/api/teams/<team_id>/card")
def team_card_detail(team_id):
    data = get_league().team_card(team_id, week_arg())
    if data is None:
        return jsonify(error="Unknown team"), 404
    return jsonify(data)


@app.get("/api/attributes")
def attribute_catalog():
    from gridiron.evidence import METRIC_CATALOG
    from gridiron.ratings import WEIGHTS, POSITION_WEIGHTS
    attributes = {
        key: dict(label=spec["label"], definition=spec["definition"],
                  weight=WEIGHTS[key],
                  measures=[dict(key=m[0], label=m[1], weight=m[2],
                                 numerator_label=m[3], denominator_label=m[4])
                            for m in spec["measures"]])
        for key, spec in METRIC_CATALOG.items()
    }
    return jsonify(attributes=attributes, position_weights=POSITION_WEIGHTS,
                   score_formula="OVR = Σ(normalized attribute × attribute weight)",
                   source="SYNTHETIC", official_employment_grade=False)


@app.get("/api/players/<player_id>")
def player(player_id):
    data = get_league().player(player_id, week_arg())
    if data is None:
        return jsonify(error="Unknown or non-participating player"), 404
    return jsonify(data)


@app.get("/api/games/<game_id>")
def game(game_id):
    l = get_league()
    data = l.game(game_id)
    if data is None:
        return jsonify(error="Unknown game"), 404
    roster = {data["home"]: l.lineups[data["week"]][data["home"]],
              data["away"]: l.lineups[data["week"]][data["away"]]}
    return jsonify({**data, "rosters": roster})


@app.get("/api/mvp")
def mvp():
    from gridiron.league import awards
    l = get_league()
    through = min(10, week_arg())
    return jsonify(week=through, rankings=awards(l.source,
                   [g for g in l.games if g["week"] <= through], through))


@app.errorhandler(500)
def internal_error(exc):
    app.logger.exception("Request failed: %s", exc)
    return jsonify(error="Service unavailable; check server configuration."), 500


@app.after_request
def safe_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Cache-Control"] = "private, max-age=60" if request.path.startswith("/api/") else "no-store"
    return response


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5055")), debug=False)
