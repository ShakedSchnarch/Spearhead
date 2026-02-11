const fallbackBase =
  typeof window !== "undefined"
    ? window.location.origin.replace(/\/$/, "")
    : "http://localhost:8000";

export class ApiError extends Error {
  constructor(message, status, detail) {
    super(message || "API error");
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

const normalizeBase = (baseUrl) => (baseUrl || fallbackBase).replace(/\/$/, "");

const buildQuery = (params) => {
  if (!params) return "";
  const entries = Object.entries(params).filter(
    ([, value]) => value !== undefined && value !== null && value !== "",
  );
  if (!entries.length) return "";
  const qs = new URLSearchParams();
  entries.forEach(([key, value]) => qs.append(key, String(value)));
  return `?${qs.toString()}`;
};

export const createApiClient = ({
  baseUrl,
  token,
  oauthSession,
  onUnauthorized,
} = {}) => {
  const resolvedBase = normalizeBase(baseUrl);
  const authHeaders = token ? { Authorization: `Bearer ${token}` } : {};
  const sessionHeader = oauthSession || token;

  const request = async (
    path,
    { method = "GET", headers, body, responseType = "json", signal } = {},
  ) => {
    const res = await fetch(`${resolvedBase}${path}`, {
      method,
      headers: {
        ...authHeaders,
        ...(sessionHeader ? { "X-OAuth-Session": sessionHeader } : {}),
        ...(headers || {}),
      },
      body,
      signal,
    });

    if (res.status === 401) {
      if (onUnauthorized) onUnauthorized();
      throw new ApiError("unauthorized", 401);
    }

    if (!res.ok) {
      let detail;
      try {
        detail = await res.json();
      } catch {
        try {
          detail = await res.text();
        } catch {
          detail = null;
        }
      }
      throw new ApiError(
        detail?.detail || detail?.message || detail || res.statusText,
        res.status,
        detail,
      );
    }

    if (responseType === "blob") return res.blob();
    if (responseType === "text") return res.text();
    if (responseType === "raw") return res;
    return res.json();
  };

  const getJson = (path, params, options = {}) =>
    request(`${path}${buildQuery(params)}`, {
      ...options,
      method: options.method || "GET",
    });

  const postJson = (path, body, options = {}) =>
    request(path, {
      ...options,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      body: JSON.stringify(body || {}),
    });

  return {
    baseUrl: resolvedBase,
    getJson,
    postJson,
    health: (signal) => getJson("/health", null, { signal }),

    // v1 responses-only API
    ingestFormEvent: (event, signal) =>
      postJson("/v1/ingestion/forms/events", event, { signal }),
    getWeeks: (params, signal) =>
      getJson("/v1/metadata/weeks", params, { signal }),
    getOverview: (params, signal) =>
      getJson("/v1/metrics/overview", params, { signal }),
    getPlatoonMetrics: (platoon, params, signal) =>
      getJson(`/v1/metrics/platoons/${encodeURIComponent(platoon)}`, params, {
        signal,
      }),
    getTankMetrics: (params, signal) =>
      getJson("/v1/metrics/tanks", params, { signal }),
    getGaps: (params, signal) =>
      getJson("/v1/queries/gaps", params, { signal }),
    getTrends: (params, signal) =>
      getJson("/v1/queries/trends", params, { signal }),
    searchResponses: (params, signal) =>
      getJson("/v1/queries/search", params, { signal }),

    // command views (battalion/company hierarchy)
    getBattalionView: (params, signal) =>
      getJson("/v1/views/battalion", params, { signal }),
    getCompanyView: (company, params, signal) =>
      getJson(`/v1/views/companies/${encodeURIComponent(company)}`, params, {
        signal,
      }),
    getCompanyTanks: (company, params, signal) =>
      getJson(`/v1/views/companies/${encodeURIComponent(company)}/tanks`, params, {
        signal,
      }),
    getCompanySectionTanks: (company, section, params, signal) =>
      getJson(
        `/v1/views/companies/${encodeURIComponent(company)}/sections/${encodeURIComponent(section)}/tanks`,
        params,
        { signal },
      ),
  };
};
