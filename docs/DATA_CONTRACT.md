# FOCUS GRIDIRON — fixture/SQL Server interchange contract

## Current truth
The application is a **standalone read-only synthetic demonstration** with six imaginary production teams, 30 invented athletes per team, and ten weeks of synthetic, position-neutral performance inputs. There is no real person, badge, shift, rework record or company SQL in this repository. Default `FOCUS_DATA_SOURCE=synthetic` is stateless and deterministic, so Vercel serverless requests and Posit processes see the same schedule, ratings and replays. All football outcomes derive from `gridiron/sources.py`, `ratings.py`, `sim.py`, and `league.py`.

The external data boundary is `LeagueSource.snapshot() -> Snapshot(teams, players, metrics, origin, weeks)`. The only authorized deployment for live employee data is internally controlled and approved, not a public Vercel deployment. For live SQL read, `FOCUS_DATA_SOURCE=sqlserver` requires `FOCUS_DEPLOYMENT_CLASS=internal`, `FOCUS_SQL_APPROVED=true`, a company-managed `FOCUS_SQLSERVER_CONNECTION`, and company-approved `pyodbc`; the adapter rejects `VERCEL` and does not silently substitute synthetic data for missing SQL. This is an integration hook, not evidence of current source approval.

## Canonical logical entities (exactly what to replace)

| Entity | Grain | Required fields | Rules |
|---|---|---|---|
| Team | One fictional/approved franchise | `id` unique varchar(40), `name` nvarchar(100), `short` varchar(5), `color` char(7), `accent` char(7), `motto` nvarchar(140) | No direct employee information; stable ID across weeks |
| Player | One consented candidate game identity | `id` stable scoped pseudonym, `team_id` authoritative current production team key, `alias` authorized pseudonym, `number` int, `opted_in` bit, `eligible` bit, `specialty` varchar(24), `is_synthetic` bit | Never native badge number or real HR name in public build; one eligible team membership at weekly cutoff |
| WeeklyMetric | Player x week | `player_id`, `week` 1..10, `quality`, `efficiency`, `flow`, `teamwork`, `records` decimal(6,2) NULL, `confidence` decimal(5,4), `exposure_minutes` int NULL, `evidence_status` varchar(24), `source_receipt` varchar(80) | Unique per player-week; missing measure NULL, never 0; all five bounded 0..100. Requires sufficient validated person-specific exposure. |
| TeamMembership | Person x team x effective date | private source or approved view mapping | Effective-dated weekly roster, consent and transfer handling need verified company mapping and logic before live deployment |

For the first adapter, `gridiron.vw_Teams`, `gridiron.vw_Players`, and `gridiron.vw_WeeklyMetrics` are *proposed* governed SQL Server projections. They are defined in `sql/reference_contract.sql`. They must be created only by authorized internal administrators. Underlying tables in the sample DDL are design suggestions, **not known real FOCUS tables**.

**Important v1 limitation:** the standalone game currently takes one `team_id` on each player's record for the whole season, and expects ten complete weeks of approved metrics. Work-side integration must explicitly implement and test effective-dated team membership and source completeness before live use. A gap (or fewer than 11 eligible teammates) must block a legitimate live game, not fabricate fill-ins. Do not treat `actual_labor` aggregate effort as reliable person-specific hours without interval and crew reconciliation.

## Metric and football formulas

Example overall game OVR (not an official production performance score):

```text
OVR = 0.30*quality + 0.25*efficiency + 0.20*flow
    + 0.15*teamwork + 0.10*records
```

All are **normalized verified scores, not raw timeclock counts**:
- quality = independently verified quality of work / first pass; a found defect must not be scored as worker-created rework;
- efficiency = expected person-effort vs validated attributable corrected actual effort (adjust job complexity, legitimate delays and shared crews);
- flow = independently verified schedule contribution, not raw job count or modeled individual aircraft penalty;
- teamwork = supported handoffs, qualified assistance or validated team contribution;
- records = approved record completeness, **not punishments for manual corrections or kiosk punch time**.

Real production adapters must record owner authorization, cutoff, source revisions/hashes, cohort confidence, valid exclusions, identity/roster authority and verification; unmapped/unauthorized data is UNKNOWN, never substituted. Legitimate LWOP/PTO/medical or safety reporting cannot reduce a performance rating. The main public site must never expose private individual labor breakdowns. Use company SSO, scope-before-fetch and security review before any internal deployment using real people; standalone mock routes have no authentication because records are fictional.

Position fit is a separate published weighting matrix (see `gridiron/ratings.py`); a maximum-weight Hungarian assignment selects the 11 strongest eligible teammates for each side. Strictly 11 unique players per offensive or defensive unit; two-way employees are permitted across units. All other teammates can be reserves. Live teams with fewer than 11 eligible/opted-in players return ROSTER_INCOMPLETE.

## Warehouse replacement procedure (work-side only)

1. Copy the repository to an approved company system. Run tests in synthetic mode; pin application revision.
2. Confirm legal, safety, privacy, quality, HR/labor and secondary-use approvals before connecting actual personnel datasets. Authorize read-only service principal; no credentials committed.
3. Privately create validated SQL views from authorized sources and document actual row-grain, native→pseudonymous identity, time zones, revision/correction logic, consent, team affiliation and week cutoff.
4. Test row cardinality, NULL/invalid values, duplicates, stale receipts, corrected clocks, shared crews, approved leave fairness, quality reporting attribution and same-team selection.
5. Adapt `SqlServerSource` to the company's exact effective-dated membership/consent contract and scope-bound authentication; never push real SQL changes, view definitions, employee data or filled mappings to this public repo.
6. Re-run adversarial tests and sign off before any work-side usage. Vercel remains demo-only.

## Recommended production extension
For corporate operation, use an internally approved separate SQL schema with `Policy`, `Season`, `Team`, `PlayerAlias`, `TeamMembership`, `OptInDecision`, `WeeklyMetricReceipt`, `RatingRun`, `PlayerRating`, `Lineup`, `Game`, `Play`, `BoxStat`, and `Audit`, as described in the full [FOCUS Gridiron specification](https://github.com/JaredVogler2/From_Nothing/blob/main/FROM-NOTHING-APP/docs/gridiron/SQL_SERVER_SCHEMA.md). These production output tables are NOT needed for this stateless demo. A real persistent league needs an owner-approved database and durable background worker, not Vercel local files.
