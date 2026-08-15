/* Thin fetch wrapper around the Wildlife Guardian API. */

const API_BASE = window.WILDLIFE_GUARDIAN_API_BASE || "http://localhost:8000/api/v1";

async function apiRequest(path, { method = "GET", body = null, params = null } = {}) {
  let url = `${API_BASE}${path}`;
  if (params) {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "")
    ).toString();
    if (qs) url += `?${qs}`;
  }

  const opts = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(url, opts);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = await res.json();
      detail = j.detail || detail;
    } catch (_) { /* ignore */ }
    throw new Error(`${res.status}: ${detail}`);
  }
  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) return res.json();
  return res;
}

const api = {
  health: () => apiRequest("/health"),

  species: () => apiRequest("/species"),
  animals: (params) => apiRequest("/animals", { params }),
  animal: (id) => apiRequest(`/animals/${id}`),
  animalHistory: (id, limit = 200) => apiRequest(`/animals/${id}/history`, { params: { limit } }),
  predictMovement: (id) => apiRequest(`/animals/${id}/predict`),
  liveTracking: () => apiRequest("/tracking/live"),
  habitatZones: () => apiRequest("/habitat-zones"),
  zoneSatellite: (id) => apiRequest(`/habitat-zones/${id}/satellite`),

  sensors: (params) => apiRequest("/sensors", { params }),
  alerts: (params) => apiRequest("/alerts", { params }),
  createAlert: (body) => apiRequest("/alerts", { method: "POST", body }),
  updateAlertStatus: (id, status) => apiRequest(`/alerts/${id}/status`, { method: "PATCH", body: { status } }),
  droneMissions: () => apiRequest("/drone-missions"),
  snares: (params) => apiRequest("/snares", { params }),
  clearSnare: (id, rangerId) => apiRequest(`/snares/${id}/clear`, { method: "PATCH", params: { ranger_id: rangerId } }),

  rangers: (params) => apiRequest("/rangers", { params }),
  patrols: (params) => apiRequest("/patrols", { params }),
  generatePatrol: (body) => apiRequest("/patrols/generate", { method: "POST", body }),
  updatePatrolStatus: (id, status) => apiRequest(`/patrols/${id}/status`, { method: "PATCH", params: { status } }),

  vetCases: (params) => apiRequest("/vet-cases", { params }),
  reportVetCase: (body) => apiRequest("/vet-cases", { method: "POST", body }),
  updateVetCaseStatus: (id, status, assignedVet) =>
    apiRequest(`/vet-cases/${id}/status`, { method: "PATCH", params: { status, assigned_vet: assignedVet } }),

  citesPermits: () => apiRequest("/cites-permits"),
  createCitesPermit: (body) => apiRequest("/cites-permits", { method: "POST", body }),
  citesPermitPdfUrl: (id) => `${API_BASE}/cites-permits/${id}/pdf`,

  communityMembers: (params) => apiRequest("/community-members", { params }),
  smsAlerts: () => apiRequest("/sms-alerts"),
  broadcastSms: (body) => apiRequest("/sms-alerts/broadcast", { method: "POST", body }),

  campaigns: (params) => apiRequest("/campaigns", { params }),
  donors: () => apiRequest("/donors"),
  donations: (params) => apiRequest("/donations", { params }),
  recordDonation: (body) => apiRequest("/donations", { method: "POST", body }),
  allocationBreakdown: () => apiRequest("/fundraising/allocation-breakdown"),

  dashboardSummary: () => apiRequest("/dashboard/summary"),
};
