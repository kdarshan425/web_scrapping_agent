// apiClient.js — all HTTP calls to the FastAPI backend live here.
import { getSettings } from "./storage.js";

/** POST /api/v1/chat. Returns the ChatResponse JSON. */
export async function sendChat({ sessionId, question, page }) {
  const { backendUrl, apiKey } = await getSettings();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 90000); // 90s timeout

  try {
    const res = await fetch(`${backendUrl}/api/v1/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
      body: JSON.stringify({ session_id: sessionId, question, page }),
      signal: controller.signal,
    });
    if (res.status === 401) throw new Error("Wrong API key. Open ⚙ Settings and check it.");
    if (!res.ok) throw new Error(`Server error (${res.status}). Check backend logs.`);
    return await res.json();
  } catch (err) {
    if (err.name === "AbortError") throw new Error("Request timed out.");
    if (err instanceof TypeError) throw new Error("Cannot reach backend. Is it running? Check ⚙ Settings URL.");
    throw err;
  } finally {
    clearTimeout(timer);
  }
}
