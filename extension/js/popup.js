// popup.js — the controller: wires buttons to storage / page reader / API / UI.
import { sendChat } from "./apiClient.js";
import { readActivePage } from "./pageReader.js";
import { getSessionId, getSettings, saveSettings, setSessionId } from "./storage.js";
import { addMessage, addMeta, clearMessages } from "./ui.js";

const $ = (id) => document.getElementById(id);
let page = null;      // { url, title, text } of the current tab
let sessionId = null; // backend chat session for this page

async function init() {
  try {
    page = await readActivePage();
    $("page-title").textContent = page.title || page.url;
    sessionId = await getSessionId(page.url);
    addMessage("assistant", sessionId
      ? "Welcome back! Continue asking about this page."
      : "Hi! I've read this page. Ask me anything about it.");
  } catch (err) {
    $("page-title").textContent = "Page not readable";
    addMessage("error", err.message);
  }
  const s = await getSettings();
  $("in-url").value = s.backendUrl;
  $("in-key").value = s.apiKey;
  if (!s.apiKey) $("settings").hidden = false; // first run: ask for the API key
}

async function onSend() {
  const question = $("in-question").value.trim();
  if (!question || !page) return;
  $("in-question").value = "";
  addMessage("user", question);
  $("btn-send").disabled = true;
  const thinking = addMessage("assistant", "Thinking…");

  try {
    const data = await sendChat({ sessionId, question, page });
    sessionId = data.session_id;
    await setSessionId(page.url, sessionId);
    thinking.remove();
    addMeta(addMessage("assistant", data.answer), data);
  } catch (err) {
    thinking.remove();
    addMessage("error", err.message);
  } finally {
    $("btn-send").disabled = false;
    $("in-question").focus();
  }
}

$("btn-send").addEventListener("click", onSend);
$("in-question").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); onSend(); }
});
$("btn-settings").addEventListener("click", () => ($("settings").hidden = !$("settings").hidden));
$("btn-save").addEventListener("click", async () => {
  await saveSettings({ backendUrl: $("in-url").value.trim(), apiKey: $("in-key").value.trim() });
  $("settings").hidden = true;
  addMessage("assistant", "Settings saved ✅");
});
$("btn-new").addEventListener("click", async () => {
  if (page) await setSessionId(page.url, null);
  sessionId = null;
  clearMessages();
  addMessage("assistant", "New chat started. Ask me about this page.");
});

init();
