// storage.js — the ONLY file that touches browser storage (repository pattern for the extension).
export const api = globalThis.browser ?? globalThis.chrome; // Safari/Firefox use `browser`, Chrome/Edge use `chrome`

const DEFAULTS = { backendUrl: "http://localhost:8000", apiKey: "" };

/** Read backend URL + API key. */
export async function getSettings() {
  const data = await api.storage.local.get(["backendUrl", "apiKey"]);
  return { ...DEFAULTS, ...data };
}

/** Save backend URL + API key. */
export async function saveSettings({ backendUrl, apiKey }) {
  await api.storage.local.set({ backendUrl: backendUrl.replace(/\/+$/, ""), apiKey });
}

/** One chat session per page URL, so re-opening the popup continues the same conversation. */
export async function getSessionId(pageUrl) {
  const { sessions = {} } = await api.storage.local.get("sessions");
  return sessions[pageUrl] ?? null;
}

export async function setSessionId(pageUrl, sessionId) {
  const { sessions = {} } = await api.storage.local.get("sessions");
  if (sessionId) sessions[pageUrl] = sessionId; else delete sessions[pageUrl];
  await api.storage.local.set({ sessions });
}
