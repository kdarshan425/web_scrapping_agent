// pageReader.js — reads the full visible text of the active tab.
import { api } from "./storage.js";

const MAX_CHARS = 120000; // keep in sync with backend MAX_PAGE_CHARS

/** Runs INSIDE the web page (must be self-contained). */
function extractInPage() {
  return {
    url: location.href,
    title: document.title,
    text: (document.body?.innerText ?? "").trim(),
  };
}

/** Returns { url, title, text } for the current tab. */
export async function readActivePage() {
  const [tab] = await api.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) throw new Error("No active tab found.");
  try {
    const [result] = await api.scripting.executeScript({ target: { tabId: tab.id }, func: extractInPage });
    const page = result.result;
    // Collapse whitespace + cap size (saves bandwidth and tokens)
    page.text = page.text.replace(/[ \t]+/g, " ").replace(/\n{3,}/g, "\n\n").slice(0, MAX_CHARS);
    return page;
  } catch {
    throw new Error("This page can't be read (browser-internal or protected page).");
  }
}
