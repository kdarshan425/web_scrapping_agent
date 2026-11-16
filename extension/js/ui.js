// ui.js — everything that draws on screen. No network or storage code here.
const box = document.getElementById("messages");

/** Escape HTML first (security!), then apply a tiny markdown subset. */
function renderMarkdown(text) {
  const escaped = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return escaped
    .split(/\n{2,}/)
    .map((p) =>
      "<p>" +
      p.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`(.+?)`/g, "<code>$1</code>")
       .replace(/^[-*] (.+)$/gm, "• $1").replace(/\n/g, "<br>") + "</p>")
    .join("");
}

export function addMessage(role, text) {
  const el = document.createElement("div");
  el.className = `msg ${role}`;
  el.innerHTML = renderMarkdown(text); // safe: text was escaped above
  box.appendChild(el);
  box.scrollTop = box.scrollHeight;
  return el;
}

/** Small footer under an assistant answer: model, cache, guardrail flags, policy sources. */
export function addMeta(el, data) {
  const meta = document.createElement("div");
  meta.className = "meta";
  const parts = [data.cached ? "⚡ cached (0 tokens)" : `${data.model_used} · ${data.usage.tokens_in + data.usage.tokens_out} tokens`];
  if (data.guardrail_flags.length) parts.push(`<span class="flag">🛡 ${data.guardrail_flags.join(", ")}</span>`);
  meta.innerHTML = parts.join(" · ");
  el.appendChild(meta);

  if (data.sources.length) {
    const d = document.createElement("details");
    d.className = "sources";
    d.innerHTML = `<summary>📄 ${data.sources.length} company policy source(s)</summary>`;
    data.sources.forEach((s) => {
      const row = document.createElement("div");
      row.textContent = `[${s.label}] ${s.filename}: ${s.snippet}…`; // textContent = always safe
      d.appendChild(row);
    });
    el.appendChild(d);
  }
}

export const clearMessages = () => (box.innerHTML = "");
