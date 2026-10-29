# FOCUS GRIDIRON

**Standalone Flask football league · synthetic-first · Vercel + Posit Connect**

A six-team American-football league driven by *invented* manufacturing performance data. Each production franchise fields its best 11 eligible teammates on offense and defense using a **maximum-weight positional assignment algorithm**, not a highest-OVR-only list. Four quarters of seeded football simulation produce plays, passing/rushing/defensive stats, standings, and a season-wide MVP race.

**Current status:** Implemented demonstration source code. Not connected to company databases or deployed from this repository by the assistant. Public Vercel deployments are synthetic-only. No live employee metrics.

## Playable features
- 6 color-coded fictional production teams with 30 imaginary mechanics apiece (28 opt-in, 2 opted-out per team).
- Quality-first weekly manufacturing-derived ratings: quality (30%), efficiency (25%), FOCUS flow (20%), teamwork (15%), records (10%). All inputs are invented and bounded 0–100.
- Two 11-person starting units, picked separately from **the same team's eligible teammates**: offense QB1/RB1/WR3/TE1/OL5; defense DL4/LB3/DB4. Hungarian optimal assignment maximizes positional fit. Two-way players are permitted across units, but no mechanic fills two positions within one unit. Bench/depth chart visible. An incomplete team stops a live 11v11 match instead of borrowing players.
- 10 weeks of double round-robin home/away: 6 teams × 5 opponents × 2 matches / 2 = **30 regular-season games**.
- Top 4 reach semifinals in week 11; final in week 12; 33 total matches. Tied playoff regulation games use an explicit demo home-seed tiebreak; no simulated overtime in this version.
- Football mechanics: four quarters, down/distance, runs, passes, receptions, sacks, interceptions, first downs, punts, field goals, TDs, PAT and safeties, basic turnover and possession logic, seeded variability.
- 2D field with 22 colored circles, animated-by-play replay controls, selected play narration, scoreboards, player cards, team rosters, weekly standings, full schedule and MVP rankings.
- 100% deterministic fixture source and stateless precomputed game projections; works on Vercel's ephemeral serverless compute without writing local state.
- Separate data-provider contract and documented SQL Server input views for eventual **approved company-only** source replacement.

## Transparent player cards and team cards

The original five horizontal **player-rating bars** remain visible when a player card opens. Tap a bar (for example **Teamwork**) to expand the exact metric inputs responsible for its score: synthetic verified handoffs and qualified support, counts, ratios, measure weights and category contribution. Each detail links back to the current week's fictional evidence receipt; no values are invented at render time.

Every team now has a **TEAM DATA DNA** card with overall rating, league OVR rank, offensive and defensive position-fit, roster coverage, all five aggregated manufacturing-based attributes, underlying pooled and mean synthetic counts, a breakdown of every rated teammate and their category contributions. Drill-down hierarchy: **team OVR → weighted category → evidence measure → contributing players → their source receipts**.

The dashboard now uses an **aviation-inspired navy, cobalt blue, steel-gray and white palette**, while retaining the high-visibility individual team colors on the football field. This is a visual inspiration, not an official Boeing-branded or endorsed product.

The code driving this feature lives in `gridiron/evidence.py`, `gridiron/cards.py`, `static/cards.js`, and `static/cards.css`, and the source contract is documented in [docs/DATA_CONTRACT.md](docs/DATA_CONTRACT.md). Relevant endpoints:

- `GET /api/attributes` — the five categories, measure descriptions and scoring weights.
- `GET /api/players/{id}?week=1` — player OVR, five evidence-backed attribute scores, raw synthetic receipts, and position weights.
- `GET /api/teams/{id}/card?week=1` — complete team card and the player/evidence hierarchy.
- `GET /api/teams/{id}?week=1` — same team card alongside starting lineups and reserves.

**Important:** This demonstration's underlying raw counts are fictional, even though the score calculations genuinely use those counts. Company SQL Server evidence cannot be connected in a public Vercel deployment. The proposed `gridiron.vw_WeeklyEvidence` and three existing input views are only future internal/private integration contracts, with approval, identity/consent mapping and SSO required.

## Run locally

Python 3.12+ recommended.

```bash
git clone https://github.com/JaredVogler2/FOCUS_GRIDIRON.git
cd FOCUS_GRIDIRON
python -m venv .venv
# Activate .venv for your OS
pip install -r requirements.txt
python app.py
# Visit http://127.0.0.1:5055/
```

Tests require pytest (not needed in production):
```bash
pip install pytest
python -m pytest tests -q
```

Production-like local WSGI server:
```bash
waitress-serve --host=127.0.0.1 --port=5055 app:app
```

## Deploy to Vercel (public synthetic demo)

1. Import [this GitHub repository](https://github.com/JaredVogler2/FOCUS_GRIDIRON) into a new project at Vercel; repository root = `./`.
2. Vercel discovers Flask from `app.py` and `requirements.txt`. Do not set a custom build command or output directory.
3. Set `FOCUS_DATA_SOURCE=synthetic` (or omit; synthetic is the default). **Do not provide SQL credentials to public Vercel.**
4. Deploy; use `/health` to check process and `/api/league?week=1` to inspect the league.
5. If you use the CLI, `vercel` creates a preview and `vercel --prod` a production deployment after reviewing the project target.

The included `vercel.json` only excludes tests/docs/SQL from the serverless function bundle; no legacy `@vercel/python` build pipeline needed. `app:app` is the recognized WSGI object.

## Deploy to Posit Connect (internal or synthetic)

Run from the repository root with Python 3.12 and `rsconnect-python` installed:

```bash
python -m pip install -r requirements.txt rsconnect-python
# Register your company Connect server with rsconnect (use secure credential storage).
rsconnect deploy api --name YOUR_SAVED_CONNECT_SERVER --entrypoint app:app .
```

The same WSGI application supports Connect's application URL prefix using Flask `request.script_root` and `url_for` for static resources. To work with approved private SQL views, the company-side operator must add the private dependencies and config in the approved network after source-owner/HR/labor/privacy/Safety/Quality approval (see below).

## Architecture

```text
data/teams.json
     │
     ├── SyntheticSource (180 fake players / 1800 week-metric rows)
     │           OR
     └── SqlServerSource (optional internal-only governed SQL projections)
                 │
                 ▼
      Snapshot(teams, players, metrics)
                 │
       ratings.rate_week(week)
                 │
       team_lineup(team, week)   <--- SAME TEAM ONLY
         ├── offense 11 (Hungarian optimal position matching)
         ├── defense 11 (Hungarian optimal position matching)
         └── reserves
                 │
     league.round_robin / playoff seeding
                 │
      sim.game_sim (pure seeded football state machine)
                 │
       Flask read-only JSON APIs
                 │
     Responsive dashboard + 2D SVG replay
```

| File | Role |
|---|---|
| `app.py` | Flask app factory/export, JSON API endpoints, static site |
| `gridiron/sources.py` | Read-only pluggable source contract and synthetic / optional SQL adapter |
| `gridiron/ratings.py` | Quality-first ratings and positional Hungarian lineup selection |
| `gridiron/sim.py` | Four-quarter deterministic football play engine |
| `gridiron/league.py` | Home-and-away schedule, playoffs, standings, MVP race |
| `data/teams.json` | Fixture franchise colors, names, branding |
| `templates/index.html`, `static/*` | Responsive frontend and top-down field |
| `docs/DATA_CONTRACT.md` | SQL source substitution and privacy gates |
| `sql/reference_contract.sql` | Illustrative SQL Server view/table DDL; **NOT applied** |
| `tests/test_gridiron.py` | Schedule, lineup optimization, source/consent, API & determinism tests |
| `.github/workflows/tests.yml` | GitHub Actions Python CI |

## Read-only API

| Endpoint | Result |
|---|---|
| `GET /` | Web UI |
| `GET /health` | Process status |
| `GET /api/league?week=1` | Scores, standings, MVP leaders, week fixtures |
| `GET /api/schedule` | All 33 games, including playoffs |
| `GET /api/teams` | League franchises |
| `GET /api/teams/{team_id}?week=1` | Starters, reserves, top team athletes |
| `GET /api/players/{player_id}?week=1` | Opt-in athlete card and OVR history |
| `GET /api/games/{game_id}` | Full play trace, score, rosters, box stats |
| `GET /api/mvp?week=1` | Cross-team MVP leaderboard |

There are no POST endpoints or employment/personnel edits in the public demonstration. Browsing another fictional player is safe because every athlete here is invented. A real deployment needs identity and authorization upgrades before any personal player view is enabled.

## Source replacement / SQL Server

See [DATA_CONTRACT.md](docs/DATA_CONTRACT.md) and [reference_contract.sql](sql/reference_contract.sql). Switch sources through the `LeagueSource` interface, **not by editing UI/game code**. The SQL adapter expects the proposed governed views `gridiron.vw_Teams`, `gridiron.vw_Players`, `gridiron.vw_WeeklyMetrics`.

For a future optional *approved internal* connection only (the standalone app's private-data request gate must FIRST be replaced with tested company SSO and team-scope authorization):
- `FOCUS_DATA_SOURCE=sqlserver`
- `FOCUS_DEPLOYMENT_CLASS=internal`
- `FOCUS_SQL_APPROVED=true`
- `FOCUS_SQLSERVER_CONNECTION` injected by your company secret manager; never committed.
- Install `pyodbc` and approved SQL Server ODBC driver in company runtime.

Private mode is blocked by the standalone application's request gate until company SSO and team-scoped authorization have been implemented and approved. The example SQL source also refuses Vercel and never falls back to fixtures on a failed SQL read. SQL views are *proposed input contracts*, not installed tables and not a map to existing FOCUS databases. In particular, the current adapter requires effective roster validation for team transfers to be added before real-world use; it is not production-certified.

**Non-negotiable policy:** no private employee information or internal SQL mappings in this public repository or Vercel; no games affecting HR decisions, pay, discipline, qualification, timekeeping, or safety reporting. Protect legitimate approved leave, corrected records and quality detection from punitive scoring. Require voluntary opt-in and approved employee-facing access before work-side use.

## Development roadmap
- v0.1: full demo league, top-down replay, position-optimized team rosters, SQL reference inputs.
- v0.2: visually animated continuous player movement, richer formations, coaching schemes and realistic drive analytics.
- v0.3: persistent immutable seasons with SQL Server worker, approved effective-dated membership and consent events; opt-in self-service under company SSO.
- v0.4: live-source evidence confidence, reviewed quality attribution, small-team participation options and privacy/fairness audits.
- v1.0: reviewed enterprise integration and independent simulation/rating validation.

**The standalone app has been coded, not released to Vercel/Posit Connect.** GitHub Actions tests are supplied for execution; CI outcomes and runtime performance must be verified in the target environment.
