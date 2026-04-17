/**
 * DOM bindings for /shows/[id].
 *
 * Reads `data-show-id` from the root element, wires up the WsClient, and
 * renders each event type into the match panel + chat panel.
 */

import { WsClient } from "./ws-client";

function el<T extends HTMLElement>(id: string): T {
  return document.getElementById(id)! as T;
}

function esc(s: string): string {
  return s.replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!
  );
}

function fmtTime(ms: number): string {
  return new Date(ms).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function hpColor(pct: number): string {
  if (pct > 70) return "var(--color-green)";
  if (pct > 40) return "var(--color-gold)";
  return "var(--color-red)";
}

export function initShowUI(): void {
  const root = document.querySelector("[data-show-id]");
  if (!root) return;
  const showId = root.getAttribute("data-show-id")!;

  const matchArea = el<HTMLDivElement>("match-area");
  const chatLog = el<HTMLDivElement>("chat-log");
  const chatForm = el<HTMLFormElement>("chat-form");
  const chatInput = el<HTMLInputElement>("chat-input");
  const handleEl = el<HTMLSpanElement>("my-handle");
  const statusEl = el<HTMLSpanElement>("conn-status");

  let myUserId = "";
  const client = new WsClient(showId);

  // ---- Connection status ----
  client.on("_connected", () => {
    statusEl.textContent = "connected";
    statusEl.className = "text-green text-xs";
  });
  client.on("_disconnected", () => {
    statusEl.textContent = "reconnecting...";
    statusEl.className = "text-red text-xs";
  });

  // ---- Hello ----
  client.on("hello", (p) => {
    myUserId = p.user_id;
    handleEl.textContent = p.handle;
    handleEl.className = p.is_authed ? "text-green font-bold" : "text-gold font-bold";

    // Replay show events that already fired (late-joiner / refresh backfill).
    (p.events || []).forEach((ev: any) => {
      client.replay(ev.kind, ev.payload);
    });

    // Chat backfill after events so chat appears below show content.
    (p.backfill || []).forEach((m: any) => appendChat(m));
  });

  // ---- Chat ----
  function appendChat(m: any): void {
    const isMine = m.user_id === myUserId;
    const div = document.createElement("div");
    div.className = "py-0.5 text-sm";
    div.innerHTML =
      `<span class="text-muted text-xs">${fmtTime(m.at_ms)}</span> ` +
      `<span class="${isMine ? "text-gold" : "text-text"} font-semibold">${esc(m.handle)}</span>` +
      `${m.is_authed ? '<span class="text-green text-xs ml-0.5">✓</span>' : ""}` +
      `: ${esc(m.text)}`;
    chatLog.appendChild(div);
    chatLog.scrollTop = chatLog.scrollHeight;
  }
  client.on("chat.message", appendChat);

  // ---- Vignettes ----
  client.on("vignette.drop", (p) => {
    const div = document.createElement("div");
    div.className = "border-l-3 border-gold bg-bg-elevated p-3 my-2 rounded-r";
    div.innerHTML =
      `<div class="text-gold font-bold text-sm mb-1">${esc(p.title || "")}</div>` +
      (p.text ? `<div class="text-sm leading-relaxed">${esc(p.text)}</div>` : "") +
      (p.ref ? `<div class="text-muted text-xs mt-1">→ ${esc(p.ref)}</div>` : "");
    matchArea.appendChild(div);
    matchArea.scrollTop = matchArea.scrollHeight;
  });

  // ---- Match start ----
  client.on("match.start", (p) => {
    const div = document.createElement("div");
    div.className = "border border-green bg-[#0d1e0d] p-3 my-2 rounded text-green font-bold text-sm";
    div.innerHTML = `⚔ ${esc(p.title || p.match_id)} — ${(p.dinos || []).join(" vs ")}`;
    matchArea.appendChild(div);

    // Create HP bars container
    const hpDiv = document.createElement("div");
    hpDiv.id = `hp-${p.match_id}`;
    hpDiv.className = "flex gap-4 my-2 text-xs";
    (p.dinos || []).forEach((slug: string) => {
      hpDiv.innerHTML +=
        `<div class="flex-1">` +
        `<div class="flex justify-between mb-1"><span class="font-bold text-text">${esc(slug)}</span>` +
        `<span id="hp-val-${p.match_id}-${slug}" class="text-muted">100</span></div>` +
        `<div class="hp-bar"><div id="hp-fill-${p.match_id}-${slug}" class="hp-bar-fill" ` +
        `style="width:100%;background:var(--color-green)"></div></div></div>`;
    });
    matchArea.appendChild(hpDiv);
    matchArea.scrollTop = matchArea.scrollHeight;
  });

  // ---- Match round ----
  client.on("match.round", (p) => {
    // Update HP bars
    if (p.hp) {
      for (const [slug, val] of Object.entries(p.hp)) {
        const v = val as number;
        const fill = document.getElementById(`hp-fill-${p.match_id}-${slug}`);
        const label = document.getElementById(`hp-val-${p.match_id}-${slug}`);
        if (fill) {
          fill.style.width = `${Math.max(0, v)}%`;
          fill.style.background = hpColor(v);
        }
        if (label) label.textContent = v.toFixed(1);
      }
    }

    const div = document.createElement("div");
    div.className = "border-l-2 border-border pl-3 my-1.5 font-mono text-xs";
    div.innerHTML =
      `<div class="text-muted mb-0.5">Round ${p.round}</div>` +
      `<div class="whitespace-pre-wrap text-text leading-relaxed">${esc(p.narration || "")}</div>`;
    matchArea.appendChild(div);
    matchArea.scrollTop = matchArea.scrollHeight;
  });

  // ---- Match end ----
  client.on("match.end", (p) => {
    const hp = p.final_hp
      ? Object.entries(p.final_hp).map(([k, v]) => `${k}: ${(v as number).toFixed(1)}`).join("  ")
      : "";
    const div = document.createElement("div");
    div.className = "border border-red bg-[#1e0d0d] p-3 my-2 rounded text-red font-bold text-sm";
    div.innerHTML =
      `★ ${esc(p.winner)} defeats ${esc(p.loser)} by ${esc(p.method)}` +
      (hp ? ` <span class="font-normal text-muted text-xs">(${esc(hp)})</span>` : "");
    matchArea.appendChild(div);
    matchArea.scrollTop = matchArea.scrollHeight;
  });

  // ---- Error ----
  client.on("error", (p) => {
    const div = document.createElement("div");
    div.className = "text-red text-xs py-0.5";
    div.textContent = `error: ${p?.code || "unknown"}`;
    chatLog.appendChild(div);
  });

  // ---- Chat send ----
  chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text) return;
    client.send("chat.send", { text });
    chatInput.value = "";
  });

  // ---- Go ----
  client.connect();
}
