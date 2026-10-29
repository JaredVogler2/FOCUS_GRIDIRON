/* Transparent synthetic metrics view: category -> submetric -> player -> source. */
"use strict";
window.GRIDIRON_CARDS = (() => {
  const escape = value => String(value ?? "—").replace(/[&<>"']/g, c =>
    ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const fixed = (value, digits=1) => value === null || value === undefined ? "—" : Number(value).toFixed(digits);
  const whole = value => value === null || value === undefined ? "—" : Number(value).toLocaleString("en-US");
  const bar = value => `<div class="metric-progress" role="img" aria-label="${escape(fixed(value))} out of 100"><i style="width:${Math.max(0,Math.min(100,Number(value)||0))}%"></i></div>`;
  const breadcrumb = `<div class="metric-breadcrumb" aria-label="Metric hierarchy">
    <span>TEAM OVR</span><b>›</b><span>WEIGHTED ATTRIBUTES</span><b>›</b>
    <span>VERIFIED SOURCE COUNTS</span><b>›</b><span>TEAMMATES</span>
  </div>`;
  const measure = item => `<div class="source-measure">
    <div class="source-top"><strong>${escape(item.label)}</strong><span class="metric-value">${fixed(item.score)} <small>/ 100</small></span></div>
    ${bar(item.score)}
    <div class="measure-math"><span>${whole(item.numerator)} ${escape(item.unit)} ÷ ${whole(item.denominator)} ${escape(item.unit)}</span>
    <span>× ${fixed(item.weight*100,0)}% = <b>${fixed(item.weighted_points,2)} pts</b></span></div>
    <small class="evidence-foot">${escape(item.numerator_label)} / ${escape(item.denominator_label)}</small>
  </div>`;
  function playerCard(r) {
    if (!r || !r.attributes) return `<div class="empty-state">Source evidence not available for this week.</div>`;
    const keys = ["quality","efficiency","flow","teamwork","records"];
    // Preserve the original player card: five immediately visible horizontal
    // attribute bars. Tapping ANY bar reveals its actual numerator, denominator,
    // weighted submetrics and evidence receipt; nothing is expanded by default.
    return `<section class="evidence-explainer original-player-card">
      <div class="card-kicker">PLAYER ATTRIBUTES <span class="card-kicker-hint">TAP ANY SCORE TO SEE ITS EVIDENCE ↓</span></div>
      <div class="original-rating-bars">${keys.map((key) => {
        const a=r.attributes[key];
        if(!a)return "";
        return `<details class="original-metric-item" data-attribute="${escape(key)}">
          <summary class="original-metric-line" aria-label="Show underlying metrics for ${escape(a.label)}, score ${fixed(a.score)}">
            <span class="original-metric-label">${escape(a.label).toUpperCase()}</span>
            <span class="original-metric-track" aria-hidden="true"><i style="width:${Math.max(0,Math.min(100,Number(a.score)||0))}%"></i></span>
            <strong class="original-metric-score">${fixed(a.score)}</strong>
            <span class="original-metric-caret" aria-hidden="true">⌄</span>
          </summary>
          <div class="original-evidence-detail">
            <div class="evidence-detail-heading"><b>WHY ${escape(a.label).toUpperCase()} = ${fixed(a.score)}?</b>
              <span>${fixed(a.weight*100,0)}% OF PLAYER OVR · +${fixed(a.weighted_points,2)} PTS</span></div>
            <p>${escape(a.definition)}</p>
            ${a.measures?.length ? a.measures.map(measure).join("") :
              '<p class="evidence-note">Approved detailed evidence is not available for this source. No raw numbers have been inferred or fabricated.</p>'}
            <div class="formula-caption">${escape(a.label)} score =
              ${a.measures?.length ?
                 a.measures.map(m=>`(${fixed(m.numerator,0)} / ${fixed(m.denominator,0)}) × 100 × ${fixed(m.weight*100,0)}%`).join(" + "):
                 "approved normalized component"}
              = <strong>${fixed(a.score)}</strong>
            </div>
            <div class="evidence-detail-foot">RECEIPT ${escape(a.receipt||r.source_receipt||"UNAVAILABLE")} ·
              ${escape(r.evidence_status||"UNVERIFIED")} · SOURCES: ${a.measures?.length ?? 0}</div>
          </div>
        </details>`;
      }).join("")}</div>
      <div class="player-ovr-foot">
        <span>OVERALL <b>${fixed(r.overall)}</b></span>
        <small>Σ(attribute score × weighting). Tap a bar for its source values.</small>
      </div>
      <details class="attribute-detail positional-detail"><summary class="attribute-head"><div>
        <span class="metric-order">+</span><b>POSITION FIT</b><small>8 FOOTBALL ROLE RATINGS</small>
        </div><strong class="metric-value">VIEW</strong></summary>
        <div class="attribute-body"><p>Game positions apply different weights to the five visible attributes. The team lineup maximizes positional fit.</p>
          <div class="position-score-grid">${Object.entries(r.position_details||{}).map(([position,detail])=>
            `<details class="position-micro"><summary><b>${escape(position)}</b><strong>${fixed(detail.score)}</strong></summary>
              ${Object.entries(detail.weights).map(([name,w])=>
                `<div class="weight-row"><span>${escape(name)}</span><span>${fixed(w*100,0)}% · +${fixed(detail.contributions[name],2)}</span></div>`).join("")}
            </details>`).join("")}</div>
        </div></details>
      <div class="source-signature">SOURCE RECEIPT: ${escape(r.source_receipt||"UNAVAILABLE")} · CONFIDENCE
        ${fixed((r.confidence||0)*100,0)}% · ${whole(r.exposure_minutes)} verified input minutes ·
        ${escape(r.evidence_status||"UNVERIFIED")}</div>
    </section>`;
  }
  function teamMeasure(m) {
    return `<div class="source-measure team-source">
      <div class="source-top"><strong>${escape(m.label)}</strong><span class="metric-value">${fixed(m.mean_score)} <small>mean</small></span></div>
      ${bar(m.mean_score)}
      <div class="measure-math"><span>MEAN × ${fixed(m.weight*100,0)}% = <b>${fixed(m.weighted_category_points,2)} category pts</b></span>
        <span>${whole(m.participant_count)} source contributors</span></div>
      <div class="raw-rollup"><b>RAW TOTALS</b><span>${whole(m.total_numerator)} ÷ ${whole(m.total_denominator)} ${escape(m.unit)}
        · pooled ${fixed(m.pooled_rate)}%</span></div>
      <small class="evidence-foot">${escape(m.numerator_label)} / ${escape(m.denominator_label)}</small>
    </div>`;
  }
  function teamCard(c, teamName) {
    if(!c) return `<div class="empty-state">Team attributes unavailable.</div>`;
    const attrs=["quality","efficiency","flow","teamwork","records"];
    const record=c.season_record||{};
    return `<section class="team-performance-card" aria-label="Detailed team rating card">
      <div class="team-card-top"><div>
        <div class="card-kicker">TEAM PERFORMANCE CARD · WEEK ${c.week}</div>
        <h2>${escape(teamName)} <span>DATA DNA</span></h2>
        <p>One score, five attributes, underlying source receipts, and every eligible contributor.</p>
        </div><div class="team-card-rank">LEAGUE RANK <strong>#${whole(c.rank)}</strong></div></div>
      ${breadcrumb}
      <div class="card-overall-row">
        <div class="overall-hero"><small>TEAM OVERALL</small><strong>${fixed(c.overall)}</strong><span>/ 100</span></div>
        <div class="card-score-facts">
          <div><small>OFFENSE FIT</small><b>${fixed(c.offense.average_fit)}</b></div>
          <div><small>DEFENSE FIT</small><b>${fixed(c.defense.average_fit)}</b></div>
          <div><small>GAME RECORD</small><b>${whole(record.wins)}–${whole(record.losses)}–${whole(record.ties)}</b></div>
          <div><small>RATED COHORT</small><b>${whole(c.participating_count)} / ${whole(c.roster.total)}</b></div>
        </div>
      </div>
      <p class="card-method"><b>ROLLUP METHOD</b> ${escape(c.methodology)}
        Each person contributes once, even when selected for offense and defense.</p>
      <div class="team-metric-grid">${attrs.map((key,index)=>{
        const a=c.attributes[key];if(!a)return "";
        return `<details class="team-attribute" ${index===0?"open":""}>
          <summary><div class="team-attr-name"><span class="metric-order">0${index+1}</span>
            <b>${escape(a.label)}</b><small>WEIGHT ${fixed(a.weight*100,0)}%</small></div>
            <div class="team-attr-value"><strong>${fixed(a.score)}</strong><span>+${fixed(a.weighted_points,2)} OVR</span></div>
          </summary>
          <div class="team-attr-details"><p>${escape(a.definition)}</p>
            <div class="detail-heading">UNDERLYING EVIDENCE <span>MEAN SCORE & RAW TOTALS</span></div>
            ${a.measures.map(teamMeasure).join("")}
            <details class="contributor-list"><summary>SHOW ALL ${a.player_scores.length} PLAYER CONTRIBUTIONS
              <span>↘</span></summary>
              <div class="contributor-rows">${a.player_scores.map(row=>
                `<div class="contributor-row"><button class="link-btn" data-player="${escape(row.player_id)}">${escape(row.alias)}</button>
                  <small>ATTR ${fixed(row.score)}</small><b>+${fixed(row.weighted_points,2)}</b></div>`).join("")}</div></details>
          </div>
        </details>`}).join("")}</div>
      <div class="card-detail-grid">
        <div class="small-data-panel"><div class="detail-heading">ROSTER COVERAGE</div>
          <div class="card-counter">${whole(c.roster.rated)} <small>/ ${whole(c.roster.total)} teammates</small></div>
          ${bar(c.roster.coverage_pct)}
          <div class="data-footline"><span>Opted in: ${whole(c.roster.opted_in)}</span><span>Opted out: ${whole(c.roster.opted_out)}</span></div>
          <div class="data-footline"><span>Verified source minutes</span><b>${whole(c.exposure_minutes)}</b></div>
          <div class="data-footline"><span>Two-way starters</span><b>${whole(c.two_way_count)}</b></div>
        </div>
        <div class="small-data-panel"><div class="detail-heading">POSITION DEPTH / FIT</div>
          <div class="role-grid">${[...c.offense.roles,...c.defense.roles].map(p=>
            `<span><b>${escape(p.position)}</b> <small>${escape(p.side==="offense"?"OFF":"DEF")}</small>
              <strong>${fixed(p.average_fit)}</strong></span>`).join("")}</div>
        </div>
      </div>
      <details class="team-contributors"><summary>TEAMMATE HIERARCHY · ALL ${c.player_ranking.length} RATED PLAYER CARDS <span>⌄</span></summary>
        <div class="full-roster-table"><div class="roster-table-header"><span>PLAYER</span><span>OVR</span>
          ${attrs.map(a=>`<span>${escape(a.slice(0,3).toUpperCase())}</span>`).join("")}</div>
          ${c.player_ranking.map(p=>
            `<div class="roster-table-row"><button class="link-btn" data-player="${escape(p.player_id)}">${escape(p.alias)}</button>
              <b>${fixed(p.overall)}</b>${attrs.map(a=>`<span>${fixed(p.components[a])}</span>`).join("")}</div>`).join("")}
        </div>
      </details>
      <div class="source-signature">SYNTHETIC ONLY · TEAM OVR: ${escape(c.formula)} · NO EMPLOYMENT EVALUATION</div>
    </section>`;
  }
  return {playerCard,teamCard};
})();