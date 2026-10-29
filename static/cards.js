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
    return `<section class="evidence-explainer">
      <div class="card-kicker">RATING COMPOSITION · SOURCE → RATING</div>
      <div class="metric-breadcrumb"><span>RAW COUNTS</span><b>›</b><span>SUBMETRICS</span><b>›</b><span>ATTRIBUTES</span><b>›</b><span>OVR</span></div>
      <div class="rating-equation"><b>PLAYER OVR <strong>${fixed(r.overall)}</strong></b>
        <small>Σ(attribute score × category weight) · ${escape(r.evidence_status)}</small></div>
      <div class="attribute-stack">${keys.map((key,index)=>{
        const a=r.attributes[key]; if(!a) return "";
        return `<details class="attribute-detail" ${index===0?"open":""}>
          <summary class="attribute-head">
            <div><span class="metric-order">0${index+1}</span>
              <b>${escape(a.label)}</b><small>${fixed(a.weight*100,0)}% OF OVERALL</small></div>
            <div class="attribute-head-score"><strong>${fixed(a.score)}</strong><span>+ ${fixed(a.weighted_points,2)} pts</span></div>
          </summary>
          <div class="attribute-body"><p>${escape(a.definition)}</p>
            ${a.measures?.length ? a.measures.map(measure).join("") :
              '<p class="evidence-note">Underlying raw receipts have not been mapped in this source. Only the approved normalized attribute is available.</p>'}
            <div class="formula-caption">Attribute ${escape(a.label)} = ${a.measures?.length ?
              a.measures.map(m=>`${fixed(m.score)} × ${fixed(m.weight*100,0)}%`).join(" + ") :
              "approved normalized component"} = ${fixed(a.score)}.</div>
          </div>
        </details>`}).join("")}</div>
      <details class="attribute-detail positional-detail"><summary class="attribute-head"><div>
        <span class="metric-order">+</span><b>POSITION FIT</b><small>THE GAME'S 8 ROLE RATINGS</small>
        </div><strong class="metric-value">VIEW</strong></summary>
        <div class="attribute-body"><p>Each position uses different weights across the same five source attributes. Selection maximizes the combined positional fit across 11 starting slots.</p>
          <div class="position-score-grid">${Object.entries(r.position_details||{}).map(([position, detail])=>
            `<details class="position-micro"><summary><b>${escape(position)}</b><strong>${fixed(detail.score)}</strong></summary>
              ${Object.entries(detail.weights).map(([name,w])=>
              `<div class="weight-row"><span>${escape(name)}</span><span>${fixed(w*100,0)}% · +${fixed(detail.contributions[name],2)}</span></div>`).join("")}
              </details>`).join("")}</div>
        </div></details>
      <div class="source-signature">SOURCE RECEIPT: ${escape(r.source_receipt||"UNAVAILABLE")} · CONFIDENCE ${fixed((r.confidence||0)*100,0)}% ·
      ${whole(r.exposure_minutes)} synthetic minutes</div>
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