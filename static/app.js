/* FOCUS GRIDIRON — all game/score/rating logic runs on Flask. UI displays persisted
   deterministic synthetic projections only. DOM escape applied to external labels. */
"use strict";
const BASE = window.GRIDIRON_BASE || "";
const state = { view:"overview", week:1, teamId:null, gameId:null, game:null,
                playIndex:0, playing:false, timer:null, league:null, schedule:null };
const $ = (q) => document.querySelector(q);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, ch =>
  ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
const byId = (t) => (state.league?.teams || []).find(x=>x.id === t) || {id:t,name:t,short:t.slice(0,3),color:"#F1F1F1"};
const isPlayoff = (w) => w > 10;
const num = (x) => Number(x || 0).toLocaleString("en-US");
// Select black or white jersey numerals according to WCAG luminance;
 // reject non-hex colors from future database-backed sources.
const teamColor = team => /^#[0-9a-f]{6}$/i.test(team?.color || "") ? team.color : "#F1F1F1";
const teamInk = team => {
  const hex=teamColor(team);
  const rgb=[1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)/255);
  const lum=rgb.map(c=>c<=0.04045?c/12.92:((c+0.055)/1.055)**2.4)
    .reduce((sum,c,i)=>sum+c*[0.2126,0.7152,0.0722][i],0);
  return lum>0.179?"#10191B":"#FFFFFF";
};
const mark = (team, size="") => `<div class="team-crest ${size}" style="background:${teamColor(team)};color:${teamInk(team)}">${esc(team.short)}</div>`;
const crestDot = (team) => `<span class="team-dot" style="background:${teamColor(team)}"></span>`;
const loading = () => '<div class="loading"><div class="spin"></div> Loading league data...</div>';

async function api(url) {
  const response = await fetch(BASE + url, { headers: {"Accept":"application/json"} });
  if (!response.ok) throw new Error(`HTTP ${response.status}: data unavailable`);
  return response.json();
}

const crumb = { overview:"Overview",teams:"Teams & starters",schedule:"Season schedule",
                mvp:"MVP race",game:"Game center" };
function setView(view) {
  if (!crumb[view]) return;
  if (state.view !== view) pause();
  state.view = view;
  document.querySelectorAll(".nav-link").forEach(el => el.classList.toggle("active",el.dataset.view===view));
  $("#crumb").textContent = crumb[view];
  render();
}
function head(title, subtitle, caption="THE PRODUCTION LEAGUE") {
  return `<div class="page-header"><div class="overline">${esc(caption)}</div><h1>${esc(title)}</h1><p>${esc(subtitle)}</p></div>`;
}
function panel(title, body, meta="") {
  return `<article class="panel"><div class="panel-pad"><div class="panel-heading"><h2>${esc(title)}</h2>${meta?`<span class="tag">${esc(meta)}</span>`:""}</div>${body}</div></article>`;
}
function fixture(g, compact=false) {
  const home=byId(g.home),away=byId(g.away);
  const score=g.status==="FINAL" ? `${g.home_score} — ${g.away_score}` : "– : –";
  return `<button class="fixture" data-game="${esc(g.id)}" aria-label="Watch ${esc(home.name)} versus ${esc(away.name)}">
    <div><div class="match-names">${crestDot(home)}${esc(home.name)} <span class="muted">vs</span> ${crestDot(away)}${esc(away.name)}</div>
    <small>${esc(g.id.startsWith("semi")?"PLAYOFF SEMIFINAL":g.id==="championship"?"CHAMPIONSHIP":"REGULAR SEASON")} · ${esc(g.status)}</small></div>
    <div class="fixture-score">${score} <span style="font-size:12px;color:var(--lime)">▶</span></div>
  </button>`;
}
function standingsTable(rows) {
  return `<table class="standings-table"><thead><tr><th>#</th><th>TEAM</th><th class="numeric">W</th><th class="numeric">L</th><th class="numeric">T</th><th class="numeric">DIFF</th></tr></thead>
  <tbody>${rows.map((r,i)=>`<tr><td class="rank">${i+1}</td><td><div class="team-cell">${crestDot(byId(r.team_id))}
  <button class="link-btn" data-team="${esc(r.team_id)}">${esc(r.name)}</button></div></td>
  <td class="numeric">${r.wins}</td><td class="numeric">${r.losses}</td><td class="numeric">${r.ties}</td>
  <td class="numeric" style="color:${r.diff>=0?'var(--lime)':'var(--red)'}">${r.diff>0?'+':''}${r.diff}</td></tr>`).join("")}</tbody></table>`;
}
function hero(data) {
  return `<section class="hero"><div class="hero-text"><div class="overline">SEASON 01 <span style="color:#eac66d"> · ${data.week>10?"POSTSEASON":"REGULAR SEASON"} · WEEK ${data.week}</span></div>
  <h1>BUILT TO<br>WIN.</h1><p>Where production teams become football franchises. Real game strategy, weekly performance-powered athletes, and a championship on the line.</p>
  <div class="hero-stats"><div class="hero-stat"><strong>${data.counts.teams}</strong><span>PRODUCTION TEAMS</span></div>
  <div class="hero-stat"><strong>${data.counts.athletes}</strong><span>FICTIONAL ATHLETES</span></div>
  <div class="hero-stat"><strong>${data.counts.games}</strong><span>SEASON MATCHUPS</span></div></div></div>
  <div class="hero-graphic" aria-hidden="true"><div class="football-illustration"></div></div></section>`;
}
function featuredGame(g) {
  if (!g) return '<p class="muted">No game on this week.</p>';
  const home=byId(g.home),away=byId(g.away);
  return `<div class="scoreboard"><div class="mini-team">${mark(home)}<b>${esc(home.name)}</b><span>HOME</span></div>
  <div class="score-text">${g.home_score??"–"} <span class="vs">:</span> ${g.away_score??"–"}</div>
  <div class="mini-team">${mark(away)}<b>${esc(away.name)}</b><span>AWAY</span></div></div>
  <div class="game-kicker">${esc(g.status)} · WEEK ${g.week} · ${isPlayoff(g.week)?"POSTSEASON":"REGULAR SEASON"}</div>
  <div class="panel-actions"><button class="primary-btn" data-game="${esc(g.id)}">▶ WATCH GAME REPLAY</button></div>`;
}
function mvpRow(p,i) {
  const t=byId(p.team_id);
  return `<div class="mvp-row"><div class="place">${i+1}</div>${crestDot(t)}
  <div class="name"><button class="link-btn" data-player="${esc(p.player_id)}">${esc(p.alias)}</button>
  <small>${esc(t.name)} · #${p.number}</small></div>
  <strong style="font-family:'Barlow Condensed';font-size:20px">${p.mvp_score.toFixed(1)}</strong></div>`;
}
function overview(data) {
  const top = data.mvp[0], leader = data.games[0], t = top?byId(top.team_id):null;
  return hero(data)+`<section class="layout-main"><div class="stack">
  ${panel("Featured matchup", featuredGame(leader),`WEEK ${data.week}`)}
  ${panel("League standings", standingsTable(data.standings), "REGULAR SEASON")}
  </div><div class="stack">
  ${panel("This week's games", `<div class="week-games">${data.games.map(g=>fixture(g,true)).join("")}</div>`, "SCHEDULE")}
  ${panel("MVP watch", top?`<div class="mvp-feature"><div class="avatar" style="background:${teamColor(t)};color:${teamInk(t)}" data-number="#${top.number}">★</div>
     <div><small>FRONTRUNNER · WEEK ${data.week}</small><b>${esc(top.alias)}</b><small>${esc(t.name)} · ${top.overall} AVG OVR</small></div>
     <div style="margin-left:auto"><span class="rating-pill">${top.mvp_score.toFixed(1)}</span></div></div>
     ${data.mvp.slice(1,5).map((p,i)=>mvpRow(p,i+1)).join("")}
     <div class="panel-actions"><button class="ghost-btn" data-view="mvp">VIEW MVP RACE →</button></div>`:"No eligible players yet.","TOP PERFORMERS")}
  </div></section>`;
}
function teamTiles() {
  return head("Choose your team","Every franchise draws its starting eleven exclusively from its own opt-in production teammates. Ratings update weekly; the best positional fit gets the start.")+
  `<div class="team-grid">${state.league.teams.map(t=>`<button class="team-tile" data-team="${esc(t.id)}" style="--tile-color:${teamColor(t)}">
   ${mark(t)}<strong>${esc(t.name)}</strong><p>${esc(t.motto)}</p>
   <div class="tile-foot"><span>TEAM ROSTER</span><span>VIEW ROSTER →</span></div></button>`).join("")}</div>`;
}
function lineupColumn(title, entries) {
  return panel(title, `<div class="depth-list">${entries.map(p=>`<div class="depth-row">
    <div class="depth-position">${esc(p.position)}</div><div class="player-info"><button class="link-btn" data-player="${esc(p.player_id)}">${esc(p.alias)}</button>
    <small>#${p.number} · FIT ${p.fit}</small></div><span class="depth-overall">${p.overall}</span></div>`).join("")}</div>`,
    "11 STARTERS · POSITION OPTIMIZED");
}
async function teamDetail() {
  const d=await api(`/api/teams/${encodeURIComponent(state.teamId)}?week=${state.week}`);
  const l=d.lineup;const color=d.color;
  return `<button class="back-button" data-back-teams>← ALL TEAMS</button>
   <div class="team-detail-hero" style="--team-shadow:${teamColor(d)}48">${mark(d)}<div><div class="overline">TEAM ROSTER · WEEK ${state.week}</div>
   <h1>${esc(d.name)}</h1><p>${esc(d.motto)}</p></div></div>
   <div class="stat-grid"><div class="statbox"><strong>${l.eligible_count}</strong><small>Eligible teammates</small></div>
   <div class="statbox"><strong>${l.offense.length}</strong><small>Offense starters</small></div>
   <div class="statbox"><strong>${l.defense.length}</strong><small>Defense starters</small></div>
   <div class="statbox"><strong>${l.reserves.length}</strong><small>Other team contributors</small></div></div>
   <div class="overline" style="margin:20px 0 10px">${esc(l.status)} · SAME-TEAM LINEUP · NO CROSS-TEAM DRAFTS</div>
   <div class="position-group">${lineupColumn("Offense · Starting XI",l.offense)}
     ${lineupColumn("Defense · Starting XI",l.defense)}</div>
   <div style="margin-top:18px">${panel("Bench & depth", l.reserves.length ?
    `<div class="depth-list">${l.reserves.map(p=>`<div class="depth-row"><span class="star">★</span><div class="player-info"><button class="link-btn" data-player="${esc(p.player_id)}">${esc(p.alias)}</button><small>#${p.number} · ELIGIBLE TEAMMATE</small></div>
     <span class="depth-overall">${p.overall}</span></div>`).join("")}</div>`:"No other eligible participants.")}</div>
   <p class="section-note" style="margin:18px 0">Starters are selected by maximum-weight positional matching from this team's approved eligible roster. One athlete may play both ways; not two slots on the same unit. Selection is game-only and not a workplace evaluation.</p>`;
}
function scheduleView(data) {
  if (!state.schedule) return loading();
  const grouped = Array.from({length:12},(_,i)=>({week:i+1, games:state.schedule.games.filter(g=>g.week===i+1)}));
  return head("The road to the championship","Six production franchises, a complete double round-robin regular season, top-four semifinals and a winner-takes-all title game.")+
  `<div class="stat-grid"><div class="statbox"><strong>10</strong><small>Round robin weeks</small></div>
  <div class="statbox"><strong>30</strong><small>Regular matches</small></div>
  <div class="statbox"><strong>4</strong><small>Playoff teams</small></div>
  <div class="statbox"><strong>1</strong><small>Champion</small></div></div>
  <div class="layout-main" style="grid-template-columns:repeat(2,minmax(0,1fr))" id="schedule-columns">
   ${[grouped.slice(0,6),grouped.slice(6)].map(part=>`<div class="stack">${part.map(w=>panel(w.week===11?"Semifinals":w.week===12?"Championship":`Week ${w.week}`,
       `<div class="week-games">${w.games.map(g=>fixture(g)).join("")}</div>`,
       w.week>10?"POSTSEASON":w.week===state.week?"CURRENT WEEK":"REGULAR SEASON")).join("")}</div>`).join("")}</div>`;
}
function mvpView(data) {
  const all=data.mvp;
  return head("The MVP race","The strongest football performers across all six teams. The demonstrative formula combines verified synthetic work-derived player ratings and simulated football production.")+
   `<div class="mvp-board">${all.slice(0,3).map((p,i)=>{const t=byId(p.team_id);
      return `<div class="mvp-podium"><span class="podium-no">#0${i+1}</span><div class="avatar" style="background:${teamColor(t)};color:${teamInk(t)}" data-number="#${p.number}">★</div>
        <h2>${esc(p.alias)}</h2><p>${esc(t.name)}</p>
        <div class="scoreboard"><div><small class="muted">MVP POINTS</small><div style="font:900 32px 'Barlow Condensed'">${p.mvp_score.toFixed(1)}</div></div>
        <div><small class="muted">AVG OVR</small><div style="font:900 32px 'Barlow Condensed'">${p.overall}</div></div></div>
        <button class="ghost-btn" style="margin-top:12px;width:100%" data-player="${esc(p.player_id)}">PLAYER CARD →</button></div>`}).join("")}</div>
   <div style="margin-top:18px">${panel("League-wide leaderboard",
      `<table class="data-table"><thead><tr><th>RANK</th><th>ATHLETE</th><th>TEAM</th><th class="numeric">AVG OVR</th><th class="numeric">FOOTBALL IMPACT</th><th class="numeric">MVP SCORE</th></tr></thead>
      <tbody>${all.map((p,i)=>`<tr><td>${i+1}</td><td><button class="link-btn" data-player="${esc(p.player_id)}">${esc(p.alias)}</button></td>
      <td>${esc(byId(p.team_id).short)}</td><td class="numeric">${p.overall}</td><td class="numeric">${p.football_impact}</td><td class="numeric" style="color:var(--lime);font-weight:800">${p.mvp_score.toFixed(1)}</td></tr>`).join("")}</tbody></table>`,"SYNTHETIC MVP MODEL")}</div>
   <p class="section-note" style="margin-top:15px">The MVP score is a demonstration entertainment metric, not an employee ranking, salary input, disciplinary signal or work performance grade.</p>`;
}
function scoreGame(game) {
  const home=byId(game.home),away=byId(game.away);
  return `<div class="game-top"><div class="overline" style="text-align:center;margin-bottom:15px">
    ${game.id==='championship'?'CHAMPIONSHIP':game.id.startsWith('semi')?'PLAYOFF SEMIFINAL':`WEEK ${game.week} · REGULAR SEASON`}</div>
    <div class="scoreboard"><div class="mini-team">${mark(home)}<b>${esc(home.name)}</b><span>HOME</span></div>
    <div class="score-text">${game.home_score??'–'} <span class="vs">:</span> ${game.away_score??'–'}</div>
    <div class="mini-team">${mark(away)}<b>${esc(away.name)}</b><span>AWAY</span></div></div>
    <div class="game-kicker">${game.status} · DETERMINISTIC SEED ${esc(String(game.seed??'—').slice(-9))}
      ${game.tiebreak_winner?' · PLAYOFF TIEBREAK APPLIED':''}</div></div>`;
}
function fieldSvg(game, play) {
  const h=byId(game.home), a=byId(game.away);
  const o=byId(play.offense),d=byId(play.defense),ro=game.rosters[play.offense],rd=game.rosters[play.defense];
  const x=Math.max(120,Math.min(880,100+play.yard_line*8));
  const end=Math.max(120,Math.min(880,100+play.end_yard*8));
  const offenseXY = ro.offense.map((p,i)=>{
    const y=72+(i*38)%392;
    const offset=p.position==='WR'?-14:p.position==='QB'?-58:p.position==='RB'?-96:p.position==='TE'?-20:-4;
    return {p,x:Math.max(110,x+offset-(i%3)*4),y};
  });
  const defenseXY=rd.defense.map((p,i)=>{
    const y=75+(i*36)%385;
    const offset=p.position==='DL'?22:p.position==='LB'?58:100;
    return {p,x:Math.min(892,x+offset+(i%2)*4),y};
  });
  const markings=Array.from({length:11},(_,i)=>{
    const px=100+i*80;
    return `<line x1="${px}" x2="${px}" y1="24" y2="500" stroke="#e4ffe2" stroke-opacity=".38" stroke-width="2"/>
      <text x="${px}" y="45" text-anchor="middle" fill="#d5e9dc" opacity=".5" font-size="14" font-family="Arial">${i<=5?i*10:(10-i)*10}</text>`;
  }).join("");
  function dot(pos, team, alpha){
    const p=pos.p;
    const active=play.actor===p.player_id || play.target===p.player_id;
    return `<g><circle cx="${pos.x}" cy="${pos.y}" r="${active?19:14}" fill="${esc(team.color)}" stroke="${active?'#fff4b0':'#09261c'}" stroke-width="${active?4:2}" opacity="${alpha}"/>
      <text x="${pos.x}" y="${pos.y+4.3}" text-anchor="middle" font-size="11" font-family="Arial" font-weight="bold" fill="#10261e">${p.number??p.slot}</text></g>`;
  }
  return `<svg viewBox="0 0 1000 525" role="img" aria-label="Top-down 2D football play: ${esc(o.name)} attacking ${esc(d.name)}, ball on the ${play.yard_line} yard line.">
    <defs><pattern id="grass" width="80" height="525" patternUnits="userSpaceOnUse"><rect width="80" height="525" fill="#215e41"/><rect width="40" height="525" fill="#276747"/></pattern></defs>
    <rect width="1000" height="525" fill="#0b3827"/><rect x="100" y="24" width="800" height="476" fill="url(#grass)" stroke="#e4ffe2" stroke-width="3"/>
    <rect x="0" y="24" width="100" height="476" fill="${teamColor(h)}" opacity=".98"/>
    <rect x="900" y="24" width="100" height="476" fill="${teamColor(a)}" opacity=".98"/>
    <text x="52" y="260" fill="#fff" font-family="Arial" font-size="28" font-weight="bold" text-anchor="middle" transform="rotate(-90 52 260)">${esc(h.short)}</text>
    <text x="948" y="260" fill="#fff" font-family="Arial" font-size="28" font-weight="bold" text-anchor="middle" transform="rotate(90 948 260)">${esc(a.short)}</text>
    ${markings}<line x1="0" y1="262" x2="1000" y2="262" stroke="#e6fce2" stroke-opacity=".24" stroke-dasharray="4 8"/>
    <circle cx="500" cy="262" r="64" fill="none" stroke="#e0f6e4" stroke-opacity=".21" stroke-width="4"/>
    <text x="500" y="270" fill="#e0f6e4" opacity=".19" font-family="Arial" font-weight="900" font-size="31" text-anchor="middle">FOCUS</text>
    <line x1="${x}" y1="24" x2="${x}" y2="500" stroke="#ffdf71" stroke-width="5" stroke-opacity=".8"/>
    <line x1="${Math.min(900,x+play.distance*8)}" y1="24" x2="${Math.min(900,x+play.distance*8)}" y2="500" stroke="#ecf7b7" stroke-width="3" stroke-opacity=".6"/>
    ${defenseXY.map(p=>dot(p,d,.98)).join("")}
    ${offenseXY.map(p=>dot(p,o,.98)).join("")}
    <path d="M${x} 262 Q${(x+end)/2} 170 ${end} 250" stroke="#fff4a5" stroke-width="4" fill="none" stroke-dasharray="9 7" opacity=".8"/>
    <ellipse cx="${end}" cy="250" rx="11" ry="7" transform="rotate(-25 ${end} 250)" fill="#e2a16c" stroke="#fff3d0" stroke-width="2"/>
    <rect x="385" y="502" width="230" height="20" rx="5" fill="#09291f"/>
    <text x="500" y="516" text-anchor="middle" fill="#d9eedc" font-size="11" font-family="Arial" font-weight="bold">PLAY ${play.number} · Q${play.quarter} · ${Math.floor(play.clock/60)}:${String(play.clock%60).padStart(2,'0')}</text>
  </svg>`;
}
function replayBlock() {
  const g=state.game;
  if (!g) return loading();
  if (!g.plays.length) return panel("Unavailable", "<p>Game cannot start: roster is incomplete.</p>");
  const play=g.plays[state.playIndex] || g.plays[0];
  return `<div class="layout-main"><div class="stack">
    <div class="field-frame"><div id="field-host">${fieldSvg(g,play)}</div>
    <div class="field-caption"><b>TOP-DOWN FOOTBALL REPLAY · 22 STARTERS</b><span id="play-count">PLAY ${state.playIndex+1} OF ${g.plays.length}</span></div></div>
    <div class="replay-controls"><button class="ghost-btn" data-replay="prev" title="Previous play">◀</button>
    <button class="primary-btn" data-replay="toggle" id="play-toggle">${state.playing?'❚❚ PAUSE':'▶ PLAY GAME'}</button>
    <button class="ghost-btn" data-replay="next" title="Next play">▶▶</button>
    <button class="ghost-btn" data-replay="reset">↺ RESTART</button>
    <span class="muted" style="font-size:11px">Seeded football simulation · no live controls</span></div>
    <div id="play-description" class="play-meta"><strong>${esc(play.description)}</strong><span>${esc(play.kind)} · DOWN ${play.down} · ${play.distance} TO GO · BALL ON ${play.yard_line}</span></div>
    ${panel("How the game works",`<p class="section-note">Each weekly starting lineup is selected from that production team's highest-performing eligible teammates by positional fit. The full game is then simulated with deterministic seeded football rules. Player attributes influence play probabilities, not guaranteed outcomes. These 2D colored circles are original stand-ins for football sprites.</p>`)}
    </div>
    <div class="stack">${panel("Play-by-play",`<div class="play-log" id="play-log">${g.plays.map((p,i)=>
     `<button class="play-row ${i===state.playIndex?'selected':''}" data-play-index="${i}"><span class="play-no">${String(i+1).padStart(3,'0')}</span>
     <span class="event-tag">${esc(p.kind)}</span> ${esc(p.description)}</button>`).join("")}</div>`, "GAME FILM")}
     ${panel("Final stats", gameStats(g), "BOX SCORE")}</div></div>`;
}
function gameStats(g) {
  const values=Object.entries(g.player_stats).map(([pid,st])=>{
    const impact=(st.pass_yards*.035+st.pass_td*8+st.rush_yards*.12+st.rush_td*9+st.receiving_yards*.12+
      st.receiving_td*9+st.tackles*.85+st.interceptions*10+st.sacks*5);
    return {pid,impact,st};
  }).sort((a,b)=>b.impact-a.impact).slice(0,9);
  const playerName = (pid) => {
    for (const team of Object.values(g.rosters)) {
      const row=[...team.offense,...team.defense,...team.reserves].find(p=>p.player_id===pid);
      if (row) return row.alias;
    }
    return pid;
  };
  return `<table class="data-table"><thead><tr><th>ATHLETE</th><th class="numeric">PASS</th><th class="numeric">RUSH</th><th class="numeric">REC</th><th class="numeric">TACK</th></tr></thead>
   <tbody>${values.map(v=>`<tr><td><button class="link-btn" data-player="${esc(v.pid)}">${esc(playerName(v.pid))}</button></td>
     <td class="numeric">${v.st.pass_yards}</td><td class="numeric">${v.st.rush_yards}</td><td class="numeric">${v.st.receiving_yards}</td><td class="numeric">${v.st.tackles}</td></tr>`).join("")}</tbody></table>`;
}
function updateReplay() {
  const p=state.game?.plays[state.playIndex];
  if (!p || state.view!=="game") return;
  if ($("#field-host")) $("#field-host").innerHTML=fieldSvg(state.game,p);
  if ($("#play-description")) $("#play-description").innerHTML=`<strong>${esc(p.description)}</strong><span>${esc(p.kind)} · DOWN ${p.down} · ${p.distance} TO GO · BALL ON ${p.yard_line}</span>`;
  if ($("#play-count")) $("#play-count").textContent=`PLAY ${state.playIndex+1} OF ${state.game.plays.length}`;
  if ($("#play-toggle")) $("#play-toggle").textContent=state.playing?"❚❚ PAUSE":"▶ PLAY GAME";
  document.querySelectorAll(".play-row").forEach((el,i)=>el.classList.toggle("selected",i===state.playIndex));
  const selected=document.querySelector(".play-row.selected");
  if (selected && state.playing) selected.scrollIntoView({block:"nearest",behavior:"auto"});
}
function pause(){state.playing=false;if(state.timer){clearInterval(state.timer);state.timer=null;}}
function toggle(){if(state.playing){pause();updateReplay();return;}
  if(!state.game?.plays?.length)return;
  if(state.playIndex>=state.game.plays.length-1)state.playIndex=0;
  state.playing=true;state.timer=setInterval(()=>{
    if(state.playIndex>=state.game.plays.length-1){pause();updateReplay();return;}
    state.playIndex++;updateReplay();
  },750);updateReplay();
}
async function gameView() {
  if (!state.gameId) {
    const first=state.league.games[0];
    if(first) state.gameId=first.id;
  }
  if (!state.gameId) return head("Game center","No games have been generated.");
  if (!state.game || state.game.id!==state.gameId) {
    state.game=await api(`/api/games/${encodeURIComponent(state.gameId)}`);state.playIndex=0;
  }
  return head("Game center","Watch the game unfold play by play. Every athlete is represented as a colored 2D marker on the field.","THE FIELD · 2D GAME FILM")+
    scoreGame(state.game)+replayBlock();
}
async function playerModal(id) {
  try {
    const d=await api(`/api/players/${encodeURIComponent(id)}?week=${state.week}`);
    const t=byId(d.team_id),r=d.ratings;
    const el=document.createElement("div");el.className="modal-scrim";el.id="player-modal";
    el.innerHTML=`<section class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-name">
      <div class="modal-head"><span class="overline">WEEK ${state.week} · SYNTHETIC PLAYER CARD</span><button class="close" data-close aria-label="Close card">×</button></div>
      <div class="team-detail-hero" style="margin-top:15px;padding:15px;--team-shadow:${teamColor(t)}44"><div class="avatar" style="background:${teamColor(t)};color:${teamInk(t)}" data-number="#${d.number}">★</div>
        <div><h2 id="modal-name" style="margin:0">${esc(d.alias)}</h2><div class="muted">${esc(t.name)} · AVG RATING</div><span class="rating-pill">${r.overall}</span></div></div>
      ${Object.entries(r.components).map(([key,val])=>`<div class="metric-line"><span>${esc(key).toUpperCase()}</span><div class="meter"><i style="width:${val}%"></i></div><b>${val}</b></div>`).join("")}
      <p class="section-note">Eligible exposure: ${num(r.exposure_minutes)} synthetic minutes. Confidence ${Math.round(r.confidence*100)}%. These are fictional sample ratings, never an employee grade.</p>
      <button class="primary-btn" data-close style="width:100%">CLOSE CARD</button></section>`;
    document.body.appendChild(el);
    el.querySelector("[data-close]").focus();
  } catch(err) { console.error("Player card unavailable",err); }
}
let lastRender=0;
async function render() {
  const tick=++lastRender;
  $("#app").innerHTML=loading();
  try {
    if (!state.league || state.league.week!==state.week) state.league=await api(`/api/league?week=${state.week}`);
    const isSynthetic=state.league.mode==="SYNTHETIC";
    const chip=$(".demo-chip");
    if(chip) chip.innerHTML=isSynthetic?"<i></i> SYNTHETIC DATA":"<i></i> INTERNAL APPROVED";
    const sidebar=$(".sidebar-bottom span");
    if(sidebar) sidebar.textContent=isSynthetic?"100% fictional athletes":"Approved internal only";
    let html="";
    if(state.view==="overview") html=overview(state.league);
    if(state.view==="teams") html=state.teamId?await teamDetail():teamTiles();
    if(state.view==="schedule") {
      if (!state.schedule) state.schedule=await api("/api/schedule");
      html=scheduleView(state.league);
    }
    if(state.view==="mvp") html=mvpView(state.league);
    if(state.view==="game") html=await gameView();
    if(tick===lastRender) $("#app").innerHTML=html;
  } catch(error) {
    console.error("FOCUS Gridiron error",error);
    if(tick===lastRender) $("#app").innerHTML=`<div class="panel panel-pad"><h2>League unavailable</h2><p class="muted">${esc(error.message)}</p><button class="primary-btn" data-retry>RETRY</button></div>`;
  }
}

document.addEventListener("click",async (event)=>{
  const t=event.target.closest("[data-view],[data-team],[data-game],[data-player],[data-back-teams],[data-replay],[data-play-index],[data-close],[data-retry]");
  if(!t)return;
  if(t.dataset.close!==undefined){$("#player-modal")?.remove();return;}
  if(t.dataset.view){state.teamId=null;setView(t.dataset.view);return;}
  if(t.dataset.team){state.teamId=t.dataset.team;setView("teams");return;}
  if(t.dataset.backTeams!==undefined){state.teamId=null;setView("teams");return;}
  if(t.dataset.player){await playerModal(t.dataset.player);return;}
  if(t.dataset.game){pause();state.gameId=t.dataset.game;state.game=null;state.playIndex=0;setView("game");return;}
  if(t.dataset.retry!==undefined){render();return;}
  if(t.dataset.playIndex!==undefined){pause();state.playIndex=Number(t.dataset.playIndex);updateReplay();return;}
  if(t.dataset.replay){const action=t.dataset.replay;
    if(action==="toggle"){toggle();return;}
    pause();
    if(action==="next")state.playIndex=Math.min(state.game.plays.length-1,state.playIndex+1);
    if(action==="prev")state.playIndex=Math.max(0,state.playIndex-1);
    if(action==="reset")state.playIndex=0;
    updateReplay();
  }
});
document.addEventListener("keydown",e=>{if(e.key==="Escape"){$("#player-modal")?.remove();pause();}});
const weekSelect=$("#week");
for(let w=1;w<=12;w++){
  const option=document.createElement("option");option.value=w;
  option.textContent=w>10?(w===11?"11 · Playoffs":"12 · Final"):`Week ${String(w).padStart(2,"0")}`;
  weekSelect.appendChild(option);
}
weekSelect.value="1";
weekSelect.addEventListener("change",()=>{
  pause();state.week=Number(weekSelect.value);state.gameId=null;state.game=null;render();
});
render();
