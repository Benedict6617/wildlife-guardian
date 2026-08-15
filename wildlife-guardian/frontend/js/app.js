/* Wildlife Guardian dashboard app logic. Vanilla JS, no build step. */

let map, markersLayer;
let charts = {};
let zoneCache = [];
let speciesCache = [];
let rangerCache = [];

// ---------------------------------------------------------------- helpers

function fmtDate(iso) {
  if (!iso) return "\u2014";
  const d = new Date(iso);
  return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function fmtMoney(n) {
  return `$${Number(n).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function badge(value) {
  const cls = String(value).toLowerCase().replace(/\s+/g, "_");
  const label = String(value).replace(/_/g, " ");
  return `<span class="badge badge-${cls}">${label}</span>`;
}

function toast(message, type = "success") {
  let el = document.getElementById("toast");
  if (!el) {
    el = document.createElement("div");
    el.id = "toast";
    el.className = "toast";
    document.body.appendChild(el);
  }
  el.textContent = message;
  el.className = `toast show ${type}`;
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove("show"), 3200);
}

function el(html) {
  const t = document.createElement("template");
  t.innerHTML = html.trim();
  return t.content.firstChild;
}

function zoneName(id) {
  const z = zoneCache.find((z) => z.id === id);
  return z ? z.name : "\u2014";
}

function speciesName(id) {
  const s = speciesCache.find((s) => s.id === id);
  return s ? s.common_name : id;
}

function rangerName(id) {
  const r = rangerCache.find((r) => r.id === id);
  return r ? r.full_name : "Unassigned";
}

async function safeCall(fn, fallback) {
  try {
    return await fn();
  } catch (e) {
    console.error(e);
    return fallback;
  }
}

// ---------------------------------------------------------------- nav

function setActiveView(viewId) {
  document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach((n) => n.classList.remove("active"));
  document.getElementById(viewId)?.classList.add("active");
  document.querySelector(`.nav-item[data-view="${viewId}"]`)?.classList.add("active");
  window.location.hash = viewId;
  loadView(viewId);
}

function loadView(viewId) {
  const loaders = {
    "view-overview": loadOverview,
    "view-tracking": loadTracking,
    "view-alerts": loadAlerts,
    "view-patrols": loadPatrols,
    "view-veterinary": loadVeterinary,
    "view-cites": loadCites,
    "view-community": loadCommunity,
    "view-fundraising": loadFundraising,
  };
  loaders[viewId]?.();
}

// ---------------------------------------------------------------- overview

async function loadOverview() {
  const wrap = document.getElementById("overview-metrics");
  wrap.innerHTML = `<div class="empty-state">Loading operational summary\u2026</div>`;

  const summary = await safeCall(() => api.dashboardSummary(), null);
  if (!summary) {
    wrap.innerHTML = `<div class="empty-state">Could not reach the API. Is the backend running at ${API_BASE}?</div>`;
    return;
  }

  wrap.className = "grid grid-4";
  wrap.innerHTML = `
    ${metricCard("Animals Tracked", summary.total_animals_tracked, `${summary.active_collars} active collars`)}
    ${metricCard("Open Alerts", summary.open_alerts, `${summary.critical_alerts_7d} critical (7d)`)}
    ${metricCard("Patrols This Week", summary.patrols_this_week, `${summary.snares_pending_removal} snares pending removal`)}
    ${metricCard("Raised To Date", fmtMoney(summary.total_raised_usd), `${summary.active_campaigns} active campaigns`)}
  `;

  const alerts = await safeCall(() => api.alerts({ days: 30 }), []);
  renderSeverityChart(alerts);
  renderRiskPulse(zoneCache, alerts);

  const zonesBody = document.getElementById("overview-zones-body");
  zonesBody.innerHTML = zoneCache
    .map(
      (z) => `<tr>
        <td>${z.name}</td>
        <td>${riskBar(z.water_index, "var(--teal)")}</td>
        <td>${riskBar(z.forage_index, "var(--green)")}</td>
        <td>${riskBar(z.risk_index, "var(--red)")}</td>
      </tr>`
    )
    .join("") || `<tr><td colspan="4" class="empty-state">No zone data</td></tr>`;

  const recentAlerts = alerts.slice(0, 6);
  const alertsBody = document.getElementById("overview-alerts-body");
  alertsBody.innerHTML =
    recentAlerts
      .map(
        (a) => `<tr>
          <td>${fmtDate(a.detected_at)}</td>
          <td>${a.alert_type.replace(/_/g, " ")}</td>
          <td>${badge(a.severity)}</td>
          <td>${badge(a.status)}</td>
        </tr>`
      )
      .join("") || `<tr><td colspan="4" class="empty-state">No recent alerts</td></tr>`;
}

function metricCard(label, value, delta) {
  return `<div class="card metric-card">
    <div class="label">${label}</div>
    <div class="value">${value}</div>
    <div class="delta">${delta}</div>
  </div>`;
}

function riskBar(value, color) {
  const pct = Math.round(value * 100);
  return `<div class="progress-track" style="width:120px"><div class="progress-fill" style="width:${pct}%;background:${color}"></div></div>`;
}

function renderSeverityChart(alerts) {
  const ctx = document.getElementById("chart-severity");
  if (!ctx) return;
  const counts = { low: 0, medium: 0, high: 0, critical: 0 };
  alerts.forEach((a) => { if (counts[a.severity] !== undefined) counts[a.severity]++; });

  charts.severity?.destroy();
  charts.severity = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["Low", "Medium", "High", "Critical"],
      datasets: [{
        data: [counts.low, counts.medium, counts.high, counts.critical],
        backgroundColor: ["#3FA796", "#F2B134", "#E4572E", "#8A2E1E"],
        borderWidth: 0,
      }],
    },
    options: {
      plugins: { legend: { position: "bottom", labels: { color: "#8FAFA0", font: { size: 11 } } } },
      cutout: "62%",
    },
  });
}

function renderRiskPulse(zones, alerts) {
  const strip = document.getElementById("pulse-strip");
  if (!strip) return;
  const bars = [];
  const n = 40;
  for (let i = 0; i < n; i++) {
    const base = zones.length ? zones[i % zones.length].risk_index : 0.2;
    const jitter = Math.sin(i * 1.7 + Date.now() / 4000) * 0.15;
    const v = Math.max(0.08, Math.min(1, base + jitter));
    bars.push(v);
  }
  strip.innerHTML = bars
    .map((v) => {
      const cls = v > 0.6 ? "risk-high" : v > 0.35 ? "risk-med" : "risk-low";
      return `<div class="pulse-bar ${cls}" style="height:${Math.round(v * 100)}%"></div>`;
    })
    .join("");
}

// ---------------------------------------------------------------- tracking

async function loadTracking() {
  if (!map) initMap();

  const animals = await safeCall(() => api.animals(), []);

  markersLayer.clearLayers();

  const select = document.getElementById("tracking-animal-select");
  select.innerHTML = animals.map((a) => `<option value="${a.id}">${a.tag_name} (${speciesName(a.species_id)})</option>`).join("");

  const bounds = [];
  for (const a of animals) {
    const hist = await safeCall(() => api.animalHistory(a.id, 1), []);
    if (!hist.length) continue;
    const last = hist[hist.length - 1];
    const marker = L.circleMarker([last.latitude, last.longitude], {
      radius: 7,
      color: "#D9A441",
      fillColor: "#D9A441",
      fillOpacity: 0.85,
      weight: 2,
    }).bindPopup(
      `<b>${a.tag_name}</b><br>${speciesName(a.species_id)}<br><span class="mono">${last.latitude.toFixed(4)}, ${last.longitude.toFixed(4)}</span><br>${fmtDate(last.recorded_at)}`
    );
    marker.addTo(markersLayer);
    bounds.push([last.latitude, last.longitude]);
  }
  if (bounds.length) map.fitBounds(bounds, { padding: [30, 30] });

  const body = document.getElementById("tracking-animals-body");
  body.innerHTML = animals
    .map(
      (a) => `<tr>
        <td>${a.tag_name}</td>
        <td>${speciesName(a.species_id)}</td>
        <td>${a.sex || "\u2014"}</td>
        <td>${badge(a.status)}</td>
        <td>${zoneName(a.home_zone_id)}</td>
        <td><button class="btn-predict" data-id="${a.id}">Predict movement</button></td>
      </tr>`
    )
    .join("") || `<tr><td colspan="6" class="empty-state">No animals</td></tr>`;

  body.querySelectorAll(".btn-predict").forEach((btn) => {
    btn.addEventListener("click", () => predictMovement(btn.dataset.id));
  });
}

function initMap() {
  map = L.map("map", { zoomControl: true }).setView([0.30, 36.82], 11);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "\u00a9 OpenStreetMap contributors",
    maxZoom: 17,
  }).addTo(map);
  markersLayer = L.layerGroup().addTo(map);
}

async function predictMovement(animalId) {
  const result = await safeCall(() => api.predictMovement(animalId), null);
  const panel = document.getElementById("prediction-panel");
  if (!result) {
    panel.innerHTML = `<div class="empty-state">Not enough telemetry history to predict movement for this animal.</div>`;
    return;
  }
  panel.innerHTML = `
    <div class="card">
      <h3>Movement Prediction</h3>
      <p class="mono">${result.predicted_latitude.toFixed(5)}, ${result.predicted_longitude.toFixed(5)}</p>
      <p><b>Likely zone:</b> ${zoneName(result.predicted_zone_id)} &middot; <b>Confidence:</b> ${result.confidence_pct}%</p>
      <p class="muted">${result.rationale}</p>
    </div>`;

  if (map) {
    L.circleMarker([result.predicted_latitude, result.predicted_longitude], {
      radius: 8,
      color: "#3FA796",
      fillColor: "#3FA796",
      fillOpacity: 0.5,
      weight: 2,
      dashArray: "3,3",
    }).bindPopup("Predicted next location").addTo(markersLayer).openPopup();
    map.panTo([result.predicted_latitude, result.predicted_longitude]);
  }
}

// ---------------------------------------------------------------- alerts / security

async function loadAlerts() {
  const [alerts, sensors, missions, snares] = await Promise.all([
    safeCall(() => api.alerts({ days: 30 }), []),
    safeCall(() => api.sensors(), []),
    safeCall(() => api.droneMissions(), []),
    safeCall(() => api.snares({ status: "pending_removal" }), []),
  ]);

  const body = document.getElementById("alerts-body");
  body.innerHTML =
    alerts
      .map(
        (a) => `<tr>
      <td>${fmtDate(a.detected_at)}</td>
      <td>${a.alert_type.replace(/_/g, " ")}</td>
      <td>${badge(a.severity)}</td>
      <td class="mono">${a.confidence_pct}%</td>
      <td class="mono">${a.latitude.toFixed(3)}, ${a.longitude.toFixed(3)}</td>
      <td>${badge(a.status)}</td>
      <td>
        <select class="status-select" data-id="${a.id}">
          ${["new", "acknowledged", "dispatched", "resolved", "false_alarm"]
            .map((s) => `<option value="${s}" ${s === a.status ? "selected" : ""}>${s.replace(/_/g, " ")}</option>`)
            .join("")}
        </select>
      </td>
    </tr>`
      )
      .join("") || `<tr><td colspan="7" class="empty-state">No alerts in this window</td></tr>`;

  body.querySelectorAll(".status-select").forEach((sel) => {
    sel.addEventListener("change", async () => {
      await safeCall(() => api.updateAlertStatus(sel.dataset.id, sel.value), null);
      toast("Alert status updated");
      loadAlerts();
    });
  });

  const sensorBody = document.getElementById("sensors-body");
  sensorBody.innerHTML = sensors
    .map(
      (s) => `<tr>
      <td class="mono">${s.node_code}</td>
      <td>${s.sensor_type.replace(/_/g, " ")}</td>
      <td>${zoneName(s.zone_id)}</td>
      <td>${riskBar(s.battery_pct / 100, s.battery_pct < 25 ? "var(--red)" : "var(--teal)")}</td>
      <td>${s.is_online ? badge("active") : badge("cancelled")}</td>
    </tr>`
    )
    .join("") || `<tr><td colspan="5" class="empty-state">No sensors</td></tr>`;

  const missionBody = document.getElementById("drones-body");
  missionBody.innerHTML = missions
    .map(
      (m) => `<tr>
      <td class="mono">${m.mission_code}</td>
      <td>${zoneName(m.zone_id)}</td>
      <td>${m.pilot_name}</td>
      <td>${fmtDate(m.launched_at)}</td>
      <td>${m.duration_minutes} min &middot; ${m.altitude_m}m</td>
      <td>${m.snares_detected_count}</td>
    </tr>`
    )
    .join("") || `<tr><td colspan="6" class="empty-state">No missions logged</td></tr>`;

  const snareBody = document.getElementById("snares-body");
  snareBody.innerHTML = snares
    .map(
      (s) => `<tr>
      <td class="mono">${s.latitude.toFixed(4)}, ${s.longitude.toFixed(4)}</td>
      <td class="mono">${s.confidence_pct}%</td>
      <td>${fmtDate(s.detected_at)}</td>
      <td><button class="btn-clear-snare" data-id="${s.id}">Mark removed</button></td>
    </tr>`
    )
    .join("") || `<tr><td colspan="4" class="empty-state">No snares pending removal</td></tr>`;

  snareBody.querySelectorAll(".btn-clear-snare").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await safeCall(() => api.clearSnare(btn.dataset.id), null);
      toast("Snare marked as removed");
      loadAlerts();
    });
  });
}

async function submitManualAlert(e) {
  e.preventDefault();
  const form = e.target;
  const fd = new FormData(form);
  const zone = zoneCache.find((z) => z.id === fd.get("zone_id"));
  if (!zone) return toast("Select a zone", "error");
  const body = {
    source: "ranger_report",
    alert_type: fd.get("alert_type"),
    severity: fd.get("severity"),
    confidence_pct: 90,
    latitude: zone.center_lat + (Math.random() - 0.5) * 0.02,
    longitude: zone.center_lon + (Math.random() - 0.5) * 0.02,
    description: fd.get("description") || `Manually logged near ${zone.name}`,
  };
  await safeCall(() => api.createAlert(body), null);
  toast("Alert logged");
  form.reset();
  loadAlerts();
  loadOverview();
}

// ---------------------------------------------------------------- patrols

async function loadPatrols() {
  const [patrols, zones, rangers] = await Promise.all([
    safeCall(() => api.patrols(), []),
    Promise.resolve(zoneCache),
    Promise.resolve(rangerCache),
  ]);

  const zoneSelect = document.getElementById("patrol-zone-select");
  if (zoneSelect && !zoneSelect.dataset.filled) {
    zoneSelect.innerHTML = zoneCache.map((z) => `<option value="${z.id}">${z.name}</option>`).join("");
    zoneSelect.dataset.filled = "1";
  }
  const rangerSelect = document.getElementById("patrol-ranger-select");
  if (rangerSelect && !rangerSelect.dataset.filled) {
    rangerSelect.innerHTML =
      `<option value="">Auto-assign later</option>` +
      rangerCache.map((r) => `<option value="${r.id}">${r.full_name} (${r.station || "Unassigned"})</option>`).join("");
    rangerSelect.dataset.filled = "1";
  }

  const body = document.getElementById("patrols-body");
  body.innerHTML =
    patrols
      .map(
        (p) => `<tr>
      <td>${fmtDate(p.scheduled_date)}</td>
      <td>${zoneName(p.zone_id)}</td>
      <td>${rangerName(p.lead_ranger_id)}</td>
      <td>${p.team_size}</td>
      <td class="mono">${p.planned_distance_km ?? "\u2014"} km</td>
      <td>${riskBar(p.risk_score, "var(--red)")}</td>
      <td>${badge(p.status)}</td>
      <td>${p.waypoints.length} stops</td>
    </tr>`
      )
      .join("") || `<tr><td colspan="8" class="empty-state">No patrols yet \u2014 generate one below</td></tr>`;

  const rangerBody = document.getElementById("rangers-body");
  rangerBody.innerHTML = rangerCache
    .map(
      (r) => `<tr>
      <td class="mono">${r.badge_number}</td>
      <td>${r.full_name}</td>
      <td>${r.rank}</td>
      <td>${r.station || "\u2014"}</td>
      <td>${r.years_of_service} yrs</td>
    </tr>`
    )
    .join("");
}

async function submitPatrolGeneration(e) {
  e.preventDefault();
  const form = e.target;
  const fd = new FormData(form);
  const body = {
    zone_id: fd.get("zone_id"),
    scheduled_date: new Date(fd.get("scheduled_date")).toISOString(),
    team_size: Number(fd.get("team_size")) || 3,
    lead_ranger_id: fd.get("lead_ranger_id") || null,
    max_waypoints: Number(fd.get("max_waypoints")) || 6,
  };
  const patrol = await safeCall(() => api.generatePatrol(body), null);
  if (!patrol) return toast("Could not generate patrol route", "error");
  toast(`Route generated: ${patrol.waypoints.length} priority stops, ${patrol.planned_distance_km} km`);
  loadPatrols();

  const panel = document.getElementById("patrol-result");
  panel.innerHTML = `
    <div class="card">
      <h3>Optimized Route \u2014 ${zoneName(patrol.zone_id)}</h3>
      <table>
        <thead><tr><th>#</th><th>Stop</th><th>Coordinates</th><th>Priority</th></tr></thead>
        <tbody>
          ${patrol.waypoints
            .map(
              (w) => `<tr>
              <td>${w.sequence}</td>
              <td>${w.label}</td>
              <td class="mono">${w.latitude.toFixed(4)}, ${w.longitude.toFixed(4)}</td>
              <td>${w.priority_score}</td>
            </tr>`
            )
            .join("")}
        </tbody>
      </table>
    </div>`;
}

// ---------------------------------------------------------------- veterinary

async function loadVeterinary() {
  const cases = await safeCall(() => api.vetCases(), []);
  const animals = await safeCall(() => api.animals(), []);

  const select = document.getElementById("vet-animal-select");
  if (select && !select.dataset.filled) {
    select.innerHTML = animals.map((a) => `<option value="${a.id}">${a.tag_name} (${speciesName(a.species_id)})</option>`).join("");
    select.dataset.filled = "1";
  }

  const body = document.getElementById("vet-cases-body");
  body.innerHTML =
    cases
      .map((c) => {
        const a = animals.find((x) => x.id === c.animal_id);
        return `<tr>
        <td>${fmtDate(c.reported_at)}</td>
        <td>${a ? a.tag_name : c.animal_id}</td>
        <td>${c.condition.replace(/_/g, " ")}</td>
        <td>${badge(c.priority)}</td>
        <td>${badge(c.status)}</td>
        <td>${c.assigned_vet || "\u2014"}</td>
      </tr>`;
      })
      .join("") || `<tr><td colspan="6" class="empty-state">No veterinary cases logged</td></tr>`;
}

async function submitVetCase(e) {
  e.preventDefault();
  const form = e.target;
  const fd = new FormData(form);
  const body = {
    animal_id: fd.get("animal_id"),
    condition: fd.get("condition"),
    priority: fd.get("priority"),
    intervention_notes: fd.get("intervention_notes") || null,
  };
  await safeCall(() => api.reportVetCase(body), null);
  toast("Veterinary case reported");
  form.reset();
  loadVeterinary();
}

// ---------------------------------------------------------------- CITES

async function loadCites() {
  const permits = await safeCall(() => api.citesPermits(), []);
  const select = document.getElementById("cites-species-select");
  if (select && !select.dataset.filled) {
    select.innerHTML = speciesCache.map((s) => `<option value="${s.id}">${s.common_name}</option>`).join("");
    select.dataset.filled = "1";
  }

  const body = document.getElementById("cites-body");
  body.innerHTML =
    permits
      .map(
        (p) => `<tr>
      <td class="mono">${p.permit_number}</td>
      <td>${speciesName(p.species_id)}</td>
      <td>${p.purpose.replace(/_/g, " ")}</td>
      <td>${p.quantity} &times; ${p.unit_description}</td>
      <td>${p.destination_country}</td>
      <td>${badge(p.status)}</td>
      <td><a href="${api.citesPermitPdfUrl(p.id)}" target="_blank">Download PDF</a></td>
    </tr>`
      )
      .join("") || `<tr><td colspan="7" class="empty-state">No permits issued yet</td></tr>`;
}

async function submitCitesPermit(e) {
  e.preventDefault();
  const form = e.target;
  const fd = new FormData(form);
  const body = {
    species_id: fd.get("species_id"),
    purpose: fd.get("purpose"),
    quantity: Number(fd.get("quantity")) || 1,
    unit_description: fd.get("unit_description") || "live specimen",
    destination_country: fd.get("destination_country"),
  };
  await safeCall(() => api.createCitesPermit(body), null);
  toast("CITES permit generated");
  form.reset();
  loadCites();
}

// ---------------------------------------------------------------- community

async function loadCommunity() {
  const [members, smsLog] = await Promise.all([
    safeCall(() => api.communityMembers(), []),
    safeCall(() => api.smsAlerts(), []),
  ]);

  const zoneSelect = document.getElementById("sms-zone-select");
  if (zoneSelect && !zoneSelect.dataset.filled) {
    zoneSelect.innerHTML =
      `<option value="">All zones</option>` + zoneCache.map((z) => `<option value="${z.id}">${z.name}</option>`).join("");
    zoneSelect.dataset.filled = "1";
  }

  document.getElementById("community-count").textContent = members.length;
  const villages = [...new Set(members.map((m) => m.village).filter(Boolean))];
  document.getElementById("community-villages").textContent = villages.length;

  const body = document.getElementById("sms-body");
  body.innerHTML =
    smsLog
      .map(
        (s) => `<tr>
      <td>${fmtDate(s.sent_at)}</td>
      <td>${s.category.replace(/_/g, " ")}</td>
      <td>${s.message}</td>
      <td>${zoneName(s.zone_id)}</td>
      <td class="mono">${s.recipient_count}</td>
      <td>${badge(s.delivery_status)}</td>
    </tr>`
      )
      .join("") || `<tr><td colspan="6" class="empty-state">No broadcasts sent yet</td></tr>`;
}

async function submitBroadcast(e) {
  e.preventDefault();
  const form = e.target;
  const fd = new FormData(form);
  const body = {
    category: fd.get("category"),
    message: fd.get("message"),
    zone_id: fd.get("zone_id") || null,
  };
  const result = await safeCall(() => api.broadcastSms(body), null);
  if (!result) return toast("Broadcast failed \u2014 check recipients exist for this zone", "error");
  toast(`SMS sent to ${result.recipient_count} community members`);
  form.reset();
  loadCommunity();
}

// ---------------------------------------------------------------- fundraising

async function loadFundraising() {
  const [campaigns, donations, breakdown] = await Promise.all([
    safeCall(() => api.campaigns(), []),
    safeCall(() => api.donations(), []),
    safeCall(() => api.allocationBreakdown(), {}),
  ]);

  const campaignWrap = document.getElementById("campaigns-wrap");
  campaignWrap.innerHTML = campaigns
    .map((c) => {
      const pct = Math.min(100, Math.round((c.raised_amount_usd / c.goal_amount_usd) * 100));
      return `<div class="card">
        <h3>${c.name}</h3>
        <p class="muted">${c.description || ""}</p>
        <div class="progress-track"><div class="progress-fill" style="width:${pct}%"></div></div>
        <p class="mono" style="margin-top:8px">${fmtMoney(c.raised_amount_usd)} of ${fmtMoney(c.goal_amount_usd)} (${pct}%)</p>
      </div>`;
    })
    .join("") || `<div class="empty-state">No active campaigns</div>`;

  const ctx = document.getElementById("chart-allocation");
  const labels = Object.keys(breakdown).map((k) => k.replace(/_/g, " "));
  const values = Object.values(breakdown);
  charts.allocation?.destroy();
  if (ctx) {
    charts.allocation = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [{ data: values, backgroundColor: "#D9A441", borderRadius: 4 }],
      },
      options: {
        indexAxis: "y",
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#8FAFA0" }, grid: { color: "rgba(234,242,236,0.06)" } },
          y: { ticks: { color: "#EAF2EC" }, grid: { display: false } },
        },
      },
    });
  }

  const donorSelect = document.getElementById("donation-donor-select");
  const donors = await safeCall(() => api.donors(), []);
  if (donorSelect && !donorSelect.dataset.filled) {
    donorSelect.innerHTML = donors.map((d) => `<option value="${d.id}">${d.name}</option>`).join("");
    donorSelect.dataset.filled = "1";
  }
  const campaignSelect = document.getElementById("donation-campaign-select");
  if (campaignSelect && !campaignSelect.dataset.filled) {
    campaignSelect.innerHTML =
      `<option value="">General fund</option>` + campaigns.map((c) => `<option value="${c.id}">${c.name}</option>`).join("");
    campaignSelect.dataset.filled = "1";
  }

  const donorMap = {};
  donors.forEach((d) => (donorMap[d.id] = d));

  const body = document.getElementById("donations-body");
  body.innerHTML =
    donations
      .slice(0, 25)
      .map(
        (d) => `<tr>
      <td>${fmtDate(d.donated_at)}</td>
      <td>${donorMap[d.donor_id]?.name || d.donor_id}</td>
      <td class="mono">${fmtMoney(d.amount_usd)}</td>
      <td>${d.allocation.replace(/_/g, " ")}</td>
    </tr>`
      )
      .join("") || `<tr><td colspan="4" class="empty-state">No donations recorded</td></tr>`;
}

async function submitDonation(e) {
  e.preventDefault();
  const form = e.target;
  const fd = new FormData(form);
  const body = {
    donor_id: fd.get("donor_id"),
    campaign_id: fd.get("campaign_id") || null,
    amount_usd: Number(fd.get("amount_usd")),
    allocation: fd.get("allocation"),
  };
  await safeCall(() => api.recordDonation(body), null);
  toast("Donation recorded");
  form.reset();
  loadFundraising();
}

// ---------------------------------------------------------------- init

async function checkConnection() {
  const dot = document.getElementById("conn-dot");
  const label = document.getElementById("conn-label");
  try {
    await api.health();
    dot.className = "conn-dot online";
    label.textContent = "API connected";
  } catch (e) {
    dot.className = "conn-dot offline";
    label.textContent = "API unreachable";
  }
}

async function init() {
  document.querySelectorAll(".nav-item").forEach((item) => {
    item.addEventListener("click", () => setActiveView(item.dataset.view));
  });

  document.getElementById("form-alert")?.addEventListener("submit", submitManualAlert);
  document.getElementById("form-patrol")?.addEventListener("submit", submitPatrolGeneration);
  document.getElementById("form-vet")?.addEventListener("submit", submitVetCase);
  document.getElementById("form-cites")?.addEventListener("submit", submitCitesPermit);
  document.getElementById("form-sms")?.addEventListener("submit", submitBroadcast);
  document.getElementById("form-donation")?.addEventListener("submit", submitDonation);

  await checkConnection();
  zoneCache = await safeCall(() => api.habitatZones(), []);
  speciesCache = await safeCall(() => api.species(), []);
  rangerCache = await safeCall(() => api.rangers(), []);

  const startView = window.location.hash?.replace("#", "") || "view-overview";
  setActiveView(document.getElementById(startView) ? startView : "view-overview");

  setInterval(checkConnection, 20000);
}

document.addEventListener("DOMContentLoaded", init);
