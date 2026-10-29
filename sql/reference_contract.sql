-- Public, synthetic-only REFERENCE contract — NOT a migration for an existing company database.
-- Intended SQL Server 2022. Company DBA must review and privately map real
-- sources to these projection shapes in an approved/internal deployment.
-- Never execute this against production without separate approval.
IF SCHEMA_ID('gridiron') IS NULL EXEC ('CREATE SCHEMA gridiron');
GO
CREATE TABLE gridiron.Team (
    id varchar(40) NOT NULL PRIMARY KEY,
    name nvarchar(100) NOT NULL,
    short varchar(5) NOT NULL,
    color char(7) NOT NULL,
    accent char(7) NOT NULL,
    motto nvarchar(140) NOT NULL
);
GO
CREATE TABLE gridiron.Player (
    id varchar(80) NOT NULL PRIMARY KEY, -- pseudonymous; NOT badge number
    team_id varchar(40) NOT NULL REFERENCES gridiron.Team(id),
    alias nvarchar(80) NOT NULL,
    number int NOT NULL,
    opted_in bit NOT NULL,
    eligible bit NOT NULL,
    specialty varchar(24) NOT NULL,
    is_synthetic bit NOT NULL DEFAULT 0
);
GO
CREATE TABLE gridiron.WeeklyMetric (
    player_id varchar(80) NOT NULL REFERENCES gridiron.Player(id),
    week tinyint NOT NULL CHECK (week BETWEEN 1 AND 10),
    quality decimal(6,2) NULL CHECK (quality BETWEEN 0 AND 100),
    efficiency decimal(6,2) NULL CHECK (efficiency BETWEEN 0 AND 100),
    flow decimal(6,2) NULL CHECK (flow BETWEEN 0 AND 100),
    teamwork decimal(6,2) NULL CHECK (teamwork BETWEEN 0 AND 100),
    records decimal(6,2) NULL CHECK (records BETWEEN 0 AND 100),
    confidence decimal(5,4) NULL CHECK (confidence BETWEEN 0 AND 1),
    exposure_minutes int NULL CHECK (exposure_minutes>=0),
    evidence_status varchar(24) NOT NULL,
    source_receipt varchar(80) NOT NULL,
    CONSTRAINT PK_GridironWeeklyMetric PRIMARY KEY(player_id,week)
);
GO
-- Four-view REPLACEMENT CONTRACT: every category has fully reconstructible
-- raw numerator / denominator source measures. This is an illustrative table;
-- production-owned evidence can be exposed through a governed view instead.
CREATE TABLE gridiron.WeeklyEvidence (
    player_id varchar(80) NOT NULL,
    week tinyint NOT NULL CHECK (week BETWEEN 1 AND 10),
    category varchar(24) NOT NULL CHECK (category IN (
        'quality', 'efficiency', 'flow', 'teamwork', 'records')),
    measure_key varchar(32) NOT NULL,
    numerator decimal(14,3) NOT NULL CHECK (numerator >= 0),
    denominator decimal(14,3) NOT NULL CHECK (denominator > 0),
    score decimal(6,2) NOT NULL CHECK (score BETWEEN 0 AND 100),
    weight decimal(8,6) NOT NULL CHECK (weight BETWEEN 0 AND 1),
    source_family varchar(80) NOT NULL,
    CONSTRAINT PK_GridironWeeklyEvidence
      PRIMARY KEY (player_id, week, category, measure_key),
    CONSTRAINT FK_GridironWeeklyEvidence_WeeklyMetric
      FOREIGN KEY (player_id,week) REFERENCES gridiron.WeeklyMetric(player_id,week),
    CONSTRAINT CK_GridironEvidenceFraction CHECK (numerator <= denominator)
);
GO
-- A future authoritative TeamMembership view must resolve effective date,
-- consent, and roster transfer at the week freeze; do not use a historical
-- inferred team as current assignment.
CREATE VIEW gridiron.vw_Teams AS
SELECT id,name,short,color,accent,motto FROM gridiron.Team;
GO
CREATE VIEW gridiron.vw_Players AS
SELECT id,team_id,alias,number,opted_in,eligible,specialty,is_synthetic FROM gridiron.Player;
GO
CREATE VIEW gridiron.vw_WeeklyMetrics AS
SELECT player_id,week,quality,efficiency,flow,teamwork,records,confidence,
       exposure_minutes,evidence_status,source_receipt FROM gridiron.WeeklyMetric;
GO
CREATE VIEW gridiron.vw_WeeklyEvidence AS
SELECT player_id, week, category, measure_key, numerator, denominator,
       score, weight, source_family FROM gridiron.WeeklyEvidence;
GO
-- Recommended SELECT-only security scope: grant the application account
-- SELECT on these FOUR views only, never on raw HR/timeclock/quality tables.
-- Exact permissions and views are an internal DBA decision.
